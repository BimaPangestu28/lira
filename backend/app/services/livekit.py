"""LiveKit service for room and token management."""

from livekit.api import AccessToken, VideoGrants

from app.core.config import get_settings


def create_room_token(room_name: str, participant_name: str) -> str:
    """
    Generate a LiveKit access token for a participant to join a room.

    @param room_name - The name of the room to join
    @param participant_name - The identity of the participant
    @returns JWT access token string
    """
    settings = get_settings()

    token = (
        AccessToken(settings.livekit_api_key, settings.livekit_api_secret)
        .with_identity(participant_name)
        .with_name(participant_name)
        .with_grants(
            VideoGrants(
                room_join=True,
                room=room_name,
                can_publish=True,
                can_subscribe=True,
                can_publish_data=True,
            )
        )
    )

    return token.to_jwt()
