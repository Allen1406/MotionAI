"""
llm_client.py
Layer 1: Local intent parser (instant)
Layer 2: Groq LLM (conversational + complex)
- Weather questions answered locally (no LLM needed)
- Apple Music / media controls added
- Counsellor mode fixed
"""

import json
import re
import requests
from core.config import (
    GROQ_API_KEY, LLM_MODEL, LLM_MAX_TOKENS, LLM_TEMPERATURE,
    COUNSELLOR_MODEL, COUNSELLOR_TEMP, USER_NAME
)

GROQ_URL = "https://api.groq.com/openai/v1/chat/completions"

# ─── Local intent patterns ────────────────────────────────────────────────────
LOCAL_INTENTS = [
    # ── Apps ──────────────────────────────────────────────────────────────────
    (r"\b(open|launch|start|run)\s+(vs\s?code|visual\s?studio\s?code|vscode)\b",
        "open_app", lambda m: {"app": "vscode"}),
    (r"\b(open|launch|start)\s+chrome\b",
        "open_app", lambda m: {"app": "chrome"}),
    (r"\b(open|launch|start)\s+whatsapp\b",
        "open_app", lambda m: {"app": "whatsapp"}),
    (r"\b(open|launch|start)\s+spotify\b",
        "open_app", lambda m: {"app": "spotify"}),
    (r"\b(open|launch|start)\s+discord\b",
        "open_app", lambda m: {"app": "discord"}),
    (r"\b(open|launch|start)\s+notepad\b",
        "open_app", lambda m: {"app": "notepad"}),
    (r"\b(open|launch|start)\s+calculator\b",
        "open_app", lambda m: {"app": "calculator"}),
    (r"\b(open|launch|start)\s+(file\s?explorer|explorer|files)\b",
        "open_app", lambda m: {"app": "explorer"}),
    (r"\b(open|launch|start)\s+vlc\b",
        "open_app", lambda m: {"app": "vlc"}),
    (r"\b(open|launch|start)\s+zoom\b",
        "open_app", lambda m: {"app": "zoom"}),
    (r"\b(open|launch|start)\s+teams\b",
        "open_app", lambda m: {"app": "teams"}),
    (r"\b(open|launch|start)\s+paint\b",
        "open_app", lambda m: {"app": "paint"}),
    (r"\b(open|launch|start)\s+(apple\s+music|music)\b",
        "open_app", lambda m: {"app": "apple_music"}),

    # ── Apple Music / Media controls ──────────────────────────────────────────
    (r"\b(play|resume)\s*(music|song|audio)?\b",
        "media_control", lambda m: {"action": "play"}),
    (r"\b(pause|stop)\s*(music|song|audio)?\b",
        "media_control", lambda m: {"action": "pause"}),
    (r"\bnext\s*(song|track)?\b",
        "media_control", lambda m: {"action": "next"}),
    (r"\b(previous|prev|back)\s*(song|track)?\b",
        "media_control", lambda m: {"action": "previous"}),
    (r"\bplay\s+(.+?)\s*(on\s+apple\s+music|in\s+apple\s+music|on\s+spotify)?\s*$",
        "media_play_song", lambda m: {"song": m.group(1).strip()}),

    # ── Web search ────────────────────────────────────────────────────────────
    (r"\b(search\s+(for\s+)?|google\s+)(.*)",
        "search_web", lambda m: {"query": m.group(3).strip()}),

    # ── Open URL ──────────────────────────────────────────────────────────────
    (r"\b(open|go\s+to|visit)\s+(https?://\S+|\S+\.(com|in|org|net|io|co)\S*)\b",
        "open_url", lambda m: {"url": m.group(2).strip()}),

    # ── WhatsApp ──────────────────────────────────────────────────────────────
    (r"send\s+(a\s+)?message\s+to\s+(\w+)\s*[:\-]?\s*(.+)",
        "send_whatsapp", lambda m: {"contact": m.group(2), "message": m.group(3).strip()}),
    (r"whatsapp\s+(\w+)\s*[:\-]?\s*(.+)",
        "send_whatsapp", lambda m: {"contact": m.group(1), "message": m.group(2).strip()}),

    # ── Volume ────────────────────────────────────────────────────────────────
    (r"\b(volume\s+up|increase\s+volume|louder|turn\s+up)\b",
        "volume_up", lambda m: {"steps": 5}),
    (r"\b(volume\s+down|decrease\s+volume|quieter|turn\s+down|lower\s+volume)\b",
        "volume_down", lambda m: {"steps": 5}),
    (r"\b(mute|silence)\b",
        "volume_down", lambda m: {"steps": 20}),

    # ── Scroll ────────────────────────────────────────────────────────────────
    (r"\bscroll\s+up\b",   "scroll_up",   lambda m: {"clicks": 5}),
    (r"\bscroll\s+down\b", "scroll_down", lambda m: {"clicks": 5}),

    # ── Screenshot ────────────────────────────────────────────────────────────
    (r"\b(take\s+a?\s*screenshot|screenshot|capture\s+screen)\b",
        "screenshot", lambda m: {}),

    # ── Modes ─────────────────────────────────────────────────────────────────
    (r"\b(start|open|enter|enable)\s+gesture\s+mode\b",
        "mode_change", lambda m: {"mode": "gesture"}),
    (r"\b(start|open|enter|enable)\s+counsell?or\s+mode\b",
        "mode_change", lambda m: {"mode": "counsellor"}),
    (r"\b(exit|close|stop|disable|back\s+to)\s+(gesture|counsell?or)\s+mode\b",
        "mode_change", lambda m: {"mode": "normal"}),

    # ── System ────────────────────────────────────────────────────────────────
    (r"\b(shut\s*down|shutdown)\b",
        "shutdown", lambda m: {"delay_seconds": 10}),
    (r"\brestart\b",
        "restart", lambda m: {"delay_seconds": 10}),

    # ── Weather (answered locally, not by LLM) ────────────────────────────────
    (r"\b(what('s|s| is)\s+the\s+weather|weather\s+(today|now|outside|forecast)|how('s|s| is)\s+the\s+weather)\b",
        "get_weather", lambda m: {}),
    (r"\b(temperature|temp)\s*(outside|today|now|right now)?\b",
        "get_weather", lambda m: {}),

    # ── Time ──────────────────────────────────────────────────────────────────
    (r"\b(what('s|s| is)\s+the\s+time|current\s+time|time\s+now)\b",
        "get_time", lambda m: {}),
]


