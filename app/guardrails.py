import re
from typing import Tuple


# Patterns that indicate medical advice requests
MEDICAL_ADVICE_PATTERNS = [
    r"what (?:medicine|medication|drug|pill|tablet) should I (?:take|use)",
    r"(?:diagnose|diagnosis)",
    r"(?:prescribe|prescription) (?:me|for)",
    r"am I (?:sick|ill|infected|dying)",
    r"is it (?:cancer|tumor|serious|fatal|dangerous)",
    r"what (?:disease|illness|condition) do I have",
    r"should I (?:go to|visit) (?:the )?(?:doctor|hospital|emergency|ER)",
    r"home remed(?:y|ies) for",
]

# Compile patterns
COMPILED_PATTERNS = [re.compile(p, re.IGNORECASE) for p in MEDICAL_ADVICE_PATTERNS]


def check_input_safety(user_message: str) -> Tuple[bool, str]:
    """
    Check if user input contains potential prompt injection or harmful content.

    Returns (is_safe, warning_message)
    """
    lower_msg = user_message.lower()

    # Check for prompt injection attempts
    injection_patterns = [
        "ignore previous instructions",
        "ignore your instructions",
        "forget your rules",
        "you are now",
        "new instructions:",
        "system prompt:",
        "override:",
    ]

    for pattern in injection_patterns:
        if pattern in lower_msg:
            return True, ""  # Don't block, but the LLM's system prompt should handle this

    return True, ""


def check_response_safety(response: str, user_type: str) -> str:
    """
    Filter the response for safety concerns.
    Returns the (possibly modified) response.
    """
    # For guest users, mask any accidentally included patient-specific information
    if user_type == "guest":
        # Simple pattern matching for patient codes
        response = re.sub(r"CGH-\d{5}", "[REDACTED]", response)
        # Mask phone numbers in responses
        response = re.sub(r"\b\d{10}\b", "[REDACTED]", response)

    return response


MEDICAL_ADVICE_REFUSAL = (
    "I'm not qualified to provide medical advice, diagnoses, or treatment recommendations. "
    "For any medical concerns, please:\n"
    "- **Visit our OPD** during working hours (Mon-Sat, 9 AM - 6 PM)\n"
    "- **Call Emergency** at +91-11-2345-6700 if it's urgent\n"
    "- **Consult a doctor** through our appointment booking system\n\n"
    "Would you like me to help you find a doctor or book an appointment instead?"
)
