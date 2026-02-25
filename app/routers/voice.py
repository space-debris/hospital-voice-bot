"""
Voice Router — Twilio webhook endpoints for inbound phone calls.
Handles the full voice conversation loop: ASR (Gather) → LLM → TTS (Say).

Barge-in: Supported inherently — <Gather> wrapping <Say> allows callers
to interrupt bot mid-speech by speaking. Twilio stops playback and captures input.
"""
from fastapi import APIRouter, Form, Depends, Request
from fastapi.responses import Response
from sqlalchemy.orm import Session
from twilio.twiml.voice_response import VoiceResponse, Gather

from app.database import get_db
from app.config import settings
from app.services.voice_session import voice_session_store, CallState
from app.services.session_store import session_store
from app.services.orchestrator import orchestrator
from app.services.auth_service import auth_service
from app.services.metrics import metrics
from app.models import Appointment

router = APIRouter(prefix="/voice", tags=["voice"])

# ── TwiML helpers ───────────────────────────────────────

VOICE_CONFIG = {
    "voice": "Google.en-IN-Neural2-A",    # Google Neural2 — natural Indian English female
    "language": "en-IN",
}

GATHER_CONFIG = {
    "input": "speech dtmf",        # accept BOTH speech and keypad
    "language": "en-IN",
    "speechTimeout": "auto",       # auto-detect end of speech
    "timeout": 8,                   # seconds of silence before timeout
    "speechModel": "phone_call",   # optimized for phone audio
}


def twiml_response(vr: VoiceResponse) -> Response:
    """Return a TwiML XML response."""
    twiml_str = str(vr)
    print(f"  📝 TwiML response ({len(twiml_str)} chars): {twiml_str[:200]}...")
    return Response(content=twiml_str, media_type="application/xml")


def say(vr: VoiceResponse, text: str) -> None:
    """Say text with consistent voice settings."""
    vr.say(text, **VOICE_CONFIG)


def gather_speech(vr: VoiceResponse, action_path: str, prompt: str = None) -> None:
    """Add a Gather element for speech input with optional prompt."""
    action_url = f"{settings.NGROK_URL}{action_path}"
    gather = Gather(action=action_url, **GATHER_CONFIG)
    if prompt:
        gather.say(prompt, **VOICE_CONFIG)
    vr.append(gather)

    # If no input is received, redirect back to incoming
    say(vr, "I didn't catch that. Let me try again.")
    vr.redirect(f"{settings.NGROK_URL}/voice/incoming")


def gather_dtmf(vr: VoiceResponse, action_path: str, prompt: str, num_digits: int = 6) -> None:
    """Add a Gather element for DTMF (keypad) input."""
    action_url = f"{settings.NGROK_URL}{action_path}"
    gather = Gather(
        action=action_url,
        input="dtmf",
        timeout=15,
        numDigits=num_digits,
        finishOnKey="#",
    )
    gather.say(prompt, **VOICE_CONFIG)
    vr.append(gather)

    # If no input, prompt again
    say(vr, "I didn't receive any input.")
    vr.redirect(f"{settings.NGROK_URL}{action_path}")


# ── Main Endpoints ──────────────────────────────────────

@router.post("/incoming")
async def voice_incoming(
    CallSid: str = Form(""),
    From: str = Form(""),
    To: str = Form(""),
    db: Session = Depends(get_db),
):
    """
    Called when a new inbound call arrives.
    Greets the caller and starts the conversation loop.
    """
    print(f"\n📞 Incoming call: {From} → {To} (CallSid: {CallSid[:8]}...)")
    metrics.increment("voice_calls_total")

    # Create voice session
    vs = voice_session_store.create_session(CallSid, From)

    # Also create an app session for the orchestrator
    app_session = session_store.get_or_create_session(None)
    vs["session_id"] = app_session["session_id"]

    voice_session_store.set_state(CallSid, CallState.MAIN_LOOP)

    # Build greeting TwiML
    vr = VoiceResponse()
    vr.pause(length=1)

    # Check for auto-login (Caller ID lookup)
    # Extract 10-digit number from E.164 format (+919876543210 -> 9876543210)
    caller_clean = _extract_phone_number(From)
    patient = auth_service.lookup_patient(db, caller_clean)

    if patient:
        # ✅ Auto-login success
        patient_name = patient.full_name
        print(f"  🔓 Auto-login successful for: {patient_name} ({caller_clean})")

        # Upgrade voice session
        voice_session_store.update_session(
            CallSid,
            user_type="registered",
            verified=True,
            patient_id=patient.id,
            patient_name=patient_name,
            login_phone=caller_clean
        )

        # Upgrade app session (for orchestrator tools)
        session_store.upgrade_session(
            vs["session_id"],
            patient_id=patient.id,
            patient_name=patient_name,
            patient_code=patient.patient_code
        )

        # Check for upcoming appointments
        next_appt = db.query(Appointment).filter(
            Appointment.patient_id == patient.id,
            Appointment.status == 'scheduled'
        ).order_by(Appointment.date, Appointment.time_slot).first()

        appt_msg = ""
        if next_appt:
            # Format date for speech (e.g., 2026-02-13 -> tomorrow/Friday)
            # For POC, simple date string is fine, TTS reads it okay
            appt_msg = f" I see you have an appointment with {next_appt.doctor.name} on {next_appt.date} at {next_appt.time_slot}."

        greeting = (
            f"Welcome back to City General Hospital, {patient_name}.{appt_msg} "
            "I'm your AI assistant. "
            "How can I help you today?"
        )
    else:
        # 👤 Guest flow
        greeting = (
            "Welcome to City General Hospital. I am your AI assistant. "
            "I can help you with department information, OPD timings, doctor schedules, "
            "and much more. "
        )
        if len(caller_clean) == 10:
            greeting += (
                "If you are a registered patient and would like to access your appointments, "
                "reports, or billing, press 1 or say 'login'. "
            )
        greeting += "How can I help you today?"

    gather_speech(vr, "/voice/respond", prompt=greeting)

    return twiml_response(vr)


