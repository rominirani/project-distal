import os
import requests
import base64
import time
import json
from services.weather_service import get_weather

def build_event_context(event):
    """
    Builds a context string for a single event.
    """
    weather_info = ""
    if event.get('location'):
        weather = get_weather(event['location'])
        weather_info = f" [Weather at {event['location']}: {weather}]"
    
    return f"Event: {event['summary']} at {event['start']}. Location: {event['location']}{weather_info}. Description: {event['description']}"

def get_stylist_recommendation(event, index=0):
    """
    Calls the external stylist API for a single event.
    Returns a dict with recommendation details and image filename.
    """
    context = build_event_context(event)
    url = "https://wardrobe-uxu5wi2jpa-uc.a.run.app/api/agent/stylist"
    
    try:
        print(f"DEBUG: Calling Stylist API for event: {event['summary']}")
        response = requests.post(url, json={"context": context}, timeout=60)
        
        if response.status_code == 200:
            data = response.json()
            print(f"DEBUG: API Response keys: {list(data.keys())}")
            
            # Extract explanation from root or use default
            explanation = data.get("explanation", data.get("context", "Here is a look for your event."))
            
            # Process items
            processed_items = []
            items_list = data.get("items", [])
            
            for i, item in enumerate(items_list):
                # Save image
                image_b64 = item.get("image_base64")
                image_filename = None
                
                if image_b64:
                    try:
                        if "," in image_b64:
                            image_b64 = image_b64.split(",")[1]
                        image_b64 = image_b64.replace("\n", "").strip()
                        
                        image_data = base64.b64decode(image_b64)
                        # Unique name: event_index + item_id + timestamp
                        image_filename = f"item_{index}_{item.get('id', i)}_{int(time.time())}.png"
                        fs_path = os.path.join("static", image_filename)
                        with open(fs_path, "wb") as f:
                            f.write(image_data)
                    except Exception as e:
                        print(f"Error saving image for item {i}: {e}")
                
                processed_items.append({
                    "category": item.get("category"),
                    "color": item.get("color"),
                    "material": item.get("material"),
                    "image_filename": image_filename
                })

            return {
                "events_involved": event['summary'],
                "recommendation": explanation,
                "items": processed_items
            }
        else:
            print(f"API Error {response.status_code}: {response.text}")
            return {
                "events_involved": event['summary'],
                "recommendation": f"Error getting advice: {response.text}",
                "items": []
            }

    except Exception as e:
        print(f"Exception calling API: {e}")
        return {
            "events_involved": event['summary'],
            "recommendation": f"Connection error: {e}",
            "items": []
        }

def get_outfit_recommendation(events):
    return rec_html, img_file
