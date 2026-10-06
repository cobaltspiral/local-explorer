import os
from datetime import date

import httpx
from dotenv import load_dotenv

from moods import MOOD_EVENT_QUERY, pick_mood

load_dotenv()  # reads SERPAPI_KEY from your .env file

SERPAPI_URL = "https://serpapi.com/search.json"
MAX_EVENTS = 5

# A tiny in-memory cache: remembers answers while the server is running.
# It is NOT a database. Everything vanishes when the server restarts.
_cache: dict = {}


def _serpapi_events(city: str, mood: str, when: str) -> list:
    """Ask SerpApi (Google search). Prefer structured events, else web results."""
    key = os.getenv("SERPAPI_KEY")
    if not key:
        raise RuntimeError("SERPAPI_KEY is missing. Check your .env file.")

    params = {
        "engine": "google",
        "q": f"{MOOD_EVENT_QUERY[mood]} in {city} this {when}",
        "hl": "en",
        "api_key": key,
    }
    try:
        response = httpx.get(SERPAPI_URL, params=params, timeout=20)
        response.raise_for_status()
    except httpx.HTTPStatusError as e:
        try:
            detail = e.response.json().get("error", "")
        except ValueError:
            detail = ""
        raise RuntimeError(f"SerpApi HTTP {e.response.status_code}: {detail}") from None
    except httpx.HTTPError as e:
        raise RuntimeError(f"SerpApi request failed ({type(e).__name__})") from None

    data = response.json()
    if "error" in data:
        if "hasn't returned any results" in data["error"]:
            return []
        raise RuntimeError(data["error"])

    # 1) Structured events, if Google showed an events panel
    events = []
    for ev in data.get("events_results", [])[:MAX_EVENTS]:
        events.append({
            "title": ev.get("title"),
            "date": (ev.get("date") or {}).get("when"),
            "venue": (ev.get("venue") or {}).get("name"),
            "address": ", ".join(ev.get("address") or []),
            "link": ev.get("link"),
            "description": ev.get("description"),
            "source": "serpapi",
            "type": "event",
        })
    if events:
        return events

    # 2) Otherwise, normal web results (listing pages)
    listings = []
    for r in data.get("organic_results", [])[:MAX_EVENTS]:
        listings.append({
            "title": r.get("title"),
            "date": None,
            "venue": None,
            "address": None,
            "link": r.get("link"),
            "description": r.get("snippet"),
            "source": "serpapi",
            "type": "listing",
        })
    return listings


def _ddgs_fallback(city: str, mood: str) -> list:
    """Free fallback: plain web search results. Less structured than SerpApi."""
    from ddgs import DDGS

    query = f"{MOOD_EVENT_QUERY[mood]} in {city} this week {date.today():%B %Y}"
    results = DDGS().text(query, max_results=MAX_EVENTS)
    return [
        {
            "title": r.get("title"),
            "date": None,  # web snippets don't give a clean date
            "venue": None,
            "address": None,
            "link": r.get("href"),
            "description": r.get("body"),
            "source": "ddgs",
            "type": "listing",
        }
        for r in results
    ]


def find_events(city: str, mood: str, when: str = "week") -> list:
    """Main function. Returns a list of events (possibly empty). Never crashes."""
    mood = pick_mood(mood)  # safe to call again if mood was already resolved
    cache_key = (city.strip().lower(), mood, when)

    if cache_key in _cache:
        print("  (events: cache hit)")
        return _cache[cache_key]

    events = []

    try:
        events = _serpapi_events(city, mood, when)
    except Exception as e:
        print(f"  (SerpApi problem: {e!r})")

    if not events:
        try:
            print("  (events: trying ddgs fallback)")
            events = _ddgs_fallback(city, mood)
        except Exception as e:
            print(f"  (ddgs problem: {e!r})")
            events = []

    if events:  # only cache real answers
        _cache[cache_key] = events
    return events


# ---------- Quick test: run with `python search.py` ----------

if __name__ == "__main__":
    for attempt in (1, 2):
        print(f"\n=== Call {attempt}: Edinburgh / creative ===")
        for ev in find_events("Edinburgh", "creative"):
            print(f"- {ev['title']}  [{ev['source']}]")
            print(f"    when: {ev['date']} | where: {ev['venue']}")
            print(f"    link: {ev['link']}")