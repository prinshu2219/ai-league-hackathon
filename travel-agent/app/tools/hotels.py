"""
tools/hotels.py — Sprint 4 (GPT-4o only)
──────────────────────────────────────────
GPT-4o generates real hotel options (hotels that actually exist)
with pre-populated Booking.com and MakeMyTrip deep links.

User clicks the link → lands on a pre-filled search page
showing hotels near that property.
"""

import json
from datetime import datetime
from urllib.parse import quote
from openai import OpenAI
from app.core.config import config
from app.utils.mock_data import get_mock_accommodation_options

_client: OpenAI | None = None


def _openai() -> OpenAI:
    global _client
    if not _client:
        _client = OpenAI(api_key=config.OPENAI_API_KEY)
    return _client


def _booking_deep_link(hotel_name: str, destination: str,
                        check_in: str, check_out: str,
                        adults: int = 1) -> str:
    """
    Booking.com pre-filled search URL.
    Searches for the exact hotel name in the destination city.
    """
    query = f"{hotel_name} {destination}"
    try:
        ci = datetime.strptime(check_in,  "%Y-%m-%d").strftime("%Y-%m-%d")
        co = datetime.strptime(check_out, "%Y-%m-%d").strftime("%Y-%m-%d")
    except ValueError:
        ci, co = check_in, check_out

    return (
        f"https://www.booking.com/searchresults.html"
        f"?ss={quote(query)}"
        f"&checkin={ci}&checkout={co}"
        f"&group_adults={adults}&no_rooms=1"
        f"&selected_currency=INR"
    )


def _mmt_hotel_link(hotel_name: str, destination: str,
                     check_in: str, check_out: str,
                     adults: int = 1) -> str:
    """MakeMyTrip hotel pre-filled search URL."""
    try:
        ci = datetime.strptime(check_in,  "%Y-%m-%d").strftime("%d/%m/%Y")
        co = datetime.strptime(check_out, "%Y-%m-%d").strftime("%d/%m/%Y")
    except ValueError:
        ci, co = check_in, check_out

    city_enc  = quote(destination)
    hotel_enc = quote(hotel_name)
    return (
        f"https://www.makemytrip.com/hotels/hotel-listing/"
        f"?checkin={ci}&checkout={co}"
        f"&city={city_enc}&searchText={hotel_enc}"
        f"&roomCount=1&adultsCount={adults}&childCount=0"
    )


def get_accommodation_options(destination: str, style: str,
                               check_in: str, check_out: str,
                               duration_days: int, budget: int,
                               num_travelers: int = 1) -> list[dict]:
    """
    GPT-4o generates real accommodation options (hotels that actually exist)
    with pre-populated Booking.com deep links.

    Returns same structure as get_mock_accommodation_options().
    """
    print(f"   🤖 [Hotels] GPT-4o: {destination} ({style})...")

    nights           = max(duration_days - 1, 1)
    budget_per_night = int((budget * 0.25) / nights)

    style_desc = {
        "backpacking": f"hostels and cheap guesthouses, max Rs {min(budget_per_night, 800)}/night",
        "budget":      f"budget hotels Rs 500-1500/night",
        "mid-range":   f"comfortable 3-star hotels Rs 1500-4000/night",
        "luxury":      f"4-5 star hotels and resorts Rs 4000+/night",
        "family":      f"family-friendly hotels with good amenities",
        "adventure":   f"camps, river camps, or homestays near activities",
    }.get(style, f"mid-range hotels around Rs {budget_per_night}/night")

    system = """You are an expert on hotels and accommodation across India.
Generate real accommodation options that ACTUALLY EXIST in the destination.

Return JSON {"hotels": [...]} with exactly 3 objects:
{
  "name": "EXACT real hotel/hostel name — must actually exist",
  "type": "hostel|guesthouse|hotel|resort|camp|homestay",
  "area": "specific area/neighbourhood within the city",
  "price_per_night": integer INR realistic price,
  "rating": float 1-5 realistic Google rating,
  "review_count": integer realistic,
  "amenities": ["wifi", "hot_water", ...],
  "why_recommended": "one specific sentence mentioning real features",
  "notes": "one practical tip (early booking, location advantage etc.)"
}

CRITICAL RULES:
- Names must be REAL properties that actually exist and are bookable
- price_per_night must match the style (backpacking Rs 400-900, mid Rs 1500-3500, luxury Rs 5000+)
- Give 3 options across a price range (budget, mid, best-value)
- amenities from: wifi, hot_water, ac, pool, restaurant, breakfast_included,
  yoga, rooftop, parking, river_view, mountain_view, bonfire, kayaking
- why_recommended must mention something specific and real about the property"""

    user = f"""Destination: {destination}, India
Style: {style} — {style_desc}
Check-in: {check_in}, Check-out: {check_out} ({nights} nights)
Travelers: {num_travelers}
Budget per night: up to Rs {budget_per_night:,}

Generate 3 real accommodation options:"""

    try:
        resp = _openai().chat.completions.create(
            model=config.PRIMARY_MODEL, temperature=0.3,
            response_format={"type": "json_object"},
            messages=[{"role": "system", "content": system},
                      {"role": "user",   "content": user}],
        )
        data   = json.loads(resp.choices[0].message.content)
        raw    = data.get("hotels", data.get("accommodation", []))
        if not raw:
            raise ValueError("empty response")

        options = []
        for i, h in enumerate(raw[:4]):
            name        = h.get("name", "Hotel")
            ppn         = int(h.get("price_per_night", budget_per_night))
            total       = ppn * nights

            # Build both links — Booking.com primary, MMT as maps fallback
            bk_link  = _booking_deep_link(name, destination, check_in,
                                           check_out, num_travelers)
            mmt_link = _mmt_hotel_link(name, destination, check_in,
                                        check_out, num_travelers)

            options.append({
                "id":              f"hotel_{i+1}",
                "name":            name,
                "type":            h.get("type", "hotel"),
                "price_per_night": ppn,
                "total_price":     total,
                "rating":          float(h.get("rating", 4.2)),
                "review_count":    int(h.get("review_count", 500)),
                "location_area":   h.get("area", destination),
                "amenities":       h.get("amenities", ["wifi", "hot_water"]),
                "booking_link":    bk_link,
                "mmt_link":        mmt_link,
                "maps_link":       f"https://maps.google.com/?q={quote(name+' '+destination)}",
                "why_recommended": h.get("why_recommended", ""),
                "notes":           h.get("notes", ""),
                "source":          "GPT-4o",
            })

        options.sort(key=lambda x: x["price_per_night"])
        print(f"   ✅ Hotels: {len(options)} options for {destination}")
        return options

    except Exception as e:
        print(f"   ⚠️ Hotels GPT-4o failed ({e}) — using mock")
        return get_mock_accommodation_options(destination, style)