"""Bounded in-memory search metadata cache; never stores credentials or raw pages."""

import time
from collections import OrderedDict
from collections.abc import Callable


class SearchCache[K, V]:
    def __init__(
        self, capacity: int, ttl: float = 900, clock: Callable[[], float] = time.monotonic
    ):
        self.capacity, self.ttl, self.clock = capacity, ttl, clock
        self._entries: OrderedDict[K, tuple[float, V]] = OrderedDict()

    def get(self, key: K) -> V | None:
        entry = self._entries.get(key)
        if entry is None:
            return None
        saved, value = entry
        if self.clock() - saved >= self.ttl:
            del self._entries[key]
            return None
        self._entries.move_to_end(key)
        return value

    def put(self, key: K, value: V) -> None:
        self._entries[key] = (self.clock(), value)
        self._entries.move_to_end(key)
        while len(self._entries) > self.capacity:
            self._entries.popitem(last=False)

    def clear(self) -> None:
        self._entries.clear()
