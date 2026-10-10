import os
from typing import Literal

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field

from geo import geocode, find_places
from llm import recommend

app = FastAPI(title="Mochi the Explorer API")

origins = os.getenv("ALLOWED_ORIGINS", "http://localhost:5173").split(",")
app.add_middleware(
    CORSMiddleware,
    allow_origins=[o.strip() for o in origins],
    allow_methods=["*"],
    allow_headers=["*"],
)


class Answers(BaseModel):
    """The four questions Mochi asks. Anything else is rejected automatically."""
    location: str = Field(min_length=2, max_length=100)
    mood: Literal["cosy", "outdoors", "adventurous", "creative", "social",
                  "food", "history", "thrifting", "unusual", "surprise"]
    duration: Literal["30min", "1-2hrs", "half_day", "full_day", "multiple_days"]
    time_of_day: Literal["morning", "afternoon", "evening", "night", "anytime"]


@app.get("/api/health")
def health():
    return {"status": "ok"}


@app.post("/api/recommend")
def api_recommend(body: Answers):
    # 1. Where is the user?
    try:
        spot = geocode(body.location)
    except Exception:
        raise HTTPException(503, "The map search service is busy. Please try again.")
    if not spot:
        raise HTTPException(404, f"I couldn't find '{body.location}'. Try a city name!")

    # 2. Real places nearby
    try:
        found = find_places(spot["lat"], spot["lon"], body.mood, body.duration)
    except Exception:
        raise HTTPException(503, "The places service is busy. Please try again in a minute.")

    mood_used = found["mood_used"]  # resolves "surprise" to a real mood

    # 4. Gemma writes the recommendation
    answers = {
        "location": body.location,
        "mood": mood_used,
        "duration": body.duration,
        "time_of_day": body.time_of_day,
    }
    result = recommend(answers, found["places"])

    result["mood_used"] = mood_used
    result["center"] = {"lat": spot["lat"], "lon": spot["lon"],
                        "name": spot["display_name"]}
    return result