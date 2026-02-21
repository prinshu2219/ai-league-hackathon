"""
tools/weather.py — Sprint 3A
──────────────────────────────
Real weather data via OpenWeatherMap 5-day forecast API.
Falls back to mock data if key missing or call fails.

API docs: https://openweathermap.org/forecast5
Free tier: 1,000 calls/day — more than sufficient.

Key format in .env:
  OPENWEATHER_API_KEY=your_key_here
  USE_REAL_WEATHER=true
"""

import requests
from datetime import datetime, timedelta
from app.core.config import config
from app.utils.mock_data import get_mock_weather_forecast

# OpenWeatherMap endpoints
GEO_URL      = "http://api.openweathermap.org/geo/1.0/direct"
FORECAST_URL = "https://api.openweathermap.org/data/2.5/forecast"
CURRENT_URL  = "https://api.openweathermap.org/data/2.5/weather"


def _geocode(city: str, api_key: str) -> tuple[float, float] | None:
    """Convert city name to lat/lng using OWM Geocoding API."""
    # Append India to improve accuracy for Indian destinations
    query = f"{city}, India"
    resp  = requests.get(GEO_URL, params={"q": query, "limit": 1, "appid": api_key}, timeout=8)
    resp.raise_for_status()
    data = resp.json()
    if not data:
        # Try without "India"
        resp  = requests.get(GEO_URL, params={"q": city, "limit": 1, "appid": api_key}, timeout=8)
        resp.raise_for_status()
        data = resp.json()
    if data:
        return data[0]["lat"], data[0]["lon"]
    return None


def _condition_label(owm_id: int) -> str:
    """Map OWM weather condition ID to a friendly label."""
    if owm_id < 300:   return "Thunderstorm"
    if owm_id < 400:   return "Drizzle"
    if owm_id < 600:   return "Rainy"
    if owm_id < 700:   return "Snowy"
    if owm_id < 800:   return "Foggy"
    if owm_id == 800:  return "Clear ☀️"
    if owm_id <= 802:  return "Partly Cloudy"
    return "Cloudy"


def _outdoor_suitable(condition_id: int, rain_prob: float) -> bool:
    return condition_id >= 700 and rain_prob < 60


def _recommendation(condition_id: int, max_temp: float, rain_prob: float) -> str:
    if condition_id < 600:
        return "⛈️ Rain likely — carry waterproof jacket, plan indoor backups."
    if rain_prob > 40:
        return "🌦️ Some rain possible — flexible schedule recommended."
    if max_temp > 35:
        return "🌡️ Very hot — carry water, avoid midday outdoor activities."
    if max_temp < 10:
        return "🧥 Cold — pack warm layers, especially for mornings."
    return "✅ Great weather for outdoor activities!"


def _activity_impact(daily: dict) -> dict:
    """Summarise weather impact on common activities."""
    rain_days = sum(1 for d in daily.values() if d["rain_probability"] > 40)
    total     = len(daily)
    good_pct  = round((total - rain_days) / max(total, 1) * 100)

    def rating(threshold_rain):
        return "excellent" if rain_days == 0 else (
               "good"      if rain_days <= 1 else (
               "fair"      if rain_days <= 2 else "poor"))

    return {
        "rafting":     rating(1),
        "trekking":    rating(1),
        "yoga":        "excellent",   # always possible
        "sightseeing": rating(2),
    }


