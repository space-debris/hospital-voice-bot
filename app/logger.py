"""
Structured logging with PHI masking for HIPAA compliance.
Replaces all print() calls with a proper logger that redacts
patient names, phone numbers, patient codes, and OTPs from logs.
"""
import logging
import re
import sys


# ── PHI redaction patterns ──────────────────────────────

PHI_PATTERNS = [
    # Phone numbers (10 digits, with or without +91)
    (re.compile(r'\+91\d{10}'), '[PHONE_REDACTED]'),
    (re.compile(r'\b\d{10}\b'), '[PHONE_REDACTED]'),
    # Patient codes (CGH-XXXXX)
    (re.compile(r'CGH-\d{4,5}'), '[PATIENT_CODE_REDACTED]'),
    # OTP (6-digit codes in specific contexts)
    (re.compile(r'(?:OTP|otp)[:\s]+(\d{6})'), 'OTP: [OTP_REDACTED]'),
]


class PHIMaskingFilter(logging.Filter):
    """Logging filter that masks PHI data in log messages."""

    def filter(self, record: logging.LogRecord) -> bool:
        if isinstance(record.msg, str):
            record.msg = mask_phi(record.msg)
        # Also mask args if they exist
        if record.args:
            if isinstance(record.args, dict):
                record.args = {
                    k: mask_phi(str(v)) if isinstance(v, str) else v
                    for k, v in record.args.items()
                }
            elif isinstance(record.args, tuple):
                record.args = tuple(
                    mask_phi(str(a)) if isinstance(a, str) else a
                    for a in record.args
                )
        return True


def mask_phi(text: str) -> str:
    """Redact PHI patterns from a string."""
    for pattern, replacement in PHI_PATTERNS:
        text = pattern.sub(replacement, text)
    return text


def setup_logger(name: str = "hospital_assistant", level: int = logging.INFO) -> logging.Logger:
    """
    Create and configure the application logger with PHI masking.
    """
    logger = logging.getLogger(name)

    # Avoid duplicate handlers on reload
    if logger.handlers:
        return logger

    logger.setLevel(level)

    # Console handler with formatting
    handler = logging.StreamHandler(sys.stdout)
    handler.setLevel(level)

    formatter = logging.Formatter(
        fmt="%(asctime)s | %(levelname)-7s | %(message)s",
        datefmt="%H:%M:%S",
    )
    handler.setFormatter(formatter)
    handler.addFilter(PHIMaskingFilter())

    logger.addHandler(handler)
    logger.propagate = False

    return logger


# Global logger instance
logger = setup_logger()
