"""
core/event_bus.py
Lightweight publish/subscribe event bus for MotionAI modules.
"""

from collections import defaultdict
from typing import Callable, Any


class EventBus:
    def __init__(self):
        self._subscribers: dict[str, list[Callable]] = defaultdict(list)

    def subscribe(self, event: str, callback: Callable):
        self._subscribers[event].append(callback)

    def unsubscribe(self, event: str, callback: Callable):
        if callback in self._subscribers[event]:
            self._subscribers[event].remove(callback)

    def publish(self, event: str, data: Any = None):
        for callback in list(self._subscribers.get(event, [])):
            try:
                callback(data)
            except Exception as e:
                print(f"[EventBus] Error in '{event}': {e}")


class Events:
    WAKE_DETECTED      = "wake_detected"
    SPEECH_RECOGNIZED  = "speech_recognized"
    INTENT_RESOLVED    = "intent_resolved"
    MODE_CHANGE        = "mode_change"
    TTS_SPEAK          = "tts_speak"
    TTS_DONE           = "tts_done"
    TTS_INTERRUPT      = "tts_interrupt"       # ← new: stop speech mid-sentence
    GESTURE_FRAME      = "gesture_frame"
    GESTURE_ACTION     = "gesture_action"
    COUNSELLOR_MESSAGE = "counsellor_message"
    SYSTEM_ACTION      = "system_action"
    ASSISTANT_RESPONSE = "assistant_response"
    ERROR              = "error"
    WEATHER_UPDATE     = "weather_update"
    SYSTEM_EXIT        = "system_exit"