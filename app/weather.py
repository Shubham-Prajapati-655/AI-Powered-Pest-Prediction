import urllib.request
import json
import urllib.parse
import time
import os
import sys
from datetime import datetime

sys.path.insert(0, os.path.abspath(os.path.dirname(__file__)))

from config import WEATHER_API_TIMEOUT, WEATHER_API_RETRIES, WEATHER_CACHE_TTL_SECONDS
from logger import log_weather_event, get_logger

logger = get_logger("weather")

# Comprehensive Indian District Coordinates Dictionary (All supported districts)
DISTRICT_COORDS = {
    "guntur": (16.3067, 80.4365),
    "vijayawada": (16.5062, 80.6480),
    "kurnool": (15.8281, 78.0373),
    "anantapur": (14.6819, 77.6006),
    "visakhapatnam": (17.6868, 83.2185),
    "ahmedabad": (23.0225, 72.5714),
    "rajkot": (22.3039, 70.8022),
    "surat": (21.1702, 72.8311),
    "vadodara": (22.3072, 73.1812),
    "bhavnagar": (21.7645, 72.1519),
    "pune": (18.5204, 73.8567),
    "nagpur": (21.1458, 79.0882),
    "nashik": (20.0059, 73.7898),
    "aurangabad": (19.8762, 75.3433),
    "solapur": (17.6599, 75.9064),
    "bengaluru": (12.9716, 77.5946),
    "belagavi": (15.8497, 74.4977),
    "hubballi": (15.3647, 75.1240),
    "mysuru": (12.2958, 76.6394),
    "dharwad": (15.4589, 75.0078),
    "kanpur": (26.4499, 80.3319),
    "lucknow": (26.8467, 80.9462),
    "varanasi": (25.3176, 82.9739),
    "agra": (27.1767, 78.0081),
    "meerut": (28.9845, 77.7064),
    "burdwan": (23.2324, 87.8615),
    "kolkata": (22.5726, 88.3639),
    "hooghly": (22.9034, 88.3966),
    "murshidabad": (24.1759, 88.2802),
    "nadia": (23.4710, 88.5565),
    "coimbatore": (11.0168, 76.9558),
    "madurai": (9.9252, 78.1198),
    "salem": (11.6643, 78.1460),
    "tiruchirappalli": (10.7905, 78.7047),
    "tirunelveli": (8.7139, 77.7567),
    "hisar": (29.1492, 75.7217),
    "karnal": (29.6857, 76.9905),
    "sirsa": (29.5349, 75.0277),
    "davanagere": (14.4644, 75.9218),
    "ujjain": (23.1765, 75.7885),
    "indore": (22.7196, 75.8577),
    "sehore": (23.2030, 77.0844),
    "ludhiana": (30.9010, 75.8573),
    "patiala": (30.3398, 76.3869),
    "sangrur": (30.2458, 75.8420),
    "erode": (11.3410, 77.7172),
    "bareilly": (28.3670, 79.4304),
    "bardhaman": (23.2324, 87.8615)
}

_GEO_CACHE = {}

DEMO_PRESETS = {
    "Monsoon High Pest Outbreak": {"temp": 32.5, "humidity": 82.0, "rainfall": 165.0, "season": "Monsoon"},
    "Winter Moderate Pest Outbreak": {"temp": 24.0, "humidity": 58.0, "rainfall": 18.0, "season": "Winter"},
    "Summer Low Risk Baseline": {"temp": 36.5, "humidity": 42.0, "rainfall": 5.0, "season": "Summer"}
}

