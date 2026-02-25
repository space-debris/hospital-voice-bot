import time
import uuid
from typing import Optional


class SessionStore:
    """In-memory session store for conversation state management."""

    def __init__(self, timeout_minutes: int = 30):
        self._sessions: dict = {}
        self._timeout = timeout_minutes * 60  # convert to seconds

    def create_session(self) -> str:
        """Create a new guest session and return the session ID."""
        session_id = str(uuid.uuid4())
        self._sessions[session_id] = {
            "session_id": session_id,
            "user_type": "guest",  # "guest" or "registered"
            "verified": False,
            "patient_id": None,
            "patient_name": None,
            "patient_code": None,
            "phone": None,
            "conversation_history": [],
            "created_at": time.time(),
            "last_active": time.time(),
        }
        return session_id

    def get_session(self, session_id: str) -> Optional[dict]:
        """Get session by ID. Returns None if expired or not found."""
        session = self._sessions.get(session_id)
        if not session:
            return None

        # Check expiry
        if time.time() - session["last_active"] > self._timeout:
            self.delete_session(session_id)
            return None

        session["last_active"] = time.time()
        return session

    def get_or_create_session(self, session_id: Optional[str] = None) -> dict:
        """Get existing session or create a new one."""
        if session_id:
            session = self.get_session(session_id)
            if session:
                return session

        new_id = self.create_session()
        return self._sessions[new_id]

    def update_session(self, session_id: str, **kwargs):
        """Update session fields."""
        session = self._sessions.get(session_id)
        if session:
            session.update(kwargs)
            session["last_active"] = time.time()

    def add_message(self, session_id: str, role: str, content: str):
        """Add a message to the conversation history."""
        session = self._sessions.get(session_id)
        if session:
            session["conversation_history"].append({
                "role": role,
                "content": content,
                "timestamp": time.time(),
            })
            # Keep only last 20 turns to manage context size
            if len(session["conversation_history"]) > 40:
                session["conversation_history"] = session["conversation_history"][-40:]

    def get_history(self, session_id: str) -> list:
        """Get conversation history for a session."""
        session = self._sessions.get(session_id)
        if session:
            return session["conversation_history"]
        return []

    def upgrade_to_registered(
        self,
        session_id: str,
        patient_id: int,
        patient_name: str,
        patient_code: str,
        phone: str,
    ):
        """Upgrade a guest session to a verified registered session."""
        self.update_session(
            session_id,
            user_type="registered",
            verified=True,
            patient_id=patient_id,
            patient_name=patient_name,
            patient_code=patient_code,
            phone=phone,
        )

    def delete_session(self, session_id: str):
        """Delete a session."""
        self._sessions.pop(session_id, None)

    def cleanup_expired(self):
        """Remove all expired sessions."""
        now = time.time()
        expired = [
            sid for sid, s in self._sessions.items()
            if now - s["last_active"] > self._timeout
        ]
        for sid in expired:
            del self._sessions[sid]


# Global session store instance
session_store = SessionStore()
