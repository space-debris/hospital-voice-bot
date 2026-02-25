from sqlalchemy.orm import Session
from app.models import LabReport


def check_report_status(db: Session, patient_id: int) -> dict:
    """Check lab report status for a patient."""
    reports = db.query(LabReport).filter(
        LabReport.patient_id == patient_id
    ).order_by(LabReport.ordered_date.desc()).all()

    if not reports:
        return {
            "found": False,
            "message": "No lab reports found for your account.",
            "reports": [],
        }

    result = []
    for report in reports:
        result.append({
            "id": report.id,
            "test_name": report.test_name,
            "status": report.status,
            "ordered_date": report.ordered_date,
            "result_date": report.result_date,
            "department": report.department,
            "notes": report.notes,
        })

    ready = [r for r in result if r["status"] == "ready"]
    pending = [r for r in result if r["status"] in ("pending", "processing")]

    return {
        "found": True,
        "total": len(result),
        "ready_count": len(ready),
        "pending_count": len(pending),
        "reports": result,
    }
