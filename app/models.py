# app/models.py
# SQLAlchemy models: Python classes that describe our database tables.

from datetime import datetime

from sqlalchemy import DateTime, Identity, Integer, String, Text, func
from sqlalchemy.orm import Mapped, mapped_column

from app.database import Base


class URL(Base):
    """One row in the `urls` table = one shortened link."""

    __tablename__ = "urls"

    # Auto-increment id. Postgres hands out 100000, 100001, 100002...
    # Starting at 100000 keeps short codes 3 characters long, same as Phase 1.
    id: Mapped[int] = mapped_column(Integer, Identity(start=100000), primary_key=True)

    # The long URL. Text = no length limit (some URLs are very long).
    original_url: Mapped[str] = mapped_column(Text, nullable=False)

    # The base62 code. It is empty (NULL) for a moment while a row is being created:
    # we only know the id after Postgres inserts the row (see crud.py).
    # unique=True: no two rows can share a code. index=True: fast lookups by code.
    short_code: Mapped[str | None] = mapped_column(String(20), unique=True, index=True, nullable=True)

    # Filled in by Postgres itself (NOW()) when the row is inserted, in UTC-aware form.
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )

    # Starts at 0 and goes up by 1 on every redirect.
    click_count: Mapped[int] = mapped_column(Integer, default=0, server_default="0", nullable=False)
