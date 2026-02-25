from sqlalchemy.orm import Session
from app.models import Appointment, Doctor, Department


def book_appointment(
    db: Session,
    patient_id: int,
    doctor_name: str,
    date: str,
    time_slot: str,
    reason: str = None,
) -> dict:
    """Book an appointment for a patient with a doctor."""
    # Find the doctor
    doctor = db.query(Doctor).filter(
        Doctor.name.ilike(f"%{doctor_name}%")
    ).first()

    if not doctor:
        return {
            "success": False,
            "message": f"Doctor '{doctor_name}' not found. Please check the name and try again.",
        }

    # Check for duplicate booking
    existing = db.query(Appointment).filter(
        Appointment.patient_id == patient_id,
        Appointment.doctor_id == doctor.id,
        Appointment.date == date,
        Appointment.time_slot == time_slot,
        Appointment.status == "scheduled",
    ).first()

    if existing:
        return {
            "success": False,
            "message": f"You already have an appointment with {doctor.name} on {date} at {time_slot}.",
        }

    # Create appointment
    appointment = Appointment(
        patient_id=patient_id,
        doctor_id=doctor.id,
        date=date,
        time_slot=time_slot,
        status="scheduled",
        reason=reason or "General consultation",
    )
    db.add(appointment)
    db.commit()
    db.refresh(appointment)

    return {
        "success": True,
        "message": "Appointment booked successfully!",
        "appointment": {
            "id": appointment.id,
            "doctor": doctor.name,
            "department": doctor.department.name,
            "date": date,
            "time_slot": time_slot,
            "reason": appointment.reason,
            "consultation_fee": doctor.consultation_fee,
        },
    }


def cancel_appointment(db: Session, patient_id: int, appointment_id: int) -> dict:
    """Cancel an appointment."""
    appointment = db.query(Appointment).filter(
        Appointment.id == appointment_id,
        Appointment.patient_id == patient_id,
    ).first()

    if not appointment:
        return {
            "success": False,
            "message": "Appointment not found or doesn't belong to you.",
        }

    if appointment.status == "cancelled":
        return {
            "success": False,
            "message": "This appointment is already cancelled.",
        }

    if appointment.status == "completed":
        return {
            "success": False,
            "message": "This appointment has already been completed and cannot be cancelled.",
        }

    appointment.status = "cancelled"
    db.commit()

    return {
        "success": True,
        "message": f"Appointment #{appointment_id} with {appointment.doctor.name} on {appointment.date} has been cancelled.",
    }


def list_appointments(db: Session, patient_id: int) -> dict:
    """List all appointments for a patient."""
    appointments = db.query(Appointment).filter(
        Appointment.patient_id == patient_id
    ).order_by(Appointment.date.desc()).all()

    if not appointments:
        return {
            "found": False,
            "message": "You don't have any appointments.",
            "appointments": [],
        }

    result = []
    for apt in appointments:
        result.append({
            "id": apt.id,
            "doctor": apt.doctor.name,
            "department": apt.doctor.department.name,
            "date": apt.date,
            "time_slot": apt.time_slot,
            "status": apt.status,
            "reason": apt.reason,
        })

    scheduled = [a for a in result if a["status"] == "scheduled"]
    return {
        "found": True,
        "total": len(result),
        "upcoming": len(scheduled),
        "appointments": result,
    }
