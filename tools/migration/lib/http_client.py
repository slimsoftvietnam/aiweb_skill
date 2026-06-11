"""HTTP client with retry, rate limit, and browser User-Agent."""

from __future__ import annotations

import time
from typing import Optional

import httpx

DEFAULT_UA = "Mozilla/5.0 (compatible; AiwebMigration/1.0; +https://slimcrm.vn)"
DEFAULT_TIMEOUT = 30.0
DEFAULT_DELAY = 0.35


class HttpClient:
    def __init__(
        self,
        delay: float = DEFAULT_DELAY,
        timeout: float = DEFAULT_TIMEOUT,
        max_retries: int = 3,
    ) -> None:
        self.delay = delay
        self.timeout = timeout
        self.max_retries = max_retries
        self._last_request = 0.0
        self.client = httpx.Client(
            headers={"User-Agent": DEFAULT_UA},
            follow_redirects=True,
            timeout=timeout,
        )

    def close(self) -> None:
        self.client.close()

    def __enter__(self) -> "HttpClient":
        return self

    def __exit__(self, *args: object) -> None:
        self.close()

    def _throttle(self) -> None:
        elapsed = time.monotonic() - self._last_request
        if elapsed < self.delay:
            time.sleep(self.delay - elapsed)
        self._last_request = time.monotonic()

    def get_text(self, url: str) -> str:
        return self.get_bytes(url).decode("utf-8", errors="replace")

    def get_bytes(self, url: str) -> bytes:
        last_error: Optional[Exception] = None
        for attempt in range(self.max_retries):
            self._throttle()
            try:
                resp = self.client.get(url)
                resp.raise_for_status()
                return resp.content
            except Exception as exc:  # noqa: BLE001
                last_error = exc
                if attempt < self.max_retries - 1:
                    time.sleep(1.5 * (attempt + 1))
        raise RuntimeError(f"GET failed after {self.max_retries} tries: {url}") from last_error
