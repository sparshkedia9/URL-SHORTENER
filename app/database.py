# app/database.py
# Everything needed to talk to PostgreSQL: the engine, the session factory,
# the Base class for our tables, and get_db() for FastAPI endpoints.

from sqlalchemy import create_engine
from sqlalchemy.orm import DeclarativeBase, sessionmaker

from app.config import settings

# The engine manages the actual connections to Postgres (a "connection pool").
# echo=True would print every SQL query SQLAlchemy runs, which is handy for learning.
engine = create_engine(settings.database_url, echo=False)

# A factory that creates new Session objects, already connected to our engine.
# autoflush=False: we decide when to flush (see crud.py in Step 8).
SessionLocal = sessionmaker(bind=engine, autoflush=False)


class Base(DeclarativeBase):
    """Parent class for all our table models (see models.py)."""
    pass


def get_db():
    """Give one request its own database session, and always close it afterwards."""
    db = SessionLocal()
    try:
        yield db      # the endpoint runs here, using `db`
    finally:
        db.close()    # runs after the request, even if an error happened
