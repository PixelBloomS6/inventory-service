from sqlalchemy import create_engine
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
import os
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

# Database configuration from environment variables
POSTGRES_USER = os.getenv("POSTGRES_USER", "postgres")
POSTGRES_PASSWORD = os.getenv("POSTGRES_PASSWORD", "YourSecurePassword123!")
POSTGRES_HOST = os.getenv("POSTGRES_HOST", "db")  # 'db' is typical in Docker Compose
POSTGRES_PORT = os.getenv("POSTGRES_PORT", "5432")
POSTGRES_DB = os.getenv("POSTGRES_DB", "inventory_db")

# Check if we're connecting to Azure PostgreSQL
is_azure_postgres = "postgres.database.azure.com" in POSTGRES_HOST

# Construct the database URL with SSL for Azure
if is_azure_postgres:
    SQLALCHEMY_DATABASE_URL = f"postgresql://{POSTGRES_USER}:{POSTGRES_PASSWORD}@{POSTGRES_HOST}:{POSTGRES_PORT}/{POSTGRES_DB}?sslmode=require"
else:
    SQLALCHEMY_DATABASE_URL = f"postgresql://{POSTGRES_USER}:{POSTGRES_PASSWORD}@{POSTGRES_HOST}:{POSTGRES_PORT}/{POSTGRES_DB}"

print(f"Connecting to database: {POSTGRES_HOST}")
print(f"Database: {POSTGRES_DB}")
print(f"User: {POSTGRES_USER}")
print(f"SSL Mode: {'require' if is_azure_postgres else 'prefer'}")

# Create SQLAlchemy engine and session
# For Azure PostgreSQL, we need to handle SSL properly
engine_kwargs = {}
if is_azure_postgres:
    engine_kwargs['connect_args'] = {"sslmode": "require"}

engine = create_engine(SQLALCHEMY_DATABASE_URL, **engine_kwargs)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()

# Dependency for getting DB session
def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()