def local_intent_parse(text: str) -> dict | None:
    t = text.lower().strip()
    for pattern, action_type, params_fn in LOCAL_INTENTS:
        m = re.search(pattern, t, re.IGNORECASE)
        if m:
            try:
                params = params_fn(m)
                print(f"[LocalIntent] '{action_type}' ← '{text}'")
                return {"type": action_type, "params": params}
            except Exception as e:
                print(f"[LocalIntent] Error: {e}")
    return None


# ─── System prompts ───────────────────────────────────────────────────────────

NORMAL_SYSTEM_PROMPT = f"""You are MotionAI, a smart personal assistant for {USER_NAME}.
Answer questions naturally and helpfully. Keep responses short (1-3 sentences).
Do NOT add any <ACTION> block unless the user explicitly asks to control the computer.
"""

COUNSELLOR_SYSTEM_PROMPT = f"""You are MotionAI in Counsellor Mode — a warm, empathetic AI for {USER_NAME}.
- Always respond with empathy and warmth
- Validate feelings first, then gently offer support
- Ask exactly ONE follow-up question at the end
- Keep responses 2-4 sentences
- Never skip responding — always say something meaningful
- Never judge, never dismiss
"""


class LLMClient:
    def __init__(self):
        self._headers = {
            "Authorization": f"Bearer {GROQ_API_KEY}",
            "Content-Type":  "application/json",
        }
        self._normal_history     = []
        self._counsellor_history = []
        self._max_history        = 10

    def chat(self, user_input: str, mode: str = "normal") -> str:
        if mode == "counsellor":
            return self._counsellor_chat(user_input)
        return self._normal_chat(user_input)

    def _normal_chat(self, user_input: str) -> str:
        history  = self._normal_history[-self._max_history:]
        messages = [
            {"role": "system", "content": NORMAL_SYSTEM_PROMPT},
            *history,
            {"role": "user",   "content": user_input},
        ]
        response = self._call_api(messages, LLM_MODEL, LLM_TEMPERATURE)
        self._normal_history.append({"role": "user",      "content": user_input})
        self._normal_history.append({"role": "assistant", "content": response})
        return response

    def _counsellor_chat(self, user_input: str) -> str:
        history  = self._counsellor_history[-self._max_history:]
        messages = [
            {"role": "system", "content": COUNSELLOR_SYSTEM_PROMPT},
            *history,
            {"role": "user",   "content": user_input},
        ]
        response = self._call_api(messages, COUNSELLOR_MODEL, COUNSELLOR_TEMP)
        self._counsellor_history.append({"role": "user",      "content": user_input})
        self._counsellor_history.append({"role": "assistant", "content": response})
        return response

    def _call_api(self, messages: list, model: str, temperature: float) -> str:
        payload = {
            "model":       model,
            "messages":    messages,
            "max_tokens":  LLM_MAX_TOKENS,
            "temperature": temperature,
        }
        try:
            r = requests.post(GROQ_URL, headers=self._headers, json=payload, timeout=15)
            r.raise_for_status()
            return r.json()["choices"][0]["message"]["content"].strip()
        except requests.exceptions.Timeout:
            return "I'm having trouble connecting. Please try again."
        except Exception as e:
            print(f"[LLM] Error: {e}")
            return "Something went wrong. Please try again."

    def extract_action(self, text: str) -> dict | None:
        m = re.search(r"<ACTION>(.*?)</ACTION>", text, re.DOTALL)
        if m:
            try:
                return json.loads(m.group(1).strip())
            except Exception as e:
                print(f"[LLM] Action parse error: {e}")
        return None

    def clean_response(self, text: str) -> str:
        return re.sub(r"<ACTION>.*?</ACTION>", "", text, flags=re.DOTALL).strip()

    def clear_history(self, mode: str = "all"):
        if mode in ("normal", "all"):   self._normal_history.clear()
        if mode in ("counsellor","all"): self._counsellor_history.clear()