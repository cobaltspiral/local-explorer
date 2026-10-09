import os
from urllib.parse import urlparse
from dotenv import load_dotenv
import math
import time
import httpx
import random

load_dotenv()

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

PUBLIC_OVERPASS_URLS = [
    "https://overpass-api.de/api/interpreter",
    "https://overpass.kumi.systems/api/interpreter",
    "https://overpass.private.coffee/api/interpreter",
]

# Your private endpoint goes first if it's set in .env
PRIVATE_OVERPASS = os.getenv("OVERPASS_PRIVATE_URL")
OVERPASS_URLS = ([PRIVATE_OVERPASS] if PRIVATE_OVERPASS else []) + PUBLIC_OVERPASS_URLS

# Used to label each place (e.g. "cafe", "park").
CATEGORY_KEYS = ["amenity", "leisure", "tourism", "historic",
                 "shop", "natural", "man_made", "sport", "waterway"]

# A place with any of these tags is probably real and still operating
DETAIL_KEYS = ["opening_hours", "website", "phone", "description"]

# Backup chain list, for chains nobody tagged with a "brand" in OpenStreetMap.
# Add the chains you keep seeing in your city.
CHAIN_NAMES = {
    "starbucks", "costa", "costa coffee", "caffè nero", "caffe nero",
    "pret a manger", "greggs", "mcdonald's", "burger king", "kfc", "subway",
    "tesco", "sainsbury's", "wetherspoons", "five guys", "nando's",
    "pizza express", "wagamama", "black sheep coffee", "hospital", "prison",
    "bridal", "motel", "apartment", "clinic", "pharmacy",
}


def is_chain_name(name: str) -> bool:
    n = name.lower().strip()
    return any(n == c or n.startswith(c + " ") for c in CHAIN_NAMES)


PER_TAG_LIMIT = 50
TAGS_PER_REQUEST = 1 


def build_query(lat: float, lon: float, tags: list, radius_m: int) -> str:
    """One statement per tag, each with its own result limit.

    'nw' = nodes and ways. ["name"] keeps only named places.
    Each 'out' caps that tag's results, so no tag crowds out the others.
    """
    parts = [
        f'nw["{key}"="{value}"]["name"](around:{radius_m},{lat},{lon});\n'
        f'out center tags {PER_TAG_LIMIT};'
        for key, value in tags
    ]
    return "[out:json][timeout:25];\n" + "\n".join(parts)


def run_overpass(query: str) -> list:
    """Tries each server in turn, retrying with a pause if all are busy."""
    last_error = None
    for attempt in range(3):
        for url in OVERPASS_URLS:
            label = urlparse(url).netloc  # e.g. "overpass.nextgis.com", never the key
            try:
                response = httpx.post(
                    url, data={"data": query}, headers=HEADERS, timeout=40
                )
                response.raise_for_status()
                data = response.json()

                remark = data.get("remark", "")
                if "runtime error" in remark.lower() or "timed out" in remark.lower():
                    raise ValueError(f"server remark: {remark}")

                return data["elements"]
            except httpx.HTTPStatusError as e:
                last_error = f"{label} -> HTTP {e.response.status_code}"
            except (httpx.HTTPError, ValueError) as e:
                last_error = f"{label} -> {type(e).__name__}"
            print(f"  (Overpass problem: {last_error})")
        wait = 5 * (attempt + 1)
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
    """Turns raw Overpass results into clean place dicts, tagged by 'tier':
    0 = independent, 1 = well-known landmark, 2 = chain."""
    places = []
    for el in elements:
        tags = el.get("tags", {})
        name = tags.get("name")
        if not name:
            continue  # skip anything without a name

        # Skip embassies and other offices that are mis-tagged as sights
        if tags.get("amenity") == "embassy" or tags.get("office") == "diplomatic":
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

        if tags.get("brand") or tags.get("brand:wikidata") or is_chain_name(name):
            tier = 2
        elif tags.get("wikipedia") or tags.get("wikidata"):
            tier = 1
        else:
            tier = 0

        places.append({
            "name": name,
            "category": category.replace("_", " "),
            "lat": p_lat,
            "lon": p_lon,
            "distance_m": round(distance_m(lat, lon, p_lat, p_lon)),
            "website": tags.get("website"),
            "opening_hours": tags.get("opening_hours"),
            "_tier": tier,
            "_details": any(k in tags for k in DETAIL_KEYS),
        })

    # Drop duplicate names (keeps the nearest branch)
    places.sort(key=lambda p: p["distance_m"])
    seen, unique = set(), []
    for p in places:
        key = p["name"].lower()
        if key in seen:
            continue
        seen.add(key)
        unique.append(p)
    return unique


def diversify(pool: list, limit: int = 20) -> list:
    """Pick a fresh, different selection every time: independents first,
    random within each tier, with a small boost for well-documented places."""
    ranked = sorted(
        pool,
        key=lambda p: (p["_tier"], -(random.random() + (0.5 if p["_details"] else 0))),
    )
    picked = ranked[:limit]
    random.shuffle(picked)  # so list position tells Gemma nothing
    return [{k: v for k, v in p.items() if not k.startswith("_")} for p in picked]


def _search(lat, lon, tags, radius_m):
    query = build_query(lat, lon, tags, radius_m)
    return parse_elements(run_overpass(query), lat, lon)


_places_cache: dict = {}

def find_places(lat: float, lon: float, mood: str, duration: str) -> dict:
    """A fresh random selection of up to 20 candidate places."""
    mood = pick_mood(mood)
    radius = DURATIONS[duration]["radius_m"]
    all_tags = MOOD_TAGS[mood]

    chosen = random.sample(all_tags, min(TAGS_PER_REQUEST, len(all_tags)))

    def fetch(tags, rad):
        key = (round(lat, 2), round(lon, 2), tuple(sorted(tags)), rad)
        if key in _places_cache:
            print("  (places: cache hit)")
            return _places_cache[key]
        pool = _search(lat, lon, tags, rad)
        if pool:  # only cache real answers
            _places_cache[key] = pool
        return pool

    pool = fetch(chosen, radius)

    # Too few results? Widen the radius and try a different tag (still just one).
    if len(pool) < 3:
        radius *= 2
        others = [t for t in all_tags if t not in chosen] or all_tags
        pool = fetch(random.sample(others, 1), radius)

    return {"mood_used": mood, "radius_m": radius, "places": diversify(pool), "tags_used": [f"{key}={value}" for key, value in chosen],}


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