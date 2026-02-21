"""
mock_data.py
────────────
Realistic mock responses for Sprint 1.
Every agent uses these instead of real APIs.

In Sprint 3, agents switch to real APIs one by one.
The feature flags in config.py control this.

These mocks are designed to be REALISTIC — same structure
as real API responses so switching is seamless.
"""

from datetime import datetime, timedelta


def get_mock_destination_info(destination: str) -> dict:
    return {
        "destination": destination,
        "overview": f"{destination} is a renowned destination offering a perfect blend of adventure and spirituality. Nestled in the foothills of the Himalayas, it attracts travelers seeking both thrills and tranquility.",
        "best_areas": [
            {
                "name": "Tapovan",
                "description": "Adventure hub — closest to rafting points, great hostels",
                "best_for": ["adventure", "backpacking", "budget"]
            },
            {
                "name": "Laxman Jhula",
                "description": "Spiritual center — ashrams, yoga studios, cafes",
                "best_for": ["spiritual", "yoga", "culture"]
            },
            {
                "name": "Ram Jhula",
                "description": "Classic tourist area — temples, markets, ghats",
                "best_for": ["sightseeing", "shopping", "spiritual"]
            }
        ],
        "top_attractions": [
            "Triveni Ghat — Evening Ganga Aarti",
            "Beatles Ashram — Historic ruins",
            "Neer Garh Waterfall",
            "Kunjapuri Temple — Sunrise view",
            "Lakshman Jhula — Iconic suspension bridge"
        ],
        "local_food_spots": [
            {"name": "Chotiwala Restaurant", "specialty": "Local thali", "cost": "₹150-250"},
            {"name": "Little Buddha Cafe", "specialty": "Continental + Indian", "cost": "₹200-400"},
            {"name": "German Bakery", "specialty": "Breakfast + baked goods", "cost": "₹150-300"}
        ],
        "cultural_tips": [
            "Dress modestly near temples and ashrams",
            "Remove shoes before entering religious sites",
            "Alcohol is banned in Rishikesh",
            "Respect morning aarti timings (5am and 7pm)"
        ],
        "safety_notes": [
            "Safe for solo travelers including women",
            "Avoid swimming in Ganga during monsoon",
            "Keep valuables secure near tourist areas"
        ],
        "best_time_to_visit": "October to June (avoid July-August monsoon)",
        "insider_tips": [
            {
                "source": "r/india",
                "tip": "Hire a local guide for Beatles Ashram — they know all the hidden murals",
                "upvotes": 847
            },
            {
                "source": "r/solotravel",
                "tip": "Zostel rooftop is great for meeting other travelers",
                "upvotes": 623
            },
            {
                "source": "TravelBlog",
                "tip": "Kunjapuri sunrise requires pre-booked shared taxi — arrange night before",
                "upvotes": 412
            }
        ],
        "activity_tags": ["rafting", "yoga", "meditation", "trekking",
                          "bungee_jumping", "temple_visits", "ganga_aarti",
                          "waterfall_trek", "cliff_jumping", "ashram_visit"]
    }


def get_mock_transport_options(origin: str, destination: str) -> list:
    return [
        {
            "id": "transport_1",
            "mode": "train",
            "operator": "Indian Railways",
            "price": 550,
            "duration_mins": 360,
            "departure_time": "06:00",
            "arrival_time": "12:00",
            "booking_link": "https://www.irctc.co.in/",
            "notes": "Delhi → Haridwar, then shared cab to Rishikesh (45 min, ₹150)"
        },
        {
            "id": "transport_2",
            "mode": "bus",
            "operator": "UPSRTC Volvo",
            "price": 700,
            "duration_mins": 420,
            "departure_time": "05:30",
            "arrival_time": "12:30",
            "booking_link": "https://www.redbus.in/",
            "notes": "Direct AC Volvo bus. Departs ISBT Kashmere Gate."
        },
        {
            "id": "transport_3",
            "mode": "shared_taxi",
            "operator": "Shared Cab Service",
            "price": 1200,
            "duration_mins": 300,
            "departure_time": "Flexible",
            "arrival_time": "Flexible",
            "booking_link": "https://www.olacabs.com/",
            "notes": "Fastest option. Shared with 3-4 travelers."
        }
    ]


def get_mock_weather_forecast(destination: str, start_date: str, days: int) -> dict:
    daily = {}
    start = datetime.strptime(start_date, "%Y-%m-%d")

    conditions = ["Sunny", "Partly Cloudy", "Clear", "Mostly Sunny"]
    for i in range(days):
        date = (start + timedelta(days=i)).strftime("%Y-%m-%d")
        daily[date] = {
            "min_temp": 12.0 + i,
            "max_temp": 22.0 + i,
            "condition": conditions[i % len(conditions)],
            "rain_probability": 5.0,
            "outdoor_suitable": True,
            "recommendation": "Great day for outdoor activities!"
        }

    return {
        "destination": destination,
        "daily": daily,
        "summary": "Excellent weather throughout your trip. Cool mornings, pleasant afternoons. Perfect for both outdoor adventure and evening spiritual activities.",
        "warnings": [],
        "activity_impact": {
            "rafting": "perfect",
            "trekking": "excellent",
            "yoga": "perfect",
            "sightseeing": "great"
        }
    }


