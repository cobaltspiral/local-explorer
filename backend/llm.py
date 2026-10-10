import json
import os
import random
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
- Refer to places ONLY by their ID (like P3 or E2). Never invent an ID or a place.
- Choose places that suit the mood, the time of day and the time available. For evening or night, prefer bars, restaurants and lively places. For morning, prefer parks, cafes and markets.
- Keep "why" to one short sentence and "tip" to one short, practical sentence.
- Never write IDs like P1 or E2 inside "why" or "tip". Use the place's name instead.
- You're only choosing one place to recommend, so use the singular form in your last message, e.g., "I found a fun spot for you" not "I found some fun spots for you".
- In your last message, if you found a spot, don't mention the type (e.g., "I found a cosy place for you", but not "I found these bookshops for you").
- The user LIVES here and has probably seen the obvious spots, so help them discover somewhere new. Prefer lesser-known, independent, local-feeling places over famous ones, and avoid big chains.
- The list is in random order. Do not favour the first items, and do not favour the closest. Pick something a little unexpected that still fits the mood.
- When choosing several stops, try your best to pick different kinds of place rather than several of the same kind.
- Reply with JSON only, in exactly this shape:
{"stops": [{"id": "P1", "why": "...", "tip": "..."}]}"""


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
    # Hosted OpenAI-style endpoint (e.g. Google AI Studio).
    # Some hosted Gemma models reject a separate system message and JSON mode,
    # so fold the system prompt into the user message and rely on parse_json().
    merged = [{
        "role": "user",
        "content": messages[0]["content"] + "\n\n" + messages[1]["content"],
    }]
    response = httpx.post(
        f"{LLM_BASE_URL}/chat/completions",
        headers={"Authorization": f"Bearer {LLM_API_KEY}"},
        json={
            "model": LLM_MODEL,
            "messages": merged,
            "temperature": 0.4,
            "max_tokens": 700,
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
    """Turn Gemma's IDs back into REAL data, with one tag per stop where possible."""
    place_by_id = {f"P{i}": p for i, p in enumerate(places, 1)}
    names = {k: p["name"] for k, p in place_by_id.items()}

    # 1. Gemma's valid, unique picks, in the order it gave them
    picks, seen_ids = [], set()
    for s in data.get("stops", []):
        pid = str(s.get("id", "")).strip().upper()
        if pid in place_by_id and pid not in seen_ids:
            seen_ids.add(pid)
            picks.append((pid, s))
    if not picks:
        raise ValueError("Gemma returned no valid stops")

    # 2. Keep one pick per tag; set aside the repeats
    chosen, used_tags, repeats = [], set(), []
    for pid, s in picks:
        tag = place_by_id[pid].get("tag")
        if tag in used_tags:
            repeats.append((pid, s))
        else:
            chosen.append((pid, s))
            used_tags.add(tag)
    chosen_ids = {pid for pid, _ in chosen}

    # 3. Still short? Add places from tags not used yet
    for pid, p in place_by_id.items():
        if len(chosen) >= n_stops:
            break
        if pid not in chosen_ids and p.get("tag") not in used_tags:
            chosen.append((pid, {}))
            chosen_ids.add(pid)
            used_tags.add(p.get("tag"))

    # 4. Still short (more stops than tags)? Allow repeats, Gemma's picks first
    for pid, s in repeats + [(pid, {}) for pid in place_by_id]:
        if len(chosen) >= n_stops:
            break
        if pid not in chosen_ids:
            chosen.append((pid, s))
            chosen_ids.add(pid)
    chosen = chosen[:n_stops]

    stops = []
    for pid, s in chosen:
        p = place_by_id[pid]
        stops.append({
            "name": p["name"],
            "category": p["category"],
            "lat": p["lat"],
            "lon": p["lon"],
            "distance_m": p["distance_m"],
            "why": clean_text(str(s.get("why", "")).strip(), names)
                   or f"A {p['category']} about {p['distance_m']} m away.",
            "tip": clean_text(str(s.get("tip", "")).strip(), names),
        })

    # recommend() overwrites this with make_message(), so this is only a default
    return {"message": "I found something fun for you!", "stops": stops,
            "fallback": False}


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


MOOD_PHRASE = {
    "cosy": "a cosy outing",
    "outdoors": "a breath of fresh air",
    "adventurous": "a little adventure",
    "creative": "a creative outing",
    "social": "a sociable outing",
    "food": "something tasty",
    "history": "a trip into the past",
    "thrifting": "a treasure hunt",
    "unusual": "something a bit different",
}

# Safe wording: no counts, no place types, no "we", no time of day.
MESSAGES_ONE_STOP = [
    "I found {phrase} for you: head to {name}! Put your phone away and enjoy it.",
    "How about {name}? It's {phrase} waiting for you. Phone in your pocket, off you go!",
    "Your next stop is {name}. Leave the screen behind and go and see it!",
]
MESSAGES_MANY_STOPS = [
    "I found {phrase} for you. Start with {name}! Put your phone away and enjoy it.",
    "Here's {phrase} for today, starting at {name}. Phone in your pocket, off you go!",
    "Time for {phrase}! Begin at {name}, then follow the map. Leave the screen behind!",
]


def make_message(answers: dict, stops: list) -> str:
    phrase = MOOD_PHRASE.get(answers["mood"], "something fun")
    pool = MESSAGES_ONE_STOP if len(stops) == 1 else MESSAGES_MANY_STOPS
    return random.choice(pool).format(phrase=phrase, name=stops[0]["name"])


def recommend(answers: dict, places: list) -> dict:
    """Main function: always returns a result, never crashes."""
    n_stops = DURATIONS[answers["duration"]]["stops"]
    print(f"  (debug: {len(places)} places available, {n_stops} stops wanted)")
    if not places:
        return {"message": "Hmm, I couldn't find anything nearby. Try another mood or a bigger area!",
                "stops": [], "fallback": True}

    messages = build_messages(answers, places, n_stops)
    for attempt in (1, 2):
        try:
            raw = call_llm(messages)
            result = validate(parse_json(raw), places, n_stops)
            result["message"] = make_message(answers, result["stops"])
            return result
        except Exception as e:
            print(f"  (Gemma attempt {attempt} failed: {type(e).__name__}: {e})")
    result = fallback_result(places, n_stops)
    return result


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