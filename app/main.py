# app/main.py
# The FastAPI app and its routes. Phase 2: data is stored in PostgreSQL.

import secrets

from fastapi import Depends, FastAPI, HTTPException
from fastapi.responses import RedirectResponse
from fastapi.security import APIKeyHeader
from sqlalchemy.orm import Session

from app import crud, models  # noqa: F401  (importing models registers the URL table with Base)
from app.config import settings
from app.database import Base, engine, get_db
from app.schemas import URLCreate, URLResponse, URLStats

# Create the `urls` table if it doesn't exist yet. Existing tables are left alone.
Base.metadata.create_all(bind=engine)

app = FastAPI(title="URL Shortener")


# ----------------------------------------------------------------------
# Admin key check (used by the DELETE endpoint)
# ----------------------------------------------------------------------

# Reads the X-Admin-Key request header. auto_error=False means a missing header
# gives us None (so we can return our own 401) instead of FastAPI's default 403.
# It also adds an "Authorize" button to /docs.
admin_key_header = APIKeyHeader(name="X-Admin-Key", auto_error=False)


def verify_admin_key(api_key: str | None = Depends(admin_key_header)) -> None:
    """Stop the request with 401 unless it sends the correct admin key."""
    # compare_digest takes the same time whether the first or last character
    # differs, so attackers can't guess the key by measuring response times.
    if api_key is None or not secrets.compare_digest(
        api_key.encode(), settings.admin_api_key.encode()
    ):
        raise HTTPException(status_code=401, detail="Invalid or missing admin key")


# ----------------------------------------------------------------------
# Endpoints
# NOTE: /stats/{short_code} is defined BEFORE /{short_code}. FastAPI checks
# routes in the order they are defined and uses the first one that matches.
# ----------------------------------------------------------------------

@app.post("/shorten", response_model=URLResponse, status_code=201)
def shorten_url(payload: URLCreate, db: Session = Depends(get_db)):
    """Create a short code for a long URL."""
    db_url = crud.create_short_url(db, str(payload.url))  # HttpUrl object -> plain string
    return URLResponse(
        short_code=db_url.short_code,
        short_url=f"{settings.base_url}/{db_url.short_code}",
    )


@app.get("/stats/{short_code}", response_model=URLStats)
def get_stats(short_code: str, db: Session = Depends(get_db)):
    """Return the original URL, creation time, and click count for a short code."""
    db_url = crud.get_url_by_code(db, short_code)
    if db_url is None:
        raise HTTPException(status_code=404, detail="Short code not found")

    return URLStats(
        original_url=db_url.original_url,
        created_at=db_url.created_at,
        click_count=db_url.click_count,
    )


@app.get("/{short_code}")
def redirect_to_url(short_code: str, db: Session = Depends(get_db)):
    """Count the click, then send the visitor to the original URL."""
    db_url = crud.get_url_by_code(db, short_code)
    if db_url is None:
        raise HTTPException(status_code=404, detail="Short code not found")

    crud.increment_click(db, db_url)
    return RedirectResponse(url=db_url.original_url, status_code=307)


@app.delete("/{short_code}", status_code=204, dependencies=[Depends(verify_admin_key)])
def delete_short_url(short_code: str, db: Session = Depends(get_db)):
    """Permanently delete a short link. Requires the X-Admin-Key header."""
    # verify_admin_key has already run: if we get here, the key was correct.
    db_url = crud.get_url_by_code(db, short_code)
    if db_url is None:
        raise HTTPException(status_code=404, detail="Short code not found")

    crud.delete_url(db, db_url)
    # Nothing to return: 204 No Content means "done, no response body".
