from geo import geocode, find_places

spot = geocode("Edinburgh")
for run in range(1, 5):
    result = find_places(spot["lat"], spot["lon"], "cosy", "1-2hrs")
    names = [p["name"] for p in result["places"][:8]]
    print(f"Run {run}: {names}\n")