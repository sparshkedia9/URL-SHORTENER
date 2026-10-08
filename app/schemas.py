# app/schemas.py
# Pydantic schemas: describe the shape of data coming IN and going OUT of the API.
# (Moved here unchanged from the Phase 1 main.py.)

from datetime import datetime

from pydantic import BaseModel, HttpUrl


class URLCreate(BaseModel):
    """Request body for POST /shorten (what the user sends us)."""
    url: HttpUrl  # must be a valid http:// or https:// address


class URLResponse(BaseModel):
    """Response for POST /shorten (what we send back)."""
    short_code: str  # e.g. "q0U"
    short_url: str   # e.g. "http://localhost:8000/q0U"


class URLStats(BaseModel):
    """Response for GET /stats/{short_code}."""
    original_url: str
    created_at: datetime
    click_count: int
