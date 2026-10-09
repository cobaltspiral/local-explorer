from geo import geocode, find_places

spot = geocode("Edinburgh")
for run in range(1, 4):
    result = find_places(spot["lat"], spot["lon"], "outdoors", "full_day")
    print(f"Run {run}  tags queried: {result['tags_used']}")
    for p in result["places"][:8]:
        print(f"   {p['name']}  [{p['tag']}]")
    print()