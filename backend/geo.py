import math
import time
import httpx

from moods import MOOD_TAGS, DURATIONS, pick_mood

NOMINATIM_URL = "https://nominatim.openstreetmap.org/search"

HEADERS = {"User-Agent": "local-explorer/0.1 (paola.ruffo@hotmail.com)"}

_last_call = 0.0

def geocode(query: str) -> dict | None:
    """Turn a place name like 'Lisbon' into coordinates.

    Returns {"lat": ..., "lon": ..., "display_name": ...}
    or None if the place wasn't found.
    """
    global _last_call

    # Nominatim's rule: max 1 request per second. Wait if needed.
    wait = 1.0 - (time.time() - _last_call)
    if wait > 0:
        time.sleep(wait)

    params = {"q": query, "format": "json", "limit": 1}
    response = httpx.get(NOMINATIM_URL, params=params, headers=HEADERS, timeout=10)
    _last_call = time.time()

    response.raise_for_status()
    results = response.json()

    if not results:
        return None

    top = results[0]
    return {
        "lat": float(top["lat"]), 
        "lon": float(top["lon"]),
        "display_name": top["display_name"],
    }

# The public Overpass servers get busy, so we try a second one if the first fails.
OVERPASS_URLS = [
    "https://overpass-api.de/api/interpreter",
    "https://overpass.kumi.systems/api/interpreter",
    "https://overpass.private.coffee/api/interpreter",
]

# Used to label each place (e.g. "cafe", "park").
CATEGORY_KEYS = ["amenity", "leisure", "tourism", "historic",
                 "shop", "natural", "man_made", "sport", "waterway"]

# Places with these tags are usually more notable (better-known, better-mapped).
RICHNESS_KEYS = ["wikipedia", "wikidata", "website", "opening_hours", "description"]


def build_query(lat: float, lon: float, tags: list, radius_m: int) -> str:
    """Builds the Overpass query text.

    'nw' means nodes and ways (points and buildings/areas). We skip relations,
    which are the slowest to search. ["name"] keeps only named places, so the
    server has far less to return.
    """
    parts = [
        f'nw["{key}"="{value}"]["name"](around:{radius_m},{lat},{lon});'
        for key, value in tags
    ]
    body = "\n  ".join(parts)
    return f"[out:json][timeout:20];\n(\n  {body}\n);\nout center tags 100;"


def run_overpass(query: str) -> list:
    """Sends the query, trying each server and retrying with a pause if busy."""
    last_error = None
    for attempt in range(3):
        for url in OVERPASS_URLS:
            try:
                response = httpx.post(
                    url, data={"data": query}, headers=HEADERS, timeout=40
                )
                response.raise_for_status()
                return response.json()["elements"]
            except (httpx.HTTPError, ValueError) as e:
                last_error = f"{url} -> {e!r}"
                print(f"  (Overpass problem: {last_error})")
        wait = 5 * (attempt + 1)  # wait 5s, then 10s, then 15s
        print(f"  Retrying in {wait}s...")
        time.sleep(wait)
    raise RuntimeError(f"All Overpass servers failed. Last error: {last_error}")


def distance_m(lat1, lon1, lat2, lon2) -> float:
    """Straight-line distance in metres between two points (haversine formula)."""
    r = 6371000
    p1, p2 = math.radians(lat1), math.radians(lat2)
    dp = p2 - p1
    dl = math.radians(lon2 - lon1)
    a = math.sin(dp / 2) ** 2 + math.cos(p1) * math.cos(p2) * math.sin(dl / 2) ** 2
    return 2 * r * math.asin(math.sqrt(a))


def parse_elements(elements: list, lat: float, lon: float) -> list:
    """Turns raw Overpass results into clean, deduplicated place dicts."""
    places = []
    for el in elements:
        tags = el.get("tags", {})
        name = tags.get("name")
        if not name:
            continue

        # Points have lat/lon directly. Buildings and areas have a 'center'.
        if el["type"] == "node":
            p_lat, p_lon = el["lat"], el["lon"]
        else:
            center = el.get("center")
            if not center:
                continue
            p_lat, p_lon = center["lat"], center["lon"]

        category = next((tags[k] for k in CATEGORY_KEYS if k in tags), "place")
        richness = sum(1 for k in RICHNESS_KEYS if k in tags)

        places.append({
            "name": name,
            "category": category.replace("_", " "),
            "lat": p_lat,
            "lon": p_lon,
            "distance_m": round(distance_m(lat, lon, p_lat, p_lon)),
            "website": tags.get("website"),
            "opening_hours": tags.get("opening_hours"),
            "_richness": richness,
        })

    # Best-known first, then closest. Then drop duplicate names.
    places.sort(key=lambda p: (-p["_richness"], p["distance_m"]))
    seen, unique = set(), []
    for p in places:
        key = p["name"].lower()
        if key in seen:
            continue
        seen.add(key)
        p.pop("_richness")
        unique.append(p)
    return unique


def _search(lat, lon, tags, radius_m):
    query = build_query(lat, lon, tags, radius_m)
    return parse_elements(run_overpass(query), lat, lon)


_places_cache: dict = {}

def find_places(lat: float, lon: float, mood: str, duration: str) -> dict:
    """Main function: find up to 20 candidate places for this mood and duration."""
    mood = pick_mood(mood)

    cache_key = (round(lat, 2), round(lon, 2), mood, duration)
    if cache_key in _places_cache:
        print("  (places: cache hit)")
        return _places_cache[cache_key]

    radius = DURATIONS[duration]["radius_m"]
    tags = MOOD_TAGS[mood]

    places = _search(lat, lon, tags, radius)

    # Small town with few results? Widen the search once.
    if len(places) < 3:
        radius *= 2
        places = _search(lat, lon, tags, radius)

    result = {"mood_used": mood, "radius_m": radius, "places": places[:20]}
    if places:  # only cache real answers
        _places_cache[cache_key] = result
    return result


if __name__ == "__main__":
    spot = geocode("Edinburgh")
    print("Geocoded:", spot["display_name"], "\n")

    for mood, duration in [("cosy", "30min"), ("history", "half_day"), ("surprise", "1-2hrs")]:
        result = find_places(spot["lat"], spot["lon"], mood, duration)
        print(f"--- {mood} / {duration}  (mood used: {result['mood_used']}, "
              f"radius: {result['radius_m']} m, {len(result['places'])} places) ---")
        for p in result["places"][:5]:
            print(f"  {p['name']}  [{p['category']}]  {p['distance_m']} m")
        print()
        time.sleep(5)  # be polite to the free Overpass servers