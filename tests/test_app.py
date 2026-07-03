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
