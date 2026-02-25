import json
from sqlalchemy.orm import Session
from app.database import SessionLocal, init_db
from app.models import Department, Doctor, Patient, Appointment, LabReport, BillingRecord


def seed_database():
    """Populate the database with realistic mock hospital data."""
    init_db()
    db: Session = SessionLocal()

    # Check if already seeded
    if db.query(Department).first():
        print("Database already seeded. Skipping.")
        db.close()
        return

    print("Seeding database with mock hospital data...")

    # ── Departments ──────────────────────────────────
    departments = [
        Department(
            name="General Medicine",
            floor="Ground Floor",
            phone_ext="101",
            description="Comprehensive primary care and internal medicine services.",
            opd_timings="Mon-Sat: 9:00 AM - 5:00 PM",
        ),
        Department(
            name="Cardiology",
            floor="2nd Floor",
            phone_ext="201",
            description="Heart and cardiovascular disease diagnosis and treatment.",
            opd_timings="Mon-Fri: 9:00 AM - 4:00 PM",
        ),
        Department(
            name="Orthopedics",
            floor="3rd Floor",
            phone_ext="301",
            description="Bone, joint, and musculoskeletal care including trauma and sports injuries.",
            opd_timings="Mon-Sat: 10:00 AM - 4:00 PM",
        ),
        Department(
            name="Pediatrics",
            floor="1st Floor",
            phone_ext="102",
            description="Medical care for infants, children, and adolescents.",
            opd_timings="Mon-Sat: 9:00 AM - 6:00 PM",
        ),
        Department(
            name="ENT",
            floor="2nd Floor",
            phone_ext="202",
            description="Ear, Nose, and Throat specialist services including audiology.",
            opd_timings="Mon-Fri: 10:00 AM - 3:00 PM",
        ),
        Department(
            name="Dermatology",
            floor="1st Floor",
            phone_ext="103",
            description="Skin, hair, and nail disease treatment and cosmetic dermatology.",
            opd_timings="Mon-Fri: 9:00 AM - 2:00 PM",
        ),
        Department(
            name="Neurology",
            floor="3rd Floor",
            phone_ext="302",
            description="Brain, spinal cord, and nervous system disorders.",
            opd_timings="Mon-Fri: 9:00 AM - 3:00 PM",
        ),
        Department(
            name="Oncology",
            floor="4th Floor",
            phone_ext="401",
            description="Cancer diagnosis, treatment, and supportive care.",
            opd_timings="Mon-Fri: 9:00 AM - 4:00 PM",
        ),
    ]
    db.add_all(departments)
    db.flush()

    dept_map = {d.name: d.id for d in departments}

    # ── Doctors ──────────────────────────────────────
    doctors = [
        Doctor(
            name="Dr. Ananya Sharma",
            department_id=dept_map["General Medicine"],
            specialization="Internal Medicine, Diabetes Management",
            qualification="MBBS, MD (Internal Medicine)",
            experience_years=12,
            schedule=json.dumps({"Mon": "9:00-13:00", "Tue": "9:00-13:00", "Wed": "9:00-13:00", "Thu": "9:00-13:00", "Fri": "9:00-13:00"}),
            consultation_fee=500,
        ),
        Doctor(
            name="Dr. Rajesh Patel",
            department_id=dept_map["General Medicine"],
            specialization="General Practice, Preventive Medicine",
            qualification="MBBS, DNB (Family Medicine)",
            experience_years=8,
            schedule=json.dumps({"Mon": "14:00-17:00", "Tue": "14:00-17:00", "Wed": "14:00-17:00", "Thu": "14:00-17:00", "Sat": "9:00-13:00"}),
            consultation_fee=400,
        ),
        Doctor(
            name="Dr. Vikram Mehta",
            department_id=dept_map["Cardiology"],
            specialization="Interventional Cardiology, Heart Failure",
            qualification="MBBS, MD, DM (Cardiology)",
            experience_years=18,
            schedule=json.dumps({"Mon": "9:00-14:00", "Wed": "9:00-14:00", "Fri": "9:00-14:00"}),
            consultation_fee=1200,
        ),
        Doctor(
            name="Dr. Priya Krishnan",
            department_id=dept_map["Cardiology"],
            specialization="Echocardiography, Preventive Cardiology",
            qualification="MBBS, MD (Cardiology)",
            experience_years=10,
            schedule=json.dumps({"Tue": "9:00-13:00", "Thu": "9:00-13:00", "Sat": "9:00-12:00"}),
            consultation_fee=1000,
        ),
        Doctor(
            name="Dr. Suresh Reddy",
            department_id=dept_map["Orthopedics"],
            specialization="Joint Replacement, Sports Medicine",
            qualification="MBBS, MS (Orthopedics), Fellowship in Joint Replacement",
            experience_years=15,
            schedule=json.dumps({"Mon": "10:00-14:00", "Tue": "10:00-14:00", "Thu": "10:00-14:00", "Sat": "10:00-13:00"}),
            consultation_fee=800,
        ),
        Doctor(
            name="Dr. Meera Iyer",
            department_id=dept_map["Pediatrics"],
            specialization="Neonatology, General Pediatrics",
            qualification="MBBS, MD (Pediatrics), Fellowship in Neonatology",
            experience_years=14,
            schedule=json.dumps({"Mon": "9:00-14:00", "Tue": "9:00-14:00", "Wed": "9:00-14:00", "Thu": "9:00-14:00", "Fri": "9:00-14:00", "Sat": "9:00-12:00"}),
            consultation_fee=600,
        ),
        Doctor(
            name="Dr. Arjun Nair",
            department_id=dept_map["Pediatrics"],
            specialization="Pediatric Pulmonology, Allergies",
            qualification="MBBS, DCH, DNB (Pediatrics)",
            experience_years=7,
            schedule=json.dumps({"Mon": "14:00-18:00", "Wed": "14:00-18:00", "Fri": "14:00-18:00"}),
            consultation_fee=500,
        ),
        Doctor(
            name="Dr. Kavya Deshmukh",
            department_id=dept_map["ENT"],
            specialization="Otology, Cochlear Implants",
            qualification="MBBS, MS (ENT), Fellowship in Otology",
            experience_years=11,
            schedule=json.dumps({"Mon": "10:00-14:00", "Wed": "10:00-14:00", "Fri": "10:00-14:00"}),
            consultation_fee=700,
        ),
        Doctor(
            name="Dr. Rohan Gupta",
            department_id=dept_map["Dermatology"],
            specialization="Clinical Dermatology, Cosmetology",
            qualification="MBBS, MD (Dermatology)",
            experience_years=9,
            schedule=json.dumps({"Mon": "9:00-13:00", "Tue": "9:00-13:00", "Wed": "9:00-13:00", "Thu": "9:00-13:00", "Fri": "9:00-13:00"}),
            consultation_fee=600,
        ),
        Doctor(
            name="Dr. Sunita Joshi",
            department_id=dept_map["Neurology"],
            specialization="Stroke, Epilepsy, Movement Disorders",
            qualification="MBBS, MD, DM (Neurology)",
            experience_years=16,
            schedule=json.dumps({"Tue": "9:00-13:00", "Thu": "9:00-13:00", "Sat": "9:00-12:00"}),
            consultation_fee=1100,
        ),
        Doctor(
            name="Dr. Anil Kapoor",
            department_id=dept_map["Neurology"],
            specialization="Headache Medicine, Neuromuscular Disorders",
            qualification="MBBS, MD (Neurology)",
            experience_years=6,
            schedule=json.dumps({"Mon": "9:00-13:00", "Wed": "9:00-13:00", "Fri": "9:00-13:00"}),
            consultation_fee=800,
        ),
        Doctor(
            name="Dr. Fatima Sheikh",
            department_id=dept_map["Oncology"],
            specialization="Medical Oncology, Breast Cancer",
            qualification="MBBS, MD, DM (Medical Oncology)",
            experience_years=13,
            schedule=json.dumps({"Mon": "9:00-14:00", "Tue": "9:00-14:00", "Wed": "9:00-14:00", "Thu": "9:00-14:00", "Fri": "9:00-14:00"}),
            consultation_fee=1500,
        ),
        Doctor(
            name="Dr. Karan Singh",
            department_id=dept_map["Orthopedics"],
            specialization="Spine Surgery, Trauma",
            qualification="MBBS, MS (Orthopedics), MCh (Spine Surgery)",
            experience_years=20,
            schedule=json.dumps({"Mon": "14:00-17:00", "Wed": "14:00-17:00", "Fri": "14:00-17:00"}),
            consultation_fee=1000,
        ),
        Doctor(
            name="Dr. Lakshmi Menon",
            department_id=dept_map["Dermatology"],
            specialization="Pediatric Dermatology, Psoriasis",
            qualification="MBBS, DVD, DNB (Dermatology)",
            experience_years=8,
            schedule=json.dumps({"Tue": "9:00-13:00", "Thu": "9:00-13:00", "Sat": "9:00-12:00"}),
            consultation_fee=500,
        ),
        Doctor(
            name="Dr. Nikhil Verma",
            department_id=dept_map["ENT"],
            specialization="Rhinology, Sinus Surgery",
            qualification="MBBS, DNB (ENT)",
            experience_years=5,
            schedule=json.dumps({"Tue": "10:00-14:00", "Thu": "10:00-14:00", "Sat": "10:00-13:00"}),
            consultation_fee=600,
        ),
    ]
    db.add_all(doctors)
    db.flush()

    doc_map = {d.name: d.id for d in doctors}

    # ── Patients ─────────────────────────────────────
    patients = [
        Patient(
            name="Amit Kumar",
            phone="9876543210",
            date_of_birth="1985-03-15",
            patient_code="CGH-10001",
            gender="Male",
            blood_group="B+",
            address="42, MG Road, Sector 14, Gurgaon",
        ),
        Patient(
            name="Sneha Verma",
            phone="9876543211",
            date_of_birth="1992-07-22",
            patient_code="CGH-10002",
            gender="Female",
            blood_group="A+",
            address="15, Lajpat Nagar, New Delhi",
        ),
        Patient(
            name="Ravi Shankar",
            phone="9876543212",
            date_of_birth="1978-11-05",
            patient_code="CGH-10003",
            gender="Male",
            blood_group="O+",
            address="7, Jubilee Hills, Hyderabad",
        ),
        Patient(
            name="Deepa Nair",
            phone="9876543213",
            date_of_birth="2001-01-30",
            patient_code="CGH-10004",
            gender="Female",
            blood_group="AB+",
            address="23, Koramangala, Bangalore",
        ),
        Patient(
            name="Mahesh Choudhary",
            phone="9876543214",
            date_of_birth="1968-09-18",
            patient_code="CGH-10005",
            gender="Male",
            blood_group="O-",
            address="88, Civil Lines, Jaipur",
        ),
    ]
    db.add_all(patients)
    db.flush()

    pat_map = {p.name: p.id for p in patients}

    # ── Appointments ─────────────────────────────────
    appointments = [
        Appointment(
            patient_id=pat_map["Amit Kumar"],
            doctor_id=doc_map["Dr. Ananya Sharma"],
            date="2026-02-12",
            time_slot="10:00 AM",
            status="scheduled",
            reason="Routine diabetes follow-up",
        ),
        Appointment(
            patient_id=pat_map["Amit Kumar"],
            doctor_id=doc_map["Dr. Vikram Mehta"],
            date="2026-02-14",
            time_slot="11:00 AM",
            status="scheduled",
            reason="Annual cardiac check-up",
        ),
        Appointment(
            patient_id=pat_map["Sneha Verma"],
            doctor_id=doc_map["Dr. Meera Iyer"],
            date="2026-02-11",
            time_slot="9:30 AM",
            status="scheduled",
            reason="Child vaccination",
        ),
        Appointment(
            patient_id=pat_map["Ravi Shankar"],
            doctor_id=doc_map["Dr. Suresh Reddy"],
            date="2026-02-10",
            time_slot="10:00 AM",
            status="completed",
            reason="Knee pain follow-up",
        ),
        Appointment(
            patient_id=pat_map["Deepa Nair"],
            doctor_id=doc_map["Dr. Rohan Gupta"],
            date="2026-02-13",
            time_slot="11:00 AM",
            status="scheduled",
            reason="Acne treatment consultation",
        ),
    ]
    db.add_all(appointments)

    # ── Lab Reports ──────────────────────────────────
    lab_reports = [
        LabReport(
            patient_id=pat_map["Amit Kumar"],
            test_name="HbA1c (Glycated Hemoglobin)",
            status="ready",
            ordered_date="2026-02-05",
            result_date="2026-02-07",
            department="Pathology",
        ),
        LabReport(
            patient_id=pat_map["Amit Kumar"],
            test_name="Lipid Profile",
            status="processing",
            ordered_date="2026-02-09",
            department="Biochemistry",
        ),
        LabReport(
            patient_id=pat_map["Sneha Verma"],
            test_name="Complete Blood Count (CBC)",
            status="ready",
            ordered_date="2026-02-06",
            result_date="2026-02-07",
            department="Hematology",
        ),
        LabReport(
            patient_id=pat_map["Ravi Shankar"],
            test_name="X-Ray Left Knee",
            status="ready",
            ordered_date="2026-02-08",
            result_date="2026-02-09",
            department="Radiology",
        ),
        LabReport(
            patient_id=pat_map["Ravi Shankar"],
            test_name="MRI Left Knee",
            status="pending",
            ordered_date="2026-02-10",
            department="Radiology",
        ),
        LabReport(
            patient_id=pat_map["Mahesh Choudhary"],
            test_name="ECG",
            status="ready",
            ordered_date="2026-02-04",
            result_date="2026-02-04",
            department="Cardiology",
        ),
        LabReport(
            patient_id=pat_map["Mahesh Choudhary"],
            test_name="Thyroid Function Test",
            status="processing",
            ordered_date="2026-02-09",
            department="Pathology",
        ),
    ]
    db.add_all(lab_reports)

    # ── Billing Records ──────────────────────────────
    billing_records = [
        BillingRecord(
            patient_id=pat_map["Amit Kumar"],
            description="Consultation - Dr. Ananya Sharma",
            amount=500,
            status="paid",
            date="2026-01-15",
            payment_method="UPI",
            invoice_number="INV-2026-0101",
        ),
        BillingRecord(
            patient_id=pat_map["Amit Kumar"],
            description="HbA1c Test",
            amount=800,
            status="paid",
            date="2026-02-05",
            payment_method="Card",
            invoice_number="INV-2026-0234",
        ),
        BillingRecord(
            patient_id=pat_map["Amit Kumar"],
            description="Lipid Profile Test",
            amount=1200,
            status="unpaid",
            date="2026-02-09",
            invoice_number="INV-2026-0289",
        ),
        BillingRecord(
            patient_id=pat_map["Sneha Verma"],
            description="Pediatric Consultation - Dr. Meera Iyer",
            amount=600,
            status="paid",
            date="2026-02-01",
            payment_method="Cash",
            invoice_number="INV-2026-0210",
        ),
        BillingRecord(
            patient_id=pat_map["Ravi Shankar"],
            description="Orthopedic Consultation + X-Ray",
            amount=1800,
            status="paid",
            date="2026-02-08",
            payment_method="Insurance",
            invoice_number="INV-2026-0267",
        ),
        BillingRecord(
            patient_id=pat_map["Ravi Shankar"],
            description="MRI Left Knee",
            amount=5500,
            status="unpaid",
            date="2026-02-10",
            invoice_number="INV-2026-0290",
        ),
        BillingRecord(
            patient_id=pat_map["Mahesh Choudhary"],
            description="Cardiology Consultation + ECG",
            amount=1600,
            status="paid",
            date="2026-02-04",
            payment_method="UPI",
            invoice_number="INV-2026-0245",
        ),
    ]
    db.add_all(billing_records)

    db.commit()
    db.close()
    print("Database seeded successfully with mock data!")


if __name__ == "__main__":
    seed_database()
