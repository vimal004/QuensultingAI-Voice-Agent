import os
import json
import logging
from typing import Dict, Any
from dotenv import load_dotenv
from fastapi import FastAPI, Request, Header, HTTPException, BackgroundTasks, status
from fastapi.middleware.cors import CORSMiddleware

from automation.webhook import verify_webhook_signature, parse_webhook_payload
from automation.google_sheets import check_slot_availability
from backend.services.booking_service import process_booking
from backend.models.schemas import SlotAvailabilityRequest, SlotAvailabilityResponse

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s"
)
logger = logging.getLogger(__name__)

# Load environment variables
load_dotenv()

app = FastAPI(
    title="QuensultingAI Dental Clinic Voice Agent Backend",
    description="Production-quality FastAPI backend for integrating RetellAI webhook payloads with Google Sheets and SMTP Email.",
    version="1.0.0"
)

# Set up CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

def run_booking_workflow(payload: Dict[str, Any]):
    """
    Background worker to process the Retell webhook payload.
    Avoids blocking the main thread and prevents webhook timeouts.
    """
    try:
        # Parse the webhook payload into standardized BookingDetails
        booking_details = parse_webhook_payload(payload)
        
        # Guard clause: only process if the booking was successful OR it's a reschedule/cancel request
        is_reschedule_or_cancel = booking_details.call_type in ["reschedule", "cancel"]
        if not booking_details.booking_successful and not is_reschedule_or_cancel:
            logger.info(
                f"Call {booking_details.call_id} (type: {booking_details.call_type}) was completed "
                "without a successful booking or reschedule/cancel request. Skipping integrations."
            )
            return
            
        # Execute Sheets append and Email notifications (includes retry-once logic)
        result = process_booking(booking_details)
        logger.info(f"Booking/Request workflow successfully executed in background: {result}")
    except Exception as e:
        logger.error(f"Error executing booking workflow in background: {e}", exc_info=True)

@app.get("/health", status_code=status.HTTP_200_OK)
def health_check():
    """
    Service health check endpoint.
    """
    return {"status": "ok", "message": "QuensultingAI Voice Agent Backend is running."}

@app.post("/check-availability", response_model=SlotAvailabilityResponse, status_code=status.HTTP_200_OK)
def handle_check_slot_availability(request: SlotAvailabilityRequest):
    """
    Synchronous slot availability check endpoint. Called during the live call
    by Retell's custom tool 'check_slot_availability'.
    
    Checks current bookings in Google Sheets. If the exact slot is booked,
    returns up to 3 alternative times on the same date.
    """
    try:
        result = check_slot_availability(
            preferred_date=request.preferred_date,
            preferred_time=request.preferred_time,
            service=request.service
        )
        return result
    except Exception as e:
        logger.error(f"Error checking slot availability: {e}", exc_info=True)
        # Fallback response so the voice agent doesn't crash during the call
        return {
            "available": False,
            "message": "I'm having a little trouble checking our calendar right now. Let me check with our team shortly.",
            "alternatives": []
        }

@app.post("/webhook/retell", status_code=status.HTTP_200_OK)
async def handle_retell_webhook(
    request: Request,
    background_tasks: BackgroundTasks,
    x_retell_signature: str = Header(None)
):
    """
    Endpoint that receives webhook calls from Retell AI.
    Verifies signature, filters for 'call_analyzed' events, and processes booking details.
    
    Edge Cases Handled:
    1. Empty/Missing x-retell-signature: Returns 401 Unauthorized.
    2. Invalid signature: Returns 401 Unauthorized.
    3. Non-JSON or malformed payload: Returns 400 Bad Request.
    4. Non-'call_analyzed' events (e.g. call_started, call_ended): Logged and acknowledged immediately with 200.
    5. Timeout prevention: Slow integrations (Google Sheets/SMTP) are run in FastAPI BackgroundTasks.
    """
    # 1. Fetch raw request body
    body_bytes = await request.body()
    body_str = body_bytes.decode("utf-8")
    
    # 2. Verify webhook signature
    retell_api_key = os.getenv("RETELL_API_KEY")
    if not verify_webhook_signature(body_str, retell_api_key, x_retell_signature):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Webhook signature verification failed."
        )
        
    # 3. Parse JSON body
    try:
        payload = json.loads(body_str)
    except json.JSONDecodeError as decode_err:
        logger.error(f"Failed to decode webhook JSON: {decode_err}")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Malformed JSON payload."
        )
        
    # 4. Filter for call_analyzed event
    event_type = payload.get("event")
    logger.info(f"Received webhook event '{event_type}' from Retell.")
    
    if event_type != "call_analyzed":
        # Retell sends other events (e.g., call_started, call_ended). 
        # We acknowledge them but perform no actions as custom fields are only available in call_analyzed.
        return {
            "status": "ignored",
            "message": f"Event type '{event_type}' acknowledged but no actions required."
        }
        
    # 5. Delegate sheets & email tasks to BackgroundTasks
    background_tasks.add_task(run_booking_workflow, payload)
    
    return {
        "status": "processing",
        "message": "Webhook received. Processing booking details in the background."
    }
