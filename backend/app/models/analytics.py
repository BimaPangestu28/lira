"""Analytics and user profile data models."""

from datetime import datetime
from uuid import UUID, uuid4

from pydantic import BaseModel, Field

from app.models.session import AgentMode, CEFRLevel


class SessionAnalytics(BaseModel):
    """Detailed analytics for a single session."""

    session_id: UUID
    user_id: str | None = None
    mode: AgentMode
    level: CEFRLevel

    # Timing
    started_at: datetime = Field(default_factory=datetime.utcnow)
    ended_at: datetime | None = None
    duration_seconds: int = 0

    # Conversation metrics
    total_turns: int = 0
    user_messages: int = 0
    agent_messages: int = 0

    # Speech metrics
    user_words_spoken: int = 0
    agent_words_spoken: int = 0

    # Quality metrics
    corrections_made: int = 0
    topics_discussed: list[str] = Field(default_factory=list)


class UserProfile(BaseModel):
    """Persistent user profile with learning progress."""

    user_id: str = Field(default_factory=lambda: str(uuid4()))
    created_at: datetime = Field(default_factory=datetime.utcnow)
    last_active: datetime = Field(default_factory=datetime.utcnow)

    # Preferences
    preferred_level: CEFRLevel = CEFRLevel.B1
    preferred_mode: AgentMode = AgentMode.FREE_TALK
    preferred_voice: str = "luna"

    # Aggregate stats
    total_sessions: int = 0
    total_practice_minutes: int = 0
    total_words_spoken: int = 0
    total_corrections_received: int = 0

    # Progress tracking
    current_streak_days: int = 0
    longest_streak_days: int = 0
    last_session_date: str | None = None  # YYYY-MM-DD format

    # Session history (last 10 session IDs)
    recent_sessions: list[str] = Field(default_factory=list)


class UserStats(BaseModel):
    """Summary statistics for a user."""

    user_id: str
    total_sessions: int
    total_practice_minutes: int
    total_words_spoken: int
    average_session_minutes: float
    current_streak_days: int
    favorite_mode: AgentMode | None = None
    improvement_score: float = 0.0  # 0-100 based on corrections trend


class LeaderboardEntry(BaseModel):
    """Entry for practice leaderboard."""

    user_id: str
    display_name: str | None = None
    total_practice_minutes: int
    current_streak_days: int
    rank: int
