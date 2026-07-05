import pytest
from unittest.mock import patch, MagicMock
from automation.google_sheets import check_slot_availability

@patch("automation.google_sheets._get_all_rows")
def test_check_slot_availability_free(mock_get_all_rows):
    """
    Test checking a slot that has no overlapping bookings in sheets.
    """
    # Empty sheet (excluding headers which _get_all_rows already does)
    mock_get_all_rows.return_value = []
    
    result = check_slot_availability(
        preferred_date="2026-07-06",
        preferred_time="10:00 AM",
        service="Cleaning"
    )
    
    assert result["available"] is True
    assert "is confirmed" in result["message"]
    assert len(result["alternatives"]) == 0

@patch("automation.google_sheets._get_all_rows")
def test_check_slot_availability_taken_with_alternatives(mock_get_all_rows):
    """
    Test checking a slot that is already booked. Should return up to 3 alternatives on the same day.
    """
    # Mock some existing bookings in sheet:
    # Column indices:
    # 0: Call ID, 1: Created At, 2: Name, 3: Phone, 4: Email, 5: Date, 6: Time, 7: Service
    mock_get_all_rows.return_value = [
        ["call_1", "now", "Alice", "111", "a@a.com", "2026-07-06", "10:00 AM", "Cleaning"],
        ["call_2", "now", "Bob", "222", "b@b.com", "2026-07-06", "11:00 AM", "Whitening"]
    ]
    
    result = check_slot_availability(
        preferred_date="2026-07-06",
        preferred_time="10:00 AM",
        service="Cleaning"
    )
    
    assert result["available"] is False
    assert "already taken" in result["message"]
    # Alternatives should exclude 10:00 AM (exclude_time) and 11:00 AM (already booked)
    # Available times are 9:00 AM, 12:00 PM, 1:00 PM, etc.
    alts = result["alternatives"]
    assert len(alts) == 3
    # Check that alternatives are free slots
    alt_times = [a["time"] for a in alts]
    assert "10:00 AM" not in alt_times
    assert "11:00 AM" not in alt_times
    assert "9:00 AM" in alt_times
    assert "12:00 PM" in alt_times
    assert "1:00 PM" in alt_times


@patch("automation.google_sheets._get_all_rows")
def test_find_booking_row_index(mock_get_all_rows):
    """
    Test finding active booking row indices under various matching cases.
    """
    mock_get_all_rows.return_value = [
        ["call_1", "now", "Alice Smith", "111-2222", "a@a.com", "2026-07-06", "10:00 AM", "Cleaning"],
        ["call_2", "now", "Bob Jones", "333-4444", "b@b.com", "2026-07-06", "11:00 AM", "[CANCELLED] Whitening"]
    ]
    
    from automation.google_sheets import find_booking_row_index
    
    # 1. Direct match by phone & name
    assert find_booking_row_index("Alice Smith", "111-2222") == 0
    # 2. Match by phone only (scoring phone match)
    assert find_booking_row_index("Alice", "1112222") == 0
    # 3. Match fails for cancelled row
    assert find_booking_row_index("Bob Jones", "333-4444") is None
    # 4. Match fails completely
    assert find_booking_row_index("Charlie", "999-9999") is None


@patch("automation.google_sheets.get_sheets_service")
@patch("automation.google_sheets.find_booking_row_index")
def test_reschedule_booking_in_sheet(mock_find_row, mock_get_service):
    """
    Test that rescheduling updates F and G columns of the correct row index.
    """
    from automation.google_sheets import reschedule_booking_in_sheet
    
    mock_find_row.return_value = 0 # Row index 0 in list -> Row 2 in sheet
    mock_service = MagicMock()
    mock_get_service.return_value = mock_service
    
    with patch.dict("os.environ", {"GOOGLE_SHEET_ID": "mock_sheet_id"}):
        success = reschedule_booking_in_sheet(
            full_name="Alice Smith",
            phone="111-2222",
            new_date="2026-07-15",
            new_time="2:00 PM"
        )
        
    assert success is True
    # Row index 0 translates to Sheet Row 2. F2:G2.
    mock_service.spreadsheets().values().update.assert_called_once_with(
        spreadsheetId="mock_sheet_id",
        range="Sheet1!F2:G2",
        valueInputOption="USER_ENTERED",
        body={"values": [["2026-07-15", "2:00 PM"]]}
    )


@patch("automation.google_sheets.get_sheets_service")
@patch("automation.google_sheets.find_booking_row_index")
def test_cancel_booking_in_sheet(mock_find_row, mock_get_service):
    """
    Test that cancellation prepends [CANCELLED] to the H column of the correct row index.
    """
    from automation.google_sheets import cancel_booking_in_sheet
    
    mock_find_row.return_value = 1 # Row index 1 in list -> Row 3 in sheet
    mock_service = MagicMock()
    mock_get_service.return_value = mock_service
    
    # Mock reading the original service
    mock_get_result = {"values": [["call_2", "now", "Bob", "222", "b@b.com", "2026-07-06", "11:00 AM", "Whitening"]]}
    mock_service.spreadsheets().values().get().execute.return_value = mock_get_result
    
    with patch.dict("os.environ", {"GOOGLE_SHEET_ID": "mock_sheet_id"}):
        success = cancel_booking_in_sheet(
            full_name="Bob Jones",
            phone="333-4444"
        )
        
    assert success is True
    # Row index 1 translates to Sheet Row 3. H3.
    mock_service.spreadsheets().values().update.assert_called_once_with(
        spreadsheetId="mock_sheet_id",
        range="Sheet1!H3",
        valueInputOption="USER_ENTERED",
        body={"values": [["[CANCELLED] Whitening"]]}
    )


