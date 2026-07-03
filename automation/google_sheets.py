import os
import logging
from datetime import datetime
from typing import Any, List, Optional
from google.oauth2.service_account import Credentials
from googleapiclient.discovery import build
import json

logger = logging.getLogger(__name__)

SCOPES = ['https://www.googleapis.com/auth/spreadsheets']

# Column indices in the sheet (0-based after header row)
# Headers: Call ID | Booking Created At | Full Name | Phone | Email | Preferred Date | Preferred Time | Service | Notes | Call Summary | Recording URL
COL_CALL_ID = 0
COL_FULL_NAME = 2
COL_PHONE = 3
COL_EMAIL = 4
COL_DATE = 5
COL_TIME = 6
COL_SERVICE = 7


def get_sheets_service() -> Any:
    """
    Authenticates and returns the Google Sheets API v4 service.
    First tries loading service account credentials from GOOGLE_CREDS_JSON env var (raw JSON),
    then falls back to the file specified in GOOGLE_APPLICATION_CREDENTIALS.
    """
    creds = None

    # Method A: Try raw JSON string from environment variable (ideal for Render/Cloud)
    raw_json = os.getenv("GOOGLE_CREDS_JSON")
    if raw_json:
        try:
            creds_info = json.loads(raw_json)
            creds = Credentials.from_service_account_info(creds_info, scopes=SCOPES)
            logger.info("Authenticated with Google Sheets API using GOOGLE_CREDS_JSON environment variable.")
        except Exception as e:
            logger.error(f"Failed to load credentials from GOOGLE_CREDS_JSON: {e}")

    # Method B: Fallback to credential JSON file path
    if not creds:
        creds_file = os.getenv("GOOGLE_APPLICATION_CREDENTIALS", "credentials.json")
        if os.path.exists(creds_file):
            try:
                creds = Credentials.from_service_account_file(creds_file, scopes=SCOPES)
                logger.info(f"Authenticated with Google Sheets API using credentials file: {creds_file}")
            except Exception as e:
                logger.error(f"Failed to load credentials from file {creds_file}: {e}")

    if not creds:
        raise ValueError(
            "Google Sheets credentials not found. Please configure GOOGLE_APPLICATION_CREDENTIALS "
            "pointing to your credentials file, or GOOGLE_CREDS_JSON with raw credentials JSON."
        )

    return build('sheets', 'v4', credentials=creds)


def _get_all_rows() -> List[List[str]]:
    """
    Fetches all rows from the sheet (excluding the header).
    Returns a list of rows, each row being a list of string cell values.
    """
    spreadsheet_id = os.getenv("GOOGLE_SHEET_ID")
    if not spreadsheet_id:
        raise ValueError("GOOGLE_SHEET_ID environment variable is missing.")

    service = get_sheets_service()
    result = service.spreadsheets().values().get(
        spreadsheetId=spreadsheet_id,
        range="Sheet1!A1:K"
    ).execute()

    rows = result.get("values", [])
    # Skip header row if present
    if rows and rows[0][0] == "Call ID":
        return rows[1:]
    return rows


def append_booking_to_sheet(booking_details: dict) -> bool:
    """
    Appends the booking details into Google Sheets as a new row.
    Raises exceptions directly to allow callers (like the orchestrator) to trigger retry logic.
    """
    spreadsheet_id = os.getenv("GOOGLE_SHEET_ID")
    if not spreadsheet_id:
        raise ValueError("GOOGLE_SHEET_ID environment variable is missing.")

    try:
        service = get_sheets_service()
        sheet_range = "Sheet1!A1"
        now_str = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

        # Check if the sheet is empty to initialize headers
        try:
            sheet_metadata = service.spreadsheets().values().get(
                spreadsheetId=spreadsheet_id,
                range="Sheet1!A1:K1"
            ).execute()
            rows = sheet_metadata.get('values', [])
            if not rows:
                headers = [
                    ["Call ID", "Booking Created At", "Full Name", "Phone", "Email",
                     "Preferred Date", "Preferred Time", "Service", "Notes", "Call Summary", "Recording URL"]
                ]
                service.spreadsheets().values().update(
                    spreadsheetId=spreadsheet_id,
                    range="Sheet1!A1",
                    valueInputOption="USER_ENTERED",
                    body={"values": headers}
                ).execute()
                logger.info("Google Sheet was empty. Automatically initialized headers.")
        except Exception as header_err:
            logger.warning(f"Could not verify/initialize Google Sheet headers: {header_err}")

        # Format the row to append
        row_data = [
            booking_details.get("call_id"),
            now_str,
            booking_details.get("full_name"),
            booking_details.get("phone"),
            booking_details.get("email") or "",
            booking_details.get("preferred_date"),
            booking_details.get("preferred_time"),
            booking_details.get("service"),
            booking_details.get("notes") or "",
            booking_details.get("call_summary") or "",
            booking_details.get("recording_url") or ""
        ]

        body = {"values": [row_data]}

        service.spreadsheets().values().append(
            spreadsheetId=spreadsheet_id,
            range=sheet_range,
            valueInputOption="USER_ENTERED",
            insertDataOption="INSERT_ROWS",
            body=body
        ).execute()

        logger.info(f"Successfully appended row to Google Sheet for call ID: {booking_details.get('call_id')}")
        return True

    except Exception as e:
        logger.error(f"Failed to append row to Google Sheet: {e}", exc_info=True)
        raise e


