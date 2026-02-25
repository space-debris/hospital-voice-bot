import random
import time
from typing import Optional, Tuple
from sqlalchemy.orm import Session
from app.models import Patient


class AuthService:
    """Handles patient identity lookup and OTP verification."""

    def __init__(self):
        # Store pending OTPs: {phone: {"otp": "123456", "expires": timestamp}}
        self._pending_otps: dict = {}
        self._otp_ttl = 300  # 5 minutes

    def lookup_patient(self, db: Session, phone: str) -> Optional[Patient]:
        """Look up a patient by phone number."""
        return db.query(Patient).filter(Patient.phone == phone).first()

    def generate_otp(self, phone: str) -> str:
        """Generate a 6-digit OTP for the given phone number."""
        otp = str(random.randint(100000, 999999))
        self._pending_otps[phone] = {
            "otp": otp,
            "expires": time.time() + self._otp_ttl,
        }
        # In production, this would send via SMS
        print(f"\n{'='*50}")
        print(f"  OTP for {phone}: {otp}")
        print(f"  (Valid for 5 minutes)")
        print(f"{'='*50}\n")
        return otp

    def verify_otp(self, phone: str, otp: str) -> Tuple[bool, str]:
        """
        Verify the OTP for a phone number.
        Returns (success, message).
        """
        pending = self._pending_otps.get(phone)

        if not pending:
            return False, "No OTP was requested for this number. Please request a new OTP."

        if time.time() > pending["expires"]:
            del self._pending_otps[phone]
            return False, "OTP has expired. Please request a new one."

        if pending["otp"] != otp:
            return False, "Invalid OTP. Please check and try again."

        # OTP verified — clean up
        del self._pending_otps[phone]
        return True, "OTP verified successfully!"

    def cleanup_expired(self):
        """Remove expired OTPs."""
        now = time.time()
        expired = [
            phone for phone, data in self._pending_otps.items()
            if now > data["expires"]
        ]
        for phone in expired:
            del self._pending_otps[phone]


# Global auth service instance
auth_service = AuthService()
