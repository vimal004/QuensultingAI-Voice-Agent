import os
import smtplib
import logging
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from typing import Dict, Any

logger = logging.getLogger(__name__)

def send_booking_confirmation_email(booking_details: dict) -> bool:
    """
    Sends an appointment booking confirmation email via SMTP.
    Notifies the clinic admin (EMAIL_TO) and CCs the patient if they provided an email.
    Raises exceptions directly to allow callers (like the orchestrator) to trigger retry logic.
    """
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

    # Formulate a clean HTML email template
    html_content = f"""
    <html>
      <body style="font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif; color: #333; line-height: 1.6; max-width: 600px; margin: 0 auto; padding: 20px; border: 1px solid #e0e0e0; border-radius: 8px;">
        <h2 style="color: #007bff; border-bottom: 2px solid #007bff; padding-bottom: 10px; margin-top: 0;">New Dental Appointment Booking</h2>
        <p>A new appointment has been scheduled via the AI Receptionist at QuensultingAI Dental Clinic.</p>
        
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
    
    msg = MIMEMultipart("alternative")
    subject = f"Appointment Booked: {booking_details.get('full_name')} - {booking_details.get('preferred_date')}"
    msg["Subject"] = subject
    msg["From"] = email_from
    msg["To"] = email_to
    
    recipients = [email_to]
    patient_email = booking_details.get('email')
    if patient_email:
        msg["Cc"] = patient_email
        recipients.append(patient_email)
        
    msg.attach(MIMEText(html_content, "html"))
    
    try:
        if smtp_port == 465:
            server = smtplib.SMTP_SSL(smtp_host, smtp_port, timeout=10)
        else:
            server = smtplib.SMTP(smtp_host, smtp_port, timeout=10)
            server.ehlo()
            server.starttls()
            server.ehlo()
            
        server.login(smtp_username, smtp_password)
        server.sendmail(email_from, recipients, msg.as_string())
        server.quit()
        
        logger.info(f"Successfully sent appointment confirmation email for Call ID: {booking_details.get('call_id')}")
        return True
    except Exception as e:
        logger.error(f"Failed to send appointment confirmation email: {e}", exc_info=True)
        raise e
