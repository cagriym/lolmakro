from __future__ import annotations

import secrets
import threading
import time
from dataclasses import dataclass


@dataclass
class PairToken:
    expires_at: float
    used: bool = False


class PairingTokenManager:
    def __init__(self, ttl_seconds: int = 600) -> None:
        self.ttl_seconds = ttl_seconds
        self._tokens: dict[str, PairToken] = {}
        self._lock = threading.Lock()

    def create_token(self) -> str:
        token = secrets.token_urlsafe(32)
        with self._lock:
            self._tokens[token] = PairToken(expires_at=time.time() + self.ttl_seconds)
            self._cleanup_locked()
        return token

    def consume_token(self, token: str) -> bool:
        with self._lock:
            item = self._tokens.get(token)
            if not item:
                return False
            now = time.time()
            if item.used or item.expires_at < now:
                self._tokens.pop(token, None)
                return False
            item.used = True
            self._tokens.pop(token, None)
            return True

    def _cleanup_locked(self) -> None:
        now = time.time()
        stale = [t for t, v in self._tokens.items() if v.expires_at < now or v.used]
        for token in stale:
            self._tokens.pop(token, None)


token_manager = PairingTokenManager(ttl_seconds=600)
