import pytest
from fastapi.testclient import TestClient
from unittest.mock import patch
from backend.app import app

client = TestClient(app)

def test_health_check():
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json()["status"] == "ok"

@patch("backend.app.verify_webhook_signature")
def test_handle_webhook_ignored_event(mock_verify):
    mock_verify.return_value = True
    
    response = client.post(
        "/webhook/retell",
        headers={"x-retell-signature": "dummy_sig"},
        json={"event": "call_started", "call": {"call_id": "call_123", "agent_id": "agent_123", "call_status": "started"}}
    )
    
    assert response.status_code == 200
    assert response.json()["status"] == "ignored"
    assert "acknowledged but no actions required" in response.json()["message"]

@patch("backend.app.verify_webhook_signature")
@patch("backend.app.run_booking_workflow")
def test_handle_webhook_analyzed_event(mock_run_workflow, mock_verify):
    mock_verify.return_value = True
    
    response = client.post(
        "/webhook/retell",
        headers={"x-retell-signature": "dummy_sig"},
        json={"event": "call_analyzed", "call": {"call_id": "call_123", "agent_id": "agent_123", "call_status": "analyzed"}}
    )
    
    assert response.status_code == 200
    assert response.json()["status"] == "processing"
    assert "Webhook received. Processing booking details" in response.json()["message"]
    # Ensure the background task was triggered
    mock_run_workflow.assert_called_once()

@patch("backend.app.process_booking")
def test_run_booking_workflow_successful(mock_process_booking):
    from backend.app import run_booking_workflow
    
    mock_payload = {
        "event": "call_analyzed",
        "call": {
            "call_id": "call_test_success",
            "from_number": "+1112223333",
            "call_analysis": {
                "custom_analysis_data": {
                    "Full Name": "Jane Success",
                    "Preferred Date": "2026-07-05",
                    "preferred_time": "10:00 AM",
                    "service": "Root Canal",
                    "booking_successful": "True"
                }
            }
        }
    }
    
    run_booking_workflow(mock_payload)
    mock_process_booking.assert_called_once()

@patch("backend.app.process_booking")
def test_run_booking_workflow_reschedule(mock_process_booking):
    from backend.app import run_booking_workflow
    
    mock_payload = {
        "event": "call_analyzed",
        "call": {
            "call_id": "call_test_resched",
            "from_number": "+1112223333",
            "call_analysis": {
                "custom_analysis_data": {
                    "booking_successful": "False",
                    "call_type": "reschedule",
                    "reschedule_cancel_details": "Jane Smith, 555-1212"
                }
            }
        }
    }
    
    run_booking_workflow(mock_payload)
    mock_process_booking.assert_called_once()

@patch("backend.app.process_booking")
def test_run_booking_workflow_unsuccessful(mock_process_booking):
    from backend.app import run_booking_workflow
    
    mock_payload = {
        "event": "call_analyzed",
        "call": {
            "call_id": "call_test_fail",
            "from_number": "+1112223333",
            "call_analysis": {
                "custom_analysis_data": {
                    "Full Name": "Jane Fail",
                    "booking_successful": "False",
                    "call_type": "faq_only"
                }
            }
        }
    }
    
    run_booking_workflow(mock_payload)
    mock_process_booking.assert_not_called()

@patch("backend.app.check_slot_availability")
def test_check_availability_endpoint(mock_check_availability):
    mock_check_availability.return_value = {
        "available": True,
        "message": "Available slot",
        "alternatives": []
    }
    
    response = client.post(
        "/check-availability",
        json={
            "preferred_date": "2026-07-06",
            "preferred_time": "11:00 AM",
            "service": "Cleaning"
        }
    )
    
    assert response.status_code == 200
    assert response.json()["available"] is True
    assert response.json()["message"] == "Available slot"
    mock_check_availability.assert_called_once_with(
        preferred_date="2026-07-06",
        preferred_time="11:00 AM",
        service="Cleaning"
    )
