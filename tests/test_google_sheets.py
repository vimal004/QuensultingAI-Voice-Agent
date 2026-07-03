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
