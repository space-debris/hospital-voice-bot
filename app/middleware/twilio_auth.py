"""
Twilio request signature validation middleware.
Ensures incoming webhook requests are genuinely from Twilio (prevents spoofing).
"""
from fastapi import Request, HTTPException
from twilio.request_validator import RequestValidator
from app.config import settings
from app.logger import logger


async def validate_twilio_signature(request: Request) -> None:
    """
    Validate that a webhook request is genuinely from Twilio.
    Uses Twilio's X-Twilio-Signature header and request body.
    
    Raises HTTPException 403 if validation fails.
    Skips validation if TWILIO_AUTH_TOKEN is not configured (dev mode).
    """
    auth_token = settings.TWILIO_AUTH_TOKEN
    if not auth_token:
        # Dev mode — skip validation
        return

    validator = RequestValidator(auth_token)

    # Get the signature from headers
    signature = request.headers.get("X-Twilio-Signature", "")
    if not signature:
        logger.warning("⚠️  Missing X-Twilio-Signature header on /voice/* request")
        raise HTTPException(status_code=403, detail="Missing Twilio signature")

    # Reconstruct the full URL (Twilio uses the public URL, not localhost)
    url = str(request.url)
    # If behind ngrok, Twilio sees the ngrok URL
    if settings.NGROK_URL and "localhost" in url:
        path = request.url.path
        url = f"{settings.NGROK_URL}{path}"

    # Get form body for POST validation
    form_data = await request.form()
    params = dict(form_data)

    is_valid = validator.validate(url, params, signature)

    if not is_valid:
        logger.warning(f"⚠️  Invalid Twilio signature for {request.url.path}")
        raise HTTPException(status_code=403, detail="Invalid Twilio signature")
