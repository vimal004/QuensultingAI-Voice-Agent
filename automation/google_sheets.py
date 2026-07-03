import os
import json
import logging
from datetime import datetime
from typing import Any, Optional
from google.oauth2.service_account import Credentials
from googleapiclient.discovery import build

logger = logging.getLogger(__name__)

SCOPES = ['https://www.googleapis.com/auth/spreadsheets']

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
