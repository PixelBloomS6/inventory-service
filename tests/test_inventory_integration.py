import uuid
import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from testcontainers.postgres import PostgresContainer
from fastapi.testclient import TestClient
import os
from urllib.parse import urlparse

from app.main import app  # Adjust if your FastAPI app is elsewhere
from app.db.database import Base, get_db

@pytest.fixture(scope="module")
def test_db():
    with PostgresContainer("postgres:15") as postgres:
        # Get the connection URL from testcontainer and parse it
        connection_url = postgres.get_connection_url()
        parsed_url = urlparse(connection_url)
        
        # Override the individual PostgreSQL environment variables
        os.environ["POSTGRES_HOST"] = parsed_url.hostname
        os.environ["POSTGRES_PORT"] = str(parsed_url.port)
        os.environ["POSTGRES_USER"] = parsed_url.username
        os.environ["POSTGRES_PASSWORD"] = parsed_url.password
        os.environ["POSTGRES_DB"] = parsed_url.path.lstrip('/')
        
        # Create engine with the testcontainer URL
        engine = create_engine(connection_url)
        TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

        # Create tables
        Base.metadata.create_all(bind=engine)

        # Dependency override
        def override_get_db():
            db = TestingSessionLocal()
            try:
                yield db
            finally:
                db.close()

        app.dependency_overrides[get_db] = override_get_db
        
        # Create test client
        client = TestClient(app)
        yield client
        
        # Cleanup
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