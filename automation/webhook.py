import logging
from typing import Dict, Any, Optional
from retell.lib.webhook_auth import verify as retell_verify
from backend.models.schemas import BookingDetails

logger = logging.getLogger(__name__)

def verify_webhook_signature(raw_body: str, api_key: Optional[str], signature: Optional[str]) -> bool:
    """
    Verifies that the webhook request is genuinely from Retell AI.
    If api_key is not set (e.g. in local development), it logs a warning and returns True.
    """
    if not api_key:
        logger.warning("RETELL_API_KEY is not set. Webhook signature verification bypassed for local testing.")
        return True
    
    if not signature:
        logger.error("Missing x-retell-signature header.")
        return False
    
    try:
        is_valid = retell_verify(raw_body, api_key, signature)
        if not is_valid:
            logger.error("Invalid webhook signature.")
        return is_valid
    except Exception as e:
        logger.error(f"Error verifying webhook signature: {e}", exc_info=True)
        return False

def extract_case_insensitive_field(data: dict, target_keys: list, default: Any = None) -> Any:
    """
    Utility helper to extract a field case-insensitively, ignoring spaces, underscores, and hyphens.
    """
    # Create a mapping of normalized keys to original values
    normalized_data = {
        str(k).lower().replace(" ", "").replace("_", "").replace("-", ""): v 
        for k, v in data.items()
    }
    
    for target in target_keys:
        norm_target = str(target).lower().replace(" ", "").replace("_", "").replace("-", "")
        if norm_target in normalized_data:
            return normalized_data[norm_target]
            
    return default

def parse_webhook_payload(payload: Dict[str, Any]) -> BookingDetails:
    """
    Parses Retell's webhook payload and extracts booking details.
    Supports flexible, case-insensitive parameter names from custom_analysis_data.
    """
    logger.info("Parsing webhook payload from Retell...")
    
    call_data = payload.get("call", {})
    call_id = call_data.get("call_id", "unknown")
    recording_url = call_data.get("recording_url")
    
    analysis = call_data.get("call_analysis", {})
    call_summary = analysis.get("call_summary")
    custom_data = analysis.get("custom_analysis_data", {}) or {}
    
    # Define mapping variations for each of the booking fields
    full_name = extract_case_insensitive_field(
        custom_data, 
        ["full_name", "fullname", "name", "patient_name", "patientname", "customer_name"], 
        "Unknown Patient"
    )
    
    phone = extract_case_insensitive_field(
        custom_data, 
        ["phone", "phone_number", "phonenumber", "number", "mobile", "contact"], 
        call_data.get("from_number", "Unknown Phone")
    )
    
    email = extract_case_insensitive_field(
        custom_data, 
        ["email", "email_address", "emailaddress", "mail"], 
        None
    )
    
    preferred_date = extract_case_insensitive_field(
        custom_data, 
        ["preferred_date", "preferreddate", "date", "appointment_date", "appointmentdate"], 
        "Not Specified"
    )
    
    preferred_time = extract_case_insensitive_field(
        custom_data, 
        ["preferred_time", "preferredtime", "time", "appointment_time", "appointmenttime"], 
        "Not Specified"
    )
    
    service = extract_case_insensitive_field(
        custom_data, 
        ["service", "treatment", "procedure", "reason", "appointment_type", "appointmenttype"], 
        "General Consultation"
    )
    
    notes = extract_case_insensitive_field(
        custom_data, 
        ["notes", "note", "comments", "comment", "symptoms", "symptom", "additional_info"], 
        None
    )
    
    booking = BookingDetails(
        call_id=call_id,
        full_name=full_name,
        phone=phone,
        email=email,
        preferred_date=preferred_date,
        preferred_time=preferred_time,
        service=service,
        notes=notes,
        call_summary=call_summary,
        recording_url=recording_url
    )
    
    logger.info(f"Successfully extracted booking details for {full_name} ({phone})")
    return booking
