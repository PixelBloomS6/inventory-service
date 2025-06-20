# from sqlalchemy import create_engine
# from sqlalchemy.ext.declarative import declarative_base
# from sqlalchemy.orm import sessionmaker
# import os
# from dotenv import load_dotenv

# # Load environment variables from .env file
# load_dotenv()

# # Database configuration from environment variables
# POSTGRES_USER = os.getenv("POSTGRES_USER", "postgres")
# POSTGRES_PASSWORD = os.getenv("POSTGRES_PASSWORD", "postgres")
# POSTGRES_HOST = os.getenv("POSTGRES_HOST", "inventory_db")  # 'db' is typical in Docker Compose
# POSTGRES_PORT = os.getenv("POSTGRES_PORT", "5432")
# POSTGRES_DB = os.getenv("POSTGRES_DB", "inventory_db")

# # Construct the database URL
# SQLALCHEMY_DATABASE_URL = f"postgresql://{POSTGRES_USER}:{POSTGRES_PASSWORD}@{POSTGRES_HOST}:{POSTGRES_PORT}/{POSTGRES_DB}"

# # Create SQLAlchemy engine and session
# engine = create_engine(SQLALCHEMY_DATABASE_URL)
# SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
# Base = declarative_base()

# # Dependency for getting DB session
# def get_db():
#     db = SessionLocal()
#     try:
#         yield db
#     finally:
#         db.close()

# app/db/database.py
import os
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.ext.declarative import declarative_base

DATABASE_URL = os.getenv("DATABASE_URL") or (
    f"postgresql://{os.getenv('POSTGRES_USER', 'postgres')}:"
    f"{os.getenv('POSTGRES_PASSWORD', 'postgres')}@"
    f"{os.getenv('POSTGRES_HOST', 'localhost')}:"
    f"{os.getenv('POSTGRES_PORT', '5432')}/"
    f"{os.getenv('POSTGRES_DB', 'postgres')}"
)

engine = create_engine(DATABASE_URL)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
