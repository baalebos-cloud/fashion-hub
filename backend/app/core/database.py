"""
Database engine, session factory, and declarative base.
"""
import os
import re
from sqlalchemy import create_engine
from sqlalchemy.orm import DeclarativeBase, Session, sessionmaker
from app.core.config import settings

# 1. Capture the raw string value safely
raw_url = str(settings.DATABASE_URL or os.getenv("DATABASE_URL", ""))

# 2. Programmatic Sanitization Pass
# Strip out any literal accidental matching string quotes (' or ") injected by dashboard panels
clean_url = raw_url.strip("'\"")

# 3. Secure Syntax Recovery Step
# If Render's variable manager mangled the port formatting down to a trailing colon (://supabase.com:/)
# this regex safely restores the missing default PostgreSQL connection port token instantly.
if "aws-0-" in clean_url and (":/" in clean_url or clean_url.endswith(".com") or "://supabase.com" in clean_url):
    if not re.search(r":\d+", clean_url.split("@")[-1]):
        clean_url = clean_url.replace("@aws-0-us-east-1.://supabase.com/", "@aws-0-us-east-1.://supabase.com:6543/")
        clean_url = clean_url.replace("@db.dbeasvpnxqwbqfiqebad.supabase.co/", "@db.dbeasvpnxqwbqfiqebad.supabase.co:5432/")

# Initialize the global engine instance with the sanitized database route
engine = create_engine(
    clean_url,
    pool_size=settings.DATABASE_POOL_SIZE,
    max_overflow=settings.DATABASE_MAX_OVERFLOW,
    echo=settings.DATABASE_ECHO,
    pool_pre_ping=True,
    future=True,
)

SessionLocal = sessionmaker(bind=engine, autoflush=False, autocommit=False, future=True)

class Base(DeclarativeBase):
    pass

def get_db() -> Generator[Session, None, None]:
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
