from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker

from stockscrape.config import DATABASE_URL

engine = create_engine(
    DATABASE_URL,
    echo=False,
    # For SQLite, allow usage from multiple threads (Alembic compat)
    **({"connect_args": {"check_same_thread": False}} if DATABASE_URL.startswith("sqlite") else {}),
)

SessionLocal: sessionmaker[Session] = sessionmaker(bind=engine, expire_on_commit=False)


def get_session() -> Session:
    return SessionLocal()
