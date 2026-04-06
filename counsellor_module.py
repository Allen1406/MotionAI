"""
counsellor_module.py
Manages Counsellor Mode state and logic.
Detects emotional triggers and routes to counsellor persona.
"""

import re
from llm_client import LLMClient
from core.event_bus import EventBus, Events

# Keywords that trigger counsellor mode automatically
EMOTIONAL_TRIGGERS = [
    "i feel sad", "i am sad", "i'm sad",
    "i feel anxious", "i'm anxious", "i'm stressed", "i feel stressed",
    "i'm depressed", "i feel depressed", "i'm lonely", "i feel lonely",
    "i'm overwhelmed", "i feel overwhelmed", "i'm crying",
    "i'm frustrated", "i feel frustrated", "i'm tired of everything",
    "i can't take this", "i need help", "i'm not okay", "i am not okay",
    "i feel hopeless", "i'm hopeless", "everything is falling apart",
    "i want to give up", "nobody cares", "i feel empty",
]

MODE_TRIGGERS = [
    "start counsellor mode", "enter counsellor mode",
    "counsellor mode", "therapy mode", "i need someone to talk to",
    "can we talk", "i need to vent",
]


class CounsellorModule:
    """
    Handles the emotional intelligence / counsellor mode for MotionAI.
    """

    def __init__(self, event_bus: EventBus, llm_client: LLMClient):
        self.bus = event_bus
        self.llm = llm_client
        self._in_counsellor_mode = False

        self.bus.subscribe(Events.SPEECH_RECOGNIZED, self._check_trigger)

    def check_emotional_trigger(self, text: str) -> bool:
        """Returns True if text should trigger counsellor mode."""
        lower = text.lower().strip()

        # Check direct mode phrases
        for trigger in MODE_TRIGGERS:
            if trigger in lower:
                return True

        # Check emotional keywords
        for trigger in EMOTIONAL_TRIGGERS:
            if trigger in lower:
                return True

        # Sentiment heuristic: multiple negative words
        negative_words = ["sad", "cry", "hurt", "pain", "lonely", "alone",
                          "hate", "scared", "afraid", "terrible", "awful",
                          "hopeless", "worthless", "useless", "fail"]
        count = sum(1 for w in negative_words if re.search(r"\b" + w + r"\b", lower))
        if count >= 2:
            return True

        return False

    def respond(self, user_text: str) -> str:
        """Generate a counsellor response for the given input."""
        return self.llm.chat(user_text, mode="counsellor")

    def get_opening_message(self) -> str:
        """Generate a warm opening when entering counsellor mode."""
        opening = self.llm.chat(
            "The user just entered counsellor mode. Greet them warmly and ask what's on their mind.",
            mode="counsellor"
        )
        return opening

    def _check_trigger(self, data: dict):
        text = data.get("text", "")
        if not self._in_counsellor_mode and self.check_emotional_trigger(text):
            self._in_counsellor_mode = True
            self.bus.publish(Events.MODE_CHANGE, {"mode": "counsellor"})

    def set_active(self, active: bool):
        self._in_counsellor_mode = active