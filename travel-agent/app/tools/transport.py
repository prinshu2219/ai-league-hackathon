"""
tools/transport.py — Sprint 4 (GPT-4o only)
─────────────────────────────────────────────
GPT-4o generates realistic transport options for any Indian route.

Key features:
- Real operator names, realistic prices & durations
- Pre-populated deep links the user can click and book directly:
    Trains  → IRCTC pre-filled search URL
    Bus     → RedBus pre-filled route URL
    Flights → MakeMyTrip pre-filled search URL
    Cab     → Ola link
"""

import json
from datetime import datetime
from urllib.parse import quote
from openai import OpenAI
from app.core.config import config
from app.utils.mock_data import get_mock_transport_options

_client: OpenAI | None = None

CITY_TO_STATION = {
    "delhi": "NDLS", "new delhi": "NDLS", "mumbai": "CSMT",
    "bangalore": "SBC", "bengaluru": "SBC", "chennai": "MAS",
    "kolkata": "KOAA", "hyderabad": "SC", "pune": "PUNE",
    "ahmedabad": "ADI", "jaipur": "JP", "lucknow": "LKO",
    "varanasi": "BSB", "agra": "AGC", "haridwar": "HW",
    "dehradun": "DDN", "rishikesh": "RKSH", "chandigarh": "CDG",
    "amritsar": "ASR", "jodhpur": "JU", "udaipur": "UDZ",
    "kochi": "ERS", "goa": "MAO", "coimbatore": "CBE",
    "mysore": "MYS", "bhopal": "BPL", "indore": "INDB",
    "nagpur": "NGP", "patna": "PNBE", "guwahati": "GHY",
    "bhubaneswar": "BBS", "visakhapatnam": "VSKP",
}

CITY_TO_IATA = {
    "delhi": "DEL", "new delhi": "DEL", "mumbai": "BOM",
    "bangalore": "BLR", "bengaluru": "BLR", "chennai": "MAA",
    "kolkata": "CCU", "hyderabad": "HYD", "pune": "PNQ",
    "ahmedabad": "AMD", "jaipur": "JAI", "kochi": "COK",
    "goa": "GOI", "varanasi": "VNS", "lucknow": "LKO",
    "chandigarh": "IXC", "amritsar": "ATQ", "coimbatore": "CJB",
    "bhubaneswar": "BBI", "guwahati": "GAU", "nagpur": "NAG",
    "udaipur": "UDR", "jodhpur": "JDH", "srinagar": "SXR", "leh": "IXL",
}


def _openai() -> OpenAI:
    global _client
    if not _client:
        _client = OpenAI(api_key=config.OPENAI_API_KEY)
    return _client


def _irctc_link(origin: str, dest: str, date: str) -> str:
    from_code = CITY_TO_STATION.get(origin.lower().strip(), "")
    to_code   = CITY_TO_STATION.get(dest.lower().strip(), "")
    try:
        irctc_dt = datetime.strptime(date, "%Y-%m-%d").strftime("%d/%m/%Y")
    except ValueError:
        irctc_dt = date
    if from_code and to_code:
        return (f"https://www.irctc.co.in/nget/train-search"
                f"?from={from_code}&to={to_code}&date={irctc_dt}&class=SL")
    return "https://www.irctc.co.in/nget/train-search"


def _redbus_link(origin: str, dest: str, date: str) -> str:
    try:
        rb_date = datetime.strptime(date, "%Y-%m-%d").strftime("%d-%b-%Y")
    except ValueError:
        rb_date = date
    o = origin.lower().replace(" ", "-")
    d = dest.lower().replace(" ", "-")
    return f"https://www.redbus.in/bus-tickets/{o}-to-{d}?doj={rb_date}"


def _mmt_flight_link(origin: str, dest: str, date: str, pax: int = 1) -> str:
    orig_iata = CITY_TO_IATA.get(origin.lower().strip(), origin.upper()[:3])
    dest_iata = CITY_TO_IATA.get(dest.lower().strip(), dest.upper()[:3])
    try:
        mmt_dt = datetime.strptime(date, "%Y-%m-%d").strftime("%m%d%Y")
    except ValueError:
        mmt_dt = date.replace("-", "")
    return (f"https://www.makemytrip.com/flights/domestic/results"
            f"?tripType=O&itinerary={orig_iata}-{dest_iata}-{mmt_dt}"
            f"&paxType=A-{pax}_C-0_I-0&cabinClass=E")


def _ola_link(origin: str, dest: str) -> str:
    return (f"https://book.olacabs.com/?pickup_name={quote(origin)}"
            f"&drop_name={quote(dest)}")


def _booking_link(mode: str, origin: str, dest: str,
                   date: str, pax: int) -> str:
    m = mode.lower()
    if "train" in m:                    return _irctc_link(origin, dest, date)
    if "flight" in m or "air" in m:    return _mmt_flight_link(origin, dest, date, pax)
    if "bus" in m or "volvo" in m:     return _redbus_link(origin, dest, date)
    if "cab" in m or "taxi" in m:      return _ola_link(origin, dest)
    return _irctc_link(origin, dest, date)


def _is_international_route(origin: str, destination: str) -> bool:
    from app.agents import _is_indian_city
    return not (_is_indian_city(origin) and _is_indian_city(destination))


