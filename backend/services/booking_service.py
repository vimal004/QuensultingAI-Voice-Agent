import logging
from backend.models.schemas import BookingDetails
from automation.google_sheets import append_booking_to_sheet
from automation.email_service import send_booking_confirmation_email

logger = logging.getLogger(__name__)

def process_booking(booking: BookingDetails) -> dict:
    """
    Orchestrates the booking workflow: Google Sheets append followed by SMTP Email sending.
    Implements a retry-once policy for each backend stage as per guidelines.
    """
    booking_dict = booking.model_dump()
    
    # 1. Google Sheets Append (with retry-once)
    sheet_success = False
    for attempt in range(1, 3):
        try:
            logger.info(f"Google Sheet append: Attempt {attempt} for Call ID {booking.call_id}")
            append_booking_to_sheet(booking_dict)
            sheet_success = True
            logger.info("Google Sheet append succeeded.")
            break
        except Exception as e:
            logger.error(f"Google Sheet append: Attempt {attempt} failed with error: {e}")
            if attempt == 2:
                logger.error("Google Sheet append failed after maximum retries.")

    # 2. Email Confirmation (with retry-once)
    email_success = False
    for attempt in range(1, 3):
        try:
            logger.info(f"SMTP Email notification: Attempt {attempt} for Call ID {booking.call_id}")
            send_booking_confirmation_email(booking_dict)
            email_success = True
            logger.info("SMTP Email notification succeeded.")
            break
        except Exception as e:
            logger.error(f"SMTP Email notification: Attempt {attempt} failed with error: {e}")
            if attempt == 2:
                logger.error("SMTP Email notification failed after maximum retries.")

    # If both integrations fail, raise a runtime error so the webhook endpoint can handle it appropriately.
    if not sheet_success and not email_success:
        raise RuntimeError("Both Google Sheets insertion and SMTP email sending failed after retries.")

    return {
        "call_id": booking.call_id,
        "google_sheets_updated": sheet_success,
        "email_notification_sent": email_success
    }
