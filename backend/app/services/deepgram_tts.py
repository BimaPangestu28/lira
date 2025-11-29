"""Deepgram Text-to-Speech service using Aura voices with true streaming."""

from typing import AsyncGenerator

import httpx

from app.core.config import get_settings


class DeepgramTTSService:
    """
    Text-to-speech using Deepgram's Aura voices.

    Uses HTTP streaming for low-latency audio delivery.
    """

    # Available Aura voices
    VOICES = {
        "asteria": "aura-asteria-en",      # Female, American
        "luna": "aura-luna-en",            # Female, American
        "stella": "aura-stella-en",        # Female, American
        "athena": "aura-athena-en",        # Female, British
        "hera": "aura-hera-en",            # Female, American
        "orion": "aura-orion-en",          # Male, American
        "arcas": "aura-arcas-en",          # Male, American
        "perseus": "aura-perseus-en",      # Male, American
        "angus": "aura-angus-en",          # Male, Irish
        "orpheus": "aura-orpheus-en",      # Male, American
        "helios": "aura-helios-en",        # Male, British
        "zeus": "aura-zeus-en",            # Male, American
    }

    TTS_URL = "https://api.deepgram.com/v1/speak"

    def __init__(self, voice: str = "asteria"):
        """
        Initialize TTS service.

        @param voice - Voice name (see VOICES dict)
        """
        settings = get_settings()
        self.api_key = settings.deepgram_api_key
        self.voice = self.VOICES.get(voice, self.VOICES["asteria"])

    async def synthesize_stream(self, text: str) -> AsyncGenerator[bytes, None]:
        """
        Stream synthesized speech audio in real-time.

        Uses HTTP streaming to receive audio chunks as they're generated.

        @param text - Text to synthesize
        @yields Audio chunks (linear16 PCM, 16kHz)
        """
        params = {
            "model": self.voice,
            "encoding": "linear16",
            "sample_rate": "16000",
        }

        headers = {
            "Authorization": f"Token {self.api_key}",
            "Content-Type": "application/json",
        }

        async with httpx.AsyncClient(timeout=30.0) as client:
            async with client.stream(
                "POST",
                self.TTS_URL,
                params=params,
                headers=headers,
                json={"text": text},
            ) as response:
                response.raise_for_status()
                async for chunk in response.aiter_bytes(chunk_size=4096):
                    if chunk:
                        yield chunk

    def set_voice(self, voice: str):
        """
        Change the TTS voice.

        @param voice - Voice name from VOICES dict
        """
        if voice in self.VOICES:
            self.voice = self.VOICES[voice]
