"""Circuit breaker — stop calling OpenAI after consecutive failures."""

import time
from threading import Lock

from app.config import config


class CircuitBreaker:
    """
    If OpenAI fails N times in a row, open circuit for cooldown seconds.
    While open, skip OpenAI and go straight to Anthropic fallback.
    """

    def __init__(self):
        self._failures = 0
        self._opened_at: float | None = None
        self._lock = Lock()

    def record_success(self) -> None:
        with self._lock:
            self._failures = 0
            self._opened_at = None

    def record_failure(self) -> None:
        with self._lock:
            self._failures += 1
            if self._failures >= config.CIRCUIT_BREAKER_THRESHOLD:
                self._opened_at = time.time()

    def is_open(self) -> bool:
        with self._lock:
            if self._opened_at is None:
                return False
            elapsed = time.time() - self._opened_at
            if elapsed >= config.CIRCUIT_BREAKER_COOLDOWN:
                self._failures = 0
                self._opened_at = None
                return False
            return True

    def reset(self) -> None:
        with self._lock:
            self._failures = 0
            self._opened_at = None


openai_circuit = CircuitBreaker()
