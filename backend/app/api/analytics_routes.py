"""API routes for analytics and user profiles."""

from uuid import UUID

from fastapi import APIRouter, HTTPException

from app.models.analytics import SessionAnalytics, UserProfile, UserStats
from app.services.analytics import analytics_service

router = APIRouter(prefix="/analytics", tags=["analytics"])


# ========== Session Analytics ==========

@router.get("/sessions/{session_id}", response_model=SessionAnalytics)
async def get_session_analytics(session_id: UUID):
    """Get analytics for a specific session."""
    analytics = await analytics_service.get_session(session_id)
    if not analytics:
        raise HTTPException(status_code=404, detail="Session not found")
    return analytics


# ========== User Profiles ==========

@router.post("/users/{user_id}", response_model=UserProfile)
async def create_or_get_profile(user_id: str):
    """Get or create a user profile."""
    return await analytics_service.get_or_create_profile(user_id)


@router.get("/users/{user_id}", response_model=UserProfile)
async def get_profile(user_id: str):
    """Get user profile."""
    profile = await analytics_service.get_profile(user_id)
    if not profile:
        raise HTTPException(status_code=404, detail="User not found")
    return profile


@router.get("/users/{user_id}/stats", response_model=UserStats)
async def get_user_stats(user_id: str):
    """Get computed statistics for a user."""
    stats = await analytics_service.get_user_stats(user_id)
    if not stats:
        raise HTTPException(status_code=404, detail="User not found")
    return stats


@router.patch("/users/{user_id}/preferences")
async def update_preferences(
    user_id: str,
    preferred_level: str | None = None,
    preferred_mode: str | None = None,
    preferred_voice: str | None = None,
):
    """Update user preferences."""
    profile = await analytics_service.get_profile(user_id)
    if not profile:
        raise HTTPException(status_code=404, detail="User not found")

    if preferred_level:
        profile.preferred_level = preferred_level
    if preferred_mode:
        profile.preferred_mode = preferred_mode
    if preferred_voice:
        profile.preferred_voice = preferred_voice

    await analytics_service.update_profile(profile)
    return {"status": "updated", "user_id": user_id}
