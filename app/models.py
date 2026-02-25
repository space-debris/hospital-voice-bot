from sqlalchemy import Column, Integer, String, Float, Boolean, Date, ForeignKey, Text
from sqlalchemy.orm import relationship
from app.database import Base


class Department(Base):
    __tablename__ = "departments"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(100), unique=True, nullable=False)
    floor = Column(String(20))
    phone_ext = Column(String(20))
    description = Column(Text)
    opd_timings = Column(String(200))

    doctors = relationship("Doctor", back_populates="department")


class Doctor(Base):
    __tablename__ = "doctors"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(100), nullable=False)
    department_id = Column(Integer, ForeignKey("departments.id"))
    specialization = Column(String(200))
    qualification = Column(String(200))
    experience_years = Column(Integer)
    schedule = Column(Text)  # JSON string: {"Mon": "9:00-13:00", "Tue": "14:00-17:00", ...}
    available = Column(Boolean, default=True)
    consultation_fee = Column(Float, default=500.0)

    department = relationship("Department", back_populates="doctors")
    appointments = relationship("Appointment", back_populates="doctor")


class Patient(Base):
    __tablename__ = "patients"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(100), nullable=False)
    phone = Column(String(15), unique=True, nullable=False)
    date_of_birth = Column(String(10))  # YYYY-MM-DD
    patient_code = Column(String(20), unique=True)  # e.g., "CGH-10001"
    gender = Column(String(10))
    blood_group = Column(String(5))
    address = Column(Text)
    registered = Column(Boolean, default=True)

    appointments = relationship("Appointment", back_populates="patient")
    lab_reports = relationship("LabReport", back_populates="patient")
    billing_records = relationship("BillingRecord", back_populates="patient")


class Appointment(Base):
    __tablename__ = "appointments"

    id = Column(Integer, primary_key=True, index=True)
    patient_id = Column(Integer, ForeignKey("patients.id"))
    doctor_id = Column(Integer, ForeignKey("doctors.id"))
    date = Column(String(10), nullable=False)  # YYYY-MM-DD
    time_slot = Column(String(20), nullable=False)  # e.g., "10:00 AM"
    status = Column(String(20), default="scheduled")  # scheduled, completed, cancelled
    reason = Column(String(200))
    notes = Column(Text)

    patient = relationship("Patient", back_populates="appointments")
    doctor = relationship("Doctor", back_populates="appointments")


class LabReport(Base):
    __tablename__ = "lab_reports"

    id = Column(Integer, primary_key=True, index=True)
    patient_id = Column(Integer, ForeignKey("patients.id"))
    test_name = Column(String(100), nullable=False)
    status = Column(String(20), default="pending")  # pending, processing, ready, delivered
    ordered_date = Column(String(10))  # YYYY-MM-DD
    result_date = Column(String(10))  # YYYY-MM-DD (null if not ready)
    department = Column(String(100))
    notes = Column(Text)

    patient = relationship("Patient", back_populates="lab_reports")


class BillingRecord(Base):
    __tablename__ = "billing_records"

    id = Column(Integer, primary_key=True, index=True)
    patient_id = Column(Integer, ForeignKey("patients.id"))
    description = Column(String(200), nullable=False)
    amount = Column(Float, nullable=False)
    status = Column(String(20), default="unpaid")  # unpaid, paid, partially_paid
    date = Column(String(10))  # YYYY-MM-DD
    payment_method = Column(String(50))  # cash, card, insurance, upi
    invoice_number = Column(String(30))

    patient = relationship("Patient", back_populates="billing_records")
