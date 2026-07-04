import pytest
from unittest.mock import patch, MagicMock
from backend.models.schemas import BookingDetails
from backend.services.booking_service import process_booking

@pytest.fixture
def sample_booking():
    return BookingDetails(
        call_id="call_mock_123",
        full_name="Jane Doe",
        phone="555-0199",
        email="jane@example.com",
        preferred_date="2026-07-06",
        preferred_time="11:00 AM",
        service="Cleaning",
        notes="None",
        booking_successful=True,
        call_type="new_booking",
        reschedule_cancel_details=None,
        call_summary="Jane booked a cleaning.",
        recording_url="http://recording.audio"
    )

@pytest.fixture
def reschedule_booking():
    return BookingDetails(
        call_id="call_mock_resched_123",
        full_name="Unknown Patient",
        phone="555-0199",
        email=None,
        preferred_date="Not Specified",
        preferred_time="Not Specified",
        service="General Consultation",
        notes=None,
        booking_successful=False,
        call_type="reschedule",
        reschedule_cancel_details="Jane Doe, phone 555-0199, wants to reschedule to 2026-07-10",
        call_summary="Caller wanted to reschedule.",
        recording_url="http://recording.audio"
    )

@patch("backend.services.booking_service.append_booking_to_sheet")
@patch("backend.services.booking_service.send_booking_confirmation_email")
def test_process_booking_success(mock_send_email, mock_append_sheet, sample_booking):
    """
    Test standard successful booking processing where both Sheets and Email succeed on attempt 1.
    """
    mock_append_sheet.return_value = True
    mock_send_email.return_value = True
    
    result = process_booking(sample_booking)
    
    assert result["google_sheets_updated"] is True
    assert result["email_notification_sent"] is True
    assert result["type"] == "new_booking"
    assert mock_append_sheet.call_count == 1
    assert mock_send_email.call_count == 1

@patch("backend.services.booking_service.send_booking_confirmation_email")
def test_process_booking_reschedule_success(mock_send_confirm_email, reschedule_booking):
    """
    Test standard reschedule processing triggers reschedule confirmation email.
    """
    mock_send_confirm_email.return_value = True
    
    result = process_booking(reschedule_booking)
    
    assert result["google_sheets_updated"] is True
    assert result["email_notification_sent"] is True
    assert result["type"] == "reschedule"
    assert mock_send_confirm_email.call_count == 1

@patch("backend.services.booking_service.send_booking_confirmation_email")
def test_process_booking_reschedule_retry_once(mock_send_confirm_email, reschedule_booking):
    """
    Test reschedule email confirmation retry-once behavior on failure.
    """
    mock_send_confirm_email.side_effect = [RuntimeError("SMTP Timeout"), True]
    
    result = process_booking(reschedule_booking)
    
    assert result["google_sheets_updated"] is True
    assert result["email_notification_sent"] is True
    assert mock_send_confirm_email.call_count == 2

@patch("backend.services.booking_service.cancel_booking_in_sheet")
@patch("backend.services.booking_service.send_reschedule_cancel_notification_email")
def test_process_booking_cancel_success(mock_send_rc_email, mock_cancel_sheet):
    """
    Test standard cancellation processing triggers sheets cancel and email alert.
    """
    from backend.models.schemas import BookingDetails
    cancel_booking = BookingDetails(
        call_id="call_mock_cancel_123",
        full_name="Jane Doe",
        phone="555-0199",
        email=None,
        preferred_date="Not Specified",
        preferred_time="Not Specified",
        service="General Consultation",
        notes=None,
        booking_successful=False,
        call_type="cancel",
        reschedule_cancel_details="Jane Doe, phone 555-0199, wants to cancel",
        call_summary="Caller wanted to cancel.",
        recording_url="http://recording.audio"
    )
    mock_cancel_sheet.return_value = True
    mock_send_rc_email.return_value = True
    
    result = process_booking(cancel_booking)
    
    assert result["google_sheets_updated"] is True
    assert result["email_notification_sent"] is True
    assert result["type"] == "cancel"
    mock_cancel_sheet.assert_called_once_with("Jane Doe", "555-0199")
    mock_send_rc_email.assert_called_once()

@patch("backend.services.booking_service.append_booking_to_sheet")
@patch("backend.services.booking_service.send_booking_confirmation_email")
def test_process_booking_retry_once_sheets(mock_send_email, mock_append_sheet, sample_booking):
    """
    Test sheets fail on first attempt but succeeds on second attempt (retry-once).
    """
    mock_append_sheet.side_effect = [RuntimeError("Sheets API error"), True]
    mock_send_email.return_value = True
    
    result = process_booking(sample_booking)
    
    assert result["google_sheets_updated"] is True
    assert result["email_notification_sent"] is True
    assert mock_append_sheet.call_count == 2
    assert mock_send_email.call_count == 1

@patch("backend.services.booking_service.append_booking_to_sheet")
@patch("backend.services.booking_service.send_booking_confirmation_email")
def test_process_booking_retry_once_email(mock_send_email, mock_append_sheet, sample_booking):
    """
    Test email fails on first attempt but succeeds on second attempt (retry-once).
    """
    mock_append_sheet.return_value = True
    mock_send_email.side_effect = [RuntimeError("SMTP connection timeout"), True]
    
    result = process_booking(sample_booking)
    
    assert result["google_sheets_updated"] is True
    assert result["email_notification_sent"] is True
    assert mock_append_sheet.call_count == 1
    assert mock_send_email.call_count == 2

@patch("backend.services.booking_service.append_booking_to_sheet")
@patch("backend.services.booking_service.send_booking_confirmation_email")
def test_process_booking_both_fail_after_retries(mock_send_email, mock_append_sheet, sample_booking):
    """
    Test that if both sheets and email fail all retry attempts, process_booking raises a RuntimeError.
    """
    mock_append_sheet.side_effect = RuntimeError("Sheets API fatal error")
    mock_send_email.side_effect = RuntimeError("SMTP server down")
    
    with pytest.raises(RuntimeError, match="Both Google Sheets insertion and SMTP email sending failed"):
        process_booking(sample_booking)
        
    assert mock_append_sheet.call_count == 2
    assert mock_send_email.call_count == 2
