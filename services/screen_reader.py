"""
services/screen_reader.py
Reads visible text from the screen using:
  Primary:  pytesseract OCR (offline, fast)
  Fallback: Groq LLaMA vision API (if tesseract not installed)
"""

import pyautogui
import io
import base64
import requests
from core.config import GROQ_API_KEY


def capture_screen() -> bytes:
    """Take a screenshot and return as PNG bytes."""
    screenshot = pyautogui.screenshot()
    buf = io.BytesIO()
    screenshot.save(buf, format="PNG")
    return buf.getvalue()


def read_screen_ocr() -> str:
    """
    Extract all visible text from screen using pytesseract.
    Returns cleaned text string.
    """
    try:
        import pytesseract
        from PIL import Image
        import io

        screenshot = pyautogui.screenshot()

        # Increase contrast for better OCR accuracy
        from PIL import ImageEnhance, ImageFilter
        screenshot = screenshot.convert("L")           # greyscale
        screenshot = ImageEnhance.Contrast(screenshot).enhance(2.0)
        screenshot = screenshot.filter(ImageFilter.SHARPEN)

        text = pytesseract.image_to_string(screenshot, lang="eng")
        text = text.strip()

        if not text:
            return None

        # Clean up: remove blank lines, extra spaces
        lines = [l.strip() for l in text.splitlines() if l.strip()]
        return "\n".join(lines)

    except ImportError:
        print("[ScreenReader] pytesseract not installed — trying Groq vision")
        return None
    except Exception as e:
        print(f"[ScreenReader] OCR error: {e}")
        return None


def read_screen_groq(question: str = "What text is visible on this screen? Read everything you can see.") -> str:
    """
    Use Groq's vision API to read and describe screen content.
    Falls back when tesseract is unavailable.
    """
    try:
        img_bytes = capture_screen()
        img_b64   = base64.b64encode(img_bytes).decode("utf-8")

        payload = {
            "model": "llama-3.2-11b-vision-preview",
            "messages": [
                {
                    "role": "user",
                    "content": [
                        {
                            "type":      "image_url",
                            "image_url": {"url": f"data:image/png;base64,{img_b64}"},
                        },
                        {
                            "type": "text",
                            "text": question,
                        },
                    ],
                }
            ],
            "max_tokens": 600,
        }

        headers = {
            "Authorization": f"Bearer {GROQ_API_KEY}",
            "Content-Type":  "application/json",
        }

        r = requests.post(
            "https://api.groq.com/openai/v1/chat/completions",
            headers=headers,
            json=payload,
            timeout=20,
        )
        r.raise_for_status()
        return r.json()["choices"][0]["message"]["content"].strip()

    except Exception as e:
        print(f"[ScreenReader] Groq vision error: {e}")
        return "Sorry, I couldn't read the screen right now."


def read_screen(question: str = None) -> str:
    """
    Main entry — try OCR first, fall back to Groq vision.
    If question is given, use vision API for context-aware reading.
    """
    # If user asked a specific question about the screen → use vision
    if question and question.strip():
        return read_screen_groq(question)

    # Try fast OCR first
    ocr_text = read_screen_ocr()
    if ocr_text and len(ocr_text) > 30:
        # Summarise with Groq if text is very long
        if len(ocr_text) > 800:
            return _summarise_text(ocr_text)
        return f"Here's what I can see on your screen: {ocr_text}"

    # Fall back to vision API
    return read_screen_groq()


def _summarise_text(text: str) -> str:
    """Ask Groq to summarise long OCR text into a spoken answer."""
    try:
        payload = {
            "model": "llama-3.1-8b-instant",
            "messages": [
                {
                    "role":    "system",
                    "content": "You summarise screen content into 2-3 spoken sentences. Be concise.",
                },
                {
                    "role":    "user",
                    "content": f"Summarise what's on the screen:\n\n{text[:2000]}",
                },
            ],
            "max_tokens": 200,
        }
        headers = {
            "Authorization": f"Bearer {GROQ_API_KEY}",
            "Content-Type":  "application/json",
        }
        r = requests.post(
            "https://api.groq.com/openai/v1/chat/completions",
            headers=headers, json=payload, timeout=10
        )
        r.raise_for_status()
        return r.json()["choices"][0]["message"]["content"].strip()
    except Exception as e:
        print(f"[ScreenReader] Summarise error: {e}")
        # Return first 3 lines as fallback
        lines = text.splitlines()[:3]
        return "On your screen I can see: " + ". ".join(lines)