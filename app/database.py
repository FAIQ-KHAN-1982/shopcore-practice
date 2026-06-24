from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, declarative_base

# PostgreSQL connection URL
# format:
# postgresql://username:password@host:port/dbname

DATABASE_URL = "postgresql://postgres:FAIQ@localhost:5432/shopcore"


# Engine = core connection to DB
engine = create_engine(
    DATABASE_URL,
    pool_pre_ping=True,   # checks connection before using it
    pool_size=10,
    max_overflow=20
)

# Session = each request gets one DB session
SessionLocal = sessionmaker(
    autocommit=False,
    autoflush=False,
    bind=engine
)

# Base class for all models
Base = declarative_base()


# Dependency (this is what FastAPI will use)
def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()