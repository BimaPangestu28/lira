"""LiveKit agent worker that handles room connections."""

import asyncio
import signal

from livekit import api, rtc

from app.core.config import get_settings
from app.agents.voice_agent import VoiceAgent


class AgentWorker:
    """
    Worker process that connects to LiveKit rooms and spawns voice agents.

    Listens for room events and creates an agent for each active session.
    """

    def __init__(self):
        settings = get_settings()
        self.livekit_url = settings.livekit_url
        self.api_key = settings.livekit_api_key
        self.api_secret = settings.livekit_api_secret
        self.agents: dict[str, VoiceAgent] = {}
        self._running = False

    async def connect_to_room(
        self,
        room_name: str,
        mode: str = "free_talk",
        level: str = "B1",
    ) -> VoiceAgent:
        """
        Connect to a LiveKit room and create a voice agent.

        @param room_name - Name of the room to join
        @param mode - Conversation mode
        @param level - CEFR level
        @returns VoiceAgent instance
        """
        room = rtc.Room()

        # Generate token for agent
        token = (
            api.AccessToken(self.api_key, self.api_secret)
            .with_identity(f"agent-{room_name}")
            .with_name("LIRA Agent")
            .with_grants(
                api.VideoGrants(
                    room_join=True,
                    room=room_name,
                    can_publish=True,
                    can_subscribe=True,
                )
            )
            .to_jwt()
        )

        # Connect to room
        await room.connect(self.livekit_url, token)
        print(f"Agent connected to room: {room_name}")
        print(f"Mode: {mode}, Level: {level}")

        # Create and start voice agent
        agent = VoiceAgent(
            room=room,
            mode=mode,
            level=level,
            on_transcription=lambda t, f: print(f"[STT] {'✓' if f else '...'} {t}"),
            on_response=lambda r: print(f"[Agent] {r}"),
        )
        await agent.start()

        self.agents[room_name] = agent
        return agent

    async def disconnect_from_room(self, room_name: str):
        """
        Disconnect agent from a room.

        @param room_name - Name of the room to leave
        """
        agent = self.agents.pop(room_name, None)
        if agent:
            await agent.stop()
            await agent.room.disconnect()
            print(f"Agent disconnected from room: {room_name}")

    async def run(self):
        """Run the worker (for standalone execution)."""
        self._running = True
        print("Agent worker started. Waiting for room connections...")

        # Keep running until stopped
        while self._running:
            await asyncio.sleep(1)

    def stop(self):
        """Stop the worker."""
        self._running = False


async def run_worker():
    """Entry point for running the agent worker."""
    worker = AgentWorker()

    # Handle shutdown signals
    loop = asyncio.get_event_loop()
    for sig in (signal.SIGINT, signal.SIGTERM):
        loop.add_signal_handler(sig, worker.stop)

    await worker.run()


if __name__ == "__main__":
    asyncio.run(run_worker())
