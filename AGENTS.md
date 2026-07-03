# AI Receptionist Voice Agent

## Project
Build a production-quality AI receptionist for QuensultingAI Dental Clinic using RetellAI Conversational Flow.

## Goals
1. Reliability
2. Clean architecture
3. Great conversation UX
4. Error handling
5. Explainability

## Stack
- RetellAI Conversational Flow
- FastAPI
- Google Sheets API
- SMTP Email
- Render

## Architecture
RetellAI -> Webhook -> FastAPI -> Booking Service -> Google Sheets -> Email

## Coding Standards
- Python 3.12+
- Type hints
- Pydantic models
- Logging
- Exception handling
- Small reusable functions

## Conversation
Be a friendly professional dental receptionist.
Always greet, identify intent, collect required details, confirm booking, then end politely.

Appointment fields:
- Full Name
- Phone
- Email
- Preferred Date
- Preferred Time
- Service
- Notes

Never hallucinate appointments.
Retry once on backend failures.
Escalate to a human when appropriate.
