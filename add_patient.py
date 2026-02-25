import sys
from app.database import SessionLocal
from app.models import Patient

def add_test_patient():
    print("🏥 Add Test Patient for Auto-Login")
    print("==================================")
    
    name = input("Enter Patient Name: ").strip()
    if not name:
        print("Name is required.")
        return

    phone = input("Enter Phone Number (10 digits): ").strip()
    if len(phone) != 10 or not phone.isdigit():
        print("Invalid phone number. Must be 10 digits.")
        return

    db = SessionLocal()
    
    # Check if exists
    existing = db.query(Patient).filter(Patient.phone == phone).first()
    if existing:
        print(f"\n✅ Patient found: {existing.name}")
        # Optional: Add test appointment for existing patient
        print("\nWould you like to add a test appointment for tomorrow?")
        add_appt = input("Add appointment? (y/n): ").lower()

        if add_appt == 'y':
            from app.models import Doctor, Appointment
            from datetime import datetime, timedelta
            import random

            doctor = db.query(Doctor).first()
            if doctor:
                tomorrow = (datetime.now() + timedelta(days=1)).strftime("%Y-%m-%d")
                appt = Appointment(
                    patient_id=existing.id,
                    doctor_id=doctor.id,
                    date=tomorrow,
                    time_slot="10:00 AM",
                    status="scheduled",
                    reason="Routine Checkup"
                )
                db.add(appt)
                db.commit()
                print(f"✅ Added appointment with {doctor.name} for {tomorrow} at 10:00 AM")
            else:
                print("⚠️ No doctors found in DB to assign appointment.")
        
        db.close()
        return

    # Create new
    patient = Patient(
        name=name,
        phone=phone,
        date_of_birth="1990-01-01",  # Dummy
        patient_code=f"CGH-{phone[-4:]}",
        gender="Unknown",
        blood_group="Unknown",
        address="Test Address"
    )
    
    try:
        db.add(patient)
        db.flush()  # Get ID

        print(f"\n✅ Successfully added patient: {name} ({phone})")

        # Optional: Add test appointment
        print("\nWould you like to add a test appointment for tomorrow?")
        add_appt = input("Add appointment? (y/n): ").lower()

        if add_appt == 'y':
            from app.models import Doctor, Appointment
            from datetime import datetime, timedelta
            import random

            doctor = db.query(Doctor).first()
            if doctor:
                tomorrow = (datetime.now() + timedelta(days=1)).strftime("%Y-%m-%d")
                appt = Appointment(
                    patient_id=patient.id,
                    doctor_id=doctor.id,
                    date=tomorrow,
                    time_slot="10:00 AM",
                    status="scheduled",
                    reason="Routine Checkup"
                )
                db.add(appt)
                print(f"✅ Added appointment with {doctor.name} for {tomorrow} at 10:00 AM")
            else:
                print("⚠️ No doctors found in DB to assign appointment.")

        db.commit()
        print("\nYou can now call the bot and it should auto-login and mention the appointment!")

    except Exception as e:
        print(f"\n❌ Error adding patient/appointment: {e}")
        db.rollback()
    finally:
        db.close()

if __name__ == "__main__":
    add_test_patient()
