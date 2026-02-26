"""
map_generator.py — Sprint 3D
──────────────────────────────
Supports both single-city and multi-city trips.

Multi-city additions:
- Inter-city route arrows drawn between city centers
- City name labels on the map
- Separate marker colors per city (not per day)
- City legend shows cities, not days
"""

import folium
import json
from openai import OpenAI
from app.core.config import config

# Day colors for single-city (per day)
DAY_COLORS = ["green","orange","purple","blue","darkgreen","red","cadetblue"]
DAY_HEX    = ["#0D9488","#EA580C","#7C3AED","#0369A1","#166534","#9D174D","#0E7490"]

# City colors for multi-city (per city)
CITY_COLORS = ["red","blue","green","purple","orange","darkred","cadetblue","darkgreen"]
CITY_HEX    = ["#DC2626","#2563EB","#16A34A","#7C3AED","#EA580C","#991B1B","#0E7490","#166534"]

SEG_ICONS = {
    "transport": "bus", "checkin": "home",
    "activity":  "star","meal":    "cutlery", "free_time":"leaf",
}

client = OpenAI(api_key=config.OPENAI_API_KEY)

KNOWN_CENTERS = {
    "rishikesh": (30.0869,78.2676), "haridwar":  (29.9457,78.1642),
    "dehradun":  (30.3165,78.0322), "mussoorie": (30.4598,78.0664),
    "goa":       (15.2993,74.1240), "agra":      (27.1767,78.0081),
    "manali":    (32.2396,77.1887), "jaipur":    (26.9124,75.7873),
    "udaipur":   (24.5854,73.7125), "varanasi":  (25.3176,82.9739),
    "ooty":      (11.4102,76.6950), "shimla":    (31.1048,77.1734),
    "munnar":    (10.0889,77.0595), "coorg":     (12.3375,75.8069),
    "pushkar":   (26.4899,74.5511), "mcleod ganj":(32.2396,76.3234),
    "delhi":     (28.6139,77.2090), "mumbai":    (19.0760,72.8777),
    "bangalore": (12.9716,77.5946), "kolkata":   (22.5726,88.3639),
    "chennai":   (13.0827,80.2707), "hyderabad": (17.3850,78.4867),
    "pune":      (18.5204,73.8567), "ahmedabad": (23.0225,72.5714),
}


def _center_for(name: str) -> tuple:
    return KNOWN_CENTERS.get(name.lower().strip(), (20.5937, 78.9629))


def _geocode_batch(destination: str, places: list[str]) -> dict[str, tuple]:
    if not places:
        return {}
    prompt = f"""For each place listed below, in or near {destination}, India,
return a JSON object: {{"place name": [latitude, longitude], ...}}
Use accurate coordinates. For generic names like "Breakfast" or "Dinner",
use the city center of {destination}.

Places:
{json.dumps(places, indent=2)}

Return ONLY valid JSON."""
    try:
        resp = client.chat.completions.create(
            model=config.FAST_MODEL, temperature=0,
            response_format={"type": "json_object"},
            messages=[{"role": "user", "content": prompt}],
        )
        data = json.loads(resp.choices[0].message.content)
        return {k: (float(v[0]), float(v[1]))
                for k, v in data.items()
                if isinstance(v, (list, tuple)) and len(v) == 2}
    except Exception as e:
        print(f"   ⚠️ Geocoding failed: {e}")
        return {}


