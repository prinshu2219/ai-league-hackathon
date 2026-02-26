"""
utils/demo_data.py — Sprint 5B
────────────────────────────────
Pre-built complete trip state for demo mode.
Loaded instantly — zero API calls, zero wait time.

Use on stage when:
  - Network is unreliable
  - You want a guaranteed smooth demo
  - Showing the UI to judges quickly

Toggle: click "🎬 Demo Mode" button on the input screen.
"""

from datetime import datetime, timedelta

# Fixed dates relative to today so the demo always looks current
_today     = datetime.now()
_start     = _today + timedelta(days=3)
_end       = _start + timedelta(days=3)
_start_str = _start.strftime("%Y-%m-%d")
_end_str   = _end.strftime("%Y-%m-%d")
_start_disp = _start.strftime("%b %d, %Y")


def get_demo_state() -> dict:
    """
    Returns a complete TravelPlanState dict representing a finished
    4-day Delhi → Rishikesh trip plan ready to display.
    All checkpoints already resolved — goes straight to final output.
    """
    return {
        # ── Input ─────────────────────────────────────────
        "user_message": "Plan a 4-day solo trip to Rishikesh from Delhi under ₹15,000. I love adventure and spiritual experiences.",

        # ── Parsed Intent ─────────────────────────────────
        "destination":      "Rishikesh",
        "origin":           "Delhi",
        "budget":           15000,
        "duration_days":    4,
        "travel_style":     "backpacking",
        "interests":        ["adventure", "spiritual"],
        "travel_dates": {
            "start":       _start_str,
            "end":         _end_str,
            "is_flexible": True,
            "assumed":     True,
        },
        "num_travelers":    1,
        "food_preferences": "local",
        "assumptions_made": [
            {"field": "dates",     "assumed_value": _start_disp,
             "reason": "No dates mentioned — defaulted to next available Friday", "can_edit": True},
            {"field": "travelers", "assumed_value": "1 (Solo)",
             "reason": "No traveler count mentioned",                             "can_edit": True},
        ],
        "origin_detected":    True,
        "interests_inferred": True,
        "is_multi_city":      False,
        "city_stops": [{
            "city": "Rishikesh", "days": 4,
            "transport_from_prev": "train",
            "transport_time_hrs":  6,
            "highlights": ["White water rafting", "Ganga Aarti", "Beatles Ashram"],
        }],
        "city_itineraries": {"Rishikesh": [1, 2, 3, 4]},

        # ── Research ──────────────────────────────────────
        "destination_info": {
            "destination": "Rishikesh",
            "overview":    "Rishikesh is the adventure and spiritual capital of India, set in the foothills of the Himalayas on the banks of the sacred Ganges. It draws thrill-seekers for rafting and bungee jumping, and soul-seekers for yoga and ancient temples.",
            "top_attractions": [
                "Triveni Ghat — Evening Ganga Aarti ceremony",
                "Beatles Ashram (Chaurasi Kutia) — Historic jungle ruins",
                "Neer Garh Waterfall — Forest trek",
                "Kunjapuri Temple — Himalayan sunrise viewpoint",
                "Laxman Jhula — Iconic suspension bridge",
            ],
            "local_food_spots": [
                {"name": "Chotiwala Restaurant", "specialty": "Local thali", "cost": "₹150–250"},
                {"name": "Little Buddha Cafe",   "specialty": "Continental + Indian", "cost": "₹200–400"},
                {"name": "German Bakery",         "specialty": "Breakfast & baked goods", "cost": "₹150–300"},
            ],
            "cultural_tips": [
                "Dress modestly near temples and ashrams",
                "Alcohol is banned throughout Rishikesh",
                "Remove shoes before entering all religious sites",
                "Respect the 5 AM and 7 PM aarti timings",
            ],
            "insider_tips": [
                {"source": "r/india",     "tip": "Book rafting the evening before — morning slots sell out fast", "upvotes": 847},
                {"source": "r/solotravel","tip": "Zostel rooftop is the best place to meet other travelers",       "upvotes": 623},
                {"source": "TravelBlog",  "tip": "Kunjapuri sunrise needs a pre-booked shared taxi — arrange night before", "upvotes": 412},
            ],
            "best_time_to_visit": "October to June (avoid July–August monsoon)",
            "activity_tags": ["rafting", "yoga", "trekking", "bungee", "aarti", "ashram"],
        },

        # ── Transport ─────────────────────────────────────
        "transport_options": [
            {
                "id": "transport_1", "mode": "train",
                "operator": "Shatabdi Express (12017)",
                "price": 550, "duration_mins": 330,
                "departure_time": "06:45", "arrival_time": "12:15",
                "class": "CC", "source": "GPT-4o",
                "booking_link": "https://www.irctc.co.in/nget/train-search?from=NDLS&to=HW&date=20/03/2026&class=CC",
                "notes": "Delhi → Haridwar, then shared cab to Rishikesh (45 min, ₹150)",
            },
            {
                "id": "transport_2", "mode": "bus",
                "operator": "UPSRTC Volvo AC",
                "price": 700, "duration_mins": 420,
                "departure_time": "05:30", "arrival_time": "12:30",
                "class": "AC Bus", "source": "GPT-4o",
                "booking_link": f"https://www.redbus.in/bus-tickets/delhi-to-rishikesh?doj={_start.strftime('%d-%b-%Y')}",
                "notes": "Direct AC Volvo from ISBT Kashmere Gate",
            },
            {
                "id": "transport_3", "mode": "shared_cab",
                "operator": "Shared Cab (Ola/Rapido)",
                "price": 1200, "duration_mins": 280,
                "departure_time": "Flexible", "arrival_time": "Flexible",
                "class": "Shared", "source": "GPT-4o",
                "booking_link": "https://book.olacabs.com/?pickup_name=Delhi&drop_name=Rishikesh",
                "notes": "Fastest option. Shared with 3–4 travelers.",
            },
        ],
        "recommended_transport_id": "transport_1",

        # ── Weather ───────────────────────────────────────
        "weather_forecast": {
            "destination": "Rishikesh",
            "summary": "Excellent weather — cool mornings (12°C), pleasant afternoons (24°C). Perfect for rafting and trekking. Clear skies throughout.",
            "warnings": [],
            "daily": {
                _start_str: {"min_temp": 12, "max_temp": 24, "condition": "Clear ☀️",     "rain_probability": 5,  "outdoor_suitable": True, "recommendation": "Perfect for rafting!"},
                ((_start + timedelta(1)).strftime("%Y-%m-%d")): {"min_temp": 11, "max_temp": 23, "condition": "Sunny",        "rain_probability": 8,  "outdoor_suitable": True, "recommendation": "Great trekking weather"},
                ((_start + timedelta(2)).strftime("%Y-%m-%d")): {"min_temp": 13, "max_temp": 25, "condition": "Partly Cloudy","rain_probability": 15, "outdoor_suitable": True, "recommendation": "Good for all activities"},
                _end_str:   {"min_temp": 12, "max_temp": 24, "condition": "Clear ☀️",     "rain_probability": 5,  "outdoor_suitable": True, "recommendation": "Beautiful sunrise day!"},
            },
            "activity_impact": {"rafting": "excellent", "trekking": "excellent", "yoga": "perfect", "sightseeing": "great"},
            "source": "OpenWeatherMap",
        },

        # ── Accommodation ─────────────────────────────────
        "accommodation_options": [
            {
                "id": "hotel_1", "name": "Zostel Rishikesh",
                "type": "hostel", "price_per_night": 900, "total_price": 2700,
                "rating": 4.5, "review_count": 2847,
                "location_area": "Tapovan",
                "amenities": ["wifi", "rooftop", "cafe", "lockers", "common_area"],
                "booking_link": f"https://www.booking.com/searchresults.html?ss=Zostel+Rishikesh&checkin={_start_str}&checkout={_end_str}&group_adults=1&selected_currency=INR",
                "maps_link":    "https://maps.google.com/?q=Zostel+Rishikesh",
                "why_recommended": "Best social hostel in Rishikesh — rooftop views, adventure crowd",
                "source": "GPT-4o",
            },
            {
                "id": "hotel_2", "name": "Moustache Hostel Rishikesh",
                "type": "hostel", "price_per_night": 750, "total_price": 2250,
                "rating": 4.3, "review_count": 1923,
                "location_area": "Laxman Jhula",
                "amenities": ["wifi", "breakfast_included", "yoga", "cafe"],
                "booking_link": f"https://www.booking.com/searchresults.html?ss=Moustache+Hostel+Rishikesh&checkin={_start_str}&checkout={_end_str}&group_adults=1&selected_currency=INR",
                "maps_link":    "https://maps.google.com/?q=Moustache+Hostel+Rishikesh",
                "why_recommended": "Breakfast included, free yoga classes — best value in Laxman Jhula",
                "source": "GPT-4o",
            },
        ],
        "recommended_accommodation_id": "hotel_1",

        # ── Plan Options ──────────────────────────────────
        "plan_options": {
            "A": {
                "style_name": "Balanced Explorer",
                "style_tag":  "Adventure + Spiritual",
                "highlights": ["White water rafting (16km)", "Beatles Ashram", "Evening Ganga Aarti", "Kunjapuri sunrise"],
                "estimated_total": 13200,
                "rough_breakdown": {"travel": 1100, "stay": 2700, "food": 2500, "activities": 4800, "local_transport": 800, "buffer": 1300},
                "why_this_works": "Perfect balance of adventure and spirituality — you get Rishikesh's two best sides without over-spending on either.",
                "trade_offs": "No time for extended meditation retreats or multi-day trekking.",
                "activities_included": ["adventure", "spiritual"],
            },
            "B": {
                "style_name": "Spiritual Seeker",
                "style_tag":  "Deep Spiritual Immersion",
                "highlights": ["Daily yoga at Parmarth Niketan", "Ashram meditation", "Temple circuit", "Ganga Aarti every evening"],
                "estimated_total": 10800,
                "rough_breakdown": {"travel": 1100, "stay": 2250, "food": 2000, "activities": 3200, "local_transport": 700, "buffer": 1550},
                "why_this_works": "Slowest pace, deepest experience — perfect if you want to leave feeling genuinely refreshed.",
                "trade_offs": "Minimal adventure — no rafting in this plan.",
                "activities_included": ["spiritual", "culture"],
            },
            "C": {
                "style_name": "Adrenaline Rush",
                "style_tag":  "Maximum Adventure",
                "highlights": ["Rafting + cliff jumping combo", "Bungee at Jumpin Heights", "Waterfall trek", "Camping on Ganges bank"],
                "estimated_total": 14600,
                "rough_breakdown": {"travel": 1100, "stay": 2700, "food": 2400, "activities": 6400, "local_transport": 800, "buffer": 1200},
                "why_this_works": "Every day has a major adrenaline hit — Rishikesh is one of the few Indian destinations where this is possible at this budget.",
                "trade_offs": "Physically demanding, very tight buffer, minimal downtime.",
                "activities_included": ["adventure", "nature"],
            },
        },
        "system_recommendation": "A",
        "recommendation_reason": "Best balance of Rishikesh's two iconic experiences — adventure and spirituality — within ₹15,000.",

        # ── Chosen Option ─────────────────────────────────
        "chosen_option": "A",
        "chosen_option_details": {
            "style_name": "Balanced Explorer",
            "style_tag":  "Adventure + Spiritual",
            "highlights": ["White water rafting", "Beatles Ashram", "Ganga Aarti", "Kunjapuri sunrise"],
            "estimated_total": 13200,
            "rough_breakdown": {"travel": 1100, "stay": 2700, "food": 2500, "activities": 4800, "local_transport": 800, "buffer": 1300},
            "activities_included": ["adventure", "spiritual"],
        },

        # ── Activities ────────────────────────────────────
        "activities": [
            {"id": "act_1", "name": "White Water Rafting (16km)",  "type": "adventure",  "price": 1500, "duration_hours": 3.0, "best_day": 2, "description": "Thrilling 16km rafting from Shivpuri to Rishikesh through grade 3–4 rapids.", "why_recommended": "Most iconic Rishikesh experience — pure adrenaline", "booking_link": "https://www.thrillophilia.com/tours/river-rafting-in-rishikesh", "maps_link": "https://maps.google.com/?q=Shivpuri+Rishikesh", "opening_hours": "7 AM–4 PM", "location_area": "Shivpuri", "source": "GPT-4o"},
            {"id": "act_2", "name": "Evening Ganga Aarti",          "type": "spiritual",  "price": 0,    "duration_hours": 1.5, "best_day": 1, "description": "Daily evening prayer ceremony on the Ganges at Triveni Ghat.", "why_recommended": "Free, deeply moving — a must on arrival evening", "booking_link": "", "maps_link": "https://maps.google.com/?q=Triveni+Ghat+Rishikesh", "opening_hours": "6:30 PM–8 PM", "location_area": "Triveni Ghat", "source": "GPT-4o"},
            {"id": "act_3", "name": "Beatles Ashram Visit",         "type": "cultural",   "price": 150,  "duration_hours": 2.0, "best_day": 3, "description": "The ashram where The Beatles stayed in 1968 — now a jungle art gallery.", "why_recommended": "Unique blend of music history and spirituality", "booking_link": "", "maps_link": "https://maps.google.com/?q=Beatles+Ashram+Rishikesh", "opening_hours": "8 AM–5 PM", "location_area": "Laxman Jhula", "source": "GPT-4o"},
            {"id": "act_4", "name": "Kunjapuri Temple Sunrise",     "type": "spiritual",  "price": 600,  "duration_hours": 4.0, "best_day": 4, "description": "Pre-dawn taxi to hilltop temple for Himalayan sunrise views.", "why_recommended": "Most memorable Rishikesh moment — worth the 4 AM wake-up", "booking_link": "", "maps_link": "https://maps.google.com/?q=Kunjapuri+Temple", "opening_hours": "5 AM–7 AM", "location_area": "20km from Rishikesh", "source": "GPT-4o"},
            {"id": "act_5", "name": "Morning Yoga at Parmarth",     "type": "spiritual",  "price": 300,  "duration_hours": 1.5, "best_day": 2, "description": "Sunrise yoga session at one of Rishikesh's most respected ashrams.", "why_recommended": "Authentic yoga in the yoga capital of the world", "booking_link": "https://www.parmarth.org/", "maps_link": "https://maps.google.com/?q=Parmarth+Niketan+Rishikesh", "opening_hours": "6 AM–7:30 AM", "location_area": "Ram Jhula", "source": "GPT-4o"},
        ],

        # ── Budget ────────────────────────────────────────
        "budget_breakdown": {
            "travel":          {"allocated": 1100, "per_day": 0,   "actual": 0, "notes": "Return transport"},
            "stay":            {"allocated": 2700, "per_day": 900, "actual": 0, "notes": "3 nights"},
            "food":            {"allocated": 2500, "per_day": 625, "actual": 0, "notes": "Local food"},
            "activities":      {"allocated": 4800, "per_day": 1200,"actual": 0, "notes": "Activities + entry"},
            "local_transport": {"allocated": 800,  "per_day": 200, "actual": 0, "notes": "Local cabs"},
            "buffer":          {"allocated": 1300, "per_day": 0,   "actual": 0, "notes": "Emergency"},
        },
        "projected_total":  13200,
        "budget_feasible":  True,
        "budget_warnings":  [],
        "approved_budget": {
            "travel":          {"allocated": 1100},
            "stay":            {"allocated": 2700},
            "food":            {"allocated": 2500},
            "activities":      {"allocated": 4800},
            "local_transport": {"allocated": 800},
            "buffer":          {"allocated": 1300},
        },
        "budget_modified": False,

        # ── Booking Cart ──────────────────────────────────
        "booking_cart": [
            {
                "category": "transport", "source": "GPT-4o",
                "name":     "Train — Shatabdi Express (12017)",
                "details":  "Delhi → Rishikesh (via Haridwar)",
                "cost":     1100,
                "booking_link": "https://www.irctc.co.in/nget/train-search?from=NDLS&to=HW&class=CC",
                "notes":    "Delhi → Haridwar, then shared cab to Rishikesh (45 min, ₹150)",
                "confirmation_required": True,
            },
            {
                "category": "stay", "source": "GPT-4o",
                "name":     "Zostel Rishikesh",
                "details":  f"₹900/night × 3 nights",
                "cost":     2700,
                "booking_link": f"https://www.booking.com/searchresults.html?ss=Zostel+Rishikesh&checkin={_start_str}&checkout={_end_str}&group_adults=1&selected_currency=INR",
                "notes":    "Best social hostel in Rishikesh — rooftop views, adventure crowd",
                "confirmation_required": True,
            },
            {
                "category": "activity", "source": "GPT-4o",
                "name":     "White Water Rafting (16km)",
                "details":  "Day 2 | 3.0hrs",
                "cost":     1500,
                "booking_link": "https://www.thrillophilia.com/tours/river-rafting-in-rishikesh",
                "notes":    "Book the evening before — morning slots sell fast",
                "confirmation_required": True,
            },
            {
                "category": "activity", "source": "GPT-4o",
                "name":     "Kunjapuri Temple Sunrise",
                "details":  "Day 4 | 4.0hrs",
                "cost":     600,
                "booking_link": "",
                "notes":    "Arrange shared taxi night before",
                "confirmation_required": False,
            },
            {
                "category": "activity", "source": "GPT-4o",
                "name":     "Morning Yoga at Parmarth Niketan",
                "details":  "Day 2 | 1.5hrs",
                "cost":     300,
                "booking_link": "https://www.parmarth.org/",
                "notes":    "Walk-ins accepted — arrive 10 min early",
                "confirmation_required": False,
            },
        ],
        "cart_total":             6200,
        "selected_transport":     {
            "id": "transport_1", "mode": "train",
            "operator": "Shatabdi Express (12017)",
            "price": 550, "duration_mins": 330,
            "departure_time": "06:45", "arrival_time": "12:15",
            "booking_link": "https://www.irctc.co.in/nget/train-search?from=NDLS&to=HW&class=CC",
            "notes": "Delhi → Haridwar, then shared cab to Rishikesh",
            "source": "GPT-4o",
        },
        "selected_accommodation": {
            "id": "hotel_1", "name": "Zostel Rishikesh",
            "type": "hostel", "price_per_night": 900, "total_price": 2700,
            "location_area": "Tapovan",
            "booking_link": f"https://www.booking.com/searchresults.html?ss=Zostel+Rishikesh&checkin={_start_str}&checkout={_end_str}&group_adults=1&selected_currency=INR",
            "maps_link": "https://maps.google.com/?q=Zostel+Rishikesh",
            "source": "GPT-4o",
        },
        "selected_activities": [
            {"id": "act_1", "name": "White Water Rafting (16km)",  "price": 1500, "duration_hours": 3.0, "best_day": 2, "booking_link": "https://www.thrillophilia.com/tours/river-rafting-in-rishikesh", "maps_link": "https://maps.google.com/?q=Shivpuri+Rishikesh", "description": "16km rafting through grade 3–4 rapids", "why_recommended": "Most iconic experience", "source": "GPT-4o"},
            {"id": "act_4", "name": "Kunjapuri Temple Sunrise",    "price": 600,  "duration_hours": 4.0, "best_day": 4, "booking_link": "", "maps_link": "https://maps.google.com/?q=Kunjapuri+Temple", "description": "Pre-dawn taxi to hilltop temple", "why_recommended": "Most memorable moment", "source": "GPT-4o"},
            {"id": "act_5", "name": "Morning Yoga at Parmarth",    "price": 300,  "duration_hours": 1.5, "best_day": 2, "booking_link": "https://www.parmarth.org/", "maps_link": "https://maps.google.com/?q=Parmarth+Niketan", "description": "Sunrise yoga session", "why_recommended": "Authentic yoga experience", "source": "GPT-4o"},
        ],
        "bookings_confirmed": True,

        # ── Itinerary ─────────────────────────────────────
        "daily_itinerary": [
            {
                "day_number": 1, "date": _start_str, "city": "Rishikesh",
                "theme": "Travel + Spiritual Arrival",
                "segments": [
                    {"time": "06:45", "type": "transport", "title": "Depart Delhi",              "description": "Shatabdi Express (12017) from New Delhi Railway Station", "duration_mins": 330, "cost": 550,  "notes": "Platform 1 — arrive 20 min early", "maps_link": "https://maps.google.com/?q=New+Delhi+Railway+Station", "booking_link": "https://www.irctc.co.in/", "weather_note": ""},
                    {"time": "12:15", "type": "transport", "title": "Haridwar → Rishikesh Cab",  "description": "Shared cab from Haridwar station to Rishikesh (45 min)", "duration_mins": 45,  "cost": 150,  "notes": "Cabs available right outside station exit", "maps_link": "", "booking_link": "", "weather_note": ""},
                    {"time": "14:00", "type": "checkin",   "title": "Check in — Zostel Rishikesh","description": "Check in, drop bags, freshen up", "duration_mins": 60,  "cost": 900,  "notes": "Located in Tapovan — 5 min walk to river", "maps_link": "https://maps.google.com/?q=Zostel+Rishikesh", "booking_link": "https://www.zostel.com/zostel/rishikesh/", "weather_note": ""},
                    {"time": "16:00", "type": "free_time", "title": "Explore Laxman Jhula",       "description": "Walk the iconic suspension bridge, browse shops, soak in the vibe", "duration_mins": 90,  "cost": 0,    "notes": "Golden hour photos from the bridge are stunning", "maps_link": "https://maps.google.com/?q=Laxman+Jhula", "booking_link": "", "weather_note": "Clear skies — perfect for sunset"},
                    {"time": "18:30", "type": "activity",  "title": "Evening Ganga Aarti",        "description": "Daily prayer ceremony at Triveni Ghat — fire, flowers, chanting", "duration_mins": 90,  "cost": 0,    "notes": "Arrive 15 min early for front row. Completely free.", "maps_link": "https://maps.google.com/?q=Triveni+Ghat+Rishikesh", "booking_link": "", "weather_note": ""},
                    {"time": "20:30", "type": "meal",      "title": "Dinner — Chotiwala",         "description": "Famous local thali restaurant near Ram Jhula", "duration_mins": 60,  "cost": 200,  "notes": "₹150–₹250 per person. Try the mixed thali.", "maps_link": "https://maps.google.com/?q=Chotiwala+Restaurant+Rishikesh", "booking_link": "", "weather_note": ""},
                ],
                "daily_cost_estimate": 1900,
                "highlights": ["First glimpse of the Ganges", "Ganga Aarti ceremony"],
            },
            {
                "day_number": 2, "date": (_start + timedelta(1)).strftime("%Y-%m-%d"), "city": "Rishikesh",
                "theme": "Adventure Day",
                "segments": [
                    {"time": "06:00", "type": "activity",  "title": "Morning Yoga — Parmarth Niketan","description": "Sunrise yoga on the banks of the Ganges at a world-famous ashram", "duration_mins": 90,  "cost": 300,  "notes": "Walk-ins welcome — wear comfortable clothes", "maps_link": "https://maps.google.com/?q=Parmarth+Niketan+Rishikesh", "booking_link": "https://www.parmarth.org/", "weather_note": "Cool 12°C — perfect for outdoor yoga"},
                    {"time": "08:00", "type": "meal",      "title": "Breakfast — German Bakery",    "description": "Famous breakfast spot for travellers", "duration_mins": 45,  "cost": 200,  "notes": "Try banana pancakes + fresh juice", "maps_link": "https://maps.google.com/?q=German+Bakery+Rishikesh", "booking_link": "", "weather_note": ""},
                    {"time": "09:30", "type": "activity",  "title": "White Water Rafting (16km)",   "description": "Epic 16km rafting from Shivpuri through grade 3–4 rapids", "duration_mins": 180, "cost": 1500, "notes": "Price includes gear. Book the evening before.", "maps_link": "https://maps.google.com/?q=Shivpuri+Rishikesh", "booking_link": "https://www.thrillophilia.com/tours/river-rafting-in-rishikesh", "weather_note": "Sunny — ideal rafting conditions"},
                    {"time": "14:00", "type": "meal",      "title": "Lunch — Little Buddha Cafe",   "description": "Riverside café popular with backpackers", "duration_mins": 60,  "cost": 300,  "notes": "Rooftop seating with Ganges view", "maps_link": "https://maps.google.com/?q=Little+Buddha+Cafe+Rishikesh", "booking_link": "", "weather_note": ""},
                    {"time": "16:00", "type": "free_time", "title": "Relax + Local Shopping",       "description": "Browse the markets near Ram Jhula for souvenirs", "duration_mins": 120, "cost": 300,  "notes": "Rudraksha beads and hemp products are specialties", "maps_link": "", "booking_link": "", "weather_note": ""},
                    {"time": "20:00", "type": "meal",      "title": "Dinner at Zostel Café",        "description": "Rooftop dinner with other travellers", "duration_mins": 60,  "cost": 250,  "notes": "Great place to plan Day 3 with fellow travellers", "maps_link": "", "booking_link": "", "weather_note": ""},
                ],
                "daily_cost_estimate": 2850,
                "highlights": ["16km white water rafting", "Sunrise yoga on the Ganges"],
            },
            {
                "day_number": 3, "date": (_start + timedelta(2)).strftime("%Y-%m-%d"), "city": "Rishikesh",
                "theme": "Culture & Nature Day",
                "segments": [
                    {"time": "07:30", "type": "meal",      "title": "Breakfast",                   "description": "Breakfast at hostel café", "duration_mins": 45,  "cost": 150,  "notes": "", "maps_link": "", "booking_link": "", "weather_note": ""},
                    {"time": "09:00", "type": "activity",  "title": "Beatles Ashram",               "description": "Explore the ashram where the Fab Four spent 6 weeks in 1968", "duration_mins": 120, "cost": 150,  "notes": "Hire guide at entrance (₹200) — they know all the hidden murals", "maps_link": "https://maps.google.com/?q=Beatles+Ashram+Rishikesh", "booking_link": "", "weather_note": ""},
                    {"time": "12:00", "type": "activity",  "title": "Neer Garh Waterfall Trek",     "description": "Easy 2km forest trek to a beautiful multi-tiered waterfall", "duration_mins": 180, "cost": 50,   "notes": "Carry water and wear trekking sandals", "maps_link": "https://maps.google.com/?q=Neer+Garh+Waterfall", "booking_link": "", "weather_note": "Partly cloudy — great trekking weather"},
                    {"time": "16:00", "type": "meal",      "title": "Chai Break + Street Food",     "description": "Local chai stalls near Ram Jhula", "duration_mins": 60,  "cost": 100,  "notes": "Best masala chai in town is near the bridge", "maps_link": "", "booking_link": "", "weather_note": ""},
                    {"time": "18:30", "type": "activity",  "title": "Evening Ganga Aarti",          "description": "Second aarti experience — different every time", "duration_mins": 90,  "cost": 0,    "notes": "Bring a diya (clay lamp) to float on the river — ₹20", "maps_link": "https://maps.google.com/?q=Triveni+Ghat+Rishikesh", "booking_link": "", "weather_note": ""},
                    {"time": "20:30", "type": "meal",      "title": "Farewell Dinner",              "description": "Dinner at a rooftop restaurant", "duration_mins": 60,  "cost": 350,  "notes": "Splurge a little — last full evening!", "maps_link": "", "booking_link": "", "weather_note": ""},
                ],
                "daily_cost_estimate": 1800,
                "highlights": ["Beatles Ashram history", "Neer Garh Waterfall trek"],
            },
            {
                "day_number": 4, "date": _end_str, "city": "Rishikesh",
                "theme": "Himalayan Sunrise + Return",
                "segments": [
                    {"time": "04:00", "type": "transport", "title": "Pre-dawn Taxi — Kunjapuri",    "description": "Shared taxi to Kunjapuri Temple (20km, 45 min drive)", "duration_mins": 45,  "cost": 300,  "notes": "Book shared taxi evening before from hostel — ask reception", "maps_link": "https://maps.google.com/?q=Kunjapuri+Temple", "booking_link": "", "weather_note": "Clear forecast — perfect sunrise"},
                    {"time": "05:30", "type": "activity",  "title": "Himalayan Sunrise Viewpoint",  "description": "Watch sunrise over the snow-capped Himalayas from 1645m altitude", "duration_mins": 90,  "cost": 300,  "notes": "Carry a jacket — it's cold at the top. Worth every rupee.", "maps_link": "https://maps.google.com/?q=Kunjapuri+Temple", "booking_link": "", "weather_note": "Crystal clear — Gangotri range visible"},
                    {"time": "08:00", "type": "meal",      "title": "Breakfast + Checkout",         "description": "Final breakfast, pack bags, check out by 10 AM", "duration_mins": 90,  "cost": 150,  "notes": "Luggage storage available at Zostel till evening", "maps_link": "", "booking_link": "", "weather_note": ""},
                    {"time": "12:00", "type": "transport", "title": "Return to Delhi",               "description": "Bus or train back to Delhi from Haridwar/Rishikesh", "duration_mins": 360, "cost": 550,  "notes": "Book return ticket in advance on IRCTC", "maps_link": "", "booking_link": "https://www.irctc.co.in/nget/train-search?from=HW&to=NDLS", "weather_note": ""},
                ],
                "daily_cost_estimate": 1400,
                "highlights": ["Himalayan sunrise from 1645m", "Safe return to Delhi"],
            },
        ],

        # ── Final Summary ─────────────────────────────────
        "final_budget_summary": {
            "travel":          1100,
            "stay":            2700,
            "food":            2000,
            "activities":      2550,
            "local_transport": 800,
            "estimated_total": 9150,
            "remaining":       5850,
        },
        "trip_summary": {
            "destination":    "Rishikesh",
            "duration":       "4 Days",
            "budget":         "₹15,000",
            "style":          "Balanced Explorer",
            "travelers":      1,
            "dates":          f"{_start_str} to {_end_str}",
            "estimated_cost": "₹9,150",
            "savings":        "₹5,850 remaining",
            "is_multi_city":  False,
            "city_stops":     [{"city": "Rishikesh", "days": 4, "transport_from_prev": "train", "transport_time_hrs": 6, "highlights": ["rafting", "aarti", "ashram"]}],
            "local_tips": [
                "Carry cash — many activity operators and small restaurants don't accept cards",
                "Alcohol is banned in Rishikesh — respect local customs",
                "Rafting slots fill up fast on weekends — book the evening before",
                "The Ganga Aarti happens every day at 6:30 PM — never miss it",
                "Kunjapuri sunrise is only worth it if the forecast is clear — check the night before",
            ],
        },

        # ── Outputs ───────────────────────────────────────
        "pdf_bytes": b"",
        "map_html":  "",

        # ── Workflow Control ──────────────────────────────
        "current_phase":     "complete",
        "awaiting_human":    False,
        "checkpoint_number": 0,
        "checkpoint_data":   {},
        "human_response":    None,
        "errors":            [],
        "warnings":          [],
        "replan_requested":  False,
        "replan_instruction": "",
        "replan_category_to_cut": "",
        "replan_scope":      [],
        "replan_count":      0,
        "retry_count":       0,
    }