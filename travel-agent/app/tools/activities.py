"""
tools/activities.py — Sprint 3A
─────────────────────────────────
Real activity/attraction data via Google Places API (New).
Searches for tourist attractions, activities, restaurants
matching the traveler's interests.

Falls back to mock data if key missing or call fails.

API docs: https://developers.google.com/maps/documentation/places/web-service
Free tier: $200/month credit (~10,000 nearby searches free

Key format in .env:
  GOOGLE_PLACES_API_KEY=your_key_here
  USE_REAL_ACTIVITIES=true
"""

import requests
import json
from openai import OpenAI
from app.core.config import config
from app.utils.mock_data import get_mock_activities

# Google Places API (New) endpoints
PLACES_SEARCH_URL  = "https://places.googleapis.com/v1/places:searchText"
PLACES_NEARBY_URL  = "https://places.googleapis.com/v1/places:searchNearby"
GEOCODE_URL        = "https://maps.googleapis.com/maps/api/geocode/json"

# Map our interest tags → Google place types
INTEREST_TO_TYPES = {
    "adventure":  ["amusement_park", "campground", "hiking_area", "rafting"],
    "spiritual":  ["hindu_temple", "mosque", "church", "place_of_worship", "ashram"],
    "food":       ["restaurant", "cafe", "bakery", "meal_takeaway"],
    "nature":     ["park", "national_park", "hiking_area", "waterfall", "natural_feature"],
    "culture":    ["museum", "art_gallery", "tourist_attraction", "historical_landmark"],
    "shopping":   ["shopping_mall", "market", "store"],
    "wellness":   ["spa", "yoga_studio", "gym"],
    "nightlife":  ["bar", "night_club", "casino"],
}

# Fields to request from Places API (controls billing)
PLACE_FIELDS = [
    "places.displayName",
    "places.editorialSummary",
    "places.rating",
    "places.userRatingCount",
    "places.priceLevel",
    "places.regularOpeningHours",
    "places.location",
    "places.googleMapsUri",
    "places.primaryTypeDisplayName",
    "places.photos",
]

_openai_client = None


def _openai() -> OpenAI:
    global _openai_client
    if not _openai_client:
        _openai_client = OpenAI(api_key=config.OPENAI_API_KEY)
    return _openai_client


def _is_international_dest(destination: str) -> bool:
    from app.agents import _is_indian_city
    return not _is_indian_city(destination)


def _geocode_city(city: str) -> tuple[float, float] | None:
    """Get lat/lng for a city using Google Geocoding API."""
    address = city if _is_international_dest(city) else f"{city}, India"
    resp = requests.get(GEOCODE_URL, params={
        "address": address,
        "key":     config.GOOGLE_PLACES_API_KEY,
    }, timeout=8)
    resp.raise_for_status()
    data = resp.json()
    if data.get("results"):
        loc = data["results"][0]["geometry"]["location"]
        return loc["lat"], loc["lng"]
    return None


def _search_places(query: str, lat: float, lng: float,
                   radius: int = 20000, max_results: int = 8) -> list[dict]:
    """
    Text search for places near a location.
    Uses Places API (New) textSearch endpoint.
    """
    headers = {
        "Content-Type":  "application/json",
        "X-Goog-Api-Key": config.GOOGLE_PLACES_API_KEY,
        "X-Goog-FieldMask": ",".join(PLACE_FIELDS),
    }
    body = {
        "textQuery":          query,
        "maxResultCount":     max_results,
        "locationBias": {
            "circle": {
                "center": {"latitude": lat, "longitude": lng},
                "radius": float(radius),
            }
        },
        "languageCode": "en",
    }
    resp = requests.post(PLACES_SEARCH_URL, headers=headers,
                         json=body, timeout=10)
    resp.raise_for_status()
    return resp.json().get("places", [])


