from dotenv import load_dotenv
import logging
from logging_config import setup_logging
from livekit import agents, rtc
from livekit.agents import AgentSession, Agent, RoomInputOptions, RoomOutputOptions
from livekit.plugins import (
    noise_cancellation,
)
from uuid import uuid4
from livekit.plugins.turn_detector.english import EnglishModel
from livekit.plugins import (groq, cartesia, deepgram, silero, google)
from instructions import AGENT_INSTRUCTION, SESSION_INSTRUCTION
from tools import check_membership
import tools


load_dotenv()
setup_logging()
logger = logging.getLogger("groq-agent")


class Assistant(Agent):
    def __init__(self, instructions: str, room: rtc.Room) -> None:
        """
        super().__init__(
            instructions=instructions,
            llm=groq.LLM(model="llama3-8b-8192"),
            stt=deepgram.STT(),
            tts=cartesia.TTS(
                model="sonic-2",
                speed="fast",
                voice="bf0a246a-8642-498a-9950-80c35e9276b5",
            ),
            vad=silero.VAD.load(),
            turn_detection=EnglishModel(),
            tools=[
                get_weather,
                search_web,
                check_membership
            ],

        )
        """

        """
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
                check_membership
            ],

        )
        self.session_id = str(uuid4())



async def entrypoint(ctx: agents.JobContext):

    await ctx.connect()


    logger.info(f"Connected to room: {ctx.room.name}")
    logger.info(f"Local participant: {ctx.room.local_participant.identity}")
    if len(ctx.room.remote_participants) == 0:
        logger.info("No remote participants in room, exiting")
        return
    logger.info(f"Found {len(ctx.room.remote_participants)} remote participants")


    session = AgentSession()
    agent = Assistant(instructions=AGENT_INSTRUCTION, room=ctx.room)

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
    tools.current_phone_number = "9474414995"

    logging.info(f"Session ID stored globally: {agent.session_id}")
    
    await session.start(
        room=ctx.room,
        agent=agent,
        room_input_options=room_input,
        room_output_options=room_output
    )

    await session.generate_reply(
        instructions=SESSION_INSTRUCTION,
    )


if __name__ == "__main__":
    agents.cli.run_app(agents.WorkerOptions(entrypoint_fnc=entrypoint))