def get_mock_accommodation_options(destination: str, style: str) -> list:
    if style in ["backpacking", "budget"]:
        return [
            {
                "id": "hotel_1",
                "name": "Zostel Rishikesh",
                "type": "hostel",
                "price_per_night": 1200,
                "total_price": 3600,
                "rating": 4.5,
                "review_count": 2847,
                "location_area": "Tapovan",
                "amenities": ["wifi", "common_area", "lockers", "cafe", "rooftop"],
                "booking_link": "https://www.zostel.com/zostel/rishikesh/",
                "image_url": "https://via.placeholder.com/400x200?text=Zostel+Rishikesh",
                "maps_link": "https://maps.google.com/?q=Zostel+Rishikesh"
            },
            {
                "id": "hotel_2",
                "name": "Moustache Hostel",
                "type": "hostel",
                "price_per_night": 900,
                "total_price": 2700,
                "rating": 4.3,
                "review_count": 1923,
                "location_area": "Laxman Jhula",
                "amenities": ["wifi", "breakfast_included", "yoga_classes", "cafe"],
                "booking_link": "https://www.moustachehostel.com/",
                "image_url": "https://via.placeholder.com/400x200?text=Moustache+Hostel",
                "maps_link": "https://maps.google.com/?q=Moustache+Hostel+Rishikesh"
            },
            {
                "id": "hotel_3",
                "name": "Shiv Shakti Guesthouse",
                "type": "guesthouse",
                "price_per_night": 700,
                "total_price": 2100,
                "rating": 4.1,
                "review_count": 654,
                "location_area": "Ram Jhula",
                "amenities": ["wifi", "hot_water", "laundry"],
                "booking_link": "https://www.booking.com/",
                "image_url": "https://via.placeholder.com/400x200?text=Shiv+Shakti",
                "maps_link": "https://maps.google.com/?q=Shiv+Shakti+Guesthouse+Rishikesh"
            }
        ]
    else:
        return [
            {
                "id": "hotel_1",
                "name": "Rishikesh Shivalik Camps",
                "type": "resort",
                "price_per_night": 3500,
                "total_price": 10500,
                "rating": 4.7,
                "review_count": 1205,
                "location_area": "Tapovan",
                "amenities": ["wifi", "pool", "spa", "restaurant", "activities"],
                "booking_link": "https://www.booking.com/",
                "image_url": "https://via.placeholder.com/400x200?text=Shivalik+Camps",
                "maps_link": "https://maps.google.com/?q=Rishikesh+Shivalik"
            }
        ]


def get_mock_activities(destination: str, interests: list) -> list:
    all_activities = [
        {
            "id": "act_1",
            "name": "White Water Rafting (16km)",
            "type": "adventure",
            "price": 1500,
            "duration_hours": 3.0,
            "best_day": 2,
            "booking_link": "https://www.thrillophilia.com/",
            "maps_link": "https://maps.google.com/?q=Shivpuri+Rishikesh",
            "description": "Thrilling 16km rafting from Shivpuri to Rishikesh through grade 3-4 rapids",
            "why_recommended": "Perfect for adventure lovers — most popular activity in Rishikesh",
            "opening_hours": "7:00 AM - 4:00 PM",
            "location_area": "Shivpuri"
        },
        {
            "id": "act_2",
            "name": "Ganga Aarti at Triveni Ghat",
            "type": "spiritual",
            "price": 0,
            "duration_hours": 1.5,
            "best_day": 1,
            "booking_link": "",
            "maps_link": "https://maps.google.com/?q=Triveni+Ghat+Rishikesh",
            "description": "Daily evening prayer ceremony on the banks of the Ganges. Free to attend.",
            "why_recommended": "Must-do spiritual experience — incredibly moving",
            "opening_hours": "6:30 PM - 8:00 PM",
            "location_area": "Triveni Ghat"
        },
        {
            "id": "act_3",
            "name": "Beatles Ashram (Chaurasi Kutia)",
            "type": "cultural",
            "price": 150,
            "duration_hours": 2.0,
            "best_day": 3,
            "booking_link": "",
            "maps_link": "https://maps.google.com/?q=Beatles+Ashram+Rishikesh",
            "description": "The ashram where The Beatles stayed in 1968. Now an open art gallery in jungle ruins.",
            "why_recommended": "Unique blend of music history and spirituality",
            "opening_hours": "8:00 AM - 5:00 PM",
            "location_area": "Laxman Jhula"
        },
        {
            "id": "act_4",
            "name": "Neer Garh Waterfall Trek",
            "type": "nature",
            "price": 50,
            "duration_hours": 3.0,
            "best_day": 3,
            "booking_link": "",
            "maps_link": "https://maps.google.com/?q=Neer+Garh+Waterfall",
            "description": "Easy 2km trek through lush forests to a beautiful multi-tiered waterfall",
            "why_recommended": "Perfect for nature lovers — scenic and refreshing",
            "opening_hours": "7:00 AM - 5:00 PM",
            "location_area": "Rishikesh outskirts"
        },
        {
            "id": "act_5",
            "name": "Morning Yoga at Parmarth Niketan",
            "type": "spiritual",
            "price": 300,
            "duration_hours": 1.5,
            "best_day": 2,
            "booking_link": "https://www.parmarth.org/",
            "maps_link": "https://maps.google.com/?q=Parmarth+Niketan+Rishikesh",
            "description": "Morning yoga session at one of Rishikesh's most respected ashrams",
            "why_recommended": "Authentic yoga experience in the yoga capital of the world",
            "opening_hours": "6:00 AM - 7:30 AM",
            "location_area": "Ram Jhula"
        },
        {
            "id": "act_6",
            "name": "Kunjapuri Temple Sunrise",
            "type": "spiritual",
            "price": 600,
            "duration_hours": 4.0,
            "best_day": 4,
            "booking_link": "",
            "maps_link": "https://maps.google.com/?q=Kunjapuri+Temple",
            "description": "Pre-dawn shared taxi to hilltop temple for spectacular Himalayan sunrise views",
            "why_recommended": "Most memorable experience in Rishikesh — worth the early wake up",
            "opening_hours": "5:00 AM - 7:00 AM (sunrise)",
            "location_area": "20km from Rishikesh"
        },
        {
            "id": "act_7",
            "name": "Cliff Jumping at Shivpuri",
            "type": "adventure",
            "price": 400,
            "duration_hours": 1.0,
            "best_day": 2,
            "booking_link": "https://www.thrillophilia.com/",
            "maps_link": "https://maps.google.com/?q=Shivpuri+Beach+Rishikesh",
            "description": "Jump from 15-25 foot cliffs into crystal clear Ganga. Done after rafting.",
            "why_recommended": "Adrenaline rush — perfect add-on to rafting day",
            "opening_hours": "9:00 AM - 4:00 PM",
            "location_area": "Shivpuri Beach"
        }
    ]

    # Filter based on interests
    if "adventure" in interests and "spiritual" in interests:
        return all_activities  # return all for balanced
    elif "adventure" in interests:
        return [a for a in all_activities
                if a["type"] in ["adventure", "nature"]]
    elif "spiritual" in interests:
        return [a for a in all_activities
                if a["type"] in ["spiritual", "cultural"]]
    else:
        return all_activities


