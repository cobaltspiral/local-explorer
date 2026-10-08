import random

# Each mood maps to a list of (key, value) OpenStreetMap tags.
# Example: ("amenity", "cafe") means "anything tagged amenity=cafe".
MOOD_TAGS = {
    "cosy": [
        ("amenity", "cafe"), ("cuisine", "ice_cream"), 
        ("cuisine", "bakery"), ("cuisine", "bubble_tea"), 
        ("amenity", "library"), ("shop", "bookstore"), 
        ("shop", "bakery"), ("shop", "books"),
        ("shop", "esoteric")

    ],

    "outdoors": [
        ("leisure", "park"), ("natural", "water"), 
        ("natural", "beach"), ("leisure", "garden"), 
        ("natural", "hills"), ("water", "canal"),
        ("water", "river"), ("water", "stream"), 
        ("water", "lake"), ("water", "waterfall"),
        ("leisure", "swimming_pool"), ("leisure", "park"),
        ("leisure", "beach"),

    ],

    "adventurous": [
        ("natural", "peak"), ("natural", "cliff"), 
        ("natural", "waterfall"), ("natural", "viewpoint"), 
        ("natural", "forest"),  ("water", "lake"),
        ("water", "river"),  ("leisure", "nature_reserve"),
        ("leisure", "hiking"), ("leisure", "wild_swimming"), 
        ("water", "reservoir"), ("water", "lake"),
    ],

    "creative": [
        ("tourism", "gallery"),
    ],

    "social": [
        ("amenity", "pub"), ("leisure", "sauna"), 
        ("leisure", "social_club"), ("leisure", "axe_throwing"), 
        ("leisure", "escape_game"), ("leisure", "nightclub"), 
        ("leisure", "music_venue"), ("leisure", "karaoke"),
        ("leisure", "rage_room"), ("leisure", "bingo_hall"),
    ],

    "food": [
        ("amenity", "restaurant"),
    ],

    "history": [
        ("tourism", "museum"), ("building", "castle"), ("historic", "castle"),
    ],

    "thrifting": [
        ("shop", "second_hand"), ("shop", "charity"), 
        ("shop", "antiques"),
    ],

    "unusual": [
        ("man_made", "lighthouse"), ("building", "bunker"), 
        ("building", "airport"),
        ("natural", "volcano"), ("natural", "island"), 
        ("natural", "geyser"), ("natural", "hot_spring"), 
        ("natural", "spring"), ("natural", "rock"), 
        ("natural", "cliff"),
        ("natural", "valley"), ("natural", "glacier"), 
        ("natural", "waterfall"), ("leisure", "ice_rink"),
        ("leisure", "axe_throwing"), ("leisure", "escape_game"),
        ("leisure", "rage_room"),
        ("man_made", "gasometer"), ("shop", "psychic"), 
        ("shop", "esoteric"), ("shop", "junk_yard"),

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