def _price_level_to_inr(price_level: str | None, international: bool = False) -> int:
    """Map Google price level to approximate INR cost (fallback only)."""
    if international:
        mapping = {
            "PRICE_LEVEL_FREE":          0,
            "PRICE_LEVEL_INEXPENSIVE":   800,
            "PRICE_LEVEL_MODERATE":      2500,
            "PRICE_LEVEL_EXPENSIVE":     5000,
            "PRICE_LEVEL_VERY_EXPENSIVE": 8000,
        }
        return mapping.get(price_level or "", 0)
    mapping = {
        "PRICE_LEVEL_FREE":          0,
        "PRICE_LEVEL_INEXPENSIVE":   200,
        "PRICE_LEVEL_MODERATE":      600,
        "PRICE_LEVEL_EXPENSIVE":     1500,
        "PRICE_LEVEL_VERY_EXPENSIVE": 3000,
    }
    return mapping.get(price_level or "", 0)


def _hours_summary(opening_hours: dict | None) -> str:
    if not opening_hours:
        return "Check locally"
    periods = opening_hours.get("weekdayDescriptions", [])
    if periods:
        return periods[0]  # e.g. "Monday: 9:00 AM – 6:00 PM"
    return "Open daily"


def _places_to_activities(places: list[dict], interests: list[str],
                           destination: str, duration_days: int) -> list[dict]:
    """
    Convert raw Google Places results to our activity format.
    Uses GPT-4o to assign best_day, estimate real ticket prices,
    and write why_recommended.
    """
    if not places:
        return []

    international = _is_international_dest(destination)

    places_summary = []
    for i, p in enumerate(places[:10]):
        name    = p.get("displayName", {}).get("text", "Unknown")
        summary = p.get("editorialSummary", {}).get("text", "")
        rating  = p.get("rating", 0)
        count   = p.get("userRatingCount", 0)
        google_price_level = p.get("priceLevel", "")
        places_summary.append({
            "index": i,
            "name":  name,
            "summary": summary[:150],
            "rating": rating,
            "review_count": count,
            "google_price_level": google_price_level or "unknown",
        })

    prompt = f"""You are a travel planner with knowledge of actual attraction prices.
Given these places in {destination}, assign each one:
1. best_day: which day (1-{duration_days}) is best for this activity
2. duration_hours: realistic time to spend (0.5 - 4)
3. price_inr: the realistic entry/ticket price in Indian Rupees (₹).
   - Use your knowledge of actual ticket prices for well-known attractions.
   - For example: NYC observation decks cost $35-45 (~₹2,900-3,750),
     museums $20-30 (~₹1,650-2,500), walking in parks/public areas = 0.
   - Parks, public plazas, markets with no entry fee = 0
   - Convert from local currency to INR (1 USD ≈ ₹83, 1 EUR ≈ ₹90, 1 GBP ≈ ₹105)
   - For Indian destinations, use actual INR prices directly.
4. why_recommended: one sentence specific to interests: {', '.join(interests)}
5. activity_type: one of adventure/spiritual/cultural/nature/food/wellness/free_time

Return JSON: {{"activities": [{{"index": 0, "best_day": 2, "duration_hours": 2.5,
"price_inr": 3000, "why_recommended": "...", "activity_type": "cultural"}}, ...]}}

Rules:
- Spread activities across different days
- Day 1 = arrival day (light activities only)
- Day {duration_days} = departure day (morning only)
- Duration should be realistic
- price_inr MUST be realistic — do NOT default everything to the same value
- Free attractions (parks, beaches, public squares) should have price_inr = 0"""

    resp = _openai().chat.completions.create(
        model=config.FAST_MODEL,
        temperature=0.2,
        response_format={"type": "json_object"},
        messages=[{"role": "user", "content": prompt +
                   f"\n\nPlaces:\n{json.dumps(places_summary, indent=2)}"}],
    )
    enrichment_list = json.loads(resp.choices[0].message.content)
    if isinstance(enrichment_list, dict):
        enrichment_list = enrichment_list.get("activities", enrichment_list.get("places", []))

    enrichment = {item["index"]: item for item in enrichment_list
                  if isinstance(item, dict)}

    activities = []
    for i, p in enumerate(places[:10]):
        name     = p.get("displayName", {}).get("text", "")
        summary  = p.get("editorialSummary", {}).get("text", "A popular attraction.")
        rating   = p.get("rating", 4.0)
        count    = p.get("userRatingCount", 0)
        maps_uri = p.get("googleMapsUri", "")
        hours    = _hours_summary(p.get("regularOpeningHours"))
        enrich   = enrichment.get(i, {})

        gpt_price = enrich.get("price_inr")
        if gpt_price is not None and isinstance(gpt_price, (int, float)):
            price = int(gpt_price)
        else:
            price = _price_level_to_inr(p.get("priceLevel"), international)

        activities.append({
            "id":              f"act_{i+1}",
            "name":            name,
            "type":            enrich.get("activity_type", "cultural"),
            "price":           price,
            "duration_hours":  float(enrich.get("duration_hours", 2.0)),
            "best_day":        int(enrich.get("best_day", min(i+2, duration_days-1))),
            "booking_link":    "",
            "maps_link":       maps_uri,
            "description":     summary,
            "why_recommended": enrich.get("why_recommended", f"Popular attraction in {destination}"),
            "opening_hours":   hours,
            "location_area":   destination,
            "rating":          rating,
            "review_count":    count,
            "source":          "Google Places",
        })

    return activities


