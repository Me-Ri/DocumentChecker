import logging
import os
import threading
import time


logger = logging.getLogger(__name__)


def _get_requests_per_minute() -> float:
    raw_value = os.getenv("LLM_REQUESTS_PER_MINUTE", "1").strip()
    try:
        return float(raw_value)
    except ValueError:
        logger.warning(
            "Invalid LLM_REQUESTS_PER_MINUTE=%r; falling back to 1 request per minute",
            raw_value,
        )
        return 1.0


class LLMRequestQueue:
    def __init__(self) -> None:
        self._lock = threading.Lock()
        self._next_available_at = 0.0

    def wait_for_turn(self, model: str) -> float:
        requests_per_minute = _get_requests_per_minute()
        if requests_per_minute <= 0:
            return 0.0

        interval_seconds = 60.0 / requests_per_minute
        now = time.monotonic()

        with self._lock:
            scheduled_at = max(now, self._next_available_at)
            self._next_available_at = scheduled_at + interval_seconds

        wait_seconds = scheduled_at - now
        if wait_seconds > 0:
            logger.info(
                "LLM request queued for %.1f seconds: model=%s rpm=%.2f",
                wait_seconds,
                model,
                requests_per_minute,
            )
            time.sleep(wait_seconds)

        return wait_seconds


llm_request_queue = LLMRequestQueue()
