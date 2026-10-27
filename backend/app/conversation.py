"""Bounded, expiring topic memory. No raw chat messages or medical histories."""

import time
import uuid
from collections import OrderedDict
from threading import Lock

from app.safety.query import Query


class ConversationStore:
    def __init__(self, limit: int = 1000, ttl: int = 1800):
        self._items = OrderedDict()
        self._lock = Lock()
        self.limit, self.ttl = limit, ttl

    def get(self, session_id: str | None) -> tuple[str, dict]:
        with self._lock:
            now = time.monotonic()
            expired = [
                key for key, (stamp, _) in self._items.items() if now - stamp > self.ttl
            ]
            for key in expired:
                del self._items[key]
            if session_id in self._items:
                stamp, context = self._items.pop(session_id)
                self._items[session_id] = (now, context)
                return session_id, dict(context)
            return str(uuid.uuid4()), {}

    def update(self, session_id: str, query: Query):
        if query.block or not query.topic:
            return
        context = {
            key: getattr(query, key)
            for key in ("topic", "countries", "clinic", "program")
        }
        with self._lock:
            self._items[session_id] = (time.monotonic(), context)
            self._items.move_to_end(session_id)
            while len(self._items) > self.limit:
                self._items.popitem(last=False)
