# AI Receptionist Voice Agent - QuensultingAI Dental Clinic

A production-quality AI voice agent built for QuensultingAI Dental Clinic using RetellAI Conversational Flow, FastAPI, Google Sheets, and SMTP email integration.

## 🎯 Project Overview

This voice agent handles inbound calls for a dental clinic, capable of:
- Booking new appointments with complete detail collection
- Answering frequently asked questions about clinic services
- Handling reschedule and cancellation requests
- Escalating to human staff when needed
- Emergency call handling
- Live slot availability checking during calls

## 🚀 Live Backend

The backend API is hosted on Render: **https://quensultingai-voice-agent.onrender.com**

- **Health Check:** https://quensultingai-voice-agent.onrender.com/health
- **Slot Availability:** https://quensultingai-voice-agent.onrender.com/check-availability
- **Webhook Endpoint:** https://quensultingai-voice-agent.onrender.com/webhook/retell

## ✨ Features

### Conversation Design
- **Natural greeting and intent detection** - Routes callers to booking, FAQ, or reschedule flows
- **Progressive detail collection** - Collects appointment info one field at a time
- **Interruption handling** - Stops immediately when caller interrupts and responds appropriately
- **Correction handling** - Updates individual fields without restarting the flow
- **FAQ system** - Answers questions about hours, services, location, payment, insurance
- **Emergency detection** - Global node triggers for dental emergencies
- **Human escalation** - Transfers to front desk when caller requests or conversation breaks down

### Backend Automation
- **Webhook signature verification** - Validates RetellAI webhooks for security
- **Background task processing** - Non-blocking Google Sheets and email operations
- **Retry-once policy** - Automatic retry for failed integrations
- **Google Sheets integration** - Stores all booking details with automatic header initialization
- **SMTP email notifications** - Sends confirmation emails to patients and clinic admin
- **Live slot availability** - Real-time checking against existing bookings

### Error Handling
- Graceful fallbacks for API failures
- Comprehensive logging at all stages
- Proper HTTP status codes and error messages
- Input validation and sanitization

## 🏗️ Architecture

```
Caller → RetellAI → Webhook → FastAPI Backend
                              ↓
                         Booking Service
                              ↓
                    ┌─────────┴─────────┐
                    ↓                   ↓
              Google Sheets         SMTP Email
                    ↓                   ↓
              Data Storage      Notifications
```

### Tech Stack

- **Voice Platform:** RetellAI Conversational Flow
- **Backend:** FastAPI (Python 3.12+)
- **Data Storage:** Google Sheets API
- **Email:** SMTP
- **Deployment:** Render
- **Testing:** Pytest

## 📋 Prerequisites

- Python 3.12 or higher
- RetellAI account with API access
- Google Cloud project with Sheets API enabled
- Google Service Account credentials
- SMTP email server (Gmail, SendGrid, etc.)
- Google Sheet for booking storage

## 🔧 Quick Setup

### Option 1: Use Hosted Backend (Easiest)

1. **Import the RetellAI Agent**
   - Open `Conversation Flow Agent.json` in RetellAI dashboard
   - Update the tool URL to: `https://quensultingai-voice-agent.onrender.com/check-availability`
   - Configure your RetellAI phone number

2. **Set Environment Variables in RetellAI**
   - Add your webhook URL: `https://quensultingai-voice-agent.onrender.com/webhook/retell`
   - Set `RETELL_API_KEY` in the hosted backend (already configured)

3. **Configure Google Sheets**
   - Create a new Google Sheet
   - Share with your service account email (editor permissions)
   - Note the Sheet ID from the URL

4. **Configure Email**
   - Set up SMTP credentials (host, port, username, password)
   - Configure sender and recipient emails

5. **Test the Agent**
   - Call your RetellAI phone number
   - Try booking an appointment
   - Check Google Sheet for new entries
   - Verify email notifications

### Option 2: Local Development

1. **Clone the repository**
   ```bash
   git clone <repository-url>
   cd QuensultingAI-Voice-Agent
   ```

2. **Create virtual environment**
   ```bash
   python -m venv .venv
   source .venv/bin/activate  # On Windows: .venv\Scripts\activate
   ```

3. **Install dependencies**
   ```bash
   pip install -r requirements.txt
   ```

4. **Configure environment variables**
   Create a `.env` file in the project root:
   ```env
   # RetellAI
   RETELL_API_KEY=your_retell_api_key_here

   # Google Sheets
   GOOGLE_SHEET_ID=your_google_sheet_id_here
   GOOGLE_APPLICATION_CREDENTIALS=path/to/credentials.json
   # OR use raw JSON (recommended for Render):
   GOOGLE_CREDS_JSON='{"type":"service_account",...}'

   # SMTP Email
   SMTP_HOST=smtp.gmail.com
   SMTP_PORT=587
   SMTP_USERNAME=your_email@gmail.com
   SMTP_PASSWORD=your_app_password
   EMAIL_FROM=clinic@quensultingai.com
   EMAIL_TO=admin@quensultingai.com
   ```

5. **Set up Google Service Account**
   - Go to Google Cloud Console
   - Create a service account
   - Enable Google Sheets API
   - Download credentials JSON
   - Save as `credentials.json` (or use GOOGLE_CREDS_JSON env var)
   - Share your Google Sheet with the service account email

6. **Run the backend**
   ```bash
   uvicorn backend.app:app --reload --host 0.0.0.0 --port 8000
   ```

7. **Test locally**
   ```bash
   # Health check
   curl http://localhost:8000/health

   # Slot availability check
   curl -X POST http://localhost:8000/check-availability \
     -H "Content-Type: application/json" \
     -d '{"preferred_date":"2024-07-10","preferred_time":"10:00 AM","service":"Cleaning"}'
   ```

## 🗂️ Project Structure

```
QuensultingAI-Voice-Agent/
├── backend/
│   ├── app.py                    # FastAPI application and endpoints
│   ├── models/
│   │   └── schemas.py            # Pydantic models for validation
│   └── services/
│       └── booking_service.py    # Booking orchestration logic
├── automation/
│   ├── google_sheets.py          # Google Sheets API integration
│   ├── email_service.py          # SMTP email functionality
│   └── webhook.py                # Webhook signature verification
├── tests/
│   ├── test_app.py               # API endpoint tests
│   ├── test_booking_service.py   # Booking logic tests
│   ├── test_google_sheets.py     # Sheets integration tests
│   └── test_webhook.py           # Webhook tests
├── docs/
│   ├── architecture.md           # System architecture
│   ├── conversation-flow.md      # Conversation design
│   ├── deployment.md             # Deployment guide
│   └── testing-checklist.md      # Testing procedures
├── prompts/
│   ├── receptionist-system.md   # System prompts
│   ├── faq.md                    # FAQ knowledge base
│   └── fallback-policy.md        # Fallback handling
├── Conversation Flow Agent.json   # RetellAI agent configuration
├── requirements.txt              # Python dependencies
└── README.md                     # This file
```

## 🧪 Testing

Run the test suite:
```bash
pytest tests/ -v
```

Run specific test files:
```bash
pytest tests/test_booking_service.py -v
pytest tests/test_google_sheets.py -v
```

## 📊 Conversation Flow

1. **Greeting** - Warm welcome and intent detection
2. **Intent Routing** - Booking, FAQ, or Reschedule/Cancel
3. **FAQ Handling** - Answer clinic questions
4. **Booking Collection** - Progressive detail collection (service, date, time, name, phone, email, notes)
5. **Confirmation** - Read back details for verification
6. **Booking Mode** - Live slot check or email confirmation
7. **Live Lookup** - Real-time availability check via tool
8. **End Call** - Professional closing

### Global Nodes
- **Emergency Handling** - Detects dental emergencies and directs to immediate care
- **Human Escalation** - Transfers to front desk when requested or needed

## 🔐 Security Considerations

- Webhook signature verification for all RetellAI calls
- Environment variables for all sensitive data
- No credentials in code (use .env or secret management)
- Input validation on all API endpoints
- CORS configuration for cross-origin requests
- Background task processing to prevent timeouts

## 🚢 Deployment

### Render Deployment

The backend is deployed on Render with the following configuration:

1. **Build Command:** `pip install -r requirements.txt`
2. **Start Command:** `uvicorn backend.app:app --host 0.0.0.0 --port $PORT`
3. **Environment Variables:** All secrets configured in Render dashboard

### Manual Deployment

1. Push code to GitHub
2. Connect repository to Render
3. Configure environment variables
4. Deploy

## 🎨 Design Decisions

- **Dual-Mode Booking Architecture (Sync vs. Async):** 
  - **Sync (Live Check):** During the call, Retell triggers a `/check-availability` tool call to query Google Sheets and check for slot conflicts in real-time. If taken, it calculates and offers up to 3 same-day alternatives.
  - **Async (Flexible):** For callers in a rush, details are collected, the call ends immediately, and scheduling runs post-call via the webhook.
  - **Why:** Minimizes mid-call API latency (1.5s–3s of silence) for 80% of callers while retaining real-time validation and re-scheduling capabilities for callers who demand certainty.
- **Conversation Flow over Prompt-Only:** Chosen for better control, deterministic state transitions, and reliability compared to pure prompt-based LLM routing.
- **Background Tasks:** Webhook handlers return immediately and run heavy integrations (Google Sheets/SMTP) in the background to prevent webhook timeouts.
- **Retry-Once Policy:** Critical integration handlers attempt the operation up to 2 times, balancing between reliability/fault tolerance and background thread performance.
- **Google Sheets:** Simple, accessible data storage without database complexity.
- **SMTP Email:** Universal email delivery without third-party API dependencies.
- **Slot Availability Logic:** Simplistic date/time matching (no service duration or capacity limits).

## 📝 Environment Variables Reference

| Variable | Required | Description |
|----------|----------|-------------|
| `RETELL_API_KEY` | Yes | RetellAI API key for webhook verification |
| `GOOGLE_SHEET_ID` | Yes | Google Sheet ID for booking storage |
| `GOOGLE_APPLICATION_CREDENTIALS` | No* | Path to service account credentials file |
| `GOOGLE_CREDS_JSON` | No* | Raw JSON string of service account credentials |
| `SMTP_HOST` | Yes | SMTP server hostname |
| `SMTP_PORT` | Yes | SMTP server port (usually 587 or 465) |
| `SMTP_USERNAME` | Yes | SMTP authentication username |
| `SMTP_PASSWORD` | Yes | SMTP authentication password |
| `EMAIL_FROM` | Yes | Sender email address |
| `EMAIL_TO` | Yes | Clinic admin email for notifications |

*Either `GOOGLE_APPLICATION_CREDENTIALS` or `GOOGLE_CREDS_JSON` is required

## 🤝 Support

For questions or issues:
- Check the `docs/` directory for detailed documentation
- Review test files for usage examples
- Examine logs in the backend for debugging

## 📄 Assignment Submission

This project was submitted for the AI Voice Agent Internship position at QuensultingAI.

**Submission includes:**
- RetellAI Agent JSON configuration
- FastAPI backend source code
- Google Sheets integration
- SMTP email automation
- Comprehensive test suite
- Documentation

**Live Demo:** Backend hosted at https://quensultingai-voice-agent.onrender.com
