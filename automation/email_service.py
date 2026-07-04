import os
import smtplib
import logging
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from typing import Dict, Any

logger = logging.getLogger(__name__)


def _get_smtp_config() -> dict:
    """Validates and returns SMTP configuration from environment variables."""
    smtp_host = os.getenv("SMTP_HOST")
    smtp_port_str = os.getenv("SMTP_PORT", "587")
    smtp_username = os.getenv("SMTP_USERNAME")
    smtp_password = os.getenv("SMTP_PASSWORD")
    email_from = os.getenv("EMAIL_FROM")
    email_to = os.getenv("EMAIL_TO")

    if not all([smtp_host, smtp_username, smtp_password, email_from, email_to]):
        raise ValueError(
            "SMTP configuration environment variables are incomplete. "
            "Please check SMTP_HOST, SMTP_PORT, SMTP_USERNAME, SMTP_PASSWORD, EMAIL_FROM, and EMAIL_TO."
        )

    try:
        smtp_port = int(smtp_port_str)
    except ValueError:
        raise ValueError(f"Invalid SMTP_PORT: {smtp_port_str}. Must be an integer.")

    return {
        "host": smtp_host,
        "port": smtp_port,
        "username": smtp_username,
        "password": smtp_password,
        "from": email_from,
        "to": email_to,
    }


def _send_email(subject: str, html_content: str, cc_address: str | None = None) -> bool:
    """
    Core SMTP send helper. Raises on failure so callers can apply retry logic.
    """
    config = _get_smtp_config()

    msg = MIMEMultipart("alternative")
    msg["Subject"] = subject
    msg["From"] = config["from"]
    msg["To"] = config["to"]

    recipients = [config["to"]]
    if cc_address:
        msg["Cc"] = cc_address
        recipients.append(cc_address)

    msg.attach(MIMEText(html_content, "html"))

    smtp_port = config["port"]
    if smtp_port == 465:
        server = smtplib.SMTP_SSL(config["host"], smtp_port, timeout=10)
    else:
        server = smtplib.SMTP(config["host"], smtp_port, timeout=10)
        server.ehlo()
        server.starttls()
        server.ehlo()

    server.login(config["username"], config["password"])
    server.sendmail(config["from"], recipients, msg.as_string())
    server.quit()
    return True


def send_booking_confirmation_email(booking_details: dict) -> bool:
    """
    Sends an appointment booking confirmation email via SMTP.
    Notifies the clinic admin (EMAIL_TO) and CCs the patient if they provided an email.
    Raises exceptions directly to allow callers (like the orchestrator) to trigger retry logic.
    """
    is_resched = booking_details.get("call_type") == "reschedule"
    title_text = "Dental Appointment Rescheduled" if is_resched else "New Dental Appointment Booking"
    intro_text = "Your appointment has been successfully rescheduled via the AI Receptionist at QuensultingAI Dental Clinic." if is_resched else "A new appointment has been scheduled via the AI Receptionist at QuensultingAI Dental Clinic."
    
    html_content = f"""
    <html>
      <body style="font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif; color: #333; line-height: 1.6; max-width: 600px; margin: 0 auto; padding: 20px; border: 1px solid #e0e0e0; border-radius: 8px;">
        <h2 style="color: #007bff; border-bottom: 2px solid #007bff; padding-bottom: 10px; margin-top: 0;">{title_text}</h2>
        <p>{intro_text}</p>

        <table style="border-collapse: collapse; width: 100%; margin-bottom: 20px;">
          <tr>
            <td style="padding: 10px; border: 1px solid #ddd; font-weight: bold; background-color: #f8f9fa; width: 35%;">Patient Name</td>
            <td style="padding: 10px; border: 1px solid #ddd;">{booking_details.get('full_name')}</td>
          </tr>
          <tr>
            <td style="padding: 10px; border: 1px solid #ddd; font-weight: bold; background-color: #f8f9fa;">Phone Number</td>
            <td style="padding: 10px; border: 1px solid #ddd;">{booking_details.get('phone')}</td>
          </tr>
          <tr>
            <td style="padding: 10px; border: 1px solid #ddd; font-weight: bold; background-color: #f8f9fa;">Email Address</td>
            <td style="padding: 10px; border: 1px solid #ddd;">{booking_details.get('email') or 'Not Provided'}</td>
          </tr>
          <tr>
            <td style="padding: 10px; border: 1px solid #ddd; font-weight: bold; background-color: #f8f9fa;">Preferred Date</td>
            <td style="padding: 10px; border: 1px solid #ddd;">{booking_details.get('preferred_date')}</td>
          </tr>
          <tr>
            <td style="padding: 10px; border: 1px solid #ddd; font-weight: bold; background-color: #f8f9fa;">Preferred Time</td>
            <td style="padding: 10px; border: 1px solid #ddd;">{booking_details.get('preferred_time')}</td>
          </tr>
          <tr>
            <td style="padding: 10px; border: 1px solid #ddd; font-weight: bold; background-color: #f8f9fa;">Requested Service</td>
            <td style="padding: 10px; border: 1px solid #ddd;">{booking_details.get('service')}</td>
          </tr>
          <tr>
            <td style="padding: 10px; border: 1px solid #ddd; font-weight: bold; background-color: #f8f9fa;">Additional Notes</td>
            <td style="padding: 10px; border: 1px solid #ddd;">{booking_details.get('notes') or 'None'}</td>
          </tr>
          <tr>
            <td style="padding: 10px; border: 1px solid #ddd; font-weight: bold; background-color: #f8f9fa;">Call ID</td>
            <td style="padding: 10px; border: 1px solid #ddd;"><code>{booking_details.get('call_id')}</code></td>
          </tr>
        </table>

        {f'<div style="background-color: #e9ecef; padding: 15px; border-radius: 5px; margin-bottom: 20px;"><strong>AI Call Summary:</strong><p style="margin: 5px 0 0 0; font-style: italic;">{booking_details.get("call_summary")}</p></div>' if booking_details.get("call_summary") else ''}

        {f'<p style="margin-bottom: 20px;"><strong>Call Recording:</strong> <a href="{booking_details.get("recording_url")}" style="color: #007bff; text-decoration: none; font-weight: bold;">Listen to audio</a></p>' if booking_details.get("recording_url") else ''}

        <hr style="border: 0; border-top: 1px solid #eee; margin: 20px 0;">
        <p style="font-size: 0.85em; color: #777; margin-bottom: 0;">This is an automated notification from the QuensultingAI Dental Clinic voice receptionist service.</p>
      </body>
    </html>
    """

    subject = f"Appointment Rescheduled: {booking_details.get('full_name')} - {booking_details.get('preferred_date')}" if is_resched else f"Appointment Booked: {booking_details.get('full_name')} - {booking_details.get('preferred_date')}"
    patient_email = booking_details.get('email')

    try:
        _send_email(subject, html_content, cc_address=patient_email)
        logger.info(f"Successfully sent booking confirmation email for Call ID: {booking_details.get('call_id')}")
        return True
    except Exception as e:
        logger.error(f"Failed to send booking confirmation email: {e}", exc_info=True)
        raise e


