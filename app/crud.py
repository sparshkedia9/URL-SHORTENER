# app/crud.py
# Database functions. Each one replaces a dict operation from Phase 1.
# The endpoints (Step 9) call these instead of touching url_db.

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models import URL

# ----------------------------------------------------------------------
# Short code generation: base62 (same function as Phase 1)
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


# ----------------------------------------------------------------------
# CRUD functions
# ----------------------------------------------------------------------

def create_short_url(db: Session, original_url: str) -> URL:
    """Save a new URL and give it a short code made from its database id.

    Phase 1 equivalent: url_db[short_code] = {...}
    """
    # 1. Build the row. No id and no short_code yet.
    db_url = URL(original_url=original_url)
    db.add(db_url)

    # 2. Flush: send the INSERT to Postgres, which assigns the id (e.g. 100000).
    #    Nothing is permanent yet; it is still inside the transaction.
    db.flush()

    # 3. Turn the id into the short code: 100000 -> "q0U".
    db_url.short_code = encode_base62(db_url.id)

    # 4. Commit: make the INSERT and the short_code UPDATE permanent, together.
    db.commit()

    # 5. Reload the row so values Postgres filled in (created_at) are available.
    db.refresh(db_url)
    return db_url


def get_url_by_code(db: Session, short_code: str) -> URL | None:
    """Find the row with this short code, or return None if there isn't one.

    Phase 1 equivalent: url_db.get(short_code)
    """
    return db.scalar(select(URL).where(URL.short_code == short_code))


def increment_click(db: Session, db_url: URL) -> URL:
    """Add 1 to the click count and save it.

    Phase 1 equivalent: record["click_count"] += 1
    """
    # Let Postgres do the +1 itself ("SET click_count = click_count + 1"),
    # so two clicks arriving at the same moment can't overwrite each other.
    db_url.click_count = URL.click_count + 1
    db.commit()
    db.refresh(db_url)
    return db_url
