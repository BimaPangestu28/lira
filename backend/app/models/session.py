"""Session data models."""

from enum import Enum
from typing import Literal
from uuid import UUID, uuid4

from pydantic import BaseModel, Field


class AgentMode(str, Enum):
    """Available agent interaction modes."""

    FREE_TALK = "free_talk"
    CORRECTIVE = "corrective"
    ROLEPLAY = "roleplay"
    GUIDED = "guided"


class CEFRLevel(str, Enum):
    """CEFR English proficiency levels."""

    A2 = "A2"
    B1 = "B1"
    B2 = "B2"
    C1 = "C1"


class Message(BaseModel):
    """A single conversation message."""

    role: Literal["user", "assistant"]
    text: str


class SessionMetrics(BaseModel):
    """Metrics tracked during a session."""

    words_spoken: int = 0
    mistakes_detected: int = 0


class Session(BaseModel):
    """Complete session state."""

    session_id: UUID = Field(default_factory=uuid4)
    mode: AgentMode = AgentMode.FREE_TALK
    level: CEFRLevel = CEFRLevel.B1
    history: list[Message] = Field(default_factory=list)
    metrics: SessionMetrics = Field(default_factory=SessionMetrics)


class SessionCreate(BaseModel):
    """Request body for creating a new session."""

    mode: AgentMode = AgentMode.FREE_TALK
    level: CEFRLevel = CEFRLevel.B1


class SessionResponse(BaseModel):
    """Response containing session info and LiveKit token."""

    session_id: UUID
    mode: AgentMode
    level: CEFRLevel
    livekit_token: str
    livekit_url: str
