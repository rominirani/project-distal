import json
import os
# --- KEY CHANGE: Import the socket-capable requests session ---
import requests_unixsocket

# --- CONFIGURATION ---
# We use a special URL format: http+unix:// + URL-encoded path to the socket file
# /tmp/wardrobe.sock becomes %2Ftmp%2Fwardrobe.sock
SOCKET_URL = "http+unix://%2Ftmp%2Fwardrobe.sock/api/ingest"
TEST_IMAGE = "new_dress.jpg" 

# --- SIMULATED SENSOR DATA ---
fake_sensor_data = {
    "roughness": 0.8,  
    "stiffness": 0.1   
}

def simulate_hardware_ingestion():
    if not os.path.exists(TEST_IMAGE):
        print(f"Error: Could not find file '{TEST_IMAGE}' next to this script.")
        return

    print(f"--- Simulating Hardware Ingestion (via Unix Socket) ---")
    print(f"Targeting: {SOCKET_URL}")
    print(f"Sending '{TEST_IMAGE}'...")

    # --- KEY CHANGE: Create a special session that speaks sockets ---
    session = requests_unixsocket.Session()

    with open(TEST_IMAGE, 'rb') as img_file:
        files = {'image': (TEST_IMAGE, img_file, 'image/jpeg')}
        data = {'tactile_json': json.dumps(fake_sensor_data)}
        
        try:
            # Use the 'session' object instead of 'requests' directly
            response = session.post(SOCKET_URL, files=files, data=data)
            
            print(f"\n[Server Status]: {response.status_code}")
            
            if response.status_code == 200:
                try:
                    result = response.json()
                    print("--- SUCCESS! Item Ingested ---")
                    print(f"New ID: {result.get('id')}")
                    # print("Gemini Analysis:")
                    # print(json.dumps(result.get('analysis'), indent=2))
                except Exception as e:
                    print(f"Error parsing JSON: {e}")
                    print("Raw Response snippet:", response.text[:200])
            else:
                print("\n--- FAILED: Server returned an error ---")
                print("Raw response sample:", response.text[:200]) 
                
        except Exception as e:
             print(f"\n--- Connection Error ---")
             print(f"Could not connect to socket. Is Gunicorn running with unix:/tmp/wardrobe.sock?")
             print(f"Error details: {e}")

if __name__ == "__main__":
    simulate_hardware_ingestion()