# TODO: Add function that takes in the data from generate_timestamps and formats it into a user friendly timestamp format. 
# This function should be callable from the frontend, since it will bring a popup window with the formatted timestamps.
# Make sure to use get_driver so the message can make sense with the driver's name/first three letters.
# This function can be called format_timestamps and should take in the result of generate_timestamps as input.
# Then we would need to change the Timestamp.js component to include the formatted timestamps component.
# After comment out console logs.

from firebase_functions import https_fn
from firebase_functions.options import set_global_options
from firebase_admin import initialize_app
import functions_framework
import os
from dotenv import load_dotenv
import requests
import json
from datetime import datetime

# Silence module prints in production; set to True to enable
PRINT_LOGS = False
if not PRINT_LOGS:
    print = lambda *args, **kwargs: None

# Load environment variables from .env file
load_dotenv(dotenv_path=os.path.join(os.path.dirname(__file__), '.env'))
BASE_API_URL = os.getenv('REACT_APP_BASE_API_URL')

# For cost control, you can set the maximum number of containers that can be
# running at the same time. This helps mitigate the impact of unexpected
# traffic spikes by instead downgrading performance. This limit is a per-function
# limit. You can override the limit for each function using the max_instances
# parameter in the decorator, e.g. @https_fn.on_request(max_instances=5).
set_global_options(max_instances=10)

initialize_app()

# Helper functions for time conversion
def _time_to_seconds(time_str):
    """Convert HH:MM:SS string to total seconds."""
    h, m, s = map(int, time_str.split(':'))
    return h * 3600 + m * 60 + s

