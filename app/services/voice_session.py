"""
Voice Session Manager — Maps Twilio CallSid to internal sessions.
Tracks call-specific state for the voice conversation flow.
"""
import time
from typing import Optional


# Voice call states
class CallState:
    GREETING = "greeting"
    MAIN_LOOP = "main_loop"
    AWAITING_LOGIN_PHONE = "awaiting_login_phone"
    AWAITING_OTP = "awaiting_otp"
    GOODBYE = "goodbye"


class VoiceSessionStore:
    """Manages voice call sessions, mapping Twilio CallSid to app sessions."""

    def __init__(self):
        self._sessions: dict[str, dict] = {}

    def create_session(self, call_sid: str, caller_number: str) -> dict:
        """Create a new voice session when a call comes in."""
        session = {
            "call_sid": call_sid,
            "caller_number": caller_number,
            "session_id": None,         # mapped after orchestrator init
            "call_state": CallState.GREETING,
            "user_type": "guest",
            "verified": False,
            "patient_id": None,
            "patient_name": None,
            "login_phone": None,
            "started_at": time.time(),
            "last_active": time.time(),
            "turn_count": 0,
        }
        self._sessions[call_sid] = session
        return session

    def get_session(self, call_sid: str) -> Optional[dict]:
        """Get an existing voice session."""
        session = self._sessions.get(call_sid)
        if session:
            session["last_active"] = time.time()
        return session

    def update_session(self, call_sid: str, **kwargs) -> Optional[dict]:
        """Update fields on an existing session."""
        session = self._sessions.get(call_sid)
        if not session:
            return None
        session.update(kwargs)
        session["last_active"] = time.time()
        return session

    def set_state(self, call_sid: str, new_state: str) -> None:
        """Transition the call state."""
        session = self._sessions.get(call_sid)
        if session:
            old_state = session["call_state"]
            session["call_state"] = new_state
            print(f"  Voice state: {old_state} → {new_state} (call {call_sid[:8]}...)")

    def increment_turn(self, call_sid: str) -> int:
        """Increment and return the turn count."""
        session = self._sessions.get(call_sid)
        if session:
            session["turn_count"] += 1
            return session["turn_count"]
        return 0

    def end_session(self, call_sid: str) -> Optional[dict]:
        """Remove a completed call session."""
        session = self._sessions.pop(call_sid, None)
        if session:
            duration = time.time() - session["started_at"]
            print(f"  Call ended: {call_sid[:8]}... | Duration: {duration:.0f}s | Turns: {session['turn_count']}")
        return session

    def cleanup_stale(self, max_age_seconds: int = 3600) -> int:
        """Remove sessions older than max_age_seconds."""
        now = time.time()
        stale = [
            sid for sid, s in self._sessions.items()
            if now - s["last_active"] > max_age_seconds
        ]
        for sid in stale:
            self._sessions.pop(sid, None)
        return len(stale)


# Global voice session store
voice_session_store = VoiceSessionStore()
