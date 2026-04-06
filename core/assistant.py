"""
core/assistant.py
Central brain of MotionAI.
Orchestrates: wake detection → speech → LLM → intent → TTS
"""

import threading
from core.event_bus import EventBus, Events
from core.config import USER_NAME


class Assistant:
    """
    Stateful assistant controller.
    Subscribes to bus events and drives the main pipeline.
    """

    MODES = ("normal", "gesture", "counsellor")

    def __init__(self, event_bus: EventBus):
        self.bus = event_bus
        self._mode = "normal"
        self._active = False   # True after wake, stays True

        # Subscribe
        self.bus.subscribe(Events.WAKE_DETECTED,      self._on_wake)
        self.bus.subscribe(Events.SPEECH_RECOGNIZED,  self._on_speech)
        self.bus.subscribe(Events.MODE_CHANGE,        self._on_mode_change)

    @property
    def mode(self) -> str:
        return self._mode

    @property
    def is_active(self) -> bool:
        return self._active

    def _on_wake(self, data: dict):
        self._active = True
        print(f"[Assistant] Activated for {USER_NAME}")

    def _on_speech(self, data: dict):
        text = data.get("text", "").lower().strip()
        if not text:
            return

        # Mode-change keywords (fast path before LLM)
        if "gesture mode" in text or "start gesture" in text:
            self.bus.publish(Events.MODE_CHANGE, {"mode": "gesture"})
            return
        if "counsellor mode" in text or "start counsellor" in text:
            self.bus.publish(Events.MODE_CHANGE, {"mode": "counsellor"})
            return
        if "normal mode" in text or "exit mode" in text or "go back" in text:
            self.bus.publish(Events.MODE_CHANGE, {"mode": "normal"})
            return

        # Publish for UI to handle via LLM pipeline
        self.bus.publish(Events.INTENT_RESOLVED, {"text": data["text"], "mode": self._mode})

    def _on_mode_change(self, data: dict):
        new_mode = data.get("mode", "normal")
        if new_mode in self.MODES:
            self._mode = new_mode
            print(f"[Assistant] Mode → {new_mode}")