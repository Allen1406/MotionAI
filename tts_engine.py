"""
tts_engine.py
- ElevenLabs via pygame (instant playback, no temp file delay)
- Interruptible: call interrupt() to stop mid-sentence
- pyttsx3 offline fallback
- NO infinite loop bug
"""

import threading
import queue
import io
import subprocess
from core.config import TTS_RATE, TTS_VOLUME, ELEVENLABS_API_KEY, ELEVENLABS_VOICE_ID, USE_ELEVENLABS
from core.event_bus import EventBus, Events

import pygame
pygame.mixer.pre_init(44100, -16, 2, 512)
pygame.mixer.init()


class TTSEngine:
    def __init__(self, event_bus: EventBus):
        self.bus       = event_bus
        self._queue    = queue.Queue()
        self._running  = True
        self._speaking = False
        self._engine   = None
        self._interrupted = False

        # Subscribe ONLY to TTS_SPEAK — never re-publish it
        self.bus.subscribe(Events.TTS_SPEAK,     self._enqueue)
        self.bus.subscribe(Events.TTS_INTERRUPT, self._on_interrupt)

        self._init_pyttsx3()

        self._thread = threading.Thread(target=self._loop, daemon=True)
        self._thread.start()

        mode = "ElevenLabs" if USE_ELEVENLABS else "pyttsx3"
        print(f"[TTS] Ready — {mode}")

    # ── Init pyttsx3 ──────────────────────────────────────────────────────────
    def _init_pyttsx3(self):
        try:
            import pyttsx3
            e = pyttsx3.init()
            e.setProperty("rate",   TTS_RATE)
            e.setProperty("volume", TTS_VOLUME)
            voices = e.getProperty("voices")
            for v in voices:
                if any(x in v.name.lower() for x in ["zira","hazel","susan","female"]):
                    e.setProperty("voice", v.id)
                    break
            self._engine = e
            print("[TTS] pyttsx3 fallback ready")
        except Exception as ex:
            print(f"[TTS] pyttsx3 init failed: {ex}")
            self._engine = None

    # ── Public API ────────────────────────────────────────────────────────────
    def speak(self, text: str):
        """Speak immediately — direct enqueue, bypasses bus."""
        if text and text.strip():
            self._queue.put(text.strip())

    def interrupt(self):
        """Stop whatever is currently playing."""
        self._interrupted = True
        try:
            pygame.mixer.music.stop()
        except Exception:
            pass
        if self._engine:
            try:
                self._engine.stop()
            except Exception:
                pass
        # Clear pending queue
        while not self._queue.empty():
            try: self._queue.get_nowait()
            except: break
        print("[TTS] ⛔ Interrupted")

    def _on_interrupt(self, _):
        self.interrupt()

    # ── Bus subscriber — puts in queue, never re-publishes TTS_SPEAK ─────────
    def _enqueue(self, data):
        text = (data.get("text","") if isinstance(data,dict) else str(data)).strip()
        if text:
            self._queue.put(text)

    # ── Worker loop ───────────────────────────────────────────────────────────
    def _loop(self):
        while self._running:
            try:
                text = self._queue.get(timeout=0.5)
                self._interrupted = False
                self._speaking    = True

                # Notify UI — use "tts_started" NOT TTS_SPEAK (avoids loop)
                self.bus.publish("tts_started", {"text": text})

                print(f"[TTS] 🔊 {text[:90]}")
                self._say(text)

                self._speaking = False
                if not self._interrupted:
                    self.bus.publish(Events.TTS_DONE, {"text": text})
                self._queue.task_done()

            except queue.Empty:
                pass
            except Exception as e:
                print(f"[TTS] Loop error: {e}")
                self._speaking = False

    # ── Say dispatcher ────────────────────────────────────────────────────────
    def _say(self, text: str):
        if USE_ELEVENLABS:
            if self._say_elevenlabs(text):
                return
        self._say_pyttsx3(text)

    # ── ElevenLabs via pygame (streaming bytes, no temp file) ─────────────────
    def _say_elevenlabs(self, text: str) -> bool:
        try:
            import requests as req
            url = f"https://api.elevenlabs.io/v1/text-to-speech/{ELEVENLABS_VOICE_ID}"
            headers = {
                "xi-api-key":   ELEVENLABS_API_KEY,
                "Content-Type": "application/json",
                "Accept":       "audio/mpeg",
            }
            body = {
                "text":     text,
                "model_id": "eleven_turbo_v2",   # fastest model
                "voice_settings": {
                    "stability":         0.45,
                    "similarity_boost":  0.82,
                    "style":             0.15,
                    "use_speaker_boost": True,
                },
            }
            r = req.post(url, headers=headers, json=body, timeout=10)
            if r.status_code != 200:
                print(f"[TTS] ElevenLabs {r.status_code}: {r.text[:80]}")
                return False

            audio_bytes = io.BytesIO(r.content)

            # Load directly into pygame — no temp file needed
            pygame.mixer.music.load(audio_bytes, "mp3")
            pygame.mixer.music.play()

            # Wait until done OR interrupted
            import time
            while pygame.mixer.music.get_busy():
                if self._interrupted:
                    pygame.mixer.music.stop()
                    return True
                time.sleep(0.05)

            return True

        except Exception as e:
            print(f"[TTS] ElevenLabs error: {e}")
            return False

    # ── pyttsx3 fallback ─────────────────────────────────────────────────────
    def _say_pyttsx3(self, text: str):
        if self._engine:
            try:
                self._engine.say(text)
                self._engine.runAndWait()
                return
            except RuntimeError:
                self._init_pyttsx3()
                if self._engine:
                    try:
                        self._engine.say(text)
                        self._engine.runAndWait()
                        return
                    except: pass
            except Exception as e:
                print(f"[TTS] pyttsx3 error: {e}")
        self._say_powershell(text)

    def _say_powershell(self, text: str):
        try:
            safe = text.replace("'","''")
            subprocess.run(
                ["powershell","-c",
                 f"Add-Type -AssemblyName System.speech; "
                 f"$s=New-Object System.Speech.Synthesis.SpeechSynthesizer; "
                 f"$s.Rate=1; $s.Speak('{safe}')"],
                capture_output=True, timeout=30
            )
        except Exception as e:
            print(f"[TTS] PowerShell error: {e}")

    @property
    def is_speaking(self): return self._speaking

    def stop(self):
        self._running = False
        self.interrupt()
        if self._engine:
            try: self._engine.stop()
            except: pass