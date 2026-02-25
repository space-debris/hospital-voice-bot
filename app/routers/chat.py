import json
from fastapi import APIRouter, WebSocket, WebSocketDisconnect, Depends
from sqlalchemy.orm import Session
from app.database import get_db
from app.schemas import ChatRequest, ChatResponse
from app.services.orchestrator import orchestrator
from app.services.session_store import session_store
from app.services.auth_service import auth_service

router = APIRouter(tags=["Chat"])


@router.post("/chat", response_model=ChatResponse)
async def chat(request: ChatRequest, db: Session = Depends(get_db)):
    """REST endpoint for chat messages."""
    result = await orchestrator.process_message(
        user_message=request.message,
        session_id=request.session_id,
        db=db,
    )
    return ChatResponse(**result)


@router.websocket("/ws/chat")
async def websocket_chat(websocket: WebSocket, db: Session = Depends(get_db)):
    """WebSocket endpoint for real-time chat."""
    await websocket.accept()

    session_id = None

    try:
        while True:
            # Receive message
            raw_data = await websocket.receive_text()
            data = json.loads(raw_data)

            msg_type = data.get("type", "chat")

            if msg_type == "ping":
                await websocket.send_json({"type": "pong"})
                continue

            if msg_type == "init":
                # Client sends session_id if it has one
                session_id = data.get("session_id")
                session = session_store.get_or_create_session(session_id)
                session_id = session["session_id"]
                await websocket.send_json({
                    "type": "init",
                    "session_id": session_id,
                    "user_type": session.get("user_type", "guest"),
                    "verified": session.get("verified", False),
                    "patient_name": session.get("patient_name"),
                })
                continue

            if msg_type == "login":
                phone = data.get("phone", "")
                # Look up patient
                patient = auth_service.lookup_patient(db, phone)
                if patient:
                    otp = auth_service.generate_otp(phone)
                    session = session_store.get_or_create_session(session_id)
                    session_id = session["session_id"]
                    session_store.update_session(session_id, phone=phone)
                    await websocket.send_json({
                        "type": "login_response",
                        "success": True,
                        "message": f"OTP has been sent to {phone[:3]}****{phone[-3:]}. Please enter it to verify.",
                        "session_id": session_id,
                    })
                else:
                    await websocket.send_json({
                        "type": "login_response",
                        "success": False,
                        "message": "This phone number is not registered with us. Please visit the hospital to register or call our helpline.",
                    })
                continue

            if msg_type == "verify_otp":
                phone = data.get("phone", "")
                otp = data.get("otp", "")
                success, message = auth_service.verify_otp(phone, otp)

                if success:
                    patient = auth_service.lookup_patient(db, phone)
                    if patient and session_id:
                        session_store.upgrade_to_registered(
                            session_id,
                            patient_id=patient.id,
                            patient_name=patient.name,
                            patient_code=patient.patient_code,
                            phone=phone,
                        )
                        await websocket.send_json({
                            "type": "otp_response",
                            "success": True,
                            "message": f"Welcome back, {patient.name}! You're now verified.",
                            "patient_name": patient.name,
                            "patient_code": patient.patient_code,
                        })
                    else:
                        await websocket.send_json({
                            "type": "otp_response",
                            "success": False,
                            "message": "Verification failed. Please try again.",
                        })
                else:
                    await websocket.send_json({
                        "type": "otp_response",
                        "success": False,
                        "message": message,
                    })
                continue

            if msg_type == "chat":
                user_message = data.get("message", "").strip()
                if not user_message:
                    continue

                # Send typing indicator
                await websocket.send_json({"type": "typing", "status": True})

                # Process through orchestrator
                result = await orchestrator.process_message(
                    user_message=user_message,
                    session_id=session_id,
                    db=db,
                )
                session_id = result["session_id"]

                # Send response
                await websocket.send_json({
                    "type": "chat_response",
                    "reply": result["reply"],
                    "session_id": result["session_id"],
                    "user_type": result["user_type"],
                    "verified": result["verified"],
                })
                continue

    except WebSocketDisconnect:
        print(f"WebSocket disconnected: session {session_id}")
    except Exception as e:
        print(f"WebSocket error: {e}")
        try:
            await websocket.send_json({"type": "error", "message": "An error occurred. Please refresh."})
        except Exception:
            pass
