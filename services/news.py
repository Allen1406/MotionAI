"""
services/news.py
Fetches latest headlines from NewsAPI (free tier).
Get your free key at https://newsapi.org — 100 requests/day free.
"""

import requests
from core.config import NEWS_API_KEY


def get_headlines(category: str = "general", country: str = "in", count: int = 5) -> list[dict]:
    """
    Fetch top headlines. Returns list of {title, source, url}.
    category options: general, technology, sports, business, entertainment, health, science
    """
    try:
        url = (
            f"https://newsapi.org/v2/top-headlines"
            f"?country={country}"
            f"&category={category}"
            f"&pageSize={count}"
            f"&apiKey={NEWS_API_KEY}"
        )
        r = requests.get(url, timeout=6)
        data = r.json()

        if data.get("status") != "ok":
            print(f"[News] API error: {data.get('message','unknown')}")
            return []

        articles = data.get("articles", [])
        return [
            {
                "title":  a.get("title", "No title"),
                "source": a.get("source", {}).get("name", "Unknown"),
                "url":    a.get("url", ""),
            }
            for a in articles
            if a.get("title") and "[Removed]" not in a.get("title","")
        ]

    except Exception as e:
        print(f"[News] Error: {e}")
        return []


def build_headlines_answer(category: str = "general", count: int = 5) -> str:
    """Build a spoken answer from top headlines."""
    articles = get_headlines(category=category, count=count)

    if not articles:
        return "Sorry, I couldn't fetch the news right now. Please check your internet connection or NewsAPI key."

    cat_label = category.capitalize() if category != "general" else "Top"
    lines = [f"Here are the {cat_label} news headlines for today."]

    for i, a in enumerate(articles, 1):
        # Clean title — remove source suffix like " - BBC News"
        title = a["title"].split(" - ")[0].strip()
        lines.append(f"Headline {i}: {title}. From {a['source']}.")

    return "  ".join(lines)