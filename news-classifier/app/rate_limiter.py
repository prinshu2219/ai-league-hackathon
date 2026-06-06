"""User-side rate limiting by tier — checked BEFORE calling the LLM."""

from collections import defaultdict
from datetime import datetime, timedelta
from threading import Lock

from app.config import config


class RateLimiter:
    """
    Token-bucket style limiter per user_id.
    Free tier: 10 RPM | Paid tier: 100 RPM (configurable via env).
    """

    def __init__(self):
        self._requests: dict[str, list[datetime]] = defaultdict(list)
        self._lock = Lock()
        self._tier_limits = {
            "free": config.FREE_TIER_RPM,
            "paid": config.PAID_TIER_RPM,
        }

    def check(self, user_id: str, tier: str = "free") -> tuple[bool, int]:
        """
        Returns (allowed, remaining_requests_this_minute).
        """
        limit = self._tier_limits.get(tier, config.FREE_TIER_RPM)
        now = datetime.now()
        cutoff = now - timedelta(minutes=1)

        with self._lock:
            recent = [t for t in self._requests[user_id] if t > cutoff]
            self._requests[user_id] = recent

            if len(recent) >= limit:
                return False, 0

            self._requests[user_id].append(now)
            return True, limit - len(recent)

    def reset(self) -> None:
        """For testing."""
        with self._lock:
            self._requests.clear()


rate_limiter = RateLimiter()