@router.post("/respond")
async def voice_respond(
    CallSid: str = Form(""),
    SpeechResult: str = Form(""),
    Confidence: str = Form("0"),
    Digits: str = Form(""),
    db: Session = Depends(get_db),
):
    """
    Called after each speech input. Processes the transcript through
    the orchestrator and responds with TTS.
    """
    vs = voice_session_store.get_session(CallSid)
    if not vs:
        vr = VoiceResponse()
        say(vr, "Sorry, your session has expired. Please call again.")
        vr.hangup()
        return twiml_response(vr)

    transcript = SpeechResult.strip()
    confidence = float(Confidence) if Confidence else 0
    turn = voice_session_store.increment_turn(CallSid)

    print(f"  🎤 Turn {turn} | Transcript: \"{transcript}\" (confidence: {confidence:.2f})")

    # Handle special intents
    lower_text = transcript.lower()

    # ── Login request ──
    if Digits == "1" or any(word in lower_text for word in ["login", "log in", "sign in", "registered", "my account"]):
        return _start_login_flow(CallSid, vs)

    # ── Escalation / transfer request ──
    if any(phrase in lower_text for phrase in [
        "talk to someone", "talk to a person", "speak to someone",
        "human", "agent", "operator", "receptionist",
        "transfer", "connect me", "real person", "staff",
    ]):
        return _transfer_to_staff(CallSid)

    # ── Hang up request ──
    if any(word in lower_text for word in ["goodbye", "bye", "hang up", "end call", "that's all", "thank you bye"]):
        return _end_call(CallSid)

    # ── Low confidence — ask to repeat ──
    if confidence > 0 and confidence < 0.4 and transcript:
        vr = VoiceResponse()
        gather_speech(vr, "/voice/respond", prompt="I'm sorry, I didn't quite catch that. Could you please repeat?")
        return twiml_response(vr)

    # ── Process through orchestrator ──
    if not transcript:
        vr = VoiceResponse()
        gather_speech(vr, "/voice/respond", prompt="I didn't hear anything. Please go ahead with your question.")
        return twiml_response(vr)

    try:
        result = await orchestrator.process_message(
            user_message=transcript,
            session_id=vs["session_id"],
            db=db,
        )

        # Update voice session with any auth changes
        vs["session_id"] = result.get("session_id", vs["session_id"])
        vs["user_type"] = result.get("user_type", vs["user_type"])
        vs["verified"] = result.get("verified", vs["verified"])

        reply = result["reply"]

        # Clean reply for voice (remove markdown formatting)
        voice_reply = _clean_for_voice(reply)

        print(f"  🤖 Reply (first 100 chars): \"{voice_reply[:100]}...\"")

    except Exception as e:
        print(f"  ❌ Orchestrator error: {e}")
        voice_reply = "I'm having trouble processing your request. Please try again."

    # Respond and gather next input
    vr = VoiceResponse()

    # If reply is very long, truncate for voice
    if len(voice_reply) > 600:
        voice_reply = voice_reply[:600] + "... Would you like me to continue, or do you have another question?"

    gather_speech(vr, "/voice/respond", prompt=voice_reply)

    return twiml_response(vr)


# ── Login Flow Endpoints ────────────────────────────────

