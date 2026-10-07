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
LLM_MODEL = os.getenv("LLM_MODEL", "gemma4:e2b")
LLM_API_KEY = os.getenv("LLM_API_KEY", "ollama")
LLM_TIMEOUT = int(os.getenv("LLM_TIMEOUT", 120))

TIME_HINTS = {
    "morning": "morning (before midday)",
    "afternoon": "afternoon",
    "evening": "evening",
    "night": "late at night",
    "anytime": "any time of day",
}

SYSTEM_PROMPT = """You are Mochi, a cheerful pixel-art travel guide who loves getting people outside.
You recommend things using ONLY the numbered lists you are given.
Rules:
- Refer to places ONLY by their ID (like P3 or E2). Never invent an ID or a place or an event.
- Choose places that suit the mood, the time of day and the time available. For evening or night, prefer bars, restaurants and lively places. For morning, prefer parks, cafes and markets.
- Keep "why" to one short sentence and "tip" to one short, practical sentence.
- "message" is two short sentences in Mochi's cheerful voice, and it ends by nudging the person to put their phone away and enjoy the outing. Don't greet the user (e.g., no 'hi', hello there' etc.).
- Never write IDs like P1 or E2 inside "message", "why" or "tip". Use the place's name instead.
- You're only choosing one place to recommend, so use the singular form in your message, e.g., "I found a fun spot for you" not "I found some fun spots for you".
- The user LIVES here and has probably seen the obvious spots, so help them discover somewhere new. Prefer lesser-known, independent, local-feeling places over famous ones, and avoid big chains.
- The list is in random order. Do not favour the first items, and do not favour the closest. Pick something a little unexpected that still fits the mood.
- Reply with JSON only, in exactly this shape:
{"message": "...", "stops": [{"id": "P1", "why": "...", "tip": "..."}]}"""


def build_messages(answers: dict, places: list, n_stops: int) -> list:
    place_lines = [
        f"P{i}: {p['name']} ({p['category']}), {p['distance_m']} m from the centre"
        for i, p in enumerate(places, 1)
    ]

    user_prompt = f"""Today is {date.today():%A %d %B %Y}.
The person is in {answers['location']}.
Mood: {answers['mood']}
Time available: {answers['duration']}
Time of day: {TIME_HINTS.get(answers['time_of_day'], answers['time_of_day'])}
Choose exactly {n_stops} stop(s) from the places, in a sensible order.

PLACES:
{chr(10).join(place_lines) if place_lines else '(none)'}"""

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
            "temperature": 0.6,
            "max_tokens": 700,
            "response_format": {"type": "json_object"},
            "reasoning_effort": "none",
        },
        timeout=LLM_TIMEOUT,
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


def clean_text(text: str, names: dict) -> str:
    """Replace any leaked IDs (P1, E2...) with the real name."""
    return re.sub(r"\b[PE]\d+\b",
                  lambda m: names.get(m.group(0).upper(), "this spot"), text)


def validate(data: dict, places: list, n_stops: int) -> dict:
    """Turn Gemma's IDs back into REAL data. Anything it invented is dropped."""
    place_by_id = {f"P{i}": p for i, p in enumerate(places, 1)}
    names = {k: p["name"] for k, p in place_by_id.items()}

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
                "why": clean_text(str(s.get("why", "")).strip(), names),
                "tip": clean_text(str(s.get("tip", "")).strip(), names),
            })
    stops = stops[:n_stops]
    if not stops:
        raise ValueError("Gemma returned no valid stops")

    message = clean_text(str(data.get("message", "")).strip(), names) or "Hi, I'm Mochi! I found something fun for you."
    return {"message": message, "stops": stops, "fallback": False}


def fallback_result(places: list, n_stops: int) -> dict:
    """Used when Gemma fails twice. No AI, just the best-ranked real places."""
    stops = [{
        "name": p["name"], "category": p["category"], "lat": p["lat"], "lon": p["lon"],
        "distance_m": p["distance_m"],
        "why": f"A {p['category']} about {p['distance_m']} m away.", "tip": "",
    } for p in places[:n_stops]]

    return {
        "message": "Mochi's brain is melting, so here are the best spots I could find. Now go outside!",
        "stops": stops, "fallback": True,
    }


def recommend(answers: dict, places: list) -> dict:
    """Main function: always returns a result, never crashes."""
    n_stops = DURATIONS[answers["duration"]]["stops"]
    if not places:
        return {"message": "Hmm, I couldn't find anything nearby. Try another mood or a bigger area!",
                "stops": [], "fallback": True}

    messages = build_messages(answers, places, n_stops)
    for attempt in (1, 2):
        try:
            raw = call_llm(messages)
            return validate(parse_json(raw), places, n_stops)
        except Exception as e:
            print(f"  (Gemma attempt {attempt} failed: {type(e).__name__}: {e})")
    return fallback_result(places, n_stops)


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


    print(f"\nAsking {LLM_MODEL}... (the first call can take a minute)")
    start = time.time()
    result = recommend(answers, places)
    print(f"Done in {time.time() - start:.1f}s\n")
    print(json.dumps(result, indent=2, ensure_ascii=False))