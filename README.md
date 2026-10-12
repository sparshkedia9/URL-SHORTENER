# URL Shortener

A URL shortening REST API built with **FastAPI**, **PostgreSQL**, **SQLAlchemy 2.x**, and **Pydantic v2**.
It turns long URLs into short codes (like `http://localhost:8000/q0U`), redirects visitors to the original URL, and tracks how many times each link is clicked.

Short codes are generated **deterministically** from the database's auto-increment id using **base62 encoding**, so every code is unique by construction: no random strings, no hashing, and no collision-retry loop.

---

## Features

- **Shorten URLs:** `POST /shorten` validates the input URL and returns a short code and a ready-to-share short URL
- **Redirect:** `GET /{short_code}` sends visitors to the original URL with a `307 Temporary Redirect`
- **Click tracking:** every redirect increments a click counter, atomically in the database
- **Stats:** `GET /stats/{short_code}` returns the original URL, creation time, and click count
- **Admin-only deletion:** `DELETE /{short_code}` permanently removes a link, protected by a secret API key
- **Input validation:** only valid `http://` / `https://` URLs are accepted (`422` otherwise)
- **Persistent storage:** links, click counts, and the id counter survive server restarts
- **Interactive API docs:** auto-generated Swagger UI at `/docs`

## Tech Stack

| Layer | Technology |
|---|---|
| Web framework | FastAPI |
| ASGI server | Uvicorn |
| Database | PostgreSQL |
| ORM | SQLAlchemy 2.x (typed `Mapped` / `mapped_column` style) |
| DB driver | psycopg2 |
| Validation & settings | Pydantic v2, pydantic-settings, python-dotenv |

---

## How Short Codes Work: Counter + Base62

1. When a URL is saved, PostgreSQL assigns the next auto-increment `id` (an identity column starting at **100000**).
2. That id is converted to **base62** using the alphabet `0-9a-zA-Z` (62 characters).
3. The result is stored as the row's unique `short_code`.

Base62 conversion repeatedly divides by 62; the remainders, read in reverse, are the digits:

```
125 → divmod(125, 62) = (2, 1)  → digit '1'
      divmod(2, 62)   = (0, 2)  → digit '2'
      reversed → "21"            check: 2×62 + 1 = 125 ✓
```

Starting the counter at 100000 makes the first code `q0U` and keeps codes 3 characters long for the first ~138,000 links. Six characters cover 62⁶ ≈ **56.8 billion** links.

### Why unique codes are guaranteed

The code is derived from the id, and PostgreSQL's identity sequence hands out each id **exactly once**, even under concurrent requests, so two links can never receive the same code. A `UNIQUE` index on `short_code` acts as an extra safety net.

### Creating a link: insert, flush, encode, commit

The id isn't known until PostgreSQL inserts the row, so creation happens in one transaction:

```python
db_url = URL(original_url=original_url)
db.add(db_url)
db.flush()                                      # INSERT runs; Postgres assigns the id
db_url.short_code = encode_base62(db_url.id)    # e.g. 100000 → "q0U"
db.commit()                                     # INSERT + UPDATE become permanent together
```

If anything fails before the commit, the whole transaction rolls back and no half-created row is left behind.

---

## API Endpoints

| Method | Path | Description | Success | Errors |
|---|---|---|---|---|
| `POST` | `/shorten` | Create a short link | `201 Created` | `422` invalid URL |
| `GET` | `/stats/{short_code}` | Get link statistics | `200 OK` | `404` unknown code |
| `GET` | `/{short_code}` | Redirect to the original URL | `307 Temporary Redirect` | `404` unknown code |
| `DELETE` | `/{short_code}` | Permanently delete a link (admin only) | `204 No Content` | `401` missing/wrong key, `404` unknown code |

### Examples

**Shorten a URL**
```http
POST /shorten
Content-Type: application/json

{ "url": "https://www.python.org" }
```
```json
201 Created
{ "short_code": "q0U", "short_url": "http://localhost:8000/q0U" }
```

**Get stats**
```http
GET /stats/q0U
```
```json
200 OK
{
  "original_url": "https://www.python.org/",
  "created_at": "2026-10-08T16:30:29.927843+05:30",
  "click_count": 3
}
```

**Redirect**
```http
GET /q0U
```
```
307 Temporary Redirect
location: https://www.python.org/
```

**Delete a link (admin only)**
```http
DELETE /q0U
X-Admin-Key: <your ADMIN_API_KEY>
```
```
204 No Content
```
Without the header, or with a wrong key, the API returns `401 {"detail": "Invalid or missing admin key"}`.

**Invalid input**
```json
422 Unprocessable Content
{
  "detail": [{
    "type": "url_parsing",
    "loc": ["body", "url"],
    "msg": "Input should be a valid URL, relative URL without a base"
  }]
}
```

---

## Database Schema

