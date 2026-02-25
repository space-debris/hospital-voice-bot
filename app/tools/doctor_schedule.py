import json
from sqlalchemy.orm import Session
from app.models import Doctor, Department


def search_doctors(db: Session, department: str = None, name: str = None, specialization: str = None) -> dict:
    """Search for doctors by department, name, or specialization."""
    query = db.query(Doctor).join(Department)

    if department:
        query = query.filter(Department.name.ilike(f"%{department}%"))
    if name:
        query = query.filter(Doctor.name.ilike(f"%{name}%"))
    if specialization:
        query = query.filter(Doctor.specialization.ilike(f"%{specialization}%"))

    doctors = query.filter(Doctor.available == True).all()

    if not doctors:
        return {"found": False, "message": "No doctors found matching your criteria.", "doctors": []}

    result = []
    for doc in doctors:
        schedule = json.loads(doc.schedule) if doc.schedule else {}
        result.append({
            "id": doc.id,
            "name": doc.name,
            "department": doc.department.name,
            "specialization": doc.specialization,
            "qualification": doc.qualification,
            "experience_years": doc.experience_years,
            "consultation_fee": doc.consultation_fee,
            "schedule": schedule,
        })

    return {
        "found": True,
        "count": len(result),
        "doctors": result,
    }


def get_department_info(db: Session, department_name: str) -> dict:
    """Get detailed information about a department."""
    dept = db.query(Department).filter(
        Department.name.ilike(f"%{department_name}%")
    ).first()

    if not dept:
        # Return all department names as suggestions
        all_depts = db.query(Department.name).all()
        dept_names = [d[0] for d in all_depts]
        return {
            "found": False,
            "message": f"Department '{department_name}' not found.",
            "available_departments": dept_names,
        }

    # Also get doctors in this department
    doctors = db.query(Doctor).filter(
        Doctor.department_id == dept.id,
        Doctor.available == True
    ).all()

    doctor_list = []
    for doc in doctors:
        doctor_list.append({
            "name": doc.name,
            "specialization": doc.specialization,
            "consultation_fee": doc.consultation_fee,
        })

    return {
        "found": True,
        "department": {
            "name": dept.name,
            "floor": dept.floor,
            "phone_extension": dept.phone_ext,
            "opd_timings": dept.opd_timings,
            "description": dept.description,
            "doctors": doctor_list,
        },
    }