@patch("automation.google_sheets._get_all_rows")
def test_check_slot_availability_sunday(mock_get_all_rows):
    """
    Test checking a slot on a Sunday. Should be rejected.
    """
    mock_get_all_rows.return_value = []
    
    # 2026-07-05 is a Sunday
    result = check_slot_availability(
        preferred_date="2026-07-05",
        preferred_time="10:00 AM",
        service="Cleaning"
    )
    
    assert result["available"] is False
    assert "clinic is closed on Sundays" in result["message"]


@patch("automation.google_sheets._get_all_rows")
def test_check_slot_availability_outside_operating_hours(mock_get_all_rows):
    """
    Test checking a slot outside clinic operating hours (e.g. 8:00 AM or 7:00 PM). Should be rejected.
    """
    mock_get_all_rows.return_value = []
    
    # Before 9:00 AM
    result_early = check_slot_availability(
        preferred_date="2026-07-06",
        preferred_time="8:00 AM",
        service="Cleaning"
    )
    assert result_early["available"] is False
    assert "outside our clinic hours" in result_early["message"]

    # After 6:00 PM (18:00)
    result_late = check_slot_availability(
        preferred_date="2026-07-06",
        preferred_time="7:00 PM",
        service="Cleaning"
    )
    assert result_late["available"] is False
    assert "outside our clinic hours" in result_late["message"]


@patch("automation.google_sheets.find_booking_row_index")
@patch("automation.google_sheets._get_all_rows")
def test_check_slot_availability_reschedule_not_found(mock_get_all_rows, mock_find_row):
    """
    Test rescheduling when the existing booking is not found in sheets. Should be rejected.
    """
    mock_find_row.return_value = None
    mock_get_all_rows.return_value = []
    
    result = check_slot_availability(
        preferred_date="2026-07-06",
        preferred_time="10:00 AM",
        service="Cleaning",
        is_reschedule=True,
        full_name="No Booking Patient",
        phone="555-9999"
    )
    
    assert result["available"] is False
    assert "couldn't find an existing appointment" in result["message"]


@patch("automation.google_sheets.find_booking_row_index")
@patch("automation.google_sheets._get_all_rows")
def test_check_slot_availability_reschedule_excludes_self(mock_get_all_rows, mock_find_row):
    """
    Test rescheduling when the new slot conflicts with another booking, 
    but does NOT conflict with the patient's own slot being rescheduled.
    """
    # Let's say Alice currently has a booking at 10:00 AM.
    # She wants to reschedule to 10:00 AM.
    # This should be available since she is the one occupying it.
    mock_find_row.return_value = 0 # Index 0 is Alice
    mock_get_all_rows.return_value = [
        ["call_1", "now", "Alice Smith", "111-2222", "a@a.com", "2026-07-06", "10:00 AM", "Cleaning"]
    ]
    
    result = check_slot_availability(
        preferred_date="2026-07-06",
        preferred_time="10:00 AM",
        service="Cleaning",
        is_reschedule=True,
        full_name="Alice Smith",
        phone="111-2222"
    )
    
    assert result["available"] is True
    assert "available for rescheduling" in result["message"]

def test_normalize_date():
    from automation.google_sheets import normalize_date
    from datetime import datetime
    
    current_year = datetime.now().year
    
    assert normalize_date("July 6") == f"{current_year}-07-06"
    assert normalize_date("July 6th") == f"{current_year}-07-06"
    assert normalize_date("6th July") == f"{current_year}-07-06"
    assert normalize_date("6th of July") == f"{current_year}-07-06"
    assert normalize_date("july 6, 2026") == "2026-07-06"
    assert normalize_date("Jul 6") == f"{current_year}-07-06"
    assert normalize_date("6 Jul") == f"{current_year}-07-06"
    assert normalize_date("2026-07-06") == "2026-07-06"
    assert normalize_date("today") == datetime.now().strftime("%Y-%m-%d")

@patch("automation.google_sheets._get_all_rows")
def test_check_slot_availability_duplicate_booking_detected(mock_get_all_rows):
    """
    Test that checking slot availability for a new booking returns duplicate warning
    if the patient already has an active appointment on that same day.
    """
    mock_get_all_rows.return_value = [
        ["call_1", "now", "Alice Smith", "111-222-3333", "alice@example.com", "2026-07-06", "10:00 AM", "Cleaning"]
    ]
    
    result = check_slot_availability(
        preferred_date="2026-07-06",
        preferred_time="2:00 PM",
        service="Whitening",
        is_reschedule=False,
        full_name="Alice Smith",
        phone="111-222-3333"
    )
    
    assert result["available"] is False
    assert result["booking_already_exists"] is True
    assert "already have an appointment booked" in result["message"]
    assert "Cleaning" in result["message"]

@patch("automation.google_sheets._get_all_rows")
def test_check_slot_availability_duplicate_booking_ignored_if_cancelled(mock_get_all_rows):
    """
    Test that duplicate check ignores cancelled appointments.
    """
    mock_get_all_rows.return_value = [
        ["call_1", "now", "Alice Smith", "111-222-3333", "alice@example.com", "2026-07-06", "10:00 AM", "[CANCELLED] Cleaning"]
    ]
    
    result = check_slot_availability(
        preferred_date="2026-07-06",
        preferred_time="2:00 PM",
        service="Whitening",
        is_reschedule=False,
        full_name="Alice Smith",
        phone="111-222-3333"
    )
    
    # Since the 10 AM booking was cancelled, 2 PM Whitening should be available
    assert result["available"] is True
    assert result["booking_already_exists"] is False

