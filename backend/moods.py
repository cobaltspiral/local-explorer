import random

# Each mood maps to a list of (key, value) OpenStreetMap tags.
# Example: ("amenity", "cafe") means "anything tagged amenity=cafe".
MOOD_TAGS = {
    "cosy": [
        ("amenity", "cafe"),
    ],
    "outdoors": [
        ("leisure", "park"),
    ],
    "adventurous": [
        ("natural", "peak"),
    ],
    "creative": [
        ("tourism", "gallery"),
    ],
    "social": [
        ("amenity", "pub"),
    ],
    "food": [
        ("amenity", "restaurant"), ("amenity", "marketplace"),
        ("amenity", "food_court"),
    ],
    "history": [
        ("tourism", "museum"),
    ],
    "thrifting": [
        ("shop", "second_hand"), ("shop", "charity"),
        ("shop", "antiques"),
    ],
    "unusual": [
        ("man_made", "lighthouse"),
    ],
}

# How far to search, and how many stops to recommend, per duration.
DURATIONS = {
    "30min":         {"radius_m": 1500,  "stops": 1},
    "1-2hrs":        {"radius_m": 4000,  "stops": 2},
    "half_day":      {"radius_m": 10000, "stops": 3},
    "full_day":      {"radius_m": 20000, "stops": 5},
    "multiple_days": {"radius_m": 40000, "stops": 8},
}

MOOD_EVENT_QUERY = {
    "cosy": "cosy events book readings",
    "outdoors": "outdoor events",
    "adventurous": "outdoor adventure events",
    "creative": "art exhibitions and creative workshops",
    "social": "social events and meetups",
    "food": "food markets and food festivals",
    "history": "history exhibitions and tours",
    "thrifting": "flea markets and vintage markets",
    "unusual": "unusual and quirky events",
}

def pick_mood(mood: str) -> str:
    """Turns 'surprise' into a random real mood. Passes others through."""
    if mood == "surprise":
        return random.choice(list(MOOD_TAGS.keys()))
    return mood