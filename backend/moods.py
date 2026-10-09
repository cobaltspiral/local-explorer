import random

# Each mood maps to a list of (key, value) OpenStreetMap tags.
# Example: ("amenity", "cafe") means "anything tagged amenity=cafe".
MOOD_TAGS = {
    "cosy": [
        ("amenity", "cafe"), 
        ("cuisine", "ice_cream"), 
        ("cuisine", "bubble_tea"),
        ("amenity", "library"),
        ("shop", "bookstore"), 
        ("shop", "bakery"), 
        ("shop", "books"),
    ],

    "outdoors": [
        ("leisure", "park"), 
        ("natural", "water"), 
        ("natural", "beach"),  
        ("natural", "hills"), 
        ("water", "canal"),
        ("water", "river"), 
        ("water", "lake"), 
        ("leisure", "park"),
    ],

    "adventurous": [
        ("natural", "peak"), 
        ("natural", "cliff"),
        ("natural", "forest"),  
        ("water", "lake"),
        ("water", "river"),
        ("leisure", "nature_reserve"),
    ],

    "creative": [
        ("tourism", "gallery"),
        ("amenity", "theatre"),
        ("amenity", "arts_centre"),
        ("amenity", "cinema"),
        ("shop", "art"),
        ("shop", "craft"),
        ("amenity", "music_venue"),
        ("amenity", "concert_hall"),
    ],

    "social": [
        ("amenity", "pub"),
        ("amenity", "bar"),
        ("leisure", "axe_throwing"), 
        ("leisure", "escape_game"), 
        ("leisure", "nightclub"), 
        ("leisure", "music_venue"), 
        ("leisure", "karaoke"),
        ("leisure", "rage_room"), 
        ("leisure", "bingo_hall"),
        ("amenity", "community_centre"),
    ],

    "food": [
        ("amenity", "restaurant"),
        ("amenity", "cafe"),
        ("amenity", "pub"),
        ("amenity", "food_court"),
    ],

    "history": [
        ("tourism", "museum"), 
        ("historic", "castle"),
        ("historic", "monument"),
        ("historic", "church"),
    ],

    "thrifting": [
        ("shop", "second_hand"), 
        ("shop", "charity"), 
        ("shop", "antiques"),
    ],

    "unusual": [
        ("man_made", "lighthouse"), 
        ("building", "bunker"), 
        ("building", "airport"),
        ("natural", "volcano"), 
        ("natural", "island"), 
        ("natural", "geyser"), 
        ("natural", "hot_spring"), 
        ("natural", "spring"), 
        ("natural", "rock"), 
        ("natural", "cliff"),
        ("natural", "valley"), 
        ("natural", "glacier"), 
        ("natural", "waterfall"), 
        ("leisure", "ice_rink"),
        ("leisure", "axe_throwing"), 
        ("leisure", "escape_game"),
        ("leisure", "rage_room"),
        ("man_made", "gasometer"), 
        ("shop", "psychic"), 
        ("shop", "esoteric"), 
        ("shop", "junk_yard"),
        ("amenity", "planetarium"),
    ],
}


DURATIONS = {
    "30min":         {"radius_m": 1500,  "stops": 1},
    "1-2hrs":        {"radius_m": 4000,  "stops": 1},
    "half_day":      {"radius_m": 10000, "stops": 2},
    "full_day":      {"radius_m": 20000, "stops": 4},
    "multiple_days": {"radius_m": 40000, "stops": 6},
}


def pick_mood(mood: str) -> str:
    """Turns 'surprise' into a random real mood. Passes others through."""
    if mood == "surprise":
        return random.choice(list(MOOD_TAGS.keys()))
    return mood