#!/usr/bin/env python
"""Create all database tables (idempotent).

Usage:
    python scripts/init_db.py
"""
import asyncio
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from backend.db.database import init_db


async def main() -> None:
    print("Creating database tables...")
    if not await init_db():
        sys.exit("DATABASE_URL is not configured.")
    print("Done.")


if __name__ == "__main__":
    asyncio.run(main())
