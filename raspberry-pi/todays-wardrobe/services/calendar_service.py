import datetime
import os.path
from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build

from google.oauth2 import service_account

# If modifying these scopes, delete the file token.json.
SCOPES = ["https://www.googleapis.com/auth/calendar.readonly"]

def get_calendar_service():
    # PATH 1: Service Account (Optional/Advanced)
    if os.path.exists("service_account.json"):
        try:
            # Load credentials first to get the email
            creds = service_account.Credentials.from_service_account_file(
                "service_account.json", scopes=SCOPES
            )
            # Extract the service account email to show the user
            print(f"Successfully loaded Service Account.")
            print(f"Make sure to share your calendar with: {creds.service_account_email}")
            
            return build("calendar", "v3", credentials=creds)
        except Exception as e:
            print(f"Error loading service_account.json: {e}")
            return None

    # PATH 2: Desktop OAuth (Standard)
    creds = None
    if os.path.exists("token.json"):
        creds = Credentials.from_authorized_user_file("token.json", SCOPES)
    
    # If there are no (valid) credentials available, let the user log in.
    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            creds.refresh(Request())
        else:
            if not os.path.exists("credentials.json"):
                print("No credentials found. Please place 'credentials.json' in the project root.")
                return None
            
            print("Initiating Google Login. Your browser should open shortly...")
            flow = InstalledAppFlow.from_client_secrets_file(
                "credentials.json", SCOPES
            )
            creds = flow.run_local_server(port=0)
        
        # Save the credentials for the next run
        with open("token.json", "w") as token:
            token.write(creds.to_json())

    service = build("calendar", "v3", credentials=creds)
    return service

def get_todays_events():
    """Shows basic usage of the Google Calendar API.
    Prints the start and name of the next 10 events on the user's calendar.
    """
    service = get_calendar_service()
    if not service:
        return []

    now = datetime.datetime.now()
    # Start of today (midnight)
    start_of_day = now.replace(hour=0, minute=0, second=0, microsecond=0)
    # End of today (23:59:59)
    end_of_day = now.replace(hour=23, minute=59, second=59, microsecond=999999)
    
    start_iso = start_of_day.isoformat() + 'Z'  # 'Z' indicates UTC time
    end_iso = end_of_day.isoformat() + 'Z'

    try:
        events_result = (
            service.events()
            .list(
                calendarId="primary",
                timeMin=start_iso,
                timeMax=end_iso,
                singleEvents=True,
                orderBy="startTime",
            )
            .execute()
        )
        events = events_result.get("items", [])

        event_list = []
        if not events:
            print("No upcoming events found.")
        else:
            for event in events:
                start_data = event.get("start", {})
                end_data = event.get("end", {})
                
                start_raw = start_data.get("dateTime", start_data.get("date"))
                end_raw = end_data.get("dateTime", end_data.get("date"))
                
                # Format time nicely
                formatted_time = start_raw
                try:
                    # Check if it's a full datetime (contains 'T')
                    if 'T' in str(start_raw) and 'T' in str(end_raw):
                        start_dt = datetime.datetime.fromisoformat(start_raw)
                        end_dt = datetime.datetime.fromisoformat(end_raw)
                        
                        start_str = start_dt.strftime("%I:%M %p")
                        end_str = end_dt.strftime("%I:%M %p")
                        
                        formatted_time = f"{start_str} - {end_str}"
                    else:
                        # It's just a date, likely all-day
                        formatted_time = "All Day"
                except Exception:
                    pass
                
                summary = event.get("summary", "No Title")
                description = event.get("description", "")
                location = event.get("location", "")
                event_list.append({
                    "start": formatted_time,
                    "summary": summary,
                    "description": description,
                    "location": location
                })

        return event_list

    except Exception as e:
        print(f"An error occurred: {e}")
        return []

if __name__ == "__main__":
    events = get_todays_events()
    for event in events:
        print(event)
