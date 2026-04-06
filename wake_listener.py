"""
wake_listener.py
- Continuous listening after wake word
- Interrupts AI speech when user speaks
- Proper exit on bye bye / goodbye
"""

import speech_recognition as sr
import time
import threading
from core.event_bus import EventBus, Events

MIC_INDEX   = 2
WAKE_PHRASE = "hello"

KILL_PHRASES = ["bye bye", "bye-bye", "goodbye", "shut down motion", "stop motion"]


class WakeListener:
    def __init__(self, event_bus: EventBus):
        self.bus      = event_bus
        self._active  = True
        self._awake   = False

        mic_list = sr.Microphone.list_microphone_names()
        print("[WakeListener] Microphones:")
        for i, n in enumerate(mic_list):
            tag = "  ← USING" if i == MIC_INDEX else ""
            print(f"  [{i}] {n}{tag}")
        print(f"[WakeListener] Wake='{WAKE_PHRASE}'  Mic=[{MIC_INDEX}]")

    def stop(self):
        self._active = False

    def listen(self):
        print("[WakeListener] ✅ Waiting for wake phrase...")

        while self._active:
            # ── Phase 1: Wait for wake word ───────────────────────────────────
            heard = self._listen_once(timeout=None, phrase_limit=4)
            if not heard:
                continue

            print(f"[WakeListener] Heard: '{heard}'")

            if WAKE_PHRASE.lower() in heard.lower():
                print("[WakeListener] ✅ Awake!")
                self.bus.publish(Events.WAKE_DETECTED, {"raw": heard})
                self._awake = True

                # Wait for greeting to finish (greeting is ~5-7s)
                print("[WakeListener] Waiting for greeting...")
                time.sleep(7)

                # ── Phase 2: Continuous command loop ─────────────────────────
                self._command_loop()
                self._awake = False

    def _command_loop(self):
        """Listen continuously. Every utterance is a command."""
        print("[WakeListener] 🎤 Continuous mode active")

        while self._active:
            self.bus.publish("mic_listening", {"active": True})
            cmd = self._listen_once(timeout=10, phrase_limit=12)
            self.bus.publish("mic_listening", {"active": False})

            if not cmd:
                continue

            print(f"[WakeListener] Command: '{cmd}'")

            # Check kill phrase
            lower = cmd.lower().strip()
            if any(kp in lower for kp in KILL_PHRASES):
                print("[WakeListener] 🔴 Kill phrase detected")
                self.bus.publish(Events.SPEECH_RECOGNIZED, {"text": cmd})
                self._active = False
                return

            # If AI is speaking — interrupt it first, then process command
            self.bus.publish(Events.TTS_INTERRUPT, {})

            # Small pause after interrupt before processing
            time.sleep(0.2)

            self.bus.publish(Events.SPEECH_RECOGNIZED, {"text": cmd})

    def _listen_once(self, timeout, phrase_limit) -> str | None:
        rec = sr.Recognizer()
        rec.energy_threshold         = 300
        rec.dynamic_energy_threshold = True
        rec.pause_threshold          = 0.7
        rec.non_speaking_duration    = 0.4
        try:
            with sr.Microphone(device_index=MIC_INDEX) as src:
                rec.adjust_for_ambient_noise(src, duration=0.25)
                self.bus.publish("mic_active", {"active": True})
                audio = rec.listen(src, timeout=timeout, phrase_time_limit=phrase_limit)
            self.bus.publish("mic_active", {"active": False})
            return rec.recognize_google(audio).strip()
        except sr.WaitTimeoutError:
            self.bus.publish("mic_active", {"active": False})
            return None
        except sr.UnknownValueError:
            self.bus.publish("mic_active", {"active": False})
            return None
        except sr.RequestError as e:
            print(f"[WakeListener] STT error: {e}")
            self.bus.publish("mic_active", {"active": False})
            time.sleep(2)
            return None
        except Exception as e:
            print(f"[WakeListener] Error: {e}")
            self.bus.publish("mic_active", {"active": False})
            time.sleep(1)
            return None


class CommandListener:
    """On-demand single-shot listener (Space key)."""
    def __init__(self, event_bus: EventBus):
        self.bus = event_bus

    def listen_once(self, timeout: int = 10) -> str | None:
        rec = sr.Recognizer()
        rec.energy_threshold         = 300
        rec.dynamic_energy_threshold = True
        rec.pause_threshold          = 0.7
        self.bus.publish("mic_listening", {"active": True})
        try:
            with sr.Microphone(device_index=MIC_INDEX) as src:
                rec.adjust_for_ambient_noise(src, duration=0.25)
                audio = rec.listen(src, timeout=timeout, phrase_time_limit=12)
            text = rec.recognize_google(audio).strip()
            print(f"[CommandListener] '{text}'")
            self.bus.publish(Events.TTS_INTERRUPT, {})
            self.bus.publish(Events.SPEECH_RECOGNIZED, {"text": text})
            return text
        except Exception as e:
            print(f"[CommandListener] {e}")
            return None
        finally:
            self.bus.publish("mic_listening", {"active": False})