def get_transport_options(origin: str, destination: str,
                           travel_date: str, budget: int = 15000,
                           num_travelers: int = 1) -> list[dict]:
    """
    GPT-4o generates 3 realistic transport options with pre-populated
    booking deep links. Falls back to mock on failure.
    """
    print(f"   🤖 [Transport] GPT-4o: {origin} → {destination}...")

    international = _is_international_route(origin, destination)
    has_airports = (origin.lower().strip() in CITY_TO_IATA and
                    destination.lower().strip() in CITY_TO_IATA)

    if international:
        system = f"""You are an expert on international travel from India.
Generate realistic flight options from {origin} (India) to {destination}.

Return JSON {{"options": [...]}} with exactly 3 objects:
{{
  "mode": "flight",
  "operator": "real airline name",
  "train_name": "",
  "train_number": "",
  "price": integer INR one-way per person (realistic international airfare),
  "duration_mins": integer (total including layovers),
  "departure_time": "HH:MM",
  "arrival_time": "HH:MM",
  "class": "Economy|Premium Economy|Business",
  "notes": "one practical sentence (layovers, visa requirements, etc.)"
}}

Rules:
- ALL options MUST be flights — trains/buses CANNOT cross international borders
- Option 1: cheapest economy (budget airline, 1-2 stops)
- Option 2: mid-range (good airline, fewer stops)
- Option 3: premium (direct or business class if available)
- Prices must be realistic for 2025 international flights from India in INR
- Mention visa requirements in notes if applicable
- A one-way economy flight from India to the US/Europe costs ₹25,000-60,000
- A one-way economy flight from India to Southeast Asia costs ₹8,000-20,000"""
    else:
        system = """You are an expert on Indian transport routes.
Generate realistic transport options between two Indian cities.

Return JSON {"options": [...]} with exactly 3 objects:
{
  "mode": "train|bus|flight|shared_cab",
  "operator": "real operator name",
  "train_name": "exact train name if train, else empty",
  "train_number": "number if train, else empty",
  "price": integer INR one-way per person,
  "duration_mins": integer,
  "departure_time": "HH:MM",
  "arrival_time": "HH:MM",
  "class": "Sleeper|3AC|2AC|AC Bus|Economy|Non-AC",
  "notes": "one practical sentence"
}

Rules:
- Option 1: cheapest (Sleeper train or non-AC bus)
- Option 2: mid-range (3AC train or AC Volvo bus)
- Option 3: fastest (flight if both have airports, else 2AC/cab)
- Prices must be realistic for 2025 India
- Use REAL train names that actually run this route
- If no direct train, mention nearest railhead + cab in notes"""

    user = f"""Origin: {origin}, Destination: {destination}
Date: {travel_date}, Travelers: {num_travelers}
Budget: Rs {budget:,}, Both cities have airports: {has_airports}
Generate 3 options:"""

    try:
        resp = _openai().chat.completions.create(
            model=config.PRIMARY_MODEL, temperature=0.2,
            response_format={"type": "json_object"},
            messages=[{"role": "system", "content": system},
                      {"role": "user",   "content": user}],
        )
        data = json.loads(resp.choices[0].message.content)
        raw  = data.get("options", data.get("transport_options", []))
        if not raw:
            raise ValueError("empty response")

        options = []
        for i, opt in enumerate(raw[:4]):
            mode = opt.get("mode", "train")
            tn   = opt.get("train_name", "")
            tno  = opt.get("train_number", "")
            name = f"{tn} ({tno})" if tn and tno else tn or opt.get("operator", "")
            options.append({
                "id":             f"transport_{i+1}",
                "mode":           mode,
                "operator":       name,
                "price":          int(opt.get("price", 500)),
                "duration_mins":  int(opt.get("duration_mins", 360)),
                "departure_time": opt.get("departure_time", "06:00"),
                "arrival_time":   opt.get("arrival_time", "12:00"),
                "class":          opt.get("class", ""),
                "booking_link":   _booking_link(mode, origin, destination,
                                                 travel_date, num_travelers),
                "notes":          opt.get("notes", ""),
                "source":         "GPT-4o",
            })

        options.sort(key=lambda x: x["price"])
        print(f"   ✅ Transport: {len(options)} options")
        return options

    except Exception as e:
        print(f"   ⚠️ Transport GPT-4o failed ({e}) — using mock")
        if international:
            return _international_mock(origin, destination)
        return get_mock_transport_options(origin, destination)


def _international_mock(origin: str, destination: str) -> list[dict]:
    """Fallback flight options for international routes using cost tier data."""
    from app.agents import _CITY_TO_TIER, _COST_TIERS
    tier_key = _CITY_TO_TIER.get(destination.lower().strip(), "europe")
    base_price = _COST_TIERS[tier_key]["flight_rt"] // 2

    return [
        {
            "id": "transport_1", "mode": "flight",
            "operator": "Budget Airline (1-2 stops)",
            "price": int(base_price * 0.75), "duration_mins": 1200,
            "departure_time": "23:00", "arrival_time": "14:00",
            "class": "Economy",
            "booking_link": _mmt_flight_link(origin, destination,
                                              "2025-03-01", 1),
            "notes": f"Budget airline with layover. Check visa requirements for {destination}.",
            "source": "Fallback",
        },
        {
            "id": "transport_2", "mode": "flight",
            "operator": "Major Airline (1-stop)",
            "price": base_price, "duration_mins": 960,
            "departure_time": "01:00", "arrival_time": "12:00",
            "class": "Economy",
            "booking_link": _mmt_flight_link(origin, destination,
                                              "2025-03-01", 1),
            "notes": f"Reputable carrier, shorter layover. Check visa for {destination}.",
            "source": "Fallback",
        },
        {
            "id": "transport_3", "mode": "flight",
            "operator": "Premium Airline (direct/1-stop)",
            "price": int(base_price * 1.5), "duration_mins": 840,
            "departure_time": "21:00", "arrival_time": "06:00",
            "class": "Economy",
            "booking_link": _mmt_flight_link(origin, destination,
                                              "2025-03-01", 1),
            "notes": f"Best routing with shortest travel time. Visa required for {destination}.",
            "source": "Fallback",
        },
    ]