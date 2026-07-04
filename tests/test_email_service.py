import os
import pytest
from unittest.mock import patch, MagicMock
from automation.email_service import _send_email, _send_via_resend, _send_via_brevo

@patch("httpx.post")
def test_send_via_resend(mock_post):
    # Mock successful HTTP post response
    mock_response = MagicMock()
    mock_response.status_code = 200
    mock_post.return_value = mock_response
    
    with patch.dict(os.environ, {"RESEND_API_KEY": "re_123456", "EMAIL_FROM": "sender@domain.com"}):
        result = _send_via_resend("Test Subject", "<p>Hello</p>", "recipient@domain.com", "cc@domain.com")
        assert result is True
        
        # Verify post parameters
        mock_post.assert_called_once_with(
            "https://api.resend.com/emails",
            json={
                "from": "sender@domain.com",
                "to": ["recipient@domain.com"],
                "subject": "Test Subject",
                "html": "<p>Hello</p>",
                "cc": ["cc@domain.com"]
            },
            headers={
                "Authorization": "Bearer re_123456",
                "Content-Type": "application/json"
            },
            timeout=10.0
        )

@patch("httpx.post")
def test_send_via_brevo(mock_post):
    # Mock successful HTTP post response
    mock_response = MagicMock()
    mock_response.status_code = 201
    mock_post.return_value = mock_response
    
    with patch.dict(os.environ, {"BREVO_API_KEY": "brevo_123456", "EMAIL_FROM": "sender@domain.com"}):
        result = _send_via_brevo("Test Subject", "<p>Hello</p>", "recipient@domain.com", "cc@domain.com")
        assert result is True
        
        # Verify post parameters
        mock_post.assert_called_once_with(
            "https://api.brevo.com/v3/smtp/email",
            json={
                "sender": {"email": "sender@domain.com"},
                "to": [{"email": "recipient@domain.com"}],
                "subject": "Test Subject",
                "htmlContent": "<p>Hello</p>",
                "cc": [{"email": "cc@domain.com"}]
            },
            headers={
                "api-key": "brevo_123456",
                "Content-Type": "application/json"
            },
            timeout=10.0
        )

@patch("automation.email_service._send_via_resend")
def test_send_email_routing_resend(mock_resend):
    mock_resend.return_value = True
    with patch.dict(os.environ, {"RESEND_API_KEY": "re_123", "EMAIL_TO": "admin@domain.com"}):
        result = _send_email("Subject", "HTML", "patient@domain.com")
        assert result is True
        mock_resend.assert_called_once_with("Subject", "HTML", "admin@domain.com", "patient@domain.com")

@patch("automation.email_service._send_via_brevo")
def test_send_email_routing_brevo(mock_brevo):
    mock_brevo.return_value = True
    with patch.dict(os.environ, {"BREVO_API_KEY": "brevo_123", "EMAIL_TO": "admin@domain.com"}):
        result = _send_email("Subject", "HTML", "patient@domain.com")
        assert result is True
        mock_brevo.assert_called_once_with("Subject", "HTML", "admin@domain.com", "patient@domain.com")

@patch("automation.email_service._get_smtp_config")
@patch("smtplib.SMTP")
def test_send_email_routing_smtp_fallback(mock_smtp, mock_smtp_config):
    # Mock SMTP setup to verify standard fallback works when no API keys are present
    mock_smtp_config.return_value = {
        "host": "smtp.domain.com",
        "port": 587,
        "username": "user",
        "password": "pwd",
        "from": "from@domain.com",
        "to": "to@domain.com"
    }
    mock_server = MagicMock()
    mock_smtp.return_value = mock_server
    
    with patch.dict(os.environ, {"EMAIL_TO": "to@domain.com"}, clear=True):
        # Temporarily clear API keys
        if "RESEND_API_KEY" in os.environ:
            del os.environ["RESEND_API_KEY"]
        if "BREVO_API_KEY" in os.environ:
            del os.environ["BREVO_API_KEY"]
            
        result = _send_email("Subject", "HTML", "patient@domain.com")
        assert result is True
        mock_smtp_config.assert_called_once()
        mock_smtp.assert_called_once_with("smtp.domain.com", 587, timeout=10)
