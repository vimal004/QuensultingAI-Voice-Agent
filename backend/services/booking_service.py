import logging
from backend.models.schemas import BookingDetails, CallType
from automation.google_sheets import append_booking_to_sheet, cancel_booking_in_sheet, reschedule_booking_in_sheet
from automation.email_service import send_booking_confirmation_email, send_reschedule_cancel_notification_email

logger = logging.getLogger(__name__)

def process_booking(booking: BookingDetails) -> dict:
    """
    Orchestrates the booking/request workflow:
    - If a booking was successful, appends to Google Sheets and sends confirmation email.
    - If it's a reschedule, sends email notification (sheets was updated synchronously during the call).
    - If it's a cancellation request, cancels it in Google Sheets and sends email notification.
    - Otherwise, logs the call type and returns.
    Implements a retry-once policy for each backend stage as per guidelines.
    """
    booking_dict = booking.model_dump()
    
    # ── Handle Reschedule (Processed Asynchronously here) ───────────────────
    if booking.call_type == CallType.RESCHEDULE.value:
        logger.info(f"Processing reschedule request for Call ID: {booking.call_id}")
        
        # 1. Asynchronously update Google Sheets
        sheet_success = False
        for attempt in range(1, 3):
            try:
                logger.info(f"Google Sheet reschedule: Attempt {attempt} for Call ID {booking.call_id}")
                updated = reschedule_booking_in_sheet(
                    full_name=booking.full_name,
                    phone=booking.phone,
                    new_date=booking.preferred_date,
                    new_time=booking.preferred_time
                )
                if updated:
                    sheet_success = True
                    logger.info("Google Sheet reschedule succeeded.")
                else:
                    # Fallback: if row not found, append a new booking so their request is not lost
                    logger.warning("Original booking not found for rescheduling. Appending as new booking fallback.")
                    fallback_details = {
                        "call_id": booking.call_id,
                        "full_name": booking.full_name,
                        "phone": booking.phone,
                        "email": booking.email,
                        "preferred_date": booking.preferred_date,
                        "preferred_time": booking.preferred_time,
                        "service": booking.service or "General Consultation",
                        "notes": f"[Reschedule Request - Original not found] {booking.notes or ''}".strip(),
                        "call_summary": booking.call_summary,
                        "recording_url": booking.recording_url
                    }
                    append_booking_to_sheet(fallback_details)
                    sheet_success = True
                    logger.info("Google Sheet fallback append succeeded.")
                break
            except Exception as e:
                logger.error(f"Google Sheet reschedule: Attempt {attempt} failed with error: {e}")
                if attempt == 2:
                    logger.error("Google Sheet reschedule failed after maximum retries.")
        
        # 2. SMTP Email notification
        email_success = False
        for attempt in range(1, 3):
            try:
                logger.info(f"SMTP Email notification (Reschedule): Attempt {attempt} for Call ID {booking.call_id}")
                send_booking_confirmation_email(booking_dict)
                email_success = True
                logger.info("SMTP Email notification (Reschedule) succeeded.")
                break
            except Exception as e:
                logger.error(f"SMTP Email notification (Reschedule): Attempt {attempt} failed with error: {e}")
                if attempt == 2:
                    logger.error("SMTP Email notification (Reschedule) failed after maximum retries.")
                    raise e
        
        return {
            "call_id": booking.call_id,
            "google_sheets_updated": sheet_success,
            "email_notification_sent": email_success,
            "type": "reschedule"
        }

    # ── Handle Cancel (Processed Asynchronously here) ────────────────────────
    if booking.call_type == CallType.CANCEL.value:
        logger.info(f"Processing cancellation request for Call ID: {booking.call_id}")
        
        # 1. Asynchronously mark cancelled in Google Sheets
        sheet_success = False
        for attempt in range(1, 3):
            try:
                logger.info(f"Google Sheet cancel: Attempt {attempt} for Call ID {booking.call_id}")
                cancel_booking_in_sheet(booking.full_name, booking.phone)
                sheet_success = True
                logger.info("Google Sheet cancel succeeded.")
                break
            except Exception as e:
                logger.error(f"Google Sheet cancel: Attempt {attempt} failed with error: {e}")
                if attempt == 2:
                    logger.error("Google Sheet cancel failed after maximum retries.")
        
        # 2. SMTP notification email to admin
        email_success = False
        for attempt in range(1, 3):
            try:
                logger.info(f"SMTP Email notification (Cancel): Attempt {attempt} for Call ID {booking.call_id}")
                send_reschedule_cancel_notification_email(booking_dict)
                email_success = True
                logger.info("SMTP Email notification (Cancel) succeeded.")
                break
            except Exception as e:
                logger.error(f"SMTP Email notification (Cancel): Attempt {attempt} failed with error: {e}")
                if attempt == 2:
                    logger.error("SMTP Email notification (Cancel) failed after maximum retries.")
                    raise e
                    
        return {
            "call_id": booking.call_id,
            "google_sheets_updated": sheet_success,
            "email_notification_sent": email_success,
            "type": "cancel"
        }

    # Standard booking path (requires booking_successful to be True)
    if not booking.booking_successful:
        logger.info(f"Call {booking.call_id} was not a successful booking or reschedule/cancel. Skipping integrations.")
        return {
            "call_id": booking.call_id,
            "google_sheets_updated": False,
            "email_notification_sent": False,
            "type": booking.call_type or "unknown"
        }

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
        "email_notification_sent": email_success,
        "type": "new_booking"
    }
