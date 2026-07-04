from enum import Enum
from pydantic import BaseModel, Field
from typing import Dict, Any, List, Optional


class CallType(str, Enum):
    """Primary intent of the call, extracted by post-call analysis."""
    NEW_BOOKING = "new_booking"
    RESCHEDULE = "reschedule"
    CANCEL = "cancel"
    FAQ_ONLY = "faq_only"
    EMERGENCY = "emergency"


class CallAnalysis(BaseModel):
    custom_analysis_data: Optional[Dict[str, Any]] = None
    call_summary: Optional[str] = None


class CallDetails(BaseModel):
    call_id: str
    agent_id: str
    call_status: str
    from_number: Optional[str] = None
    start_timestamp: Optional[int] = None
    end_timestamp: Optional[int] = None
    transcript: Optional[str] = None
    recording_url: Optional[str] = None
    call_analysis: Optional[CallAnalysis] = None


class WebhookPayload(BaseModel):
    event: str
    call: CallDetails


class BookingDetails(BaseModel):
    call_id: str
    full_name: str = Field(..., description="Full Name of the patient")
    phone: str = Field(..., description="Phone number of the patient")
    email: Optional[str] = Field(None, description="Email of the patient")
    preferred_date: str = Field(..., description="Preferred appointment date")
    preferred_time: str = Field(..., description="Preferred appointment time")
    service: str = Field(..., description="Requested service")
    notes: Optional[str] = Field(None, description="Additional notes or symptoms")
    booking_successful: bool = Field(False, description="Whether the booking was completed")
    call_type: Optional[str] = Field(None, description="Primary call intent: new_booking, reschedule, cancel, faq_only, emergency")
    reschedule_cancel_details: Optional[str] = Field(None, description="Captured details for reschedule/cancel requests")
    call_summary: Optional[str] = None
    recording_url: Optional[str] = None


# ── Live Slot Availability (used by /check-availability endpoint) ──────────────

class SlotAvailabilityRequest(BaseModel):
    """
    Request body sent by Retell's check_slot_availability tool call.
    """
    preferred_date: str = Field(..., description="Requested appointment date (e.g. '2026-07-10')")
    preferred_time: str = Field(..., description="Requested appointment time (e.g. '10:00 AM')")
    service: str = Field(..., description="Requested dental service")
    is_reschedule: Optional[bool] = Field(False, description="Whether this is a reschedule request")
    full_name: Optional[str] = Field(None, description="The name on the existing appointment to reschedule")
    phone: Optional[str] = Field(None, description="The phone number on the existing appointment to reschedule")


class AlternativeSlot(BaseModel):
    date: str
    time: str


class SlotAvailabilityResponse(BaseModel):
    """
    Response returned to Retell's check_slot_availability tool call.
    The voice agent reads `message` aloud and uses `available` / `alternatives`
    to decide its next action.
    """
    available: bool
    message: str
    alternatives: List[AlternativeSlot] = Field(default_factory=list)