def _start_login_flow(call_sid: str, vs: dict) -> Response:
    """Initiate the login flow — ask for phone number."""
    voice_session_store.set_state(call_sid, CallState.AWAITING_LOGIN_PHONE)

    vr = VoiceResponse()
    gather_speech(
        vr, "/voice/login-input",
        prompt="Sure, let me help you log in. Please say your 10-digit registered phone number.",
    )
    return twiml_response(vr)


@router.post("/login-input")
async def voice_login_input(
    CallSid: str = Form(""),
    SpeechResult: str = Form(""),
    db: Session = Depends(get_db),
):
    """Captures the phone number spoken by the caller."""
    vs = voice_session_store.get_session(CallSid)
    if not vs:
        vr = VoiceResponse()
        say(vr, "Session expired. Please call again.")
        vr.hangup()
        return twiml_response(vr)

    spoken_text = SpeechResult.strip()

    # Extract digits from spoken text (handles "nine eight seven six...")
    phone = _extract_phone_number(spoken_text)

    print(f"  📱 Login phone input: \"{spoken_text}\" → extracted: \"{phone}\"")

    if not phone or len(phone) != 10:
        vr = VoiceResponse()
        gather_speech(
            vr, "/voice/login-input",
            prompt=f"I heard '{spoken_text}', but I need a 10-digit phone number. Please try again.",
        )
        return twiml_response(vr)

    # Attempt login via auth service
    result = auth_service.initiate_login(phone, db)

    if not result["success"]:
        vr = VoiceResponse()
        say(vr, f"{result['message']}. Let me help you with general information instead.")
        voice_session_store.set_state(CallSid, CallState.MAIN_LOOP)
        gather_speech(vr, "/voice/respond", prompt="What would you like to know?")
        return twiml_response(vr)

    # Store login state
    voice_session_store.update_session(CallSid, login_phone=phone)
    voice_session_store.set_state(CallSid, CallState.AWAITING_OTP)

    # Ask for OTP via DTMF (keypad)
    vr = VoiceResponse()
    gather_dtmf(
        vr, "/voice/verify-otp",
        prompt=(
            f"An OTP has been sent to your phone. "
            f"Please enter the 6-digit OTP using your phone keypad, followed by the hash key."
        ),
        num_digits=6,
    )
    return twiml_response(vr)


@router.post("/verify-otp")
async def voice_verify_otp(
    CallSid: str = Form(""),
    Digits: str = Form(""),
    db: Session = Depends(get_db),
):
    """Verifies the OTP entered via DTMF."""
    vs = voice_session_store.get_session(CallSid)
    if not vs:
        vr = VoiceResponse()
        say(vr, "Session expired. Please call again.")
        vr.hangup()
        return twiml_response(vr)

    otp = Digits.strip()
    phone = vs.get("login_phone", "")

    print(f"  🔑 OTP verification: phone={phone}, otp={otp}")

    if not otp or len(otp) != 6:
        vr = VoiceResponse()
        gather_dtmf(
            vr, "/voice/verify-otp",
            prompt="That doesn't seem right. Please enter the 6-digit OTP using your keypad.",
            num_digits=6,
        )
        return twiml_response(vr)

    # Verify OTP
    result = auth_service.verify_otp(phone, otp, db)

    if not result["success"]:
        vr = VoiceResponse()
        gather_dtmf(
            vr, "/voice/verify-otp",
            prompt=f"{result['message']}. Please try entering the OTP again.",
            num_digits=6,
        )
        return twiml_response(vr)

    # Success — upgrade session
    patient_name = result.get("patient_name", "")

    # Upgrade the app session
    if vs.get("session_id"):
        session_store.upgrade_session(
            vs["session_id"],
            patient_id=result.get("patient_id"),
            patient_name=patient_name,
            patient_code=result.get("patient_code", ""),
        )

    voice_session_store.update_session(
        CallSid,
        user_type="registered",
        verified=True,
        patient_id=result.get("patient_id"),
        patient_name=patient_name,
    )
    voice_session_store.set_state(CallSid, CallState.MAIN_LOOP)

    print(f"  ✅ Patient verified: {patient_name}")

    vr = VoiceResponse()
    gather_speech(
        vr, "/voice/respond",
        prompt=(
            f"You're now logged in as {patient_name}. "
            f"You can now ask about your appointments, lab reports, or billing. "
            f"How can I help you?"
        ),
    )
    return twiml_response(vr)


# ── Call Status Callback ────────────────────────────────

