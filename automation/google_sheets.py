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


# Global cache for the Google Sheets API service client to avoid discovery overhead
_sheets_service_cache = None


def get_sheets_service() -> Any:
    """
    Authenticates and returns the Google Sheets API v4 service.
    First tries loading service account credentials from GOOGLE_CREDS_JSON env var (raw JSON),
    then falls back to the file specified in GOOGLE_APPLICATION_CREDENTIALS.
    """
    global _sheets_service_cache
    if _sheets_service_cache is not None:
        return _sheets_service_cache

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

    _sheets_service_cache = build('sheets', 'v4', credentials=creds)
    return _sheets_service_cache


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
    Handles relative terms like 'today' and 'tomorrow'.
    Supports dates with or without years, ordinal suffixes, and prepended/appended 'of'.
    """
    import re
    from datetime import timedelta
    d = date_str.strip().lower()
    
    # Collapse multiple spaces
    d = re.sub(r"\s+", " ", d)
    
    if d == "today":
        return datetime.now().strftime("%Y-%m-%d")
    elif d == "tomorrow":
        return (datetime.now() + timedelta(days=1)).strftime("%Y-%m-%d")
        
    # Pre-process cleaning:
    # 1. Strip 'of' (e.g., '6th of July' -> '6th July')
    d = re.sub(r"\bof\b", "", d)
    d = re.sub(r"\s+", " ", d).strip()
    
    # 2. Strip ordinal suffixes from numbers (e.g., '6th' -> '6', '1st' -> '1')
    d = re.sub(r"(\d+)(st|nd|rd|th)\b", r"\1", d)
    d = d.strip()
    
    # Try parsing formats with year first
    formats_with_year = (
        "%Y-%m-%d",
        "%m/%d/%Y",
        "%d/%m/%Y",
        "%Y/%m/%d",
        "%B %d, %Y",
        "%b %d, %Y",
        "%B %d %Y",
        "%b %d %Y",
        "%d %B %Y",
        "%d %b %Y",
        "%B %d, %y",
        "%b %d, %y",
        "%B %d %y",
        "%b %d %y",
        "%d %B %y",
        "%d %b %y"
    )
    
    for fmt in formats_with_year:
        try:
            return datetime.strptime(d, fmt).strftime("%Y-%m-%d")
        except ValueError:
            continue
            
    # If parsing with year failed, try appending current year to handle month+day only
    current_year = datetime.now().year
    d_with_year = f"{d} {current_year}"
    
    formats_no_year = (
        "%B %d %Y",
        "%b %d %Y",
        "%d %B %Y",
        "%d %b %Y"
    )
    
    for fmt in formats_no_year:
        try:
            return datetime.strptime(d_with_year, fmt).strftime("%Y-%m-%d")
        except ValueError:
            continue
            
    return date_str.strip()  # Fallback

def normalize_phone(phone_str: str) -> str:
    """
    Strips non-digit characters from the phone number for consistent comparison.
    """
    if not phone_str:
        return ""
    return "".join(c for c in phone_str if c.isdigit())


def find_booking_row_index(full_name: str, phone: str) -> Optional[int]:
    """
    Locates the 0-based row index (excluding header) of a patient's active booking.
    It matches by normalized phone number or by exact/close name match.
    Skips rows marked as [CANCELLED].
    """
    try:
        rows = _get_all_rows()
    except Exception as e:
        logger.error(f"Error fetching rows for index lookup: {e}")
        return None

    target_phone = normalize_phone(phone)
    target_name = full_name.lower().strip() if full_name else ""
    target_name_parts = set(target_name.split())

    best_match_idx = None
    best_match_score = 0.0  # 3.0 = phone & name match, 2.0 = phone match, 1.5 = name exact match, 1.0 = name significant match

    for idx, row in enumerate(rows):
        if len(row) <= COL_PHONE:
            continue
            
        # Ignore cancelled bookings
        row_service = row[COL_SERVICE] if len(row) > COL_SERVICE else ""
        if "[CANCELLED]" in row_service:
            continue

        row_phone = normalize_phone(row[COL_PHONE]) if len(row) > COL_PHONE else ""
        row_name = row[COL_FULL_NAME].lower().strip() if len(row) > COL_FULL_NAME else ""
        row_name_parts = set(row_name.split())

        phone_matches = bool(target_phone and row_phone and (target_phone in row_phone or row_phone in target_phone))
        
        name_exact_match = bool(target_name and row_name and target_name == row_name)
        name_significant_match = name_exact_match or (len(target_name_parts & row_name_parts) >= 2)

        score = 0.0
        if phone_matches and name_significant_match:
            score = 3.0
        elif phone_matches:
            score = 2.0
        elif name_exact_match:
            score = 1.5
        elif name_significant_match:
            score = 1.0

        if score > best_match_score:
            best_match_score = score
            best_match_idx = idx

    if best_match_score >= 1.5:
        return best_match_idx
    return None


def reschedule_booking_in_sheet(
    full_name: str,
    phone: str,
    new_date: str,
    new_time: str
) -> bool:
    """
    Finds the active booking row for full_name/phone and updates preferred date/time.
    Returns True if row was updated, False if target row was not found.
    """
    row_idx = find_booking_row_index(full_name, phone)
    if row_idx is None:
        logger.warning(f"Could not find existing booking to reschedule for {full_name} / {phone}.")
        return False

    spreadsheet_id = os.getenv("GOOGLE_SHEET_ID")
    if not spreadsheet_id:
        raise ValueError("GOOGLE_SHEET_ID environment variable is missing.")

    # Sheets is 1-indexed, and rows list skips header (row 1), so row number is row_idx + 2
    row_num = row_idx + 2
    service = get_sheets_service()
    
    # We update Preferred Date (Column F / Index 5) and Preferred Time (Column G / Index 6)
    # Range is F{row_num}:G{row_num}
    range_name = f"Sheet1!F{row_num}:G{row_num}"
    body = {
        "values": [[new_date, new_time]]
    }
    
    service.spreadsheets().values().update(
        spreadsheetId=spreadsheet_id,
        range=range_name,
        valueInputOption="USER_ENTERED",
        body=body
    ).execute()
    
    logger.info(f"Rescheduled row {row_num} to date={new_date}, time={new_time} for {full_name}.")
    return True


def cancel_booking_in_sheet(
    full_name: str,
    phone: str
) -> bool:
    """
    Finds the active booking row for full_name/phone and prepends '[CANCELLED]' to its service.
    Returns True if row was updated, False if not found.
    """
    row_idx = find_booking_row_index(full_name, phone)
    if row_idx is None:
        logger.warning(f"Could not find existing booking to cancel for {full_name} / {phone}.")
        return False

    spreadsheet_id = os.getenv("GOOGLE_SHEET_ID")
    if not spreadsheet_id:
        raise ValueError("GOOGLE_SHEET_ID environment variable is missing.")

    row_num = row_idx + 2
    service = get_sheets_service()
    
    # Get current row to read original service
    result = service.spreadsheets().values().get(
        spreadsheetId=spreadsheet_id,
        range=f"Sheet1!A{row_num}:K{row_num}"
    ).execute()
    
    row_values = result.get("values", [])[0]
    original_service = row_values[COL_SERVICE] if len(row_values) > COL_SERVICE else "General Consultation"
    
    # Update service column (Column H / Index 7)
    range_name = f"Sheet1!H{row_num}"
    body = {
        "values": [[f"[CANCELLED] {original_service}"]]
    }
    
    service.spreadsheets().values().update(
        spreadsheetId=spreadsheet_id,
        range=range_name,
        valueInputOption="USER_ENTERED",
        body=body
    ).execute()
    
    logger.info(f"Cancelled row {row_num} (original service: {original_service}) for {full_name}.")
    return True


def check_slot_availability(
    preferred_date: str,
    preferred_time: str,
    service: str,
    is_reschedule: bool = False,
    full_name: Optional[str] = None,
    phone: Optional[str] = None,
) -> dict:
    """
    Checks Google Sheets for existing bookings at the requested date/time/service combination.
    Enforces clinic operating hours/days and verifies existing appointments for reschedules.

    Logic:
    - Normalises date and time strings for comparison (case-insensitive, strip whitespace).
    - Rejects Sunday appointments.
    - Rejects appointments outside clinic hours (9:00 AM – 6:00 PM).
    - If is_reschedule is True, verifies that the existing booking exists. Excludes this row
      from the conflict check so the patient does not conflict with their own slot.
    - A slot is considered TAKEN if any existing row has the same preferred_date AND preferred_time.
    - If the exact slot is taken, returns up to 3 alternative slots on the same date.
    """
    logger.info(f"Checking slot availability for {preferred_date} at {preferred_time} ({service}), is_reschedule={is_reschedule}")

    import re
    norm_date = normalize_date(preferred_date)
    norm_time = normalize_time(preferred_time)

    # 1. Enforce operating days (Monday - Saturday)
    try:
        dt = datetime.strptime(norm_date, "%Y-%m-%d")
        if dt.weekday() == 6:  # 6 is Sunday
            return {
                "available": False,
                "message": "I'm sorry, our clinic is closed on Sundays. Please select a day from Monday to Saturday.",
                "alternatives": []
            }
    except Exception:
        pass

    # 2. Enforce operating hours (9:00 AM - 6:00 PM)
    if norm_time < "09:00" or norm_time > "18:00":
        return {
            "available": False,
            "message": "I'm sorry, that time is outside our clinic hours of 9:00 AM to 6:00 PM. Please select a time within those hours.",
            "alternatives": []
        }

    # Validate that normalized date matches YYYY-MM-DD pattern to avoid database corruption with relative dates
    if not re.match(r"^\d{4}-\d{2}-\d{2}$", norm_date):
        logger.warning(f"Unresolvable date format received: {preferred_date}")
        return {
            "available": False,
            "message": "I'm sorry, I couldn't record that date. Could you please specify a calendar date, like next Tuesday or a specific date?",
            "alternatives": []
        }

    # 3. For reschedule requests, verify the patient has an active existing appointment
    exclude_row_idx = None
    if is_reschedule and full_name and phone:
        exclude_row_idx = find_booking_row_index(full_name, phone)
        if exclude_row_idx is None:
            clean_phone = phone[-4:] if phone and len(phone) >= 4 else phone
            return {
                "available": False,
                "message": f"I'm sorry, I couldn't find an existing appointment for {full_name} with phone number ending in {clean_phone}. Could you verify your details, or would you like to book a new appointment instead?",
                "alternatives": []
            }

    try:
        rows = _get_all_rows()
    except Exception as e:
        logger.error(f"Could not fetch rows from Google Sheets: {e}", exc_info=True)
        raise

    # Collect all booked date+time pairs
    booked_slots: set[tuple[str, str]] = set()
    for idx, row in enumerate(rows):
        # Exclude the reschedule target's existing booking from causing a conflict with itself
        if exclude_row_idx is not None and idx == exclude_row_idx:
            continue

        if len(row) > COL_TIME:
            row_service = row[COL_SERVICE] if len(row) > COL_SERVICE else ""
            if "[CANCELLED]" in row_service:
                continue
            row_date = normalize_date(row[COL_DATE]) if row[COL_DATE] else ""
            row_time = normalize_time(row[COL_TIME]) if row[COL_TIME] else ""
            booked_slots.add((row_date, row_time))

    # Check exact slot
    if (norm_date, norm_time) not in booked_slots:
        logger.info(f"Slot is AVAILABLE: {preferred_date} at {preferred_time}")
        success_msg = f"That slot is available! Your appointment for {service} on {preferred_date} at {preferred_time} is confirmed."
        if is_reschedule:
            success_msg = f"Great news! The slot on {preferred_date} at {preferred_time} is available for rescheduling. Shall I go ahead and confirm this change for you?"
        return {
            "available": True,
            "message": success_msg,
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

