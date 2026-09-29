import threading
import time
from collections import deque

# Brute-force protection for /auth/login: after MAX_FAILED_ATTEMPTS wrong
# passwords for one email within WINDOW_SECONDS, further attempts for that
# email are refused until the oldest failure ages out of the window.
# In-memory and per-process: counts reset on restart and aren't shared
# between multiple server processes - adequate for a single instance.

MAX_FAILED_ATTEMPTS = 5
WINDOW_SECONDS = 15 * 60

_failures: dict[str, deque] = {}
_lock = threading.Lock()


def _recent(key: str, now: float) -> deque | None:
    attempts = _failures.get(key)
    if attempts is None:
        return None
    while attempts and now - attempts[0] > WINDOW_SECONDS:
        attempts.popleft()
    if not attempts:
        del _failures[key]
        return None
    return attempts


def retry_after_seconds(key: str) -> int:
    """0 if a login attempt is allowed, else seconds until it will be."""
    with _lock:
        now = time.monotonic()
        attempts = _recent(key, now)
        if attempts is None or len(attempts) < MAX_FAILED_ATTEMPTS:
            return 0
        return int(WINDOW_SECONDS - (now - attempts[0])) + 1


def record_failure(key: str) -> None:
    with _lock:
        now = time.monotonic()
        _recent(key, now)
        _failures.setdefault(key, deque()).append(now)


def reset(key: str) -> None:
    with _lock:
        _failures.pop(key, None)


def clear_all() -> None:
    with _lock:
        _failures.clear()
