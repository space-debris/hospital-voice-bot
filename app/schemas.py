from pydantic import BaseModel
from typing import Optional


# ── Chat ──────────────────────────────────────────────

class ChatRequest(BaseModel):
    message: str
    session_id: Optional[str] = None


class ChatResponse(BaseModel):
    reply: str
    session_id: str
    user_type: str  # "guest" or "registered"
    verified: bool


# ── Auth ──────────────────────────────────────────────

class LoginRequest(BaseModel):
    phone: str
    session_id: Optional[str] = None


class LoginResponse(BaseModel):
    success: bool
    message: str
    session_id: str


class OTPVerifyRequest(BaseModel):
    phone: str
    otp: str
    session_id: str


class OTPVerifyResponse(BaseModel):
    success: bool
    message: str
    patient_name: Optional[str] = None
    patient_code: Optional[str] = None


# ── WebSocket Messages ───────────────────────────────

class WSMessage(BaseModel):
    type: str  # "chat", "login", "verify_otp", "ping"
    data: dict = {}