def get_mock_plan_options(destination: str, interests: list, budget: int) -> dict:
    return {
        "A": {
            "style_name": "Balanced Explorer",
            "style_tag": "Adventure + Spiritual",
            "highlights": [
                "White water rafting on the Ganges",
                "Beatles Ashram exploration",
                "Evening Ganga Aarti ceremony",
                "Sunrise at Kunjapuri Temple"
            ],
            "estimated_total": 13200,
            "rough_breakdown": {
                "travel": 1100,
                "stay": 3600,
                "food": 2500,
                "activities": 4000,
                "local_transport": 800,
                "buffer": 1200
            },
            "why_this_works": "Perfect balance of adventure thrills and spiritual experiences — you get the best of what Rishikesh is famous for without over-spending on either.",
            "trade_offs": "You won't have time for extended meditation retreats or multiple trekking days",
            "activities_included": ["rafting", "ganga_aarti", "beatles_ashram", "kunjapuri_sunrise"]
        },
        "B": {
            "style_name": "Spiritual Seeker",
            "style_tag": "Deep Spiritual Immersion",
            "highlights": [
                "Daily yoga at Parmarth Niketan",
                "Ashram meditation sessions",
                "Temple circuit tour",
                "Ganga Aarti every evening"
            ],
            "estimated_total": 11500,
            "rough_breakdown": {
                "travel": 1100,
                "stay": 2700,
                "food": 2000,
                "activities": 3500,
                "local_transport": 700,
                "buffer": 1500
            },
            "why_this_works": "Deepest spiritual experience possible — slower pace, more meaningful connections, significant budget savings allow longer trip extension if desired.",
            "trade_offs": "Minimal adventure activities — rafting not included in this plan",
            "activities_included": ["yoga", "meditation", "temple_visits", "ganga_aarti", "ashram_stay"]
        },
        "C": {
            "style_name": "Adrenaline Rush",
            "style_tag": "Maximum Adventure",
            "highlights": [
                "White water rafting (16km stretch)",
                "Bungee jumping at Jumpin Heights",
                "Cliff jumping at Shivpuri",
                "Neer Garh waterfall trek"
            ],
            "estimated_total": 14800,
            "rough_breakdown": {
                "travel": 1100,
                "stay": 3600,
                "food": 2500,
                "activities": 5800,
                "local_transport": 800,
                "buffer": 1000
            },
            "why_this_works": "Maximum adventure packed into 4 days — every day has a major adrenaline activity. Rishikesh is one of the few places in India where this is possible at this budget.",
            "trade_offs": "Tight budget buffer, minimal spiritual experiences, physically demanding",
            "activities_included": ["rafting", "bungee", "cliff_jumping", "waterfall_trek"]
        }
    }
