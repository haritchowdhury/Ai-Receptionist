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
from livekit.plugins import (groq, cartesia, deepgram, silero)
from instructions import AGENT_INSTRUCTION, SESSION_INSTRUCTION

load_dotenv()
setup_logging()
logger = logging.getLogger("groq-agent")

class Assistant(Agent):
    def __init__(self, instructions: str, room: rtc.Room) -> None:
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
            # No tools for testing
        )
        self.session_id = str(uuid4())

async def entrypoint(ctx: agents.JobContext):
    await ctx.connect()
    logger.info(f"Connected to room: {ctx.room.name}")

    if len(ctx.room.remote_participants) == 0:
        logger.info("No remote participants in room, exiting")
        return

    session = AgentSession()
    agent = Assistant(instructions=AGENT_INSTRUCTION, room=ctx.room)

    room_input = RoomInputOptions(
        audio_enabled=True,
        noise_cancellation=noise_cancellation.BVC(),
    )
    room_output = RoomOutputOptions(
        audio_enabled=True,
        transcription_enabled=True
    )

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