import os
from collections.abc import Generator

from sqlalchemy import create_engine
from sqlalchemy.orm import Session, declarative_base, sessionmaker


DATABASE_URL = os.getenv("DATABASE_URL", "sqlite:///./auto_loan_dev.db")


def _engine_options(database_url: str) -> dict:
	options: dict = {"pool_pre_ping": True}

	if database_url.startswith("sqlite"):
		options["connect_args"] = {"check_same_thread": False}

	return options


engine = create_engine(DATABASE_URL, **_engine_options(DATABASE_URL))

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

Base = declarative_base()


def get_db() -> Generator[Session, None, None]:
	db = SessionLocal()
	try:
		yield db
	finally:
		db.close()
