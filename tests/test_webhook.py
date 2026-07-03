import pytest
from automation.webhook import parse_webhook_payload, extract_case_insensitive_field

def test_extract_case_insensitive_field():
    data = {
        "Full Name": "Alice Smith",
        "phone_number": "123-456-7890",
        "Preferred-Date": "2026-07-04"
    }
    
    assert extract_case_insensitive_field(data, ["full_name"]) == "Alice Smith"
    assert extract_case_insensitive_field(data, ["phone", "phone_number"]) == "123-456-7890"
    assert extract_case_insensitive_field(data, ["preferred_date"]) == "2026-07-04"
    assert extract_case_insensitive_field(data, ["missing_field"], "DefaultVal") == "DefaultVal"

def test_parse_webhook_payload():
    mock_payload = {
        "event": "call_analyzed",
        "call": {
            "call_id": "call_99999",
            "recording_url": "https://recording.url/99999",
            "from_number": "+1112223333",
            "call_analysis": {
                "call_summary": "Patient booked an appointment for root canal.",
                "custom_analysis_data": {
                    "Full Name": "Bob Jones",
                    "email": "bob@example.com",
                    "Preferred Date": "2026-07-05",
                    "preferred_time": "10:00 AM",
                    "service": "Root Canal",
                    "notes": "Has high anxiety"
                }
            }
        }
    }
    
    booking = parse_webhook_payload(mock_payload)
    
    assert booking.call_id == "call_99999"
    assert booking.full_name == "Bob Jones"
    assert booking.phone == "+1112223333" # Fallback from from_number if phone missing in custom_data
    assert booking.email == "bob@example.com"
    assert booking.preferred_date == "2026-07-05"
    assert booking.preferred_time == "10:00 AM"
    assert booking.service == "Root Canal"
    assert booking.notes == "Has high anxiety"
    assert booking.call_summary == "Patient booked an appointment for root canal."
    assert booking.recording_url == "https://recording.url/99999"