def generate_map_html(destination: str, daily_itinerary: list,
                      city_stops: list = None, is_multi_city: bool = False) -> str:
    print(f"🗺️  [Map] Building {'multi-city' if is_multi_city else 'single-city'} map...")

    city_stops = city_stops or []

    # ── Determine map center ─────────────────────────────
    if is_multi_city and city_stops:
        lats = [_center_for(s["city"])[0] for s in city_stops]
        lngs = [_center_for(s["city"])[1] for s in city_stops]
        center = (sum(lats)/len(lats), sum(lngs)/len(lngs))
        zoom   = 8 if len(city_stops) > 2 else 10
    else:
        center = _center_for(destination)
        zoom   = 13

    m = folium.Map(location=center, zoom_start=zoom, tiles="CartoDB positron")

    # ── Build city → color mapping for multi-city ────────
    city_color_map = {}
    if is_multi_city:
        for i, stop in enumerate(city_stops):
            city_color_map[stop["city"]] = {
                "folium": CITY_COLORS[i % len(CITY_COLORS)],
                "hex":    CITY_HEX[i % len(CITY_HEX)],
            }

    # ── Collect titles per city for geocoding ────────────
    city_titles: dict[str, list] = {}
    for day in daily_itinerary:
        city = day.get("city", destination)
        for seg in day.get("segments", []):
            title = seg.get("title", "")
            if title:
                city_titles.setdefault(city, []).append(title)

    # Geocode each city's places separately for accuracy
    all_coords: dict[str, tuple] = {}
    for city, titles in city_titles.items():
        unique = list(dict.fromkeys(titles))  # deduplicate preserving order
        coords = _geocode_batch(city, unique)
        all_coords.update(coords)

    # ── Legend HTML ───────────────────────────────────────
    if is_multi_city:
        legend_items = "".join(
            f'<span style="color:{city_color_map[s["city"]]["hex"]}">&#9679;</span> '
            f'{s["city"]} ({s["days"]}d)<br>'
            for s in city_stops if s["city"] in city_color_map
        )
        legend_title = "Cities"
    else:
        legend_items = "".join(
            f'<span style="color:{DAY_HEX[i%len(DAY_HEX)]}">&#9679;</span> '
            f'Day {day["day_number"]}: {day.get("theme","")[:22]}<br>'
            for i, day in enumerate(daily_itinerary)
        )
        legend_title = "Days"

    legend_html = f"""
    <div style="position:fixed;bottom:30px;left:30px;z-index:1000;
        background:white;padding:12px 16px;border-radius:8px;
        box-shadow:0 2px 8px rgba(0,0,0,0.2);font-family:Arial;font-size:12px;min-width:140px;">
    <b style="color:#1E293B">{legend_title}</b><br>{legend_items}
    </div>"""
    m.get_root().html.add_child(folium.Element(legend_html))

    # ── Plot segment markers ──────────────────────────────
    plotted: dict[str, tuple] = {}
    for day in daily_itinerary:
        day_num = day["day_number"]
        city    = day.get("city", destination)

        if is_multi_city:
            col_info = city_color_map.get(city, {"folium":"blue","hex":"#2563EB"})
            marker_color = col_info["folium"]
            hex_color    = col_info["hex"]
        else:
            marker_color = DAY_COLORS[(day_num-1) % len(DAY_COLORS)]
            hex_color    = DAY_HEX[(day_num-1)   % len(DAY_HEX)]

        day_route_pts = []

        for seg in day.get("segments", []):
            title    = seg.get("title","")
            seg_type = seg.get("type","activity")
            icon_nm  = SEG_ICONS.get(seg_type,"info-sign")
            cost_str = f"Rs {seg.get('cost',0):,}" if seg.get("cost",0)>0 else "Free"

            lat_lng = all_coords.get(title)
            if not lat_lng:
                continue

            # Slight offset if exact duplicate location
            if title in plotted and plotted[title] == lat_lng:
                lat_lng = (lat_lng[0]+0.0003, lat_lng[1]+0.0003)
            plotted[title] = lat_lng
            day_route_pts.append(list(lat_lng))

            popup_html = f"""
            <div style="font-family:Arial;min-width:170px">
                <b style="color:{hex_color}">{seg.get('time','')} · {title}</b>
                {f'<span style="background:{hex_color};color:white;font-size:10px;padding:1px 6px;border-radius:3px;margin-left:4px">{city}</span>' if is_multi_city else ''}
                <br><span style="color:#64748B;font-size:11px">{seg.get('description','')}</span>
                <br><b style="color:#0D9488">{cost_str}</b>
                {f'<br><span style="color:#94A3B8;font-size:10px">💡 {seg["notes"]}</span>' if seg.get("notes") else ''}
            </div>"""

            folium.Marker(
                location=lat_lng,
                popup=folium.Popup(popup_html, max_width=230),
                tooltip=f"{'Day '+str(day_num)+' · ' if not is_multi_city else city+' · '}{title}",
                icon=folium.Icon(color=marker_color, icon=icon_nm, prefix="glyphicon"),
            ).add_to(m)

        # Day route polyline
        if len(day_route_pts) > 1:
            folium.PolyLine(
                day_route_pts, color=hex_color,
                weight=2, opacity=0.5, dash_array="6 4",
            ).add_to(m)

    # ── Multi-city: draw inter-city arrows ────────────────
    if is_multi_city and len(city_stops) > 1:
        # Origin → first city
        origin_coords = None
        # Try to find origin from day 1 transport segment
        if daily_itinerary:
            for seg in daily_itinerary[0].get("segments",[]):
                if seg.get("type") == "transport":
                    t = seg.get("title","")
                    origin_coords = all_coords.get(t)
                    break

        city_centers = [_center_for(s["city"]) for s in city_stops]

        # Draw thick colored lines between consecutive city centers
        all_centers = city_centers  # could prepend origin_coords if found
        for i in range(len(all_centers)-1):
            c1  = all_centers[i]
            c2  = all_centers[i+1]
            h1  = CITY_HEX[i % len(CITY_HEX)]
            h2  = CITY_HEX[(i+1) % len(CITY_HEX)]
            tt  = (f"{city_stops[i]['city']} → {city_stops[i+1]['city']} · "
                   f"{city_stops[i+1]['transport_from_prev']} · "
                   f"~{city_stops[i+1]['transport_time_hrs']}hrs")
            folium.PolyLine(
                [c1, c2], color=h2,
                weight=4, opacity=0.75,
                tooltip=tt,
            ).add_to(m)

        # City center labels
        for i, stop in enumerate(city_stops):
            cx = city_centers[i]
            hex_c = CITY_HEX[i % len(CITY_HEX)]
            folium.Marker(
                location=cx,
                icon=folium.DivIcon(html=f"""
                    <div style="font-family:Arial;font-size:13px;font-weight:bold;
                        color:white;background:{hex_c};padding:3px 8px;
                        border-radius:12px;white-space:nowrap;
                        box-shadow:0 1px 4px rgba(0,0,0,0.3)">
                        {stop['city']}
                    </div>""",
                    icon_size=(120, 30), icon_anchor=(60, 15)),
                tooltip=f"{stop['city']}: {stop['days']} days",
            ).add_to(m)

    marker_count = len(plotted)
    print(f"   ✅ Map: {marker_count} markers, {len(city_stops)} cities")
    return m._repr_html_()