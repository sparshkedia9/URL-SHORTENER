# main.py
# Phase 1: everything lives in this one file for no

from datetime import datetime, timezone

from fastapi import FastAPI, HTTPException
from fastapi.responses import RedirectResponse
from pydantic import BaseModel, HttpUrl


# ----------------------------------------------------------------------
# Pydantic schemas: describe the shape of data coming IN and going OUT
# ----------------------------------------------------------------------

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


# ----------------------------------------------------------------------
# Short code generation: counter + base62
# ----------------------------------------------------------------------

# The 62 "digits" of base62, in order: 0-9 are worth 0-9,
# a-z are worth 10-35, and A-Z are worth 36-61.
BASE62_ALPHABET = "0123456789abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ"
BASE = len(BASE62_ALPHABET)  # 62


def encode_base62(num: int) -> str:
    """Convert a non-negative integer into a base62 string. Example: 125 -> "21"."""
    if num < 0:
        raise ValueError("encode_base62 only works with non-negative numbers")
    if num == 0:
        return BASE62_ALPHABET[0]  # the loop below would return "" for 0

    digits = []
    while num > 0:
        # divmod gives (quotient, remainder) in one step: divmod(125, 62) -> (2, 1)
        num, remainder = divmod(num, BASE)
        digits.append(BASE62_ALPHABET[remainder])

    # Remainders come out smallest place first, so reverse them.
    return "".join(reversed(digits))


# Phase 1 counter: the next number to hand out.
# Starts at 100000 so codes are 3 characters long instead of "1", "2", "3"...
# (In Phase 2 the database's auto-increment id replaces this.)
next_id = 100000


def get_next_id() -> int:
    """Return the current counter value, then move the counter up by one."""
    global next_id  # we want to change the module-level variable, not create a local one
    current = next_id
    next_id += 1
    return current


# ----------------------------------------------------------------------
# App setup and temporary storage
# ----------------------------------------------------------------------

app = FastAPI(title="URL Shortener")

# The address our server runs at, used to build the full short URL.
# (In Phase 2 this moves into config.py / .env.)
BASE_URL = "http://localhost:8000"

# Phase 1 "database": a plain dict that maps short_code -> that URL's data.
# It lives in memory, so it is emptied every time the server restarts.
url_db: dict[str, dict] = {}


# ----------------------------------------------------------------------
# Endpoints
# NOTE: /stats/{short_code} is defined BEFORE /{short_code}. FastAPI checks
# routes in the order they are defined and uses the first one that matches.
# ----------------------------------------------------------------------

@app.post("/shorten", response_model=URLResponse, status_code=201)
def shorten_url(payload: URLCreate):
    """Create a short code for a long URL."""
    new_id = get_next_id()
    short_code = encode_base62(new_id)

    url_db[short_code] = {
        "id": new_id,
        "original_url": str(payload.url),  # HttpUrl object -> plain string
        "short_code": short_code,
        "created_at": datetime.now(timezone.utc),
        "click_count": 0,
    }

    return URLResponse(short_code=short_code, short_url=f"{BASE_URL}/{short_code}")


@app.get("/stats/{short_code}", response_model=URLStats)
def get_stats(short_code: str):
    """Return the original URL, creation time, and click count for a short code."""
    record = url_db.get(short_code)
    if record is None:
        raise HTTPException(status_code=404, detail="Short code not found")

    return URLStats(
        original_url=record["original_url"],
        created_at=record["created_at"],
        click_count=record["click_count"],
    )


@app.get("/{short_code}")
def redirect_to_url(short_code: str):
    """Count the click, then send the visitor to the original URL."""
    record = url_db.get(short_code)
    if record is None:
        raise HTTPException(status_code=404, detail="Short code not found")

    record["click_count"] += 1
    return RedirectResponse(url=record["original_url"], status_code=307)