def _seconds_to_time(seconds):
    """Convert total seconds to HH:MM:SS string."""
    h = int(seconds // 3600)
    m = int((seconds % 3600) // 60)
    s = int(seconds % 60)
    return f"{h:02d}:{m:02d}:{s:02d}"

# Main HTTP callable function
@https_fn.on_call()
def generate_timestamps(req: https_fn.CallableRequest) -> dict:
    """
    HTTP callable function to generate F1 race timestamps.
    
    Expected request data:
    {
        "year": int,
        "country": str,
        "meeting_name": str,
        "driver_number": int (optional),
        "event_filter": str ("all", "overtakes", "pits", "flags")
        "calibration_offset": ISO 8601 time str
    }
    
    Returns:
        dict: Timestamp data including meetings, session, and filtered events
    """
    try:
        data = req.data
        print(f"[generate_timestamps] Called with data: {data}")
        
        year = data.get("year")
        country = data.get("country")
        meeting_name = data.get("meeting_name")
        driver_number = data.get("driver_number")
        event_filter = data.get("event_filter").lower()
        calibration_offset = data.get("calibration_offset")
        
        # Validate required fields
        if not year or not country or not meeting_name:
            print("[generate_timestamps] Validation failed: Missing required fields")
            return {
                "error": "Missing required fields: year, country, and meeting_name are required",
                "status": 400
            }
        
        # Step 1: Get meeting data
        print("[generate_timestamps] Step 1: Fetching meeting data...")
        meetings_data = _get_meetings(year, country, meeting_name)
        
        if not meetings_data or len(meetings_data) == 0:
            return {
                "error": "No meeting found for the given parameters",
                "status": 404
            }
        
        meeting = meetings_data[0]
        circuit_key = meeting.get("circuit_key")
        meeting_key = meeting.get("meeting_key")
        
        # Step 2: Get session data
        print("[generate_timestamps] Step 2: Fetching session data...")
        session_data = _get_session(year, circuit_key, meeting_key)
        
        if not session_data or len(session_data) == 0:
            return {
                "error": "No race session found for this meeting",
                "status": 404
            }
        
        session = session_data[0]
        session_key = session.get("session_key")
        session_start = session.get("date_start")
        
        # Extract time from ISO 8601 format
        dt = datetime.fromisoformat(session_start.replace('Z', '+00:00'))
        session_time = dt.strftime("%H:%M:%S")
        
        # Calculate calibration offset (default user time to 00:00:00 if empty)
        # Calibration Offset = API_Event_UTC - User_Video_Timestamp
        api_seconds = _time_to_seconds(session_time)
        try:
            user_seconds = _time_to_seconds(calibration_offset) if calibration_offset else 0
        except Exception:
            user_seconds = 0
        offset_seconds = api_seconds - user_seconds
        print(f"[generate_timestamps] Calibration: API time={session_time}, User time={calibration_offset or '00:00:00'}, Offset={offset_seconds}s")
        
        # Step 3: Fetch event data based on filter
        events_data = {}
        
        if event_filter == "all" or event_filter == "overtakes":
            print("[generate_timestamps] Step 3: Fetching overtakes...")
            events_data["overtakes"] = _get_overtakes(session_key, driver_number)
        
        if event_filter == "all" or event_filter == "pits":
            print("[generate_timestamps] Step 3: Fetching pits...")
            events_data["pits"] = _get_pits(session_key, driver_number)
        
        if event_filter == "all" or event_filter == "yellow and red flags":
            print("[generate_timestamps] Step 3: Fetching flags...")
            events_data["flags"] = _get_flags(session_key)
        
        # Step 4: Apply calibration to all events
        events_data = _apply_calibration(events_data, offset_seconds)
        
        print(f"[generate_timestamps] Successfully generated timestamps")
        
        payload = {
            "meeting": meeting,
            "session": session,
            "session_time": session_time,
            "calibration_offset": calibration_offset,
            "offset_seconds": offset_seconds,
            "events": events_data
        }

        # Return the formatted list directly
        formatted = _format_timestamps(payload)
        return formatted
    
    except Exception as e:
        print(f"[generate_timestamps] Error: {str(e)}")
        return {
            "error": str(e),
            "status": 500
        }

# Internal helper functions (not directly callable from frontend)

def _get_meetings(year, country, meeting_name):
    """Internal function to fetch F1 meetings from OpenF1 API."""
    print(f"[_get_meetings] year: {year}, country: {country}, meeting_name: {meeting_name}")
    
    meetings_url = f"{BASE_API_URL}meetings?year={year}&country_name={country}&meeting_name={meeting_name}"
    print(f"[_get_meetings] API URL: {meetings_url}")
    
    response = requests.get(meetings_url)
    response.raise_for_status()
    meetings_data = response.json()
    print(f"[_get_meetings] Successfully fetched {len(meetings_data)} meeting(s)")
    
    return meetings_data


def _get_session(year, circuit_key, meeting_key):
    """Internal function to fetch F1 session from OpenF1 API."""
    print(f"[_get_session] year: {year}, circuit_key: {circuit_key}, meeting_key: {meeting_key}")
    
    race_session_url = f"{BASE_API_URL}sessions?year={year}&circuit_key={circuit_key}&meeting_key={meeting_key}&session_name=Race&session_type=Race"
    print(f"[_get_session] API URL: {race_session_url}")
    
    response = requests.get(race_session_url)
    response.raise_for_status()
    session_data = response.json()
    print(f"[_get_session] Successfully fetched {len(session_data)} session(s)")
    
    return session_data


def _get_driver(driver_number, session_key):
    """Internal function to fetch F1 drivers from OpenF1 API."""
    print(f"[_get_driver] driver_number: {driver_number}, session_key: {session_key}")
    
    driver_url = f"{BASE_API_URL}drivers?driver_number={driver_number}&session_key={session_key}"
    print(f"[_get_driver] API URL: {driver_url}")
    
    response = requests.get(driver_url)
    response.raise_for_status()
    driver_data = response.json()
    print(f"[_get_driver] Successfully fetched {len(driver_data)} driver(s)")
    
    return driver_data


def _get_flags(session_key):
    """Internal function to fetch F1 flags from OpenF1 API."""
    print(f"[_get_flags] session_key: {session_key}")
    
    flags_url = f"{BASE_API_URL}race_control?session_key={session_key}&flag=YELLOW&flag=RED"
    print(f"[_get_flags] API URL: {flags_url}")
    
    response = requests.get(flags_url)
    response.raise_for_status()
    flags_data = response.json()
    print(f"[_get_flags] Successfully fetched {len(flags_data)} flag(s)")
    
    return flags_data


def _get_pits(session_key, driver_number=None):
    """Internal function to fetch F1 pits from OpenF1 API."""
    print(f"[_get_pits] session_key: {session_key}")
    if driver_number:
        print(f"[_get_pits] driver_number: {driver_number}")
    
    pits_url = f"{BASE_API_URL}pit?session_key={session_key}"
    # Fetch pits for specific driver if driver_number is provided
    if driver_number:
        pits_url += f"&driver_number={driver_number}"
    print(f"[_get_pits] API URL: {pits_url}")
    
    response = requests.get(pits_url)
    response.raise_for_status()
    pits_data = response.json()
    print(f"[_get_pits] Successfully fetched {len(pits_data)} pit(s)")
    
    return pits_data


def _get_overtakes(session_key, driver_number=None):
    """Internal function to fetch F1 overtakes from OpenF1 API."""
    print(f"[_get_overtakes] session_key: {session_key}")
    if driver_number:
        print(f"[_get_overtakes] driver_number: {driver_number}")
    
    overtake_url = f"{BASE_API_URL}overtakes?session_key={session_key}"
    if driver_number:
        # Fetch overtakes made by and overtakes against the driver if driver_number is provided
        overtakes_url = overtake_url + f"&overtaking_driver_number={driver_number}"
        overtaken_url = overtake_url + f"&overtaken_driver_number={driver_number}"
        print(f"[_get_overtakes] API URL: {overtakes_url}")
        print(f"[_get_overtakes] API URL: {overtaken_url}")
    else:
        overtakes_url = overtake_url
        print(f"[_get_overtakes] API URL: {overtakes_url}")
    
    response = requests.get(overtakes_url)
    response.raise_for_status()
    overtakes_data = response.json()
    print(f"[_get_overtakes] Successfully fetched {len(overtakes_data)} overtake(s)")
    
    if driver_number:
        response = requests.get(overtaken_url)
        response.raise_for_status()
        overtaken_data = response.json()
        overtakes_data.extend(overtaken_data)
        print(f"[_get_overtakes] Successfully fetched {len(overtaken_data)} overtaken(s)")
    
    return overtakes_data


def _apply_calibration(events_data, offset_seconds):
    """Apply calibration offset to all event timestamps."""
    print(f"[_apply_calibration] Applying offset of {offset_seconds} seconds")
    
    calibrated_events = {}
    
    # Process overtakes
    if "overtakes" in events_data:
        calibrated_events["overtakes"] = []
        for event in events_data["overtakes"]:
            if "date" in event:
                event_dt = datetime.fromisoformat(event["date"].replace('Z', '+00:00'))
                event_time = event_dt.strftime("%H:%M:%S")
                event_seconds = _time_to_seconds(event_time)
                video_seconds = event_seconds - offset_seconds
                video_time = _seconds_to_time(video_seconds)
                event["video_timestamp"] = video_time
            calibrated_events["overtakes"].append(event)
    
    # Process pits
    if "pits" in events_data:
        calibrated_events["pits"] = []
        for event in events_data["pits"]:
            if "date" in event:
                event_dt = datetime.fromisoformat(event["date"].replace('Z', '+00:00'))
                event_time = event_dt.strftime("%H:%M:%S")
                event_seconds = _time_to_seconds(event_time)
                video_seconds = event_seconds - offset_seconds
                video_time = _seconds_to_time(video_seconds)
                event["video_timestamp"] = video_time
            calibrated_events["pits"].append(event)
    
    # Process flags
    if "flags" in events_data:
        calibrated_events["flags"] = []
        for event in events_data["flags"]:
            if "date" in event:
                event_dt = datetime.fromisoformat(event["date"].replace('Z', '+00:00'))
                event_time = event_dt.strftime("%H:%M:%S")
                event_seconds = _time_to_seconds(event_time)
                video_seconds = event_seconds - offset_seconds
                video_time = _seconds_to_time(video_seconds)
                event["video_timestamp"] = video_time
            calibrated_events["flags"].append(event)
    
    return calibrated_events

def _format_timestamps(timestamps_data):
    """Format the timestamps data into user-friendly strings."""
    formatted_data = []
    seen_drivers = {}

    session_key = timestamps_data.get("session", {}).get("session_key")

    def _driver_acronym(driver_number):
        if driver_number in seen_drivers:
            return seen_drivers[driver_number]
        try:
            drivers = _get_driver(driver_number, session_key)
            acronym = drivers[0]["name_acronym"] if isinstance(drivers, list) and drivers else f"#{driver_number}"
        except Exception:
            acronym = f"#{driver_number}"
        seen_drivers[driver_number] = acronym
        return acronym

    events = timestamps_data.get("events", {})

    # Format overtakes
    for overtake in events.get("overtakes", []):
        time = overtake.get("video_timestamp")
        if not time:
            continue
        overtaking_driver = _driver_acronym(overtake.get("overtaking_driver_number"))
        overtaken_driver = _driver_acronym(overtake.get("overtaken_driver_number"))
        formatted_data.append(f"{time} - {overtaking_driver} overtakes {overtaken_driver}")

    # Format pits
    for pit in events.get("pits", []):
        time = pit.get("video_timestamp")
        if not time:
            continue
        driver = _driver_acronym(pit.get("driver_number"))
        formatted_data.append(f"{time} - {driver} pits")

    # Format flags
    for flag in events.get("flags", []):
        time = flag.get("video_timestamp")
        flag_type = flag.get("flag")
        if not time:
            continue
        formatted_data.append(f"{time} - {flag_type} FLAG")

    formatted_data.sort(key=lambda x: x.split(" - ", 1)[0])
    return formatted_data