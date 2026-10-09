import unittest
import os
import sys
import json
import urllib.request

# Add app directory to Python path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "app")))

from weather import fetch_open_meteo_weather, get_coordinates, WEATHER_CACHE, LAST_SUCCESSFUL_WEATHER

class TestWeatherAccuracyAndReliability(unittest.TestCase):

    def setUp(self):
        # Clear cache for isolated tests
        WEATHER_CACHE.clear()
        LAST_SUCCESSFUL_WEATHER.clear()

    def test_01_geocoding_district_precision(self):
        """Verify district geocoding returns valid latitude and longitude coordinates."""
        test_cases = [
            ("Guntur", "Andhra Pradesh"),
            ("Ahmedabad", "Gujarat"),
            ("Pune", "Maharashtra"),
            ("Bengaluru", "Karnataka"),
            ("Kanpur", "Uttar Pradesh")
        ]
        for dist, state in test_cases:
            lat, lon = get_coordinates(dist, state)
            self.assertIsInstance(lat, float)
            self.assertIsInstance(lon, float)
            self.assertGreater(lat, 5.0)
            self.assertLess(lat, 38.0)
            self.assertGreater(lon, 68.0)
            self.assertLess(lon, 98.0)

    def test_02_10_minute_coordinate_caching(self):
        """Verify 10-minute cache returns cached result without refetching."""
        dist, state = "Guntur", "Andhra Pradesh"
        w1 = fetch_open_meteo_weather(dist, state)
        lat, lon = w1["latitude"], w1["longitude"]
        cache_key = (round(lat, 4), round(lon, 4))
        
        self.assertIn(cache_key, WEATHER_CACHE)
        
        w2 = fetch_open_meteo_weather(dist, state)
        self.assertEqual(w1["temperature"], w2["temperature"])
        self.assertEqual(w1["humidity"], w2["humidity"])

    def test_03_last_successful_weather_fallback(self):
        """Verify last successful weather store falls back gracefully on API error."""
        lat, lon = 16.3067, 80.4365
        cache_key = (round(lat, 4), round(lon, 4))
        
        # Populate last successful weather store
        sample_data = {
            "temperature": 30.5,
            "humidity": 70.0,
            "rainfall_mm": 15.0,
            "wind_speed": 12.0,
            "weather_condition": "Partly Cloudy ⛅",
            "last_updated": "25 Aug 2026 • 09:15 AM IST • Cached",
            "is_live": True,
            "source_note": "Last Successful Test Data"
        }
        LAST_SUCCESSFUL_WEATHER[cache_key] = sample_data
        
        # Simulate fetch failure with bad district name (triggers fallback)
        res = fetch_open_meteo_weather("NonExistentDistrictXYZ", "NonExistentState")
        self.assertIn("temperature", res)
        self.assertIn("humidity", res)

    def test_04_open_meteo_accuracy_comparison(self):
        """Compare app weather output with direct official Open-Meteo endpoint and report average deviation."""
        test_districts = [
            ("Guntur", "Andhra Pradesh"),
            ("Ahmedabad", "Gujarat"),
            ("Pune", "Maharashtra"),
            ("Bengaluru", "Karnataka"),
            ("Kolkata", "West Bengal")
        ]

        temp_diffs = []
        hum_diffs = []
        wind_diffs = []

        print("\n" + "="*70)
        print("OPEN-METEO LIVE WEATHER ACCURACY COMPARISON REPORT")
        print("="*70)
        print(f"{'District':<12} | {'App Temp (°C)':<14} | {'Ref Temp (°C)':<14} | {'Dev (°C)':<10}")
        print("-" * 70)

        for dist, state in test_districts:
            WEATHER_CACHE.clear()
            app_weather = fetch_open_meteo_weather(dist, state)
            lat, lon = app_weather["latitude"], app_weather["longitude"]

            # Fetch reference weather directly from Open-Meteo API
            ref_url = f"https://api.open-meteo.com/v1/forecast?latitude={lat}&longitude={lon}&current=temperature_2m,relative_humidity_2m,wind_speed_10m&timezone=auto"
            try:
                req = urllib.request.Request(ref_url, headers={"User-Agent": "PestPredictionTest/1.0"})
                with urllib.request.urlopen(req, timeout=5) as resp:
                    ref_data = json.loads(resp.read().decode("utf-8"))["current"]
                    ref_temp = float(ref_data["temperature_2m"])
                    ref_hum = float(ref_data["relative_humidity_2m"])
                    ref_wind = float(ref_data["wind_speed_10m"])

                    t_diff = abs(app_weather["temperature"] - ref_temp)
                    h_diff = abs(app_weather["humidity"] - ref_hum)
                    w_diff = abs(app_weather["wind_speed"] - ref_wind)

                    temp_diffs.append(t_diff)
                    hum_diffs.append(h_diff)
                    wind_diffs.append(w_diff)

                    print(f"{dist:<12} | {app_weather['temperature']:<14.2f} | {ref_temp:<14.2f} | {t_diff:<10.2f}")
            except Exception as e:
                print(f"Skipping reference check for {dist}: {e}")

        if temp_diffs:
            avg_t_dev = sum(temp_diffs) / len(temp_diffs)
            avg_h_dev = sum(hum_diffs) / len(hum_diffs)
            avg_w_dev = sum(wind_diffs) / len(wind_diffs)

            print("-" * 70)
            print(f"AVERAGE TEMPERATURE DEVIATION: {avg_t_dev:.4f} °C")
            print(f"AVERAGE HUMIDITY DEVIATION:    {avg_h_dev:.4f} %")
            print(f"AVERAGE WIND SPEED DEVIATION:   {avg_w_dev:.4f} km/h")
            print("="*70 + "\n")

            self.assertLess(avg_t_dev, 1.0, "Average temperature deviation exceeds acceptable threshold")
            self.assertLess(avg_h_dev, 2.0, "Average humidity deviation exceeds acceptable threshold")

if __name__ == "__main__":
    unittest.main()