def send_reschedule_cancel_notification_email(booking_details: dict) -> bool:
    """
    Sends an internal notification email when a caller requests a reschedule or cancellation.
    Only sent to the clinic admin (EMAIL_TO) — patient email not available for these calls.
    Raises exceptions directly to allow callers (like the orchestrator) to trigger retry logic.
    """
    call_type = booking_details.get("call_type", "reschedule/cancel").replace("_", " ").title()
    rc_details = booking_details.get("reschedule_cancel_details") or "No details captured."

    html_content = f"""
    <html>
      <body style="font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif; color: #333; line-height: 1.6; max-width: 600px; margin: 0 auto; padding: 20px; border: 1px solid #e0e0e0; border-radius: 8px;">
        <h2 style="color: #e67e22; border-bottom: 2px solid #e67e22; padding-bottom: 10px; margin-top: 0;">
          ⚠️ Appointment {call_type} Request
        </h2>
        <p>A caller has requested a <strong>{call_type.lower()}</strong> via the AI Receptionist. Please follow up with the patient directly.</p>

        <table style="border-collapse: collapse; width: 100%; margin-bottom: 20px;">
          <tr>
            <td style="padding: 10px; border: 1px solid #ddd; font-weight: bold; background-color: #fff8f0; width: 35%;">Request Type</td>
            <td style="padding: 10px; border: 1px solid #ddd;">{call_type}</td>
          </tr>
          <tr>
            <td style="padding: 10px; border: 1px solid #ddd; font-weight: bold; background-color: #fff8f0;">Patient Details</td>
            <td style="padding: 10px; border: 1px solid #ddd;">{rc_details}</td>
          </tr>
          <tr>
            <td style="padding: 10px; border: 1px solid #ddd; font-weight: bold; background-color: #fff8f0;">Call ID</td>
            <td style="padding: 10px; border: 1px solid #ddd;"><code>{booking_details.get('call_id')}</code></td>
          </tr>
        </table>

        {f'<div style="background-color: #e9ecef; padding: 15px; border-radius: 5px; margin-bottom: 20px;"><strong>AI Call Summary:</strong><p style="margin: 5px 0 0 0; font-style: italic;">{booking_details.get("call_summary")}</p></div>' if booking_details.get("call_summary") else ''}

        {f'<p><strong>Call Recording:</strong> <a href="{booking_details.get("recording_url")}" style="color: #007bff;">Listen to audio</a></p>' if booking_details.get("recording_url") else ''}

        <hr style="border: 0; border-top: 1px solid #eee; margin: 20px 0;">
        <p style="font-size: 0.85em; color: #777; margin-bottom: 0;">This is an automated notification from the QuensultingAI Dental Clinic voice receptionist service. Action required: please contact the patient to confirm their request.</p>
      </body>
    </html>
    """

    subject = f"[Action Required] Appointment {call_type}: {booking_details.get('call_id')}"

    try:
        _send_email(subject, html_content, cc_address=None)
        logger.info(f"Sent reschedule/cancel notification for Call ID: {booking_details.get('call_id')}")
        return True
    except Exception as e:
        logger.error(f"Failed to send reschedule/cancel notification email: {e}", exc_info=True)
        raise e
