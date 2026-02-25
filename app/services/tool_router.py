from sqlalchemy.orm import Session
import time
import json
from app.tools.doctor_schedule import search_doctors, get_department_info
from app.tools.appointment import book_appointment, cancel_appointment, list_appointments
from app.tools.reports import check_report_status
from app.tools.billing import get_billing_summary
from app.logger import logger


# ── Tool Registry ────────────────────────────────────
# Define which tools require authentication and their handlers

TOOL_REGISTRY = {
    "search_doctors": {
        "handler": "search_doctors",
        "requires_auth": False,
        "description": "Search for doctors",
    },
    "get_department_info": {
        "handler": "get_department_info",
        "requires_auth": False,
        "description": "Get department information",
    },
    "book_appointment": {
        "handler": "book_appointment",
        "requires_auth": True,
        "description": "Book an appointment",
    },
    "cancel_appointment": {
        "handler": "cancel_appointment",
        "requires_auth": True,
        "description": "Cancel an appointment",
    },
    "list_appointments": {
        "handler": "list_appointments",
        "requires_auth": True,
        "description": "List appointments",
    },
    "check_report_status": {
        "handler": "check_report_status",
        "requires_auth": True,
        "description": "Check lab report status",
    },
    "get_billing_summary": {
        "handler": "get_billing_summary",
        "requires_auth": True,
        "description": "Get billing summary",
    },
}


class ToolRouter:
    """Routes and executes tool calls from the LLM safely."""

    def execute(self, tool_name: str, args: dict, session: dict, db: Session) -> dict:
        """
        Execute a tool call with audit logging.

        Args:
            tool_name: Name of the tool to execute
            args: Arguments from the LLM
            session: Current session data
            db: Database session

        Returns:
            Tool result dict
        """
        start_time = time.time()

        # Check if tool exists
        tool_config = TOOL_REGISTRY.get(tool_name)
        if not tool_config:
            return {"error": True, "message": f"Unknown tool: {tool_name}"}

        # Check authorization
        if tool_config["requires_auth"]:
            if not session.get("verified"):
                return {
                    "error": True,
                    "message": "This action requires authentication. Please login first with your registered phone number.",
                    "requires_login": True,
                }

        try:
            result = self._dispatch(tool_name, args, session, db)
            duration_ms = (time.time() - start_time) * 1000
            success = not result.get("error", False)

            # Audit log
            self._audit(
                db, session, tool_name, args,
                success=success,
                result_summary=json.dumps(result)[:500],
                duration_ms=duration_ms,
            )

            return result
        except Exception as e:
            duration_ms = (time.time() - start_time) * 1000
            logger.error(f"Tool execution error ({tool_name}): {e}")

            # Audit log (failure)
            self._audit(
                db, session, tool_name, args,
                success=False,
                result_summary=str(e)[:500],
                duration_ms=duration_ms,
            )

            return {
                "error": True,
                "message": f"An error occurred while executing {tool_name}. Please try again.",
            }

    def _audit(self, db, session, tool_name, args, success, result_summary, duration_ms):
        """Write an audit log entry (best-effort, never blocks execution)."""
        try:
            from app.services.audit import log_tool_usage
            log_tool_usage(
                db=db,
                session_id=session.get("session_id", ""),
                user_type=session.get("user_type", "guest"),
                patient_id=session.get("patient_id"),
                channel=session.get("channel", "web"),
                tool_name=tool_name,
                tool_args=args,
                success=success,
                result_summary=result_summary,
                duration_ms=duration_ms,
            )
        except Exception as e:
            logger.warning(f"Audit log write failed: {e}")

    def _dispatch(self, tool_name: str, args: dict, session: dict, db: Session) -> dict:
        """Dispatch to the appropriate tool handler."""
        patient_id = session.get("patient_id")

        if tool_name == "search_doctors":
            return search_doctors(
                db,
                department=args.get("department"),
                name=args.get("name"),
                specialization=args.get("specialization"),
            )

        elif tool_name == "get_department_info":
            return get_department_info(db, args.get("department_name", ""))

        elif tool_name == "book_appointment":
            return book_appointment(
                db,
                patient_id=patient_id,
                doctor_name=args.get("doctor_name", ""),
                date=args.get("date", ""),
                time_slot=args.get("time_slot", ""),
                reason=args.get("reason"),
            )

        elif tool_name == "cancel_appointment":
            return cancel_appointment(
                db,
                patient_id=patient_id,
                appointment_id=args.get("appointment_id", 0),
            )

        elif tool_name == "list_appointments":
            return list_appointments(db, patient_id=patient_id)

        elif tool_name == "check_report_status":
            return check_report_status(db, patient_id=patient_id)

        elif tool_name == "get_billing_summary":
            return get_billing_summary(db, patient_id=patient_id)

        else:
            return {"error": True, "message": f"Tool '{tool_name}' is not implemented."}


# Global tool router instance
tool_router = ToolRouter()
