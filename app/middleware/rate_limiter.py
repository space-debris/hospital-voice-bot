"""
Rate limiter middleware — prevents abuse by limiting requests per caller/session.
Uses a simple in-memory token bucket per IP/caller.
"""
import time
from collections import defaultdict
from fastapi import Request, HTTPException
from app.logger import logger


class RateLimiter:
    """
    Simple token-bucket rate limiter.
    
    Args:
        max_requests: Maximum requests allowed in the window
        window_seconds: Time window in seconds
    """

    def __init__(self, max_requests: int = 30, window_seconds: int = 60):
        self.max_requests = max_requests
        self.window_seconds = window_seconds
        self._buckets: dict[str, list[float]] = defaultdict(list)

    def _cleanup(self, key: str) -> None:
        """Remove expired timestamps from the bucket."""
        cutoff = time.time() - self.window_seconds
        self._buckets[key] = [
            t for t in self._buckets[key] if t > cutoff
        ]

    def is_allowed(self, key: str) -> bool:
        """Check if a request is allowed for the given key."""
        self._cleanup(key)
        if len(self._buckets[key]) >= self.max_requests:
            return False
        self._buckets[key].append(time.time())
        return True

    def remaining(self, key: str) -> int:
        """Return how many requests remain in the current window."""
        self._cleanup(key)
        return max(0, self.max_requests - len(self._buckets[key]))


# Global rate limiters for different endpoints
api_limiter = RateLimiter(max_requests=30, window_seconds=60)     # 30 req/min for API
voice_limiter = RateLimiter(max_requests=60, window_seconds=60)   # 60 req/min for voice (higher due to multi-turn)


async def check_api_rate_limit(request: Request) -> None:
    """FastAPI dependency — rate limits based on client IP."""
    client_ip = request.client.host if request.client else "unknown"
    if not api_limiter.is_allowed(client_ip):
        logger.warning(f"🚫 Rate limit exceeded for {client_ip}")
        raise HTTPException(
            status_code=429,
            detail="Too many requests. Please slow down.",
        )


async def check_voice_rate_limit(request: Request) -> None:
    """FastAPI dependency — rate limits Twilio voice webhooks by caller."""
    form = await request.form()
    caller = form.get("From", "unknown")
    if not voice_limiter.is_allowed(caller):
        logger.warning(f"🚫 Voice rate limit exceeded for caller")
        raise HTTPException(
            status_code=429,
            detail="Too many requests.",
        )
