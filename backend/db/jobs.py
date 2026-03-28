"""Job CRUD operations."""
from __future__ import annotations

import uuid
from datetime import datetime, timezone

from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession

from backend.db.models import Job


async def create_job(
    db: AsyncSession,
    user_id: uuid.UUID,
    *,
    song_name: str | None = None,
    original_key: str | None = None,
    semitones: int = 0,
    mode: str = "above",
    image_hash: str | None = None,
    input_path: str | None = None,
) -> Job:
    """Insert a new job in 'pending' status."""
    job = Job(
        user_id=user_id,
        song_name=song_name,
        original_key=original_key,
        semitones=semitones,
        mode=mode,
        image_hash=image_hash,
        input_path=input_path,
        status="pending",
    )
    db.add(job)
    await db.commit()
    await db.refresh(job)
    return job


async def update_job_completed(
    db: AsyncSession,
    job_id: uuid.UUID,
    *,
    output_path: str | None = None,
    original_key: str | None = None,
    target_key: str | None = None,
    chords: list[dict] | None = None,
    detected_chords_count: int = 0,
    processing_time_ms: int = 0,
    from_cache: bool = False,
) -> None:
    """Mark a job as completed with results."""
    values: dict = dict(
        status="completed",
        output_path=output_path,
        target_key=target_key,
        chords=chords,
        detected_chords_count=detected_chords_count,
        processing_time_ms=processing_time_ms,
        from_cache=from_cache,
        completed_at=datetime.now(timezone.utc),
    )
    if original_key is not None:
        values["original_key"] = original_key
    await db.execute(
        update(Job)
        .where(Job.id == job_id)
        .values(**values)
    )
    await db.commit()


async def update_job_failed(
    db: AsyncSession,
    job_id: uuid.UUID,
    error_message: str,
) -> None:
    """Mark a job as failed with an error message."""
    await db.execute(
        update(Job)
        .where(Job.id == job_id)
        .values(
            status="failed",
            error_message=error_message,
            completed_at=datetime.now(timezone.utc),
        )
    )
    await db.commit()


async def get_user_jobs(
    db: AsyncSession,
    user_id: uuid.UUID,
    *,
    limit: int = 20,
    offset: int = 0,
) -> list[Job]:
    """Return a user's non-deleted jobs, newest first."""
    result = await db.execute(
        select(Job)
        .where(Job.user_id == user_id, Job.is_deleted == False)  # noqa: E712
        .order_by(Job.created_at.desc())
        .limit(limit)
        .offset(offset)
    )
    return list(result.scalars().all())


async def soft_delete_job(
    db: AsyncSession,
    job_id: uuid.UUID,
    user_id: uuid.UUID,
) -> bool:
    """Soft-delete a job if it belongs to *user_id*. Return True if deleted."""
    result = await db.execute(
        select(Job).where(Job.id == job_id, Job.user_id == user_id)
    )
    job = result.scalar_one_or_none()
    if job is None:
        return False
    job.is_deleted = True
    await db.commit()
    return True
