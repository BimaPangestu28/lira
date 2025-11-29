"""Deepgram Speech-to-Text service for real-time transcription."""

import asyncio
from typing import AsyncGenerator, Callable

from deepgram import DeepgramClient, LiveTranscriptionEvents, LiveOptions

from app.core.config import get_settings


class DeepgramSTTService:
    """
    Real-time speech-to-text using Deepgram's streaming API.

    Handles continuous audio input and emits transcription results.
    """

    def __init__(self):
        settings = get_settings()
        self.client = DeepgramClient(settings.deepgram_api_key)
        self.connection = None
        self.transcript_callback: Callable[[str, bool], None] | None = None

    async def start(
        self,
        on_transcript: Callable[[str, bool], None],
        language: str = "en-US",
    ):
        """
        Start the live transcription connection.

        @param on_transcript - Callback(text, is_final) for transcription results
        @param language - Language code for transcription
        """
        self.transcript_callback = on_transcript

        options = LiveOptions(
            model="nova-2",
            language=language,
            smart_format=True,
            interim_results=True,
            utterance_end_ms=1000,
            vad_events=True,
            # LiveKit sends 48kHz 16-bit PCM mono audio
            encoding="linear16",
            sample_rate=48000,
            channels=1,
        )

        self.connection = self.client.listen.asynclive.v("1")

        # Register event handlers
        self.connection.on(LiveTranscriptionEvents.Transcript, self._on_transcript)
        self.connection.on(LiveTranscriptionEvents.UtteranceEnd, self._on_utterance_end)
        self.connection.on(LiveTranscriptionEvents.Error, self._on_error)

        print("[Deepgram] Starting connection...")
        started = await self.connection.start(options)
        print(f"[Deepgram] Connection started: {started}")

    async def send_audio(self, audio_data: bytes):
        """
        Send audio data to Deepgram for transcription.

        @param audio_data - Raw audio bytes (16-bit PCM, 16kHz mono recommended)
        """
        if self.connection:
            await self.connection.send(audio_data)

    async def stop(self):
        """Close the transcription connection."""
        if self.connection:
            await self.connection.finish()
            self.connection = None

    async def _on_transcript(self, _self, result, **kwargs):
        """Handle incoming transcription results."""
        try:
            if not self.transcript_callback:
                return

            sentence = result.channel.alternatives[0].transcript
            if sentence:
                is_final = result.is_final
                print(f"[Deepgram] Transcript: '{sentence}' (final={is_final})")
                self.transcript_callback(sentence, is_final)
        except Exception as e:
            print(f"[Deepgram] Error processing transcript: {e}")

    async def _on_utterance_end(self, *args, **kwargs):
        """Handle end of utterance (speaker stopped talking)."""
        pass  # Can be used for turn-taking logic

    async def _on_error(self, _self, error, **kwargs):
        """Handle transcription errors."""
        print(f"Deepgram STT error: {error}")
