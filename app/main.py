# app/main.py
# The FastAPI app and its routes. Phase 2: data is stored in PostgreSQL.

from fastapi import Depends, FastAPI, HTTPException
from fastapi.responses import RedirectResponse
from sqlalchemy.orm import Session

from app import crud, models  # noqa: F401  (importing models registers the URL table with Base)
from app.config import settings
from app.database import Base, engine, get_db
from app.schemas import URLCreate, URLResponse, URLStats

# Create the `urls` table if it doesn't exist yet. Existing tables are left alone.
Base.metadata.create_all(bind=engine)

app = FastAPI(title="URL Shortener")


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
