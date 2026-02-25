from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from app.database import get_db
from app.schemas import LoginRequest, LoginResponse, OTPVerifyRequest, OTPVerifyResponse
from app.services.auth_service import auth_service
from app.services.session_store import session_store

router = APIRouter(prefix="/auth", tags=["Authentication"])


@router.post("/login", response_model=LoginResponse)
async def login(request: LoginRequest, db: Session = Depends(get_db)):
    """Send OTP to a registered phone number."""
    session = session_store.get_or_create_session(request.session_id)
    session_id = session["session_id"]

    patient = auth_service.lookup_patient(db, request.phone)
    if not patient:
        return LoginResponse(
            success=False,
            message="This phone number is not registered. Please visit the hospital to register.",
            session_id=session_id,
        )

    otp = auth_service.generate_otp(request.phone)
    session_store.update_session(session_id, phone=request.phone)

    return LoginResponse(
        success=True,
        message=f"OTP sent to {request.phone[:3]}****{request.phone[-3:]}",
        session_id=session_id,
    )


@router.post("/verify-otp", response_model=OTPVerifyResponse)
async def verify_otp(request: OTPVerifyRequest, db: Session = Depends(get_db)):
    """Verify OTP and upgrade session to registered."""
    success, message = auth_service.verify_otp(request.phone, request.otp)

    if not success:
        return OTPVerifyResponse(success=False, message=message)

    patient = auth_service.lookup_patient(db, request.phone)
    if patient:
        session_store.upgrade_to_registered(
            request.session_id,
            patient_id=patient.id,
            patient_name=patient.name,
            patient_code=patient.patient_code,
            phone=request.phone,
        )
        return OTPVerifyResponse(
            success=True,
            message=f"Welcome back, {patient.name}!",
            patient_name=patient.name,
            patient_code=patient.patient_code,
        )

    return OTPVerifyResponse(success=False, message="Patient not found.")