# WMO Weather Code Mappings
WMO_WEATHER_CODES = {
    0: ("Clear Sky", "☀️"),
    1: ("Mainly Clear", "🌤️"),
    2: ("Partly Cloudy", "⛅"),
    3: ("Overcast", "☁️"),
    45: ("Foggy", "🌫️"),
    48: ("Depositing Rime Fog", "🌫️"),
    51: ("Light Drizzle", "🌧️"),
    53: ("Moderate Drizzle", "🌧️"),
    55: ("Dense Drizzle", "🌧️"),
    56: ("Light Freezing Drizzle", "🌧️"),
    57: ("Dense Freezing Drizzle", "🌧️"),
    61: ("Slight Rain", "🌧️"),
    63: ("Moderate Rain", "🌧️"),
    65: ("Heavy Rain", "🌧️"),
    66: ("Light Freezing Rain", "🌧️"),
    67: ("Heavy Freezing Rain", "🌧️"),
    71: ("Slight Snow", "🌨️"),
    73: ("Moderate Snow", "🌨️"),
    75: ("Heavy Snow", "🌨️"),
    77: ("Snow Grains", "🌨️"),
    80: ("Slight Rain Showers", "🌦️"),
    81: ("Moderate Rain Showers", "🌦️"),
    82: ("Violent Rain Showers", "🌦️"),
    85: ("Slight Snow Showers", "🌨️"),
    86: ("Heavy Snow Showers", "🌨️"),
    95: ("Thunderstorm", "⛈️"),
    96: ("Thunderstorm with Light Hail", "⛈️"),
    99: ("Thunderstorm with Heavy Hail", "⛈️"),
}

# In-Memory Cache and Fallback Storage
WEATHER_CACHE = {}         # Key: (round(lat, 4), round(lon, 4)), Value: (timestamp, result_dict)
LAST_SUCCESSFUL_WEATHER = {}  # Key: (round(lat, 4), round(lon, 4)), Value: result_dict
CACHE_TTL_SECONDS = WEATHER_CACHE_TTL_SECONDS

def get_wmo_weather_condition(code):
    """Map WMO weather code integer to human readable description and emoji."""
    info = WMO_WEATHER_CODES.get(code, ("Partly Cloudy", "⛅"))
    return f"{info[0]} {info[1]}"

def get_current_sowing_season():
    """
    Auto-detect current sowing season based on calendar date/month:
    - June to September (Months 6-9) -> Kharif
    - October to March (Months 10-12, 1-3) -> Rabi
    - April to May (Months 4-5) -> Zaid
    """
    month = datetime.now().month
    if 6 <= month <= 9:
        return "Kharif"
    elif 10 <= month <= 12 or 1 <= month <= 3:
        return "Rabi"
    else:
        return "Zaid"

def derive_season_from_sowing(sowing_season=None):
    """Auto-derive meteorological season from sowing season or calendar date."""
    if not sowing_season:
        sowing_season = get_current_sowing_season()
            
    s_clean = sowing_season.strip().lower()
    if "kharif" in s_clean:
        return "Monsoon"
    elif "rabi" in s_clean:
        return "Winter"
    elif "zaid" in s_clean:
        return "Summer"
    else:
        return "Monsoon"

import ssl

def get_coordinates(district, state):
    """Fetch Lat, Lon from pre-cached dictionary or Open-Meteo Geocoding API with memory caching."""
    clean_dist = district.strip().lower()
    clean_state = state.strip().lower()
    
    # 1. Immediate lookup in pre-configured district dictionary (0 ms)
    if clean_dist in DISTRICT_COORDS:
        return DISTRICT_COORDS[clean_dist]
        
    # 2. Check dynamic memory cache
    cache_key = (clean_dist, clean_state)
    if cache_key in _GEO_CACHE:
        return _GEO_CACHE[cache_key]
    
    try:
        query = f"{district}, {state}, India"
        encoded_query = urllib.parse.quote(query)
        geo_url = f"https://geocoding-api.open-meteo.com/v1/search?name={encoded_query}&count=5&language=en&format=json"
        
        req = urllib.request.Request(geo_url, headers={"User-Agent": "PestPredictionApp/2.2"})
        try:
            resp_ctx = urllib.request.urlopen(req, timeout=3)
        except Exception as e_ssl:
            if "CERTIFICATE_VERIFY_FAILED" in str(e_ssl) or "ssl" in str(e_ssl).lower():
                unverified_ctx = ssl._create_unverified_context()
                resp_ctx = urllib.request.urlopen(req, timeout=3, context=unverified_ctx)
            else:
                raise e_ssl
        with resp_ctx as resp:
            data = json.loads(resp.read().decode("utf-8"))
            if "results" in data and len(data["results"]) > 0:
                for res in data["results"]:
                    country = res.get("country", "").lower()
                    if country == "india" or "in" in res.get("country_code", "").lower():
                        coords = (float(res["latitude"]), float(res["longitude"]))
                        _GEO_CACHE[cache_key] = coords
                        return coords
                coords = (float(data["results"][0]["latitude"]), float(data["results"][0]["longitude"]))
                _GEO_CACHE[cache_key] = coords
                return coords
    except Exception as e:
        logger.warning(f"Geocoding lookup fallback for ({district}, {state}): {e}")
        
    fallback = DISTRICT_COORDS.get(clean_dist, (16.3067, 80.4365))
    _GEO_CACHE[cache_key] = fallback
    return fallback

def fetch_open_meteo_weather(district, state, sowing_season="Kharif", demo_mode=False, demo_preset="Monsoon High Pest Outbreak"):
    """
    Fetch current Temperature, Humidity, 24h Rainfall, Wind Speed, and Weather Condition from Open-Meteo.
    Implements 10-minute coordinate-based caching and last successful weather fallback.
    """
    now_time = datetime.now()
    formatted_time = now_time.strftime("%d %b %Y • %I:%M %p IST")

    if demo_mode and demo_preset in DEMO_PRESETS:
        dp = DEMO_PRESETS[demo_preset]
        temp = dp["temp"]
        humidity = dp["humidity"]
        rainfall = dp["rainfall"]
        season = dp["season"]
        lat, lon = DISTRICT_COORDS.get(district.strip().lower(), (16.3067, 80.4365))
        thi = round(0.8 * temp + (humidity / 100.0) * (temp - 14.3) + 46.4, 2)
        rf_hum_ratio = round(rainfall / (humidity + 1.0), 4)
        return {
            "temperature": round(temp, 2),
            "humidity": round(humidity, 2),
            "rainfall_mm": round(rainfall, 2),
            "wind_speed": 12.5,
            "cloud_cover": 40.0,
            "weather_condition": "Partly Cloudy ⛅",
            "last_updated": f"{formatted_time} • Demo Mode",
            "observation_time": formatted_time,
            "thi": thi,
            "rainfall_humidity_ratio": rf_hum_ratio,
            "season": season,
            "latitude": lat,
            "longitude": lon,
            "is_live": False,
            "source_note": f"Demo Mode ({demo_preset})"
        }

    lat, lon = get_coordinates(district, state)
    cache_key = (round(lat, 4), round(lon, 4))
    curr_timestamp = time.time()

    # 1. Check in-memory cache
    if cache_key in WEATHER_CACHE:
        cached_ts, cached_data = WEATHER_CACHE[cache_key]
        if curr_timestamp - cached_ts < CACHE_TTL_SECONDS:
            log_weather_event("CACHE_HIT", f"{district}, {state}")
            return cached_data

    api_url = f"https://api.open-meteo.com/v1/forecast?latitude={lat}&longitude={lon}&current=temperature_2m,relative_humidity_2m,precipitation,weather_code,wind_speed_10m,cloud_cover&timezone=auto"
    
    # Fast retry loop with minimal timeout to prevent blocking UI
    last_err = None
    timeout_val = min(float(WEATHER_API_TIMEOUT), 1.2)
    for attempt in range(max(1, WEATHER_API_RETRIES)):
        start_time = time.time()
        try:
            req = urllib.request.Request(api_url, headers={"User-Agent": "PestPredictionApp/2.2"})
            try:
                resp_ctx = urllib.request.urlopen(req, timeout=timeout_val)
            except Exception as e_ssl:
                if "CERTIFICATE_VERIFY_FAILED" in str(e_ssl) or "ssl" in str(e_ssl).lower():
                    unverified_ctx = ssl._create_unverified_context()
                    resp_ctx = urllib.request.urlopen(req, timeout=timeout_val, context=unverified_ctx)
                else:
                    raise e_ssl
            with resp_ctx as resp:
                http_status = resp.getcode()
                response_time_ms = round((time.time() - start_time) * 1000, 2)
                data = json.loads(resp.read().decode("utf-8"))
                
                if "current" in data:
                    cur = data["current"]
                    temp = float(cur.get("temperature_2m", 28.0))
                    humidity = float(cur.get("relative_humidity_2m", 65.0))
                    precipitation = float(cur.get("precipitation", 0.0))
                    weather_code = int(cur.get("weather_code", 0))
                    wind_speed = float(cur.get("wind_speed_10m", 10.0))
                    cloud_cover = float(cur.get("cloud_cover", 35.0))
                    
                    weather_cond = get_wmo_weather_condition(weather_code)
                    season = derive_season_from_sowing(sowing_season)
                    
                    if precipitation <= 0.1:
                        if season == "Monsoon":
                            rainfall = round(max(15.0, (humidity / 100.0) * 120.0), 2)
                        elif season == "Winter":
                            rainfall = round(max(2.0, (humidity / 100.0) * 25.0), 2)
                        else:
                            rainfall = 5.0
                    else:
                        rainfall = round(precipitation * 24.0, 2)

                    thi = round(0.8 * temp + (humidity / 100.0) * (temp - 14.3) + 46.4, 2)
                    rf_hum_ratio = round(rainfall / (humidity + 1.0), 4)

                    result_data = {
                        "temperature": round(temp, 2),
                        "humidity": round(humidity, 2),
                        "rainfall_mm": round(rainfall, 2),
                        "wind_speed": round(wind_speed, 2),
                        "cloud_cover": round(cloud_cover, 1),
                        "weather_condition": weather_cond,
                        "last_updated": f"{formatted_time} • Open-Meteo",
                        "observation_time": formatted_time,
                        "thi": thi,
                        "rainfall_humidity_ratio": rf_hum_ratio,
                        "season": season,
                        "latitude": lat,
                        "longitude": lon,
                        "is_live": True,
                        "source_note": "Live Weather Data (Open-Meteo)"
                    }

                    log_weather_event("SUCCESS", f"{district}, {state}", response_time_ms)

                    # Store in cache and last successful store
                    WEATHER_CACHE[cache_key] = (curr_timestamp, result_data)
                    LAST_SUCCESSFUL_WEATHER[cache_key] = result_data

                    return result_data

        except Exception as e:
            last_err = e
            if attempt < WEATHER_API_RETRIES - 1:
                time.sleep(0.1)

    log_weather_event("ERROR", f"{district}, {state}", error=str(last_err))

    # 2. Check last successful weather fallback before baseline defaults
    if cache_key in LAST_SUCCESSFUL_WEATHER:
        logger.warning(f"Using Last Successful Weather Fallback for ({lat}, {lon})")
        fallback_res = dict(LAST_SUCCESSFUL_WEATHER[cache_key])
        fallback_res["source_note"] = "Last Successful Weather (Cached Fallback)"
        if "cloud_cover" not in fallback_res:
            fallback_res["cloud_cover"] = 30.0
        if "observation_time" not in fallback_res:
            fallback_res["observation_time"] = formatted_time
        return fallback_res

    # 3. Baseline Default Fallback
    season = derive_season_from_sowing(sowing_season)
    if season == "Monsoon":
        temp, humidity, rainfall, wind_speed, cloud_cover = 29.5, 75.0, 140.0, 14.0, 65.0
    elif season == "Winter":
        temp, humidity, rainfall, wind_speed, cloud_cover = 22.0, 55.0, 15.0, 8.0, 20.0
    else:
        temp, humidity, rainfall, wind_speed, cloud_cover = 34.0, 45.0, 10.0, 12.0, 15.0

    thi = round(0.8 * temp + (humidity / 100.0) * (temp - 14.3) + 46.4, 2)
    rf_hum_ratio = round(rainfall / (humidity + 1.0), 4)

    baseline_data = {
        "temperature": round(temp, 2),
        "humidity": round(humidity, 2),
        "rainfall_mm": round(rainfall, 2),
        "wind_speed": round(wind_speed, 2),
        "cloud_cover": round(cloud_cover, 1),
        "weather_condition": "Partly Cloudy ⛅",
        "last_updated": f"{formatted_time} • Baseline Fallback",
        "observation_time": formatted_time,
        "thi": thi,
        "rainfall_humidity_ratio": rf_hum_ratio,
        "season": season,
        "latitude": lat,
        "longitude": lon,
        "is_live": False,
        "source_note": "Baseline Fallback Weather Data"
    }
    WEATHER_CACHE[cache_key] = (curr_timestamp, baseline_data)
    LAST_SUCCESSFUL_WEATHER[cache_key] = baseline_data
    return baseline_data
