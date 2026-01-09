from flask import Flask, render_template, Response, stream_with_context
from dotenv import load_dotenv
import json
import time

# Import services
from services.calendar_service import get_todays_events
from services.gemini_service import get_stylist_recommendation
import os

load_dotenv()

app = Flask(__name__)

@app.route('/')
def index():
    # Render the page with just the button initially. 
    # State flags in template will handle visibility (or we assume 'events' is None initially)
    return render_template('index.html', events=None)

@app.route('/stream_wardrobe_generation')
def stream_wardrobe_generation():
    def generate():
        # Setup SSE format helper
        def sse(data):
            return f"data: {json.dumps(data)}\n\n"

        try:
            # Step 1: Calendar
            yield sse({"status": "📅 Connecting to Google Calendar...", "progress": 10})
            events = get_todays_events()
            yield sse({"status": f"Found {len(events)} events for today.", "progress": 25})
            
            # Step 2: Stylist API (Loop through each event)
            processed_outfits = []
            total_events = len(events)
            
            if total_events == 0:
                # Handle no events case
                yield sse({"status": "No events found, but checking for a general recommendation...", "progress": 50})
                # Create a dummy event for general advice
                dummy_event = {"summary": "General Day", "start": "Today", "location": "", "description": "Just a regular day"}
                outfit = get_stylist_recommendation(dummy_event, index=0)
                processed_outfits.append(outfit)
            else:
                for i, event in enumerate(events):
                    progress = 25 + int((i / total_events) * 70)
                    yield sse({"status": f"✨ Styling for '{event['summary']}'...", "progress": progress})
                    
                    outfit = get_stylist_recommendation(event, index=i)
                    processed_outfits.append(outfit)
            
            # Finish
            yield sse({
                "status": "All Done!", 
                "progress": 100, 
                "complete": True, 
                "events": events, 
                "outfits": processed_outfits
            })
            
        except Exception as e:
            yield sse({"error": str(e)})

    return Response(stream_with_context(generate()), mimetype='text/event-stream')

if __name__ == '__main__':
    # Host 0.0.0.0 is important for Raspberry Pi to be accessible from other devices
    app.run(debug=True, host='0.0.0.0', port=5000)
