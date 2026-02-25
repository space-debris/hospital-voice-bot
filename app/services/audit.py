"""
Audit trail — logs every tool invocation for compliance and traceability.
Stores: who called what, with which args, when, and the result.
"""
import time
from datetime import datetime
from sqlalchemy import Column, Integer, String, Float, Text, create_engine
from sqlalchemy.orm import Session
from app.database import Base
from app.logger import logger


class AuditLog(Base):
    """Stores a log entry for each tool invocation."""
    __tablename__ = "audit_logs"

    id = Column(Integer, primary_key=True, index=True)
    timestamp = Column(String(30), nullable=False)
    session_id = Column(String(50))
    user_type = Column(String(20))        # guest / registered
    patient_id = Column(Integer, nullable=True)
    channel = Column(String(20))          # web / voice
    tool_name = Column(String(50), nullable=False)
    tool_args = Column(Text)              # JSON string of arguments
    success = Column(String(10))          # true / false
    result_summary = Column(Text)         # brief result or error
    duration_ms = Column(Float)           # execution time


def log_tool_usage(
    db: Session,
    session_id: str,
    user_type: str,
    patient_id: int | None,
    channel: str,
    tool_name: str,
    tool_args: dict,
    success: bool,
    result_summary: str,
    duration_ms: float,
) -> None:
    """Write an audit log entry to the database."""
    import json

    entry = AuditLog(
        timestamp=datetime.now().isoformat(),
        session_id=session_id,
        user_type=user_type,
        patient_id=patient_id,
        channel=channel,
        tool_name=tool_name,
        tool_args=json.dumps(tool_args),
        success=str(success).lower(),
        result_summary=result_summary[:500] if result_summary else "",
        duration_ms=round(duration_ms, 2),
    )

    try:
        db.add(entry)
        db.commit()
        logger.info(f"📋 Audit: {tool_name} | user={user_type} | success={success} | {duration_ms:.0f}ms")
    except Exception as e:
        logger.error(f"❌ Audit log failed: {e}")
        db.rollback()
