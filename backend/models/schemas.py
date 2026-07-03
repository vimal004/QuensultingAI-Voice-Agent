from pydantic import BaseModel, Field
from typing import Dict, Any, Optional

class CallAnalysis(BaseModel):
    custom_analysis_data: Optional[Dict[str, Any]] = None
    call_summary: Optional[str] = None

class CallDetails(BaseModel):
    call_id: str
    agent_id: str
    call_status: str
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
    booking_successful: bool = Field(False, description="Whether the appointment booking was successfully completed")
    call_summary: Optional[str] = None
    recording_url: Optional[str] = None