def normalize_time(time_str: str) -> str:
    """
    Normalizes time strings to HH:MM format (24-hour) for reliable comparison.
    Handles formats like: "11:00 AM", "11:00 am", "11:00", "11:00:00", "1:00 PM", "13:00".
    """
    t = time_str.strip().lower()
    is_pm = "pm" in t
    is_am = "am" in t
    
    t_clean = t.replace("am", "").replace("pm", "").strip()
    parts = t_clean.split(":")
    if not parts or not parts[0]:
        return time_str
        
    try:
        hours = int(parts[0])
        minutes = int(parts[1]) if len(parts) > 1 else 0
        
        if is_pm and hours < 12:
            hours += 12
        elif is_am and hours == 12:
            hours = 0
            
        return f"{hours:02d}:{minutes:02d}"
    except Exception:
        return time_str


def normalize_date(date_str: str) -> str:
    """
    Normalizes date strings to YYYY-MM-DD format.
    """
    d = date_str.strip()
    for fmt in ("%Y-%m-%d", "%m/%d/%Y", "%d/%m/%Y", "%Y/%m/%d"):
        try:
            return datetime.strptime(d, fmt).strftime("%Y-%m-%d")
        except ValueError:
            continue
    return d.lower()


def check_slot_availability(
    preferred_date: str,
    preferred_time: str,
    service: str,
) -> dict:
    """
    Checks Google Sheets for existing bookings at the requested date/time/service combination.

    Logic:
    - Normalises date and time strings for comparison (case-insensitive, strip whitespace).
    - A slot is considered TAKEN if any existing row has the same preferred_date AND preferred_time.
      (We don't enforce per-service limits; the clinic controls capacity via the front desk.)
    - If the exact slot is taken, returns up to 3 alternative slots on the same date at
      different hours within clinic hours (9 AM – 6 PM, on the hour), or the next available
      business day if the same-day alternatives are exhausted.

    Returns a dict matching SlotAvailabilityResponse schema.
    """
    logger.info(f"Checking slot availability for {preferred_date} at {preferred_time} ({service})")

    try:
        rows = _get_all_rows()
    except Exception as e:
        logger.error(f"Could not fetch rows from Google Sheets: {e}", exc_info=True)
        raise

    # Normalise the requested slot for comparison
    norm_date = normalize_date(preferred_date)
    norm_time = normalize_time(preferred_time)

    # Collect all booked date+time pairs
    booked_slots: set[tuple[str, str]] = set()
    for row in rows:
        if len(row) > COL_TIME:
            row_date = normalize_date(row[COL_DATE]) if row[COL_DATE] else ""
            row_time = normalize_time(row[COL_TIME]) if row[COL_TIME] else ""
            booked_slots.add((row_date, row_time))

    # Check exact slot
    if (norm_date, norm_time) not in booked_slots:
        logger.info(f"Slot is AVAILABLE: {preferred_date} at {preferred_time}")
        return {
            "available": True,
            "message": f"That slot is available! Your appointment for {service} on {preferred_date} at {preferred_time} is confirmed.",
            "alternatives": []
        }

    # Slot is taken — build alternatives on the same date
    logger.info(f"Slot is TAKEN: {preferred_date} at {preferred_time}. Finding alternatives.")
    alternatives = _find_alternative_slots(norm_date, booked_slots, exclude_time=norm_time)

    if alternatives:
        alt_text = ", ".join(f"{a['time']}" for a in alternatives[:3])
        return {
            "available": False,
            "message": (
                f"I'm sorry, {preferred_time} on {preferred_date} is already taken. "
                f"I do have availability at {alt_text} on the same day. Would any of those work for you?"
                f" Please select one or suggest another time."
            ),
            "alternatives": alternatives[:3]
        }

    return {
        "available": False,
        "message": (
            f"I'm sorry, we don't have any open slots on {preferred_date}. "
            "Would you like to try a different date, or would you prefer our front desk to call you back with options?"
        ),
        "alternatives": []
    }


def _find_alternative_slots(
    norm_date: str,
    booked_slots: set,
    exclude_time: str,
    max_alternatives: int = 3
) -> List[dict]:
    """
    Returns up to `max_alternatives` free on-the-hour time slots on `norm_date`
    within clinic hours (9 AM – 6 PM), excluding the already-requested time.
    """
    # All candidate hours within clinic hours
    candidate_hours = [
        "9:00 am", "10:00 am", "11:00 am", "12:00 pm",
        "1:00 pm", "2:00 pm", "3:00 pm", "4:00 pm", "5:00 pm"
    ]

    alternatives = []
    for hour in candidate_hours:
        norm_hour = normalize_time(hour)
        if norm_hour == exclude_time:
            continue
        if (norm_date, norm_hour) not in booked_slots:
            # Format for display: "9:00 AM"
            alternatives.append({
                "date": norm_date,
                "time": hour.upper()
            })
        if len(alternatives) >= max_alternatives:
            break

    return alternatives

