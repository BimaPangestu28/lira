"""LiveKit voice agent for real-time audio processing."""

import asyncio
import random
import time
from typing import Callable
from uuid import UUID

from livekit import rtc

from app.agents.conversation import ConversationAgent
from app.services.deepgram_stt import DeepgramSTTService
from app.services.deepgram_tts import DeepgramTTSService
from app.services.analytics import analytics_service


# Filler phrases to play while LLM is generating
FILLER_PHRASES = [
    "Hmm...",
    "I see...",
    "Oh...",
    "Well...",
    "Let me think...",
    "Interesting...",
    "Right...",
]


class VoiceAgent:
    """
    Voice agent that handles the audio pipeline:
    User Audio → STT → LLM → TTS → Playback

    Integrates with LangGraph for conversation management.
    """

    def __init__(
        self,
        room: rtc.Room,
        session_id: UUID,
        mode: str = "free_talk",
        level: str = "B1",
        on_transcription: Callable[[str, bool], None] | None = None,
        on_response: Callable[[str], None] | None = None,
    ):
        """
        Initialize the voice agent.

        @param room - LiveKit room instance
        @param session_id - Session UUID for analytics tracking
        @param mode - Conversation mode (free_talk, corrective, roleplay, guided)
        @param level - CEFR level (A2, B1, B2, C1)
        @param on_transcription - Callback for user speech transcription
        @param on_response - Callback for agent responses
        """
        self.room = room
        self.session_id = session_id
        self.mode = mode
        self.level = level

        # Services
        self.stt: DeepgramSTTService | None = None
        self.tts = DeepgramTTSService(voice="luna")  # Warm female voice
        self.conversation = ConversationAgent(mode=mode, level=level)

        # Callbacks
        self.on_transcription = on_transcription
        self.on_response = on_response

        # Audio handling
        self.audio_source: rtc.AudioSource | None = None
        self.audio_track: rtc.LocalAudioTrack | None = None
        self.is_speaking = False
        self._stt_started = False

        self._pending_text = ""
        self._accumulated_text = ""  # Accumulate transcripts before processing
        self._process_task: asyncio.Task | None = None
        self._debounce_task: asyncio.Task | None = None
        self._tts_queue: asyncio.Queue[str | None] = asyncio.Queue()
        self._tts_worker_task: asyncio.Task | None = None
        self._interrupt_tts = False
        self._debounce_delay = 0.5  # Wait 500ms after last transcript (reduced from 800ms)
        self._response_start_time = 0.0  # For timing measurements
        self._filler_cache: dict[str, bytes] = {}  # Pre-generated filler audio
        self._fillers_ready = False

    async def start(self):
        """Start the voice agent and begin listening."""
        # Create audio source for TTS playback
        self.audio_source = rtc.AudioSource(16000, 1)  # 16kHz mono
        self.audio_track = rtc.LocalAudioTrack.create_audio_track(
            "agent-voice",
            self.audio_source,
        )

        # Publish agent's audio track
        await self.room.local_participant.publish_track(
            self.audio_track,
            rtc.TrackPublishOptions(source=rtc.TrackSource.SOURCE_MICROPHONE),
        )

        # Start TTS worker
        self._tts_worker_task = asyncio.create_task(self._tts_worker())

        # Pre-generate filler audio in background
        asyncio.create_task(self._pregenerate_fillers())

        # Listen for room events (must be sync callbacks)
        self.room.on("participant_connected", self._on_participant_connected)
        self.room.on("track_subscribed", self._on_track_subscribed_sync)
        self.room.on("track_published", self._on_track_published)

        # Also check for already-published tracks from existing participants
        for participant in self.room.remote_participants.values():
            for publication in participant.track_publications.values():
                if publication.track and publication.subscribed:
                    print(f"Found existing track from {participant.identity}")
                    self._on_track_subscribed_sync(
                        publication.track,
                        publication,
                        participant,
                    )

        print("Voice agent started, waiting for participant audio...")

    async def _pregenerate_fillers(self):
        """Pre-generate filler audio for instant playback."""
        print("[Filler] Pre-generating filler audio...")
        for phrase in FILLER_PHRASES:
            try:
                audio_chunks = []
                async for chunk in self.tts.synthesize_stream(phrase):
                    audio_chunks.append(chunk)
                self._filler_cache[phrase] = b"".join(audio_chunks)
            except Exception as e:
                print(f"[Filler] Failed to generate '{phrase}': {e}")

        self._fillers_ready = True
        print(f"[Filler] Ready! {len(self._filler_cache)} fillers cached")

    async def _play_filler(self):
        """Play a random filler phrase instantly."""
        if not self._fillers_ready or not self._filler_cache:
            return

        phrase = random.choice(list(self._filler_cache.keys()))
        audio_data = self._filler_cache[phrase]
        print(f"[Filler] Playing: {phrase}")

        # Play the cached audio directly (no TTS delay)
        chunk_size = 4096
        for i in range(0, len(audio_data), chunk_size):
            if self._interrupt_tts:
                break
            chunk = audio_data[i:i + chunk_size]
            frame = rtc.AudioFrame(
                data=chunk,
                sample_rate=16000,
                num_channels=1,
                samples_per_channel=len(chunk) // 2,
            )
            await self.audio_source.capture_frame(frame)

    async def _start_stt(self):
        """Start STT service (lazy initialization)."""
        if self._stt_started:
            print("[STT] Already started, skipping")
            return

        self._stt_started = True
        try:
            print("[STT] Initializing Deepgram...")
            self.stt = DeepgramSTTService()
            await self.stt.start(on_transcript=self._handle_transcript)
            print("[STT] Started successfully")
        except Exception as e:
            print(f"[STT] Failed to start: {e}")
            self._stt_started = False

    async def _send_opening_greeting(self):
        """Send opening greeting when user joins."""
        greetings = {
            "free_talk": "Hey! What's up?",
            "corrective": "Hi! Let's chat. I'll help with tips!",
            "roleplay": "Ready for roleplay! What scenario?",
            "guided": "Hi! How's your day going?",
        }

        greeting = greetings.get(self.mode, greetings["free_talk"])
        print(f"[Agent] Opening: {greeting}")

        if self.on_response:
            self.on_response(greeting)

        await self.speak(greeting)

    async def _tts_worker(self):
        """Background worker that processes TTS queue sequentially."""
        while True:
            text = await self._tts_queue.get()
            if text is None:  # Shutdown signal
                break
            await self._speak_internal(text)
            self._tts_queue.task_done()

    async def stop(self):
        """Stop the voice agent."""
        if self.stt:
            await self.stt.stop()

        if self.audio_track:
            await self.room.local_participant.unpublish_track(self.audio_track.sid)

        if self._process_task:
            self._process_task.cancel()

        # Stop TTS worker
        if self._tts_worker_task:
            await self._tts_queue.put(None)  # Signal shutdown
            self._tts_worker_task.cancel()

    def _handle_transcript(self, text: str, is_final: bool):
        """Handle incoming transcription from STT."""
        if self.on_transcription:
            self.on_transcription(text, is_final)

        if is_final and text.strip():
            # Interrupt any ongoing TTS when user speaks
            self._interrupt_tts_playback()

            # Accumulate text instead of processing immediately
            if self._accumulated_text:
                self._accumulated_text += " " + text
            else:
                self._accumulated_text = text

            # Cancel previous debounce timer and start new one
            if self._debounce_task and not self._debounce_task.done():
                self._debounce_task.cancel()

            self._debounce_task = asyncio.create_task(self._debounced_process())

    async def _debounced_process(self):
        """Wait for user to stop speaking, then process accumulated text."""
        try:
            await asyncio.sleep(self._debounce_delay)

            # User stopped speaking, process accumulated text
            if self._accumulated_text:
                self._pending_text = self._accumulated_text
                self._accumulated_text = ""
                self._response_start_time = time.time()
                print(f"[STT] Processing: {self._pending_text}")

                # Schedule response processing
                if self._process_task is None or self._process_task.done():
                    self._process_task = asyncio.create_task(self._process_response())
        except asyncio.CancelledError:
            # Timer cancelled because user is still speaking
            pass

    def _interrupt_tts_playback(self):
        """Clear TTS queue, cancel LLM task, and interrupt current playback."""
        self._interrupt_tts = True

        # Cancel ongoing LLM response task
        if self._process_task and not self._process_task.done():
            self._process_task.cancel()
            print("[LLM] Cancelled - user interrupted")

        # Note: Don't cancel debounce task here - we want to keep accumulating

        # Clear the queue
        while not self._tts_queue.empty():
            try:
                self._tts_queue.get_nowait()
                self._tts_queue.task_done()
            except asyncio.QueueEmpty:
                break
        print("[TTS] Queue cleared")

    def _count_words(self, text: str) -> int:
        """Count words in text."""
        return len(text.split())

    def _detect_correction(self, response: str) -> bool:
        """Detect if response contains a correction."""
        correction_patterns = [
            "you could say",
            "you might say",
            "better to say",
            "instead of",
            "correct way",
            "should be",
            "try saying",
            "more natural",
        ]
        response_lower = response.lower()
        return any(pattern in response_lower for pattern in correction_patterns)

    async def _track_analytics(self, user_text: str, agent_response: str):
        """Track conversation analytics."""
        user_words = self._count_words(user_text)
        agent_words = self._count_words(agent_response)
        has_correction = self._detect_correction(agent_response)

        await analytics_service.update_session(
            session_id=self.session_id,
            user_words=user_words,
            agent_words=agent_words,
            correction=has_correction,
        )
        print(f"[Analytics] User: {user_words} words, Agent: {agent_words} words, Correction: {has_correction}")

    async def _process_response(self):
        """Process pending text and generate streaming LLM response."""
        if not self._pending_text:
            return

        text = self._pending_text
        self._pending_text = ""

        # Reset interrupt flag for new response
        self._interrupt_tts = False

        # Play filler IMMEDIATELY while LLM generates (non-blocking)
        filler_task = None
        if self._fillers_ready and self.audio_source:
            filler_task = asyncio.create_task(self._play_filler())

        try:
            # Stream response and speak phrases as they complete
            phrase_buffer = ""
            full_response = ""
            first_chunk = True
            # Speak on sentence endings AND commas for more natural flow
            phrase_endings = {'.', '!', '?', ','}
            min_phrase_length = 10  # Minimum characters before speaking (reduced for lower latency)

            # Start LLM stream - runs concurrently with filler
            async for chunk in self.conversation.respond_stream(text):
                if first_chunk:
                    llm_latency = time.time() - self._response_start_time
                    print(f"[Timing] LLM first token: {llm_latency:.2f}s")
                    first_chunk = False
                    # Wait for filler to finish before speaking actual response
                    if filler_task:
                        await filler_task

                full_response += chunk
                phrase_buffer += chunk

                # Check for phrase completion
                while True:
                    # Find the first phrase ending
                    end_pos = -1
                    for i, char in enumerate(phrase_buffer):
                        if char in phrase_endings:
                            # For commas, only break if we have enough text
                            if char == ',' and i < min_phrase_length:
                                continue
                            # Check if followed by space or end of buffer
                            if i == len(phrase_buffer) - 1 or phrase_buffer[i + 1] in ' \n':
                                end_pos = i
                                break

                    if end_pos == -1:
                        break

                    # Extract and queue phrase for TTS
                    phrase = phrase_buffer[:end_pos + 1].strip()
                    if phrase:
                        print(f"[LLM] → {phrase}")
                        await self.speak(phrase)  # Queues for TTS worker
                    phrase_buffer = phrase_buffer[end_pos + 1:].lstrip()

            # Speak any remaining text
            if phrase_buffer.strip():
                print(f"[LLM] → {phrase_buffer.strip()}")
                await self.speak(phrase_buffer.strip())

            print(f"[LLM] Complete: {full_response}")
            if self.on_response:
                self.on_response(full_response)

            # Track analytics for this turn
            await self._track_analytics(text, full_response)

        except asyncio.CancelledError:
            # User interrupted - this is expected, don't treat as error
            pass
        except Exception as e:
            print(f"[LLM] Error: {e}")
            fallback = "I'm sorry, I had trouble understanding. Could you repeat that?"
            if self.on_response:
                self.on_response(fallback)
            await self.speak(fallback)

    def set_mode(self, mode: str):
        """Change conversation mode."""
        self.mode = mode
        self.conversation.set_mode(mode)

    def set_level(self, level: str):
        """Change CEFR level."""
        self.level = level
        self.conversation.set_level(level)

    async def speak(self, text: str):
        """
        Queue text for TTS playback.

        @param text - Text to speak
        """
        await self._tts_queue.put(text)

    async def _speak_internal(self, text: str):
        """
        Internal method to synthesize and play speech.

        @param text - Text to speak
        """
        if not self.audio_source:
            print("[TTS] No audio source available")
            return

        # Check if interrupted before starting
        if self._interrupt_tts:
            print(f"[TTS] Skipped (interrupted): {text[:30]}...")
            return

        self.is_speaking = True
        tts_start = time.time()
        print(f"[TTS] Speaking: {text[:50]}...")

        try:
            chunk_count = 0
            total_bytes = 0
            first_audio = True
            async for chunk in self.tts.synthesize_stream(text):
                if first_audio:
                    tts_latency = time.time() - tts_start
                    print(f"[Timing] TTS first audio: {tts_latency:.2f}s")
                    first_audio = False
                # Check for interruption during playback
                if self._interrupt_tts:
                    print(f"[TTS] Stopped mid-speech")
                    break

                chunk_count += 1
                total_bytes += len(chunk)
                # Convert bytes to AudioFrame
                frame = rtc.AudioFrame(
                    data=chunk,
                    sample_rate=16000,
                    num_channels=1,
                    samples_per_channel=len(chunk) // 2,  # 16-bit = 2 bytes per sample
                )
                await self.audio_source.capture_frame(frame)

            if not self._interrupt_tts:
                print(f"[TTS] Done: {chunk_count} chunks, {total_bytes} bytes")

                # Add silence padding to prevent audio clicks (100ms of silence)
                silence = bytes(3200)  # 100ms at 16kHz, 16-bit = 3200 bytes
                silence_frame = rtc.AudioFrame(
                    data=silence,
                    sample_rate=16000,
                    num_channels=1,
                    samples_per_channel=1600,
                )
                await self.audio_source.capture_frame(silence_frame)
        except Exception as e:
            print(f"[TTS] Error: {e}")
        finally:
            self.is_speaking = False

    def _on_participant_connected(self, participant: rtc.RemoteParticipant):
        """Handle participant connection."""
        print(f"[Event] Participant connected: {participant.identity}")

    def _on_track_published(
        self,
        publication: rtc.RemoteTrackPublication,
        participant: rtc.RemoteParticipant,
    ):
        """Handle track publication."""
        print(f"[Event] Track published by {participant.identity}: {publication.kind}")

    def _on_track_subscribed_sync(
        self,
        track: rtc.Track,
        publication: rtc.RemoteTrackPublication,
        participant: rtc.RemoteParticipant,
    ):
        """Sync wrapper for track subscription (required by LiveKit SDK)."""
        asyncio.create_task(self._on_track_subscribed(track, publication, participant))

    async def _on_track_subscribed(
        self,
        track: rtc.Track,
        publication: rtc.RemoteTrackPublication,
        participant: rtc.RemoteParticipant,
    ):
        """Handle new audio track from participant."""
        if track.kind != rtc.TrackKind.KIND_AUDIO:
            return

        print(f"Audio track subscribed from {participant.identity}")

        # Start STT when we get audio
        await self._start_stt()

        # Send opening greeting
        await self._send_opening_greeting()

        audio_stream = rtc.AudioStream(track)

        frame_count = 0
        async for event in audio_stream:
            if isinstance(event, rtc.AudioFrameEvent):
                frame_count += 1
                audio_data = event.frame.data.tobytes()

                # Debug: log every 100 frames
                if frame_count % 100 == 0:
                    print(f"[Audio] Received {frame_count} frames, last frame size: {len(audio_data)} bytes")

                # Send audio to STT
                if self.stt:
                    await self.stt.send_audio(audio_data)
