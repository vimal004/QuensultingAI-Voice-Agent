# Loom Walkthrough Script: AI Voice Receptionist

This script is structured to be crisp, professional, and run between **3 to 5 minutes**. It directly maps to the QuensultingAI assignment checklist and evaluation criteria.

---

## 🎬 Video Overview

* **Target Length**: ~4 minutes
* **Screen Layout**: Screen-share + Camera bubble (bottom corner)
* **Required Open Tabs/Apps**:
  1. **Retell AI Dashboard** (Visualizing the Conversational Flow)
  2. **FastAPI Codebase** ([app.py](file:///Users/vimalmanoharan/Desktop/QuensultingAI-Voice-Agent/backend/app.py) & [email_service.py](file:///Users/vimalmanoharan/Desktop/QuensultingAI-Voice-Agent/automation/email_service.py))
  3. **Google Sheet** (Showing rows matching Call ID, Name, Phone, Email, Date, Time, Service, Notes, Call Summary, and Recording URL)
  4. **Resend Dashboard** (Showing email logs / email received in inbox)

---

## 🎙️ Section-by-Section Script

### Section 1: Introduction (30 seconds)
🖥️ **Visual**: Your face camera bubble + **Retell AI Conversational Flow Builder** showing the agent graph.

> *"Hi everyone, my name is **[Your Name]**, and today I am excited to walk you through my implementation of the AI Receptionist Voice Agent for QuensultingAI Dental Clinic."*
>
> *"For this project, I've built a production-quality receptionist that handles bookings, cancels/reschedules, and FAQs. The tech stack consists of **Retell AI Conversational Flow** on the front end, backed by a **FastAPI** orchestrator deployed on **Render**, integrated with **Google Sheets API** for scheduling, and **Resend's HTTP API** for automated email confirmations."*

---

### Section 2: Conversational Design in Retell AI (1 minute)
🖥️ **Visual**: Hover/zoom over nodes in the **Retell AI Flow Builder** (Greeting, Booking, FAQ, and End Call).

> *"Let's look at the conversational design. I chose a structured Conversational Flow over a prompt-only agent because it provides deterministic, reliable state transitions — which is critical for medical environments."*
>
> *"The flow begins with an warm greeting and immediate intent detection. We handle three main paths: booking new appointments, answering FAQs from a structured knowledge base, and handling reschedule/cancellation requests."*
>
> *"We support **graceful interruption handling**, so the agent stops speaking immediately when the user talks, and **progressive detail collection**, gathering name, phone, email, date, time, and service step-by-step. If the conversation breaks down or a medical emergency is detected, it triggers a global node that escalates the caller by transferring them to a human front-desk line."*

---

### Section 3: Technical Architecture & Design Decisions (1 minute 30 seconds)
🖥️ **Visual**: Switch to VS Code. Show [backend/app.py](file:///Users/vimalmanoharan/Desktop/QuensultingAI-Voice-Agent/backend/app.py) around the `/webhook/retell` endpoint and background tasks.

> *"Moving on to the backend architecture, I made three key design decisions to ensure production-grade reliability:"*
>
> 1. **Dual-Mode Booking**: *"During live calls, Retell invokes our synchronous `/check-availability` endpoint to query Google Sheets in real-time. If the slot is free, it confirms it immediately. If it's taken, the backend calculates and returns up to three same-day alternative slots to the voice agent to read out. However, if the caller is in a hurry or the clinic is closed, it switches to post-call webhook mode to save the request, minimizing mid-call API latency."*
>
> 2. **Non-Blocking Webhook Processing**: *"External API operations like writing to Google Sheets or sending emails can take 2–5 seconds. If run synchronously, this would cause Retell's webhook to time out. My FastAPI webhook endpoint instantly verifies the cryptographic Retell signature, responds `200 OK`, and delegates the Sheets and Email integrations to FastAPI `BackgroundTasks`."*
>
> 3. **SMTP Workaround via HTTP APIs**: *"Since hosting platforms like Render block standard SMTP ports (587, 465) on their free tiers, I avoided fragile SMTP connections entirely and implemented **Resend's HTTP-based Email API**. This sends confirmations securely over HTTPS (port 443) with zero latency."*

---

### Section 4: Live Walkthrough & Validation (1 minute)
🖥️ **Visual**: Show a split-screen of **Google Sheets** and the **Resend logs / Inbox**. Run a webhook test payload via Postman/terminal or play a short snippet of a recorded call.

> *"Let's see it in action. Here is our Google Sheet, currently showing our patient list. When a booking is finalized, the Retell webhook triggers our FastAPI app."*
> 
> *"The sheet is automatically updated with the patient's Name, Phone, Email, Preferred Date/Time, Service, and crucially, the **AI-generated call summary** and **call recording audio link** for the clinic staff."*
> 
> *(Show email)* *"Almost instantly, our background worker triggers a Resend request, delivering a clean, responsive HTML confirmation email both to the clinic admin and the patient."*

---

### Section 5: Conclusion (15 seconds)
🖥️ **Visual**: Switch back to your camera bubble or the GitHub repository home page.

> *"By combining strict conversational flows, synchronous slot checking, background webhook processing, and HTTP-based emailing, we have a highly reliable, error-tolerant system ready for real-world deployment."*
>
> *"Thank you for your time, and I look forward to discussing the implementation in the technical interview!"*

---

## 💡 Pro-Tips for Recording

1. **Test Your Audio First**: Ensure your microphone is clear and there is no background noise.
2. **Smooth Transitions**: Use keyboard shortcuts (like `Cmd + Tab` or `Alt + Tab`) to switch cleanly between your web browser and code editor.
3. **No Code Typing**: Do not write code live. Show the already-written code and point to specific lines (like `background_tasks.add_task` or the `httpx.post` call to Resend) to keep the video fast-paced and professional.
