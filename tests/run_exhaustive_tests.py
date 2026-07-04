import json
import urllib.request
import time
import sys

BASE_URL = "http://127.0.0.1:8000"

def send_post(endpoint, data, headers=None):
    if headers is None:
        headers = {}
    url = f"{BASE_URL}{endpoint}"
    req_headers = {"Content-Type": "application/json", **headers}
    req_data = json.dumps(data).encode("utf-8")
    req = urllib.request.Request(url, data=req_data, headers=req_headers, method="POST")
    try:
        with urllib.request.urlopen(req) as response:
            return response.status, json.loads(response.read().decode("utf-8"))
    except urllib.error.HTTPError as e:
        try:
            err_data = json.loads(e.read().decode("utf-8"))
        except Exception:
            err_data = e.reason
        return e.code, err_data

def send_get(endpoint):
    url = f"{BASE_URL}{endpoint}"
    try:
        with urllib.request.urlopen(url) as response:
            return response.status, json.loads(response.read().decode("utf-8"))
    except urllib.error.HTTPError as e:
        return e.code, e.reason

def run_tests():
    print("==================================================")
    print("STARTING EXHAUSTIVE INTEGRATION TEST SUITE")
    print("==================================================")
    
    # 1. Health Check
    print("\n[Scenario 1] Health Check")
    status, res = send_get("/health")
    print(f"-> Status: {status}")
    print(f"-> Response: {res}")
    
    # 2. Check Slot Availability (Free Slot)
    print("\n[Scenario 2] Check Slot Availability (Free Slot)")
    avail_req = {
        "preferred_date": "2026-07-28",
        "preferred_time": "10:00 AM",
        "service": "Dental Cleaning"
    }
    status, res = send_post("/check-availability", avail_req)
    print(f"-> Status: {status}")
    print(f"-> Response: {res}")
    
    # 3. Webhook: Successful Booking
    print("\n[Scenario 3] Webhook: Successful Booking (Appends to Sheets + Confirmation Email)")
    booking_payload = {
        "event": "call_analyzed",
        "call": {
            "call_id": "call_exhaustive_booking_999",
            "agent_id": "agent_test_123",
            "call_status": "analyzed",
            "from_number": "+15550199000",
            "recording_url": "https://example.com/exhaustive_recording.mp3",
            "call_analysis": {
                "call_summary": "Patient John Doe booked a Dental Cleaning for 2026-07-28 at 10:00 AM.",
                "custom_analysis_data": {
                    "Full Name": "John Doe - Exhaustive Test",
                    "Phone": "+15550199000",
                    "Email": "vimalmanoharan.workspace+johndoe@gmail.com",
                    "Preferred Date": "2026-07-28",
                    "Preferred Time": "10:00 AM",
                    "Service": "Dental Cleaning",
                    "Notes": "Please handle with care, testing integrations.",
                    "booking_successful": "True",
                    "call_type": "new_booking"
                }
            }
        }
    }
    status, res = send_post("/webhook/retell", booking_payload, {"x-retell-signature": "dummy_signature"})
    print(f"-> Status: {status}")
    print(f"-> Response: {res}")
    
    # Wait for the async task to finish writing to Google Sheets
    print("Waiting 5 seconds for Google Sheets write to complete...")
    time.sleep(5)
    
    # 4. Check Slot Availability (Now Taken Slot)
    print("\n[Scenario 4] Check Slot Availability (Now Taken Slot)")
    status, res = send_post("/check-availability", avail_req)
    print(f"-> Status: {status}")
    print(f"-> Response: {res}")

    # 5. Webhook: Reschedule Request
    print("\n[Scenario 5] Webhook: Reschedule Request (Admin Notification Email)")
    resched_payload = {
        "event": "call_analyzed",
        "call": {
            "call_id": "call_exhaustive_resched_999",
            "agent_id": "agent_test_123",
            "call_status": "analyzed",
            "from_number": "+15550199000",
            "recording_url": "https://example.com/exhaustive_resched.mp3",
            "call_analysis": {
                "call_summary": "Patient John Doe wants to reschedule to next week.",
                "custom_analysis_data": {
                    "booking_successful": "True",
                    "call_type": "reschedule",
                    "reschedule_cancel_details": "John Doe wants to move their 2026-07-28 10:00 AM appointment to 2026-08-04 10:00 AM."
                }
            }
        }
    }
    status, res = send_post("/webhook/retell", resched_payload, {"x-retell-signature": "dummy_signature"})
    print(f"-> Status: {status}")
    print(f"-> Response: {res}")

    # 6. Webhook: Cancellation Request
    print("\n[Scenario 6] Webhook: Cancellation Request (Admin Notification Email)")
    cancel_payload = {
        "event": "call_analyzed",
        "call": {
            "call_id": "call_exhaustive_cancel_999",
            "agent_id": "agent_test_123",
            "call_status": "analyzed",
            "from_number": "+15550199000",
            "recording_url": "https://example.com/exhaustive_cancel.mp3",
            "call_analysis": {
                "call_summary": "Patient John Doe wants to cancel their appointment.",
                "custom_analysis_data": {
                    "booking_successful": "True",
                    "call_type": "cancel",
                    "reschedule_cancel_details": "John Doe wants to cancel their appointment on 2026-07-28."
                }
            }
        }
    }
    status, res = send_post("/webhook/retell", cancel_payload, {"x-retell-signature": "dummy_signature"})
    print(f"-> Status: {status}")
    print(f"-> Response: {res}")

    # 7. Webhook: FAQ Only Event (Ignored)
    print("\n[Scenario 7] Webhook: FAQ Only Event (Ignored)")
    faq_payload = {
        "event": "call_analyzed",
        "call": {
            "call_id": "call_exhaustive_faq_999",
            "agent_id": "agent_test_123",
            "call_status": "analyzed",
            "from_number": "+15550199000",
            "recording_url": "https://example.com/exhaustive_faq.mp3",
            "call_analysis": {
                "call_summary": "Patient asked about billing, parking details, and clinic hours.",
                "custom_analysis_data": {
                    "booking_successful": "False",
                    "call_type": "faq_only"
                }
            }
        }
    }
    status, res = send_post("/webhook/retell", faq_payload, {"x-retell-signature": "dummy_signature"})
    print(f"-> Status: {status}")
    print(f"-> Response: {res}")

    # 8. Webhook: Non-'call_analyzed' Event (Ignored)
    print("\n[Scenario 8] Webhook: Ignored Webhook Event (e.g. call_started)")
    started_payload = {
        "event": "call_started",
        "call": {
            "call_id": "call_exhaustive_started_999",
            "agent_id": "agent_test_123",
            "call_status": "started"
        }
    }
    status, res = send_post("/webhook/retell", started_payload, {"x-retell-signature": "dummy_signature"})
    print(f"-> Status: {status}")
    print(f"-> Response: {res}")

    print("\nWaiting 10 seconds for background tasks (FastAPI BackgroundTasks) to complete...")
    time.sleep(10)
    print("\n==================================================")
    print("ALL TEST SCENARIOS TRIGGERED AND EXECUTED")
    print("==================================================")

if __name__ == "__main__":
    run_tests()
