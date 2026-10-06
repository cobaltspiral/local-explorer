import time
import httpx

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

if __name__ == "__main__":
    for place in ["Lisbon", "Brooklyn, New York", "Pisticci", "asdkjhasdkjh"]:
        print(place, "->", geocode(place))