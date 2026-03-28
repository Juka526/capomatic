"""Database-backed result cache with TTL and hit counting."""
from __future__ import annotations

import hashlib
from datetime import datetime, timedelta, timezone

from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession

from backend.db.models import Cache

DEFAULT_TTL_HOURS = 72

_instance: CacheManager | None = None


class CacheManager:
    """Check / save transposition results to avoid redundant OCR + render."""

    @staticmethod
    def generate_cache_key(
        image_hash: str,
        semitones: int,
        mode: str,
    ) -> str:
        """Deterministic SHA-256 key from input parameters."""
        raw = f"{image_hash}:{semitones}:{mode}"
        return hashlib.sha256(raw.encode()).hexdigest()

    async def check_cache(
        self,
        db: AsyncSession,
        image_hash: str,
        semitones: int,
        mode: str,
    ) -> dict | None:
        """Return cached result dict if valid, or None."""
        key = self.generate_cache_key(image_hash, semitones, mode)
        result = await db.execute(select(Cache).where(Cache.cache_key == key))
        entry = result.scalar_one_or_none()

        if entry is None:
            return None

        # TTL check
        if entry.expires_at and entry.expires_at < datetime.now(timezone.utc):
            await db.delete(entry)
            await db.commit()
            return None

        # Bump hit count
        await db.execute(
            update(Cache)
            .where(Cache.id == entry.id)
            .values(hit_count=Cache.hit_count + 1)
        )
        await db.commit()

        return {
            "output_path": entry.output_path,
            "chords": entry.chords,
            "original_key": entry.original_key,
            "target_key": entry.target_key,
        }

    async def save_to_cache(
        self,
        db: AsyncSession,
        image_hash: str,
        semitones: int,
        mode: str,
        original_key: str | None,
        target_key: str | None,
        chords: list[dict] | None,
        output_path: str | None,
        ttl_hours: int = DEFAULT_TTL_HOURS,
    ) -> Cache:
        """Insert a new cache entry and return the model."""
        key = self.generate_cache_key(image_hash, semitones, mode)
        entry = Cache(
            cache_key=key,
            image_hash=image_hash,
            semitones=semitones,
            mode=mode,
            original_key=original_key,
            target_key=target_key,
            chords=chords,
            output_path=output_path,
            expires_at=datetime.now(timezone.utc) + timedelta(hours=ttl_hours),
        )
        db.add(entry)
        await db.commit()
        await db.refresh(entry)
        return entry


def get_cache_manager() -> CacheManager:
    """Return the singleton CacheManager instance."""
    global _instance
    if _instance is None:
        _instance = CacheManager()
    return _instance