def get_weather_forecast(destination: str, start_date: str, days: int) -> dict:
    """
    Fetch real weather forecast from OpenWeatherMap.
    Returns same structure as get_mock_weather_forecast().

    Args:
        destination: city name (e.g. "Rishikesh")
        start_date:  "YYYY-MM-DD"
        days:        number of days to forecast
    """
    if not config.USE_REAL_WEATHER or not config.OPENWEATHER_API_KEY:
        print("   [Weather] Using mock data (USE_REAL_WEATHER=false or key missing)")
        return get_mock_weather_forecast(destination, start_date, days)

    try:
        print(f"   [Weather] Fetching real forecast for {destination}...")
        key = config.OPENWEATHER_API_KEY

        # Step 1: Geocode
        coords = _geocode(destination, key)
        if not coords:
            raise ValueError(f"Could not geocode '{destination}'")
        lat, lon = coords

        # Step 2: 5-day / 3-hour forecast (free tier)
        resp = requests.get(FORECAST_URL, params={
            "lat": lat, "lon": lon,
            "appid": key, "units": "metric",
            "cnt": min(days * 8, 40),   # 8 slots per day (3-hr intervals), max 40
        }, timeout=10)
        resp.raise_for_status()
        data = resp.json()

        # Step 3: Aggregate into daily summaries
        start  = datetime.strptime(start_date, "%Y-%m-%d")
        daily  = {}
        warnings = []

        for offset in range(days):
            date     = (start + timedelta(days=offset)).strftime("%Y-%m-%d")
            # Collect all 3-hr slots for this date
            slots    = [item for item in data.get("list", [])
                        if item["dt_txt"].startswith(date)]

            if not slots:
                # If OWM doesn't have data for that day (>5 days out), use last known
                slots = data.get("list", [{}])[-3:]

            temps      = [s["main"]["temp"]     for s in slots if "main" in s]
            pop_vals   = [s.get("pop", 0) * 100 for s in slots]   # pop = probability of precip (0-1)
            cond_ids   = [s["weather"][0]["id"]  for s in slots if "weather" in s]
            # Use daytime (12:00) condition if available, else first slot
            noon_slots = [s for s in slots if "12:00" in s.get("dt_txt","")]
            main_slot  = noon_slots[0] if noon_slots else (slots[0] if slots else {})
            cond_id    = main_slot.get("weather",[{}])[0].get("id", 800)
            cond_desc  = _condition_label(cond_id)

            min_t      = round(min(temps), 1) if temps else 18.0
            max_t      = round(max(temps), 1) if temps else 28.0
            rain_prob  = round(max(pop_vals), 1) if pop_vals else 5.0

            daily[date] = {
                "min_temp":        min_t,
                "max_temp":        max_t,
                "condition":       cond_desc,
                "rain_probability": rain_prob,
                "outdoor_suitable": _outdoor_suitable(cond_id, rain_prob),
                "recommendation":  _recommendation(cond_id, max_t, rain_prob),
            }

            # Collect warnings
            if rain_prob > 70:
                warnings.append(f"⚠️ Heavy rain likely on {date} ({rain_prob:.0f}% chance)")
            if max_t > 40:
                warnings.append(f"⚠️ Extreme heat on {date} ({max_t}°C) — plan accordingly")

        # Build summary sentence
        avg_max   = round(sum(d["max_temp"] for d in daily.values()) / len(daily), 1)
        avg_rain  = round(sum(d["rain_probability"] for d in daily.values()) / len(daily), 1)
        city_name = data.get("city", {}).get("name", destination)

        if avg_rain > 50:
            summary = (f"Wet conditions expected in {city_name} — avg high {avg_max}°C "
                       f"with {avg_rain:.0f}% average rain chance. Pack waterproofs.")
        elif avg_rain > 20:
            summary = (f"Mixed weather in {city_name} — avg high {avg_max}°C "
                       f"with occasional showers. Flexible plans recommended.")
        else:
            summary = (f"Good weather in {city_name} — avg high {avg_max}°C, "
                       f"mostly clear skies. Great for outdoor activities.")

        print(f"   ✅ Real weather: {city_name} | avg {avg_max}°C | {avg_rain:.0f}% rain")
        return {
            "destination":     city_name,
            "daily":           daily,
            "summary":         summary,
            "warnings":        warnings,
            "activity_impact": _activity_impact(daily),
            "source":          "OpenWeatherMap",
        }

    except Exception as e:
        print(f"   ⚠️ Weather API failed ({e}) — using mock")
        return get_mock_weather_forecast(destination, start_date, days)