Table `urls`:

| Column | Type | Constraints |
|---|---|---|
| `id` | `integer` | Primary key, identity (starts at 100000) |
| `original_url` | `text` | Not null |
| `short_code` | `varchar(20)` | Unique, indexed |
| `created_at` | `timestamp with time zone` | Not null, default `now()` |
| `click_count` | `integer` | Not null, default `0` |

---

## Project Structure

```
url_shortener/
├── app/
│   ├── __init__.py
│   ├── main.py        # FastAPI app and routes
│   ├── database.py    # engine, SessionLocal, Base, get_db
│   ├── models.py      # SQLAlchemy model (urls table)
│   ├── schemas.py     # Pydantic request/response schemas
│   ├── crud.py        # database operations + base62 encoding
│   └── config.py      # settings loaded from .env
├── .env.example       # template for your own .env
├── .gitignore
├── requirements.txt
└── README.md
```

Request flow: **`main.py`** (HTTP) → **`schemas.py`** (validation) → **`crud.py`** (database logic) → **`models.py`** (table) → PostgreSQL.

---

## Getting Started

### Prerequisites
- Python 3.10+
- PostgreSQL (running locally)

### 1. Clone and create a virtual environment
```bash
git clone <your-repo-url>
cd url_shortener
python -m venv venv

# Windows (PowerShell)
.\venv\Scripts\Activate.ps1
# macOS / Linux
source venv/bin/activate
```

### 2. Install dependencies
```bash
pip install -r requirements.txt
```

### 3. Create the database
```bash
psql -U postgres -h localhost -c "CREATE DATABASE url_shortener;"
```

### 4. Configure environment variables
Copy `.env.example` to `.env`, set your PostgreSQL password, and generate an admin key:
```env
DATABASE_URL=postgresql+psycopg2://postgres:your_password@localhost:5432/url_shortener
BASE_URL=http://localhost:8000
ADMIN_API_KEY=<output of: python -c "import secrets; print(secrets.token_urlsafe(32))">
```
The app refuses to start if `ADMIN_API_KEY` is missing or shorter than 32 characters.

### 5. Run the server (from the project root)
```bash
uvicorn app.main:app --reload
```
The `urls` table is created automatically on startup. Open **http://localhost:8000/docs** to try the API.

---

## Design Decisions & Trade-offs

**Counter-based codes are predictable.**
Because codes come from sequential ids, they are guessable: if your link is `q0U`, someone can try `q0V`, `q0W`, ... and discover other users' links. This was a deliberate trade-off for **guaranteed uniqueness and simplicity** (no collisions, no retry loop). For links that must stay private, alternatives include random codes with a collision check, or obfuscating the id before encoding (e.g. a reversible permutation / Hashids-style encoding).

**307 instead of 301.**
A `301 Moved Permanently` is cached by browsers, so repeat visits would skip the server and **clicks would stop being counted**. `307` is temporary, so every visit reaches the API.

**Atomic click counting.**
Clicks are incremented in SQL (`SET click_count = click_count + 1`) rather than read-modify-write in Python, so concurrent clicks on the same link are never lost to a race condition.

**Models and schemas are separate.**
SQLAlchemy models describe *storage*; Pydantic schemas describe the *API contract*. Users can't set fields like `click_count` or `created_at`, and internal columns are never exposed by accident.

**Hard delete, protected by an admin key.**
Deleting a link removes the row permanently (`DELETE FROM urls ...`); there is no undo, which is why the endpoint requires a secret `X-Admin-Key` header. The key is compared with `secrets.compare_digest` (constant-time, to prevent timing attacks), and it is checked *before* the database lookup, so callers without the key get `401` for every code and cannot use `404` vs `401` to discover which codes exist. Deleted codes are never reused, because the PostgreSQL sequence never hands out the same id twice, so an old shared link can't start pointing somewhere new.

**Settings live in `.env`.**
Database credentials are loaded with `pydantic-settings` and never committed. The app fails fast with a clear error if a required setting is missing.

**Stateless application.**
All state lives in PostgreSQL, so the API can be restarted or run as multiple instances behind a load balancer without losing data or generating duplicate codes.

## Known Limitations

- Codes are predictable (see above)
- No user accounts or rate limiting: anyone with access can create links, and only the single admin key can delete them
- Hard delete only: deleted links and their click history cannot be recovered
- No deduplication: shortening the same URL twice creates two codes
- Tables are created with `create_all`, which does not apply schema changes to existing tables (no migrations yet)

## Possible Improvements

- Per-link delete tokens, so each creator can delete their own links
- Custom aliases (e.g. `/my-portfolio`)
- Link expiry dates
- Database migrations with Alembic
- Automated tests with pytest
- Docker Compose for one-command setup
- Rate limiting and blocked-domain checks
- Deployment to a cloud host with a managed PostgreSQL database
