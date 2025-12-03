"""In-memory rolling counter for FoxESS Cloud API calls."""

from __future__ import annotations

import asyncio
from collections.abc import Mapping
from datetime import datetime, timedelta, timezone


class ApiCallTracker:
    """Track API calls in a rolling 24 hour window."""

    def __init__(self) -> None:
        self._buckets: dict[int, int] = {}
        self._lock = asyncio.Lock()

    async def record_call(self, *, now: datetime | None = None) -> None:
        """Record a single API call occurrence."""

        timestamp = now or datetime.now(timezone.utc)
        bucket = self._bucket_for(timestamp)

        async with self._lock:
            self._buckets[bucket] = self._buckets.get(bucket, 0) + 1
            self._prune_locked(timestamp)

    async def count_last_24h(self, *, now: datetime | None = None) -> int:
        """Return the number of calls made in the last 24 hours."""

        timestamp = now or datetime.now(timezone.utc)
        cutoff_bucket = self._bucket_for(timestamp - timedelta(hours=24))

        async with self._lock:
            self._prune_locked(timestamp)
            return sum(
                count for bucket, count in self._buckets.items() if bucket >= cutoff_bucket
            )

    async def snapshot_buckets(self) -> Mapping[int, int]:
        """Return a copy of the internal bucket map for diagnostics."""

        async with self._lock:
            return dict(self._buckets)

    @staticmethod
    def _bucket_for(timestamp: datetime) -> int:
        return int(timestamp.timestamp() // 3600)

    def _prune_locked(self, now: datetime) -> None:
        cutoff_bucket = self._bucket_for(now - timedelta(hours=24))
        stale = [bucket for bucket in self._buckets if bucket < cutoff_bucket]
        for bucket in stale:
            del self._buckets[bucket]
