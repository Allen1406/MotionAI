"""
services/weather.py
Real-time weather + location. Returns answer for direct weather questions too.
"""

import requests
from datetime import datetime
from core.config import WEATHER_API_KEY, DEFAULT_CITY


def get_location() -> dict:
    try:
        r = requests.get("https://ipapi.co/json/", timeout=5)
        d = r.json()
        return {
            "city":    d.get("city", DEFAULT_CITY),
            "region":  d.get("region", ""),
            "country": d.get("country_name", "India"),
        }
    except Exception as e:
        print(f"[Weather] Location error: {e}")
        return {"city": DEFAULT_CITY, "region": "", "country": "India"}


def get_weather(city: str = None) -> dict:
    if not city:
        city = get_location()["city"]
    try:
        url = (
            f"https://api.openweathermap.org/data/2.5/weather"
            f"?q={city}&appid={WEATHER_API_KEY}&units=metric"
        )
        r = requests.get(url, timeout=6)
        d = r.json()
        if d.get("cod") != 200:
            print(f"[Weather] API returned: {d.get('message','unknown error')}")
            return _fallback(city)
        return {
            "city":        city,
            "temp":        round(d["main"]["temp"]),
            "feels_like":  round(d["main"]["feels_like"]),
            "description": d["weather"][0]["description"].capitalize(),
            "humidity":    d["main"]["humidity"],
            "wind_speed":  d["wind"]["speed"],
            "ok":          True,
        }
    except Exception as e:
        print(f"[Weather] Error: {e}")
        return _fallback(city)


def _fallback(city: str) -> dict:
    return {
        "city": city, "temp": "unknown", "feels_like": "unknown",
        "description": "unavailable", "humidity": "--",
        "wind_speed": "--", "ok": False,
    }


def get_weather_answer(city: str = None) -> str:
    """Returns a spoken weather answer — used by LLM fallback."""
    w = get_weather(city)
    if not w["ok"]:
        return f"Sorry, I couldn't fetch the weather right now. Please check your internet connection."
    return (
        f"The weather in {w['city']} is {w['description']}, "
        f"{w['temp']} degrees Celsius. "
        f"It feels like {w['feels_like']} degrees. "
        f"Humidity is {w['humidity']} percent."
    )


def build_greeting(user_name: str) -> str:
    now      = datetime.now()
    time_str = now.strftime("%I:%M %p")
    loc      = get_location()
    city     = loc["city"]
    w        = get_weather(city)

    loc_str  = city
    if loc.get("region"):
        loc_str += f", {loc['region']}"

    temp_str = f"{w['temp']}°C" if w["ok"] else "unknown temperature"
    desc     = w["description"] if w["ok"] else "unknown conditions"

    return (
        f"Hi {user_name}! You're in {loc_str}. "
        f"The weather is {desc}, {temp_str}. "
        f"The time is {time_str}. "
        f"What do you want me to do?"
    )