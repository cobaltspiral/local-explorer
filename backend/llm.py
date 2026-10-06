import json
import os
import re
import time
from datetime import date

import httpx
from dotenv import load_dotenv

from moods import DURATIONS

load_dotenv()

LLM_BASE_URL = os.getenv("LLM_BASE_URL", "http://localhost:11434/v1")
LLM_MODEL = os.getenv("LLM_MODEL", "gemma4:e4b")
LLM_API_KEY = os.getenv("LLM_API_KEY", "ollama")

TIME_HINTS = {
    "morning": "morning (before midday)",
    "afternoon": "afternoon",
    "evening": "evening",
    "night": "late at night",
    "anytime": "any time of day",
}

SYSTEM_PROMPT = """You are Pip, a cheerful pixel-art travel guide who loves getting people outside.
You recommend things using ONLY the numbered lists you are given.
Rules:
- Refer to places and events ONLY by their ID (like P3 or E2). Never invent an ID, a place or an event.
- Items marked [EVENT] are specific events. Items marked [WEB PAGE] are just pages listing what's on: never pretend a web page is a specific event, say it is a page worth checking.
- Choose places that suit the mood, the time of day and the time available. For evening or night, prefer bars, restaurants and lively places. For morning, prefer parks, cafes and markets.
- Keep "why" to one short sentence and "tip" to one short, practical sentence.
- "intro" is two short sentences in Pip's cheerful voice, and it ends by nudging the person to put their phone away and enjoy the outing.
- Reply with JSON only, in exactly this shape:
{"intro": "...", "stops": [{"id": "P1", "why": "...", "tip": "..."}], "event": {"id": "E1", "why": "..."} or null}"""


def build_messages(answers: dict, places: list, events: list, n_stops: int) -> list:
    place_lines = [
        f"P{i}: {p['name']} ({p['category']}), {p['distance_m']} m from the centre"
        for i, p in enumerate(places, 1)
    ]

    event_lines = []
    for i, e in enumerate(events, 1):
        desc = (e.get("description") or "")[:200]
        if e.get("type") == "event":
            event_lines.append(
                f"E{i}: [EVENT] {e.get('title')} | when: {e.get('date') or 'date unknown'} "
                f"| where: {e.get('venue') or 'venue unknown'} | {desc}"
            )
        else:
            event_lines.append(f"E{i}: [WEB PAGE] {e.get('title')} | {desc}")

    user_prompt = f"""Today is {date.today():%A %d %B %Y}.
The person is in {answers['location']}.
Mood: {answers['mood']}
Time available: {answers['duration']}
Time of day: {TIME_HINTS.get(answers['time_of_day'], answers['time_of_day'])}

Choose exactly {n_stops} stop(s) from the places, in a sensible order.
Optionally choose ONE item from the events list if it genuinely fits, otherwise use null.

PLACES:
{chr(10).join(place_lines) if place_lines else '(none)'}

EVENTS:
{chr(10).join(event_lines) if event_lines else '(none)'}"""

    return [
        {"role": "system", "content": SYSTEM_PROMPT},
        {"role": "user", "content": user_prompt},
    ]


def call_llm(messages: list) -> str:
    """Calls any OpenAI-compatible endpoint (Ollama locally, something else later)."""
    response = httpx.post(
        f"{LLM_BASE_URL}/chat/completions",
        headers={"Authorization": f"Bearer {LLM_API_KEY}"},
        json={
            "model": LLM_MODEL,
            "messages": messages,
            "temperature": 0.4,
            "response_format": {"type": "json_object"},
        },
        timeout=180,
    )
    response.raise_for_status()
    return response.json()["choices"][0]["message"]["content"]


def parse_json(text: str) -> dict:
    """Small models sometimes wrap JSON in ``` fences or add chatter. Cope with it."""
    text = re.sub(r"```(?:json)?", "", text).strip()
    start, end = text.find("{"), text.rfind("}")
    if start == -1 or end == -1:
        raise ValueError("No JSON object found in the model's reply")
    return json.loads(text[start:end + 1])


def validate(data: dict, places: list, events: list, n_stops: int) -> dict:
    """Turn Gemma's IDs back into REAL data. Anything it invented is dropped."""
    place_by_id = {f"P{i}": p for i, p in enumerate(places, 1)}
    event_by_id = {f"E{i}": e for i, e in enumerate(events, 1)}

    stops, seen = [], set()
    for s in data.get("stops", []):
        pid = str(s.get("id", "")).strip().upper()
        if pid in place_by_id and pid not in seen:
            seen.add(pid)
            p = place_by_id[pid]
            stops.append({
                "name": p["name"],
                "category": p["category"],
                "lat": p["lat"],
                "lon": p["lon"],
                "distance_m": p["distance_m"],
                "why": str(s.get("why", "")).strip(),
                "tip": str(s.get("tip", "")).strip(),
            })
    stops = stops[:n_stops]
    if not stops:
        raise ValueError("Gemma returned no valid stops")

    event = None
    ev = data.get("event")
    if isinstance(ev, dict):
        eid = str(ev.get("id", "")).strip().upper()
        if eid in event_by_id:
            e = event_by_id[eid]
            event = {
                "title": e["title"],
                "date": e.get("date"),
                "venue": e.get("venue"),
                "link": e.get("link"),
                "type": e.get("type"),
                "why": str(ev.get("why", "")).strip(),
            }

    intro = str(data.get("intro", "")).strip() or "Hi, I'm Pip! I found something fun for you."
    return {"intro": intro, "stops": stops, "event": event, "fallback": False}


def fallback_result(places: list, events: list, n_stops: int) -> dict:
    """Used when Gemma fails twice. No AI, just the best-ranked real places."""
    stops = [{
        "name": p["name"], "category": p["category"], "lat": p["lat"], "lon": p["lon"],
        "distance_m": p["distance_m"],
        "why": f"A {p['category']} about {p['distance_m']} m away.", "tip": "",
    } for p in places[:n_stops]]

    event = None
    if events:
        e = events[0]
        event = {"title": e["title"], "date": e.get("date"), "venue": e.get("venue"),
                 "link": e.get("link"), "type": e.get("type"), "why": ""}

    return {
        "intro": "Pip's brain is napping, so here are the best spots I could find. Now go outside!",
        "stops": stops, "event": event, "fallback": True,
    }


def recommend(answers: dict, places: list, events: list) -> dict:
    """Main function: always returns a result, never crashes."""
    n_stops = DURATIONS[answers["duration"]]["stops"]
    if not places:
        return {"intro": "Hmm, I couldn't find anything nearby. Try another mood or a bigger area!",
                "stops": [], "event": None, "fallback": True}

    messages = build_messages(answers, places, events, n_stops)
    for attempt in (1, 2):
        try:
            raw = call_llm(messages)
            return validate(parse_json(raw), places, events, n_stops)
        except Exception as e:
            print(f"  (Gemma attempt {attempt} failed: {type(e).__name__}: {e})")
    return fallback_result(places, events, n_stops)


# ---------- Quick test ----------

# Sample places for testing Gemma when Overpass is down.
# Coordinates are approximate and only used for this test.
SAMPLE_PLACES = [
    {"name": "Fruitmarket Gallery", "category": "gallery", "lat": 55.9519, "lon": -3.1887, "distance_m": 400, "website": None, "opening_hours": None},
    {"name": "Collective", "category": "gallery", "lat": 55.9547, "lon": -3.1815, "distance_m": 900, "website": None, "opening_hours": None},
    {"name": "Talbot Rice Gallery", "category": "gallery", "lat": 55.9470, "lon": -3.1888, "distance_m": 1100, "website": None, "opening_hours": None},
    {"name": "Summerhall", "category": "arts centre", "lat": 55.9400, "lon": -3.1812, "distance_m": 2300, "website": None, "opening_hours": None},
    {"name": "Scottish National Gallery of Modern Art", "category": "gallery", "lat": 55.9514, "lon": -3.2279, "distance_m": 3000, "website": None, "opening_hours": None},
]

if __name__ == "__main__":
    from geo import geocode, find_places
    from search import find_events

    answers = {"location": "Edinburgh", "mood": "creative",
               "duration": "1-2hrs", "time_of_day": "afternoon"}

    try:
        spot = geocode(answers["location"])
        found = find_places(spot["lat"], spot["lon"], answers["mood"], answers["duration"])
        places = found["places"]
        answers["mood"] = found["mood_used"]  # so "surprise" stays consistent
    except Exception as e:
        print(f"\n(Overpass failed: {e})\n(Using SAMPLE_PLACES so we can still test Gemma)\n")
        places = SAMPLE_PLACES

    events = find_events(answers["location"], answers["mood"])

    print(f"\nAsking {LLM_MODEL}... (the first call can take a minute)")
    start = time.time()
    result = recommend(answers, places, events)
    print(f"Done in {time.time() - start:.1f}s\n")
    print(json.dumps(result, indent=2, ensure_ascii=False))