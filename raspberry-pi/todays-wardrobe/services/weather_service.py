import requests
from geopy.geocoders import Nominatim
from datetime import datetime

# Initialize Geocoder with a custom user agent (required by Nominatim terms)
geolocator = Nominatim(user_agent="smart_wardrobe_pi")

def get_lat_long(location_name):
    """
    Converts a location string (e.g., "Times Square, NY") to (latitude, longitude).
    """
    try:
        location = geolocator.geocode(location_name)
        if location:
            return location.latitude, location.longitude
        return None, None
    except Exception as e:
        print(f"Geocoding error for {location_name}: {e}")
        return None, None

def get_weather(location_name):
    """
    Fetches the weather forecast for today for a given location name.
    """
    lat, lon = get_lat_long(location_name)
    if not lat:
        return f"(Weather data unavailable for '{location_name}')"

    # API request to Open-Meteo
    # We ask for max/min temp and weather code for today
    url = "https://api.open-meteo.com/v1/forecast"
    params = {
        "latitude": lat,
        "longitude": lon,
        "daily": ["weather_code", "temperature_2m_max", "temperature_2m_min"],
        "timezone": "auto",
        "forecast_days": 1
    }

    try:
        response = requests.get(url, params=params)
        data = response.json()
        
        if "daily" in data:
            daily = data["daily"]
            max_temp = daily["temperature_2m_max"][0]
            min_temp = daily["temperature_2m_min"][0]
            # Simple WMO weather code interpretation (could be expanded)
            code = daily.get("weather_code", [0])[0]
            
            # Basic WMO code map
            condition = "Clear"
            if code in [1, 2, 3]: condition = "Cloudy"
            elif code in [45, 48]: condition = "Foggy"
            elif code in [51, 53, 55, 61, 63, 65]: condition = "Rainy"
            elif code in [71, 73, 75, 77]: condition = "Snowy"
            elif code >= 95: condition = "Thunderstorm"

            return f"{condition}, High: {max_temp}°C, Low: {min_temp}°C"
        
        return "(Weather data parse error)"

    except Exception as e:
        print(f"Weather API error: {e}")
        return "(Weather fetch failed)"
