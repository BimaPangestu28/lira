"""Agent manager for handling multiple voice agent sessions."""

import asyncio
from uuid import UUID

from app.agents.worker import AgentWorker


class AgentManager:
    """
    Singleton manager for voice agent lifecycle.

    Handles spawning and cleaning up agents for sessions.
    """

    _instance: "AgentManager | None" = None
    _worker: AgentWorker | None = None

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._worker = AgentWorker()
        return cls._instance

    @property
    def worker(self) -> AgentWorker:
        if self._worker is None:
            self._worker = AgentWorker()
        return self._worker

    async def spawn_agent(self, session_id: UUID, mode: str = "free_talk", level: str = "B1"):
        """
        Spawn a voice agent for a session.

        @param session_id - Session UUID
        @param mode - Conversation mode
        @param level - CEFR level
        """
        room_name = f"lira-{session_id}"
        await self.worker.connect_to_room(
            room_name,
            session_id=session_id,
            mode=mode,
            level=level,
        )

    async def stop_agent(self, session_id: UUID):
        """
        Stop and cleanup agent for a session.

        @param session_id - Session UUID
        """
        room_name = f"lira-{session_id}"
        await self.worker.disconnect_from_room(room_name)

    def get_agent(self, session_id: UUID):
        """
        Get the voice agent for a session.

        @param session_id - Session UUID
        @returns VoiceAgent or None
        """
        room_name = f"lira-{session_id}"
        return self.worker.agents.get(room_name)


# Global instance
agent_manager = AgentManager()