def get_activities(destination: str, interests: list[str],
                   duration_days: int = 4) -> list[dict]:
    """
    Fetch real activities via Google Places API.
    Returns same structure as get_mock_activities().

    Runs 2-3 place searches based on interests,
    then enriches with GPT-4o for day assignment + why_recommended.
    """
    if not config.USE_REAL_ACTIVITIES or not config.GOOGLE_PLACES_API_KEY:
        print(f"   [Activities] Using mock data (USE_REAL_ACTIVITIES=false or key missing)")
        return get_mock_activities(destination, interests)

    try:
        print(f"   [Activities] Searching Google Places for {destination}...")

        # Geocode the destination
        coords = _geocode_city(destination)
        if not coords:
            raise ValueError(f"Could not geocode '{destination}'")
        lat, lng = coords

        # Build search queries from interests
        search_queries = []
        if "adventure" in interests:
            search_queries.append(f"adventure sports activities {destination}")
        if "spiritual" in interests:
            search_queries.append(f"temples ashrams spiritual sites {destination}")
        if "nature" in interests:
            search_queries.append(f"nature parks waterfalls trekking {destination}")
        if "culture" in interests:
            search_queries.append(f"museums historical sites cultural attractions {destination}")
        if "food" in interests:
            search_queries.append(f"best local restaurants street food {destination}")

        suffix = "" if _is_international_dest(destination) else " India"
        search_queries.append(f"top tourist attractions sightseeing {destination}{suffix}")

        # Deduplicate and limit to 3 searches (cost control)
        search_queries = list(dict.fromkeys(search_queries))[:3]

        # Run searches and collect unique places
        all_places  = []
        seen_names  = set()
        for q in search_queries:
            try:
                places = _search_places(q, lat, lng, radius=25000, max_results=6)
                for p in places:
                    name = p.get("displayName", {}).get("text", "")
                    if name and name not in seen_names:
                        seen_names.add(name)
                        all_places.append(p)
            except Exception as e:
                print(f"   ⚠️ Places search failed for '{q}': {e}")

        if not all_places:
            raise ValueError("No places returned from Google Places")

        print(f"   [Activities] Got {len(all_places)} places, enriching with GPT-4o...")

        # Sort by rating desc, take top 10
        all_places.sort(key=lambda p: p.get("rating", 0), reverse=True)
        top_places = all_places[:10]

        activities = _places_to_activities(top_places, interests, destination, duration_days)

        print(f"   ✅ Real activities: {len(activities)} for {destination}")
        return activities

    except Exception as e:
        print(f"   ⚠️ Activities API failed ({e}) — using mock")
        return get_mock_activities(destination, interests)