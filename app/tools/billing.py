from sqlalchemy.orm import Session
from app.models import BillingRecord


def get_billing_summary(db: Session, patient_id: int) -> dict:
    """Get billing summary for a patient."""
    records = db.query(BillingRecord).filter(
        BillingRecord.patient_id == patient_id
    ).order_by(BillingRecord.date.desc()).all()

    if not records:
        return {
            "found": False,
            "message": "No billing records found for your account.",
            "records": [],
        }

    result = []
    total_amount = 0
    total_paid = 0
    total_unpaid = 0

    for rec in records:
        result.append({
            "id": rec.id,
            "description": rec.description,
            "amount": rec.amount,
            "status": rec.status,
            "date": rec.date,
            "payment_method": rec.payment_method,
            "invoice_number": rec.invoice_number,
        })
        total_amount += rec.amount
        if rec.status == "paid":
            total_paid += rec.amount
        else:
            total_unpaid += rec.amount

    return {
        "found": True,
        "total_records": len(result),
        "total_amount": total_amount,
        "total_paid": total_paid,
        "total_outstanding": total_unpaid,
        "records": result,
    }
