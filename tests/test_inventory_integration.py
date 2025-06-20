import uuid
import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from testcontainers.postgres import PostgresContainer
from fastapi.testclient import TestClient
import os
from urllib.parse import urlparse

# Set test environment variables before importing app modules
os.environ["TESTING"] = "true"
# Set dummy values to prevent connection attempts during import
os.environ["POSTGRES_HOST"] = "localhost"
os.environ["POSTGRES_PORT"] = "5432"
os.environ["POSTGRES_USER"] = "test"
os.environ["POSTGRES_PASSWORD"] = "test"
os.environ["POSTGRES_DB"] = "test"

from app.main import app  # Adjust if your FastAPI app is elsewhere
from app.db.database import Base, get_db

@pytest.fixture(scope="module")
def test_db():
    with PostgresContainer("postgres:15") as postgres:
        # Get dynamic test DB URL
        connection_url = postgres.get_connection_url()

        # Override global SQLAlchemy engine dynamically
        from app.db import database
        database.engine = create_engine(connection_url)
        database.SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=database.engine)

        # Create test tables
        database.Base.metadata.create_all(bind=database.engine)

        # Dependency override for get_db
        def override_get_db():
            db = database.SessionLocal()
            try:
                yield db
            finally:
                db.close()

        app.dependency_overrides[get_db] = override_get_db
        client = TestClient(app)
        yield client

        app.dependency_overrides.clear()
def test_create_inventory_item(test_db):
    response = test_db.post(
        "/inventory/items/",
        data={
            "shop_id": str(uuid.uuid4()),
            "name": "Red Roses",
            "description": "Fresh roses",
            "category": "Flowers",
            "price": 15.99,
            "quantity": 10,
        },
        files=[]
    )
    assert response.status_code == 201
    assert response.json()["name"] == "Red Roses"

def test_get_inventory_items(test_db):
    # First create an item
    shop_id = str(uuid.uuid4())
    create_response = test_db.post(
        "/inventory/items/",
        data={
            "shop_id": shop_id,
            "name": "Blue Tulips",
            "description": "Beautiful tulips",
            "category": "Flowers",
            "price": 12.50,
            "quantity": 5,
        },
        files=[]
    )
    assert create_response.status_code == 201
    
    # Then get items for that shop
    get_response = test_db.get(f"/inventory/shops/{shop_id}/items")
    assert get_response.status_code == 200
    items = get_response.json()
    assert len(items) >= 1
    assert any(item["name"] == "Blue Tulips" for item in items)