# Loom Walkthrough Script: AI Voice Receptionist

This script is structured to be high-impact, professional, and run within **3 to 4 minutes**. It focuses on demonstrating the working agent first, verifying the integrations, and highlighting key design decisions that show you understand production-grade systems.

---

## 🎬 Video Overview

* **Target Length**: ~3.5 minutes
* **Screen Layout**: Screen-share + Camera bubble (bottom corner)
* **Required Open Tabs/Apps**:
  1. **Google Sheet** (Showing rows matching patient records)
  2. **Inbox/Resend Dashboard** (To show the email arriving)
  3. **Retell AI Dashboard** (Showing the Conversational Flow agent)
  4. **VS Code** (FastAPI backend files: `app.py`, `sheets_service.py`, `email_service.py`)

---

## 🎙️ Section-by-Section Script

### Section 1: Introduction & Live Demo (1 minute 30 seconds)
🖥️ **Visual**: Your face camera bubble + **Google Sheet** (empty/ready to receive data).

> *"Hi everyone, my name is **[Your Name]**, and today I'll walk you through my implementation of the AI Receptionist Voice Agent for QuensultingAI Dental Clinic.*
>
> *I want to start by showing you a live demonstration. Let's make a call to the agent and book a slot for Teeth Whitening."*

🖥️ **Visual**: Click to make the call (either on your phone or using Retell's web call client). Let the audio play clearly.
* **Agent:** *"Hi, thank you for calling QuensultingAI Dental Clinic! How can I help you today?"*
* **You:** *"Hi, I'd like to book an appointment for Teeth Whitening next Monday at 10 AM."*
* **Agent:** *"I can help with that. Let me check if that slot is available... Yes, that time is free! Can I get your full name, phone number, and email to confirm the booking?"*
* **You:** *(Provide details: e.g., John Doe, +1 234 567 8900, john@example.com)*
* **Agent:** *(Confirms the booking, thanks you, and politely ends the call).*

---

### Section 2: Verification of Integrations (45 seconds)
🖥️ **Visual**: Switch immediately to the **Google Sheet**.

> *"Now that the call has ended, let's verify our integrations. If we look at our Google Sheet, a new entry has been recorded in real-time. It includes the patient's Name, Phone, Email, Date, Time, and Service. Crucially, the backend has processed and stored the **AI-generated call summary** and the **call recording URL** directly in the sheet for clinic staff to review."*

🖥️ **Visual**: Switch immediately to your **Email Inbox**.

> *"Almost instantly, our system dispatched this clean, professional HTML confirmation email containing all booking details, ensuring the patient gets immediate reassurance."*

---

### Section 3: Engineering & Design Decisions (1 minute)
🖥️ **Visual**: Switch to **VS Code** (specifically `backend/app.py`).

> *"To make this solution production-grade, I made five key design decisions:*
>
> 1. **Dual-Mode Booking Architecture**: *Callers benefit from two confirmation flows. We support Sync booking—where the voice agent queries Google Sheets in real-time and offers up to three same-day alternatives if a slot is taken—and Async booking for callers in a rush. This reduces mid-call latency for the majority of callers while maintaining real-time verification when needed.*
> 
> 2. **Global Node Guardrails**: *Instead of manually wiring emergency and front-desk transfer paths from every individual node—which creates a messy, error-prone conversational graph—I implemented them as Retell Global Nodes. This guarantees consistent escalation safety from any state.*
> 
> 3. **Non-Blocking Webhook Processing**: *Operations like writing to Google Sheets and sending emails take 2 to 5 seconds. To prevent Retell webhooks from timing out or triggering retry storms, our FastAPI endpoint validates the cryptographic `x-retell-signature`, responds with `200 OK` instantly, and offloads integrations to background tasks.*
> 
> 4. **LLM-Proof Payload Parsing**: *LLM post-call analysis can output non-deterministic keys (e.g., casing or spacing differences). I built a custom parser that normalizes keys case-insensitively and strips white space, ensuring 100% reliable post-call data extraction.*
> 
> 5. **Reschedule & Cancellation Safety Net**: *We don't just process bookings; the backend extracts rescheduling or cancellation requests and dynamically routes them as high-priority `[Action Required]` email alerts to the clinic administrator, ensuring no patient request is lost.*"

---

### Section 4: Conclusion (15 seconds)
🖥️ **Visual**: Switch back to your camera bubble.

> *"By combining deterministic conversation flows, real-time availability checks, background processing, and secure HTTP-based emailing, we've created a reliable, production-ready receptionist.*
>
> *Thank you, and I look forward to discussing this in the interview!"*

---

## 💡 Quick Tips for Success:
1. **Speak clearly & confidently**: Practice the booking conversation once before hit recording to avoid stumbles.
2. **Smooth Transitions**: Use `Cmd + Tab` (Mac) or `Alt + Tab` (Windows) to jump cleanly between browser windows and VS Code.
3. **No Dead Air**: While the agent is "checking slots," keep speaking or briefly mention that it is invoking the backend tool.
