"""File storage abstraction — local filesystem with S3 stub for future."""
from __future__ import annotations

import hashlib
import logging
import os

import aiofiles

logger = logging.getLogger(__name__)

USE_S3 = os.environ.get("USE_S3", "false").lower() == "true"
LOCAL_STORAGE_DIR = os.environ.get("LOCAL_STORAGE_DIR", "./storage")

_instance: StorageManager | None = None


class StorageManager:
    """Handles input/output file persistence."""

    def __init__(self, base_dir: str = LOCAL_STORAGE_DIR) -> None:
        self._base = base_dir

    @staticmethod
    def compute_hash(data: bytes) -> str:
        """Return SHA-256 hex digest of *data*."""
        return hashlib.sha256(data).hexdigest()

    async def save_input(self, image_hash: str, data: bytes) -> str:
        """Persist an uploaded input image; return its storage path."""
        directory = os.path.join(self._base, "inputs", image_hash[:2])
        os.makedirs(directory, exist_ok=True)
        path = os.path.join(directory, image_hash)
        async with aiofiles.open(path, "wb") as f:
            await f.write(data)
        return path

    def get_output_path(self, image_hash: str, semitones: int, mode: str) -> str:
        """Return the deterministic output path for the given parameters."""
        filename = f"{image_hash}_{semitones}_{mode}.png"
        return os.path.join(self._base, "outputs", image_hash[:2], filename)

    def check_cache(self, image_hash: str, semitones: int, mode: str) -> str | None:
        """Return output path if a cached file exists, None otherwise."""
        path = self.get_output_path(image_hash, semitones, mode)
        if os.path.exists(path):
            logger.info("Cache HIT: %s", path)
            return path
        logger.info("Cache MISS: %s", path)
        return None

    async def save_output(
        self,
        image_hash: str,
        semitones: int,
        mode: str,
        data: bytes,
    ) -> str:
        """Persist a rendered output image; return its storage path."""
        path = self.get_output_path(image_hash, semitones, mode)
        os.makedirs(os.path.dirname(path), exist_ok=True)
        async with aiofiles.open(path, "wb") as f:
            await f.write(data)
        return path

    async def get_output(self, path: str) -> bytes:
        """Read a stored file and return its bytes."""
        async with aiofiles.open(path, "rb") as f:
            return await f.read()

    async def delete_file(self, path: str) -> None:
        """Delete a stored file (no-op if missing)."""
        if os.path.exists(path):
            os.remove(path)


def get_storage_manager() -> StorageManager:
    """Return the singleton StorageManager instance."""
    global _instance
    if _instance is None:
        _instance = StorageManager()
    return _instance
