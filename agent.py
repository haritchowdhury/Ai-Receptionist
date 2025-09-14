from dotenv import load_dotenv
import logging
from livekit import agents, rtc
from livekit.agents import AgentSession, Agent, RoomInputOptions, RoomOutputOptions
from livekit.plugins import (
    noise_cancellation,
)
from uuid import uuid4
from livekit.plugins.turn_detector.english import EnglishModel
from livekit.plugins import (groq, cartesia, deepgram, silero, google)
import asyncio
import os
from upstash_vector import Index

from tools import query_knowledge_base, text_supervisor
from utils import get_huggingface_embedding, AGENT_INSTRUCTION, SESSION_INSTRUCTION, setup_logging
import tools
from dbDrivers.session_operations import SessionOperations




load_dotenv()
logger = logging.getLogger("groq-agent")
Member = SessionOperations()


class Assistant(Agent):
    def __init__(self, instructions: str, room: rtc.Room) -> None:
        """
        """
        
        super().__init__(
            instructions=instructions,
            llm=groq.LLM(model="moonshotai/kimi-k2-instruct-0905"),
            stt=deepgram.STT(),
            tts=cartesia.TTS(
                model="sonic-2",
                speed="fast",
                voice="bf0a246a-8642-498a-9950-80c35e9276b5",
            ),
            vad=silero.VAD.load(),
            turn_detection=EnglishModel(),
            tools=[
                query_knowledge_base,
                text_supervisor
            ],

        )
        
        

        """
        super().__init__(
            instructions=instructions,
            llm=google.beta.realtime.RealtimeModel(
            voice="Aoede",
            temperature=0.8,
        ),
        vad=silero.VAD.load(),
        turn_detection = EnglishModel(),
        tools=[
                query_knowledge_base,
                text_supervisor
            ],

        )
        """
        self.session_id = str(uuid4())
        setup_logging(self.session_id)

    async def _pre_warm_services(self):
        """Pre-warm HuggingFace and Upstash services to avoid cold starts"""
        try:
            logging.info("Pre-warming serverless functions...")

            # Pre-warm HuggingFace embedding API
            hf_api_key = os.getenv("HUGGINGFACE_API_KEY")
            if hf_api_key:
                test_embedding = get_huggingface_embedding("test query", hf_api_key)
                logging.info("HuggingFace API pre-warmed successfully")
            else:
                logging.warning("HUGGINGFACE_API_KEY not found, skipping HF pre-warming")

            # Pre-warm Upstash Vector DB
            vector_client = Index(
                url=os.getenv("UPSTASH_VECTOR_REST_URL"),
                token=os.getenv("UPSTASH_VECTOR_REST_TOKEN")
            )
            # Make a simple test query with a dummy vector (384 dimensions for bge-small-en-v1.5)
            dummy_vector = [0.1] * 384
            test_results = vector_client.query(
                vector=dummy_vector,
                top_k=1,
                namespace=os.getenv("NAMESPACE")
            )
            logging.info("Upstash Vector DB pre-warmed successfully")

        except Exception as e:
            logging.warning(f"Pre-warming failed (non-critical): {e}")



async def entrypoint(ctx: agents.JobContext):

    await ctx.connect()

    # Caller's number
    phone_number = "+555-9183746"


    logger.info(f"Connected to room: {ctx.room.name}")
    logger.info(f"Local participant: {ctx.room.local_participant.identity}")
    if len(ctx.room.remote_participants) == 0:
        logger.info("No remote participants in room, exiting")
        return
    logger.info(f"Found {len(ctx.room.remote_participants)} remote participants")


    session = AgentSession()
    agent = Assistant(instructions=AGENT_INSTRUCTION, room=ctx.room)

    # Pre-warm serverless functions before starting session
    await agent._pre_warm_services()

    room_input = RoomInputOptions(
            # - For telephony applications, use `BVCTelephony` for best results
            audio_enabled=True,
            #video_enabled=True,
            noise_cancellation=noise_cancellation.BVC(),
        )
    room_output = RoomOutputOptions(
        audio_enabled=True,
        transcription_enabled=True
    )
    
    
    # Store session_id in global variable for access in tools
    tools.current_session_id = agent.session_id
    tools.current_phone_number = phone_number


    logging.info(f"Session ID stored globally: {agent.session_id}")
    
    await session.start(
        room=ctx.room,
        agent=agent,
        room_input_options=room_input,
        room_output_options=room_output
    )
    
    MemberCreated = Member.add_member_session(phone_number, agent.session_id)
    if not MemberCreated:
        logging.info(f"Failed to create session for: {agent.session_id}")

    await session.generate_reply(
        instructions=SESSION_INSTRUCTION,
    )


if __name__ == "__main__":
    agents.cli.run_app(agents.WorkerOptions(
        entrypoint_fnc=entrypoint,
    ))