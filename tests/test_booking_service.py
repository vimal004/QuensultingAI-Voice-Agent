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
        call_summary="Jane booked a cleaning.",
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
    assert mock_append_sheet.call_count == 1
    assert mock_send_email.call_count == 1

@patch("backend.services.booking_service.append_booking_to_sheet")
@patch("backend.services.booking_service.send_booking_confirmation_email")
def test_process_booking_retry_once_sheets(mock_send_email, mock_append_sheet, sample_booking):
    """
    Test sheets fail on first attempt but succeeds on second attempt (retry-once).
    """
    # First call raises error, second succeeds
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
    # First call raises error, second succeeds
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
