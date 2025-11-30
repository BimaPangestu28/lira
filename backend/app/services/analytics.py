"""Analytics service for tracking session metrics and user profiles."""

import json
from datetime import datetime, timedelta
from uuid import UUID

import redis.asyncio as redis

from app.core.config import get_settings
from app.models.analytics import SessionAnalytics, UserProfile, UserStats
from app.models.session import AgentMode, CEFRLevel


class AnalyticsService:
    """Service for tracking and persisting analytics data."""

    def __init__(self):
        settings = get_settings()
        self.redis_url = settings.redis_url
        self._redis: redis.Redis | None = None

        # In-memory fallback if Redis unavailable
        self._sessions: dict[str, SessionAnalytics] = {}
        self._profiles: dict[str, UserProfile] = {}

    async def _get_redis(self) -> redis.Redis | None:
        """Get Redis connection (lazy init)."""
        if self._redis is None:
            try:
                self._redis = redis.from_url(self.redis_url, decode_responses=True)
                await self._redis.ping()
            except Exception as e:
                print(f"[Analytics] Redis unavailable, using in-memory: {e}")
                self._redis = None
        return self._redis

    # ========== Session Analytics ==========

    async def start_session(
        self,
        session_id: UUID,
        mode: AgentMode,
        level: CEFRLevel,
        user_id: str | None = None,
    ) -> SessionAnalytics:
        """Start tracking a new session."""
        analytics = SessionAnalytics(
            session_id=session_id,
            user_id=user_id,
            mode=mode,
            level=level,
        )

        r = await self._get_redis()
        if r:
            await r.setex(
                f"session:{session_id}",
                3600,  # 1 hour TTL
                analytics.model_dump_json(),
            )
        else:
            self._sessions[str(session_id)] = analytics

        print(f"[Analytics] Session started: {session_id}")
        return analytics

    async def get_session(self, session_id: UUID) -> SessionAnalytics | None:
        """Get session analytics."""
        r = await self._get_redis()
        if r:
            data = await r.get(f"session:{session_id}")
            if data:
                return SessionAnalytics.model_validate_json(data)
        else:
            return self._sessions.get(str(session_id))
        return None

    async def update_session(
        self,
        session_id: UUID,
        user_words: int = 0,
        agent_words: int = 0,
        correction: bool = False,
    ):
        """Update session metrics."""
        analytics = await self.get_session(session_id)
        if not analytics:
            return

        if user_words > 0:
            analytics.user_words_spoken += user_words
            analytics.user_messages += 1
            analytics.total_turns += 1

        if agent_words > 0:
            analytics.agent_words_spoken += agent_words
            analytics.agent_messages += 1

        if correction:
            analytics.corrections_made += 1

        # Save
        r = await self._get_redis()
        if r:
            await r.setex(
                f"session:{session_id}",
                3600,
                analytics.model_dump_json(),
            )
        else:
            self._sessions[str(session_id)] = analytics

    async def end_session(self, session_id: UUID) -> SessionAnalytics | None:
        """End session and calculate final metrics."""
        analytics = await self.get_session(session_id)
        if not analytics:
            return None

        analytics.ended_at = datetime.utcnow()
        analytics.duration_seconds = int(
            (analytics.ended_at - analytics.started_at).total_seconds()
        )

        # Update user profile if user_id exists
        if analytics.user_id:
            await self._update_user_from_session(analytics)

        # Save final state
        r = await self._get_redis()
        if r:
            # Store in session history (keep 30 days)
            await r.setex(
                f"session_history:{session_id}",
                86400 * 30,
                analytics.model_dump_json(),
            )
            await r.delete(f"session:{session_id}")
        else:
            self._sessions.pop(str(session_id), None)

        print(f"[Analytics] Session ended: {session_id}, duration: {analytics.duration_seconds}s")
        return analytics

    # ========== User Profiles ==========

    async def get_or_create_profile(self, user_id: str) -> UserProfile:
        """Get existing profile or create new one."""
        profile = await self.get_profile(user_id)
        if profile:
            return profile

        profile = UserProfile(user_id=user_id)

        r = await self._get_redis()
        if r:
            await r.set(f"profile:{user_id}", profile.model_dump_json())
        else:
            self._profiles[user_id] = profile

        print(f"[Analytics] Created profile: {user_id}")
        return profile

    async def get_profile(self, user_id: str) -> UserProfile | None:
        """Get user profile."""
        r = await self._get_redis()
        if r:
            data = await r.get(f"profile:{user_id}")
            if data:
                return UserProfile.model_validate_json(data)
        else:
            return self._profiles.get(user_id)
        return None

    async def update_profile(self, profile: UserProfile):
        """Save user profile."""
        profile.last_active = datetime.utcnow()

        r = await self._get_redis()
        if r:
            await r.set(f"profile:{profile.user_id}", profile.model_dump_json())
        else:
            self._profiles[profile.user_id] = profile

    async def _update_user_from_session(self, session: SessionAnalytics):
        """Update user profile from completed session."""
        if not session.user_id:
            return

        profile = await self.get_or_create_profile(session.user_id)

        # Update totals
        profile.total_sessions += 1
        profile.total_practice_minutes += session.duration_seconds // 60
        profile.total_words_spoken += session.user_words_spoken
        profile.total_corrections_received += session.corrections_made

        # Update streak
        today = datetime.utcnow().strftime("%Y-%m-%d")
        if profile.last_session_date:
            last_date = datetime.strptime(profile.last_session_date, "%Y-%m-%d")
            days_diff = (datetime.utcnow() - last_date).days

            if days_diff == 1:
                # Consecutive day
                profile.current_streak_days += 1
            elif days_diff > 1:
                # Streak broken
                profile.current_streak_days = 1
            # Same day = no change
        else:
            profile.current_streak_days = 1

        profile.longest_streak_days = max(
            profile.longest_streak_days, profile.current_streak_days
        )
        profile.last_session_date = today

        # Add to recent sessions
        profile.recent_sessions.insert(0, str(session.session_id))
        profile.recent_sessions = profile.recent_sessions[:10]  # Keep last 10

        await self.update_profile(profile)

    async def get_user_stats(self, user_id: str) -> UserStats | None:
        """Get computed user statistics."""
        profile = await self.get_profile(user_id)
        if not profile:
            return None

        avg_minutes = (
            profile.total_practice_minutes / profile.total_sessions
            if profile.total_sessions > 0
            else 0
        )

        return UserStats(
            user_id=user_id,
            total_sessions=profile.total_sessions,
            total_practice_minutes=profile.total_practice_minutes,
            total_words_spoken=profile.total_words_spoken,
            average_session_minutes=round(avg_minutes, 1),
            current_streak_days=profile.current_streak_days,
            favorite_mode=profile.preferred_mode,
        )


# Global instance
analytics_service = AnalyticsService()
