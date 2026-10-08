from geo import geocode, find_places

spot = geocode("Pisticci, Italy")
for run in range(1, 6):
    result = find_places(spot["lat"], spot["lon"], "outdoors", "half_day")
    print(f"Run {run}")
    print(f"  tag:    {result['tags_used']}")
    print(f"  radius: {result['radius_m']} m")
    print(f"  places: {[p['name'] for p in result['places'][:6]]}\n")