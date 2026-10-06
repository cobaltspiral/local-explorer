import random

# Each mood maps to a list of (key, value) OpenStreetMap tags.
# Example: ("amenity", "cafe") means "anything tagged amenity=cafe".
MOOD_TAGS = {
    "cosy": [
        ("amenity", "cafe"), ("amenity", "library"),
        ("shop", "books"), ("shop", "tea"),
    ],
    "outdoors": [
        ("leisure", "park"), ("leisure", "garden"),
        ("natural", "peak"), ("tourism", "viewpoint"),
    ],
    "adventurous": [
        ("natural", "peak"), ("leisure", "nature_reserve"),
        ("sport", "climbing"), ("waterway", "waterfall"),
    ],
    "creative": [
        ("tourism", "gallery"), ("tourism", "artwork"),
        ("amenity", "arts_centre"),
    ],
    "social": [
        ("amenity", "pub"), ("amenity", "bar"),
        ("leisure", "bowling_alley"), ("amenity", "biergarten"),
    ],
    "food": [
        ("amenity", "restaurant"), ("amenity", "marketplace"),
        ("amenity", "food_court"),
    ],
    "history": [
        ("tourism", "museum"), ("historic", "castle"),
        ("historic", "monument"), ("historic", "ruins"),
        ("historic", "archaeological_site"), ("historic", "fort"),
    ],
    "thrifting": [
        ("shop", "second_hand"), ("shop", "charity"),
        ("shop", "antiques"), ("amenity", "marketplace"),
    ],
    "unusual": [
        ("tourism", "attraction"), ("historic", "ruins"),
        ("man_made", "lighthouse"), ("tourism", "artwork"),
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


def pick_mood(mood: str) -> str:
    """Turns 'surprise' into a random real mood. Passes others through."""
    if mood == "surprise":
        return random.choice(list(MOOD_TAGS.keys()))
    return mood