@router.post("/status")
async def voice_status(
    CallSid: str = Form(""),
    CallStatus: str = Form(""),
    CallDuration: str = Form("0"),
):
    """Called by Twilio when call status changes (completed, failed, etc.)."""
    print(f"  📊 Call status: {CallStatus} (duration: {CallDuration}s, sid: {CallSid[:8]}...)")

    if CallStatus in ("completed", "failed", "busy", "no-answer", "canceled"):
        voice_session_store.end_session(CallSid)
        if CallStatus == "completed":
            metrics.observe("voice_call_duration_s", float(CallDuration))
        elif CallStatus == "failed":
            metrics.increment("voice_calls_failed")

    return Response(content="", status_code=200)


# ── Helpers ─────────────────────────────────────────────

def _end_call(call_sid: str) -> Response:
    """End the call gracefully."""
    voice_session_store.set_state(call_sid, CallState.GOODBYE)

    vr = VoiceResponse()
    say(vr, (
        "Thank you for calling City General Hospital. "
        "We hope we could help. Have a great day! Goodbye."
    ))
    vr.hangup()

    voice_session_store.end_session(call_sid)
    return twiml_response(vr)


def _transfer_to_staff(call_sid: str) -> Response:
    """Transfer the caller to hospital reception / human agent."""
    voice_session_store.set_state(call_sid, CallState.GOODBYE)

    vr = VoiceResponse()
    reception = settings.HOSPITAL_RECEPTION_NUMBER

    if reception:
        print(f"  🔀 Transferring call {call_sid[:8]}... to {reception}")
        say(vr, "Sure, let me connect you to our reception. Please hold.")
        vr.dial(reception, caller_id=settings.TWILIO_PHONE_NUMBER, timeout=30)
        # If dial fails or no answer, end gracefully
        say(vr, "I'm sorry, the reception line is busy. Please try calling again later.")
        vr.hangup()
    else:
        # No reception number configured — provide the number verbally
        print(f"  🔀 Escalation requested but no reception number configured")
        say(vr, (
            "I'd be happy to connect you with our staff. "
            "Please call our reception directly at 011-2345-6700. "
            "They will be able to assist you further. "
            "Is there anything else I can help you with?"
        ))
        # Don't hang up — go back to conversation
        gather_speech(vr, "/voice/respond")

    voice_session_store.end_session(call_sid)
    return twiml_response(vr)


def _clean_for_voice(text: str) -> str:
    """Remove markdown formatting from text for TTS."""
    import re
    # Remove markdown
    text = re.sub(r'\*\*(.+?)\*\*', r'\1', text)     # bold
    text = re.sub(r'\*(.+?)\*', r'\1', text)          # italic
    text = re.sub(r'`(.+?)`', r'\1', text)            # code
    text = re.sub(r'^#{1,3}\s+', '', text, flags=re.MULTILINE)  # headers
    text = re.sub(r'^\s*[\-\*]\s+', '• ', text, flags=re.MULTILINE)  # bullets
    text = re.sub(r'\|', ', ', text)                   # table pipes
    text = re.sub(r'-{3,}', '', text)                  # hr
    text = re.sub(r'\n{3,}', '\n\n', text)             # excess newlines
    text = text.strip()
    return text


def _extract_phone_number(text: str) -> str:
    """
    Extract a 10-digit phone number from spoken text.
    Handles: "9876543210", "nine eight seven six...", "98765 43210", etc.
    """
    import re

    # First try: direct digit extraction
    digits = re.sub(r'[^\d]', '', text)
    if len(digits) == 10:
        return digits
    if len(digits) == 12 and digits.startswith("91"):
        return digits[2:]
    if len(digits) == 13 and digits.startswith("+91"):
        return digits[3:]

    # Second try: convert spoken words to digits
    word_to_digit = {
        'zero': '0', 'oh': '0', 'o': '0',
        'one': '1', 'two': '2', 'three': '3', 'four': '4',
        'five': '5', 'six': '6', 'seven': '7', 'eight': '8', 'nine': '9',
        'double': None,  # special: "double seven" = "77"
        'triple': None,  # special: "triple nine" = "999"
    }

    words = text.lower().split()
    result = []
    i = 0
    while i < len(words):
        word = words[i]
        if word == 'double' and i + 1 < len(words) and words[i + 1] in word_to_digit:
            d = word_to_digit[words[i + 1]]
            if d:
                result.append(d * 2)
            i += 2
        elif word == 'triple' and i + 1 < len(words) and words[i + 1] in word_to_digit:
            d = word_to_digit[words[i + 1]]
            if d:
                result.append(d * 3)
            i += 2
        elif word in word_to_digit and word_to_digit[word] is not None:
            result.append(word_to_digit[word])
            i += 1
        else:
            i += 1

    extracted = ''.join(result)
    if len(extracted) == 10:
        return extracted

    # Return whatever digits we found
    return digits if len(digits) >= 10 else extracted
