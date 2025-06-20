import os
import sys
import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from urllib.parse import urlparse
from testcontainers.postgres import PostgresContainer
from fastapi.testclient import TestClient


@pytest.fixture(scope="module")
def test_db():
    """Setup test database with testcontainers"""
    
    # Start PostgreSQL container
    with PostgresContainer("postgres:15") as postgres:
        # Get connection details
        database_url = postgres.get_connection_url()
        
        # Create engine and session for testing
        engine = create_engine(database_url)
        TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
        
        # Set environment variables for the app
        parsed = urlparse(database_url)
        os.environ["POSTGRES_HOST"] = parsed.hostname
        os.environ["POSTGRES_PORT"] = str(parsed.port)
        os.environ["POSTGRES_USER"] = parsed.username
        os.environ["POSTGRES_PASSWORD"] = parsed.password
        os.environ["POSTGRES_DB"] = parsed.path.lstrip("/")
        os.environ["TESTING"] = "true"
        
        # Import app after setting environment variables
        from app.main import app
        from app.db.database import Base, get_db
        
        # Create tables
        Base.metadata.create_all(bind=engine)
        
        # Override the get_db dependency
        def override_get_db():
            try:
                db = TestingSessionLocal()
                yield db
            finally:
                db.close()
        
        app.dependency_overrides[get_db] = override_get_db
        
        # Create test client
        client = TestClient(app)
        
        yield client
        
        # Cleanup
        app.dependency_overrides.clear()
        Base.metadata.drop_all(bind=engine)


def test_create_inventory_item(test_db):
    """Test creating an inventory item"""
    import uuid
    
    # Test data
    test_data = {
        "shop_id": str(uuid.uuid4()),
        "name": "Test Item",
        "description": "Test Description", 
        "category": "Test Category",
        "price": 10.99,
        "quantity": 5
    }
    
    # Make request
    response = test_db.post("/inventory/items/", data=test_data)
    
    # Print response for debugging
    print(f"Response status: {response.status_code}")
    print(f"Response body: {response.text}")
    
    # Assertions
    assert response.status_code == 201
    data = response.json()
    assert data["name"] == test_data["name"]
    assert data["description"] == test_data["description"]
    assert data["category"] == test_data["category"]
    assert data["price"] == test_data["price"]
    assert data["quantity"] == test_data["quantity"]


def test_health_check(test_db):
    """Test basic application health"""
    # Test that the app is running
    response = test_db.get("/docs")  # FastAPI docs endpoint should exist
    assert response.status_code == 200


def test_database_connection(test_db):
    """Test that database connection works"""
    # This test will pass if the fixture setup worked correctly
    assert test_db is not None
    
    # Test a simple database operation
    from app.db.database import get_engine
    engine = get_engine()
    
    # Try to connect to the database
    with engine.connect() as connection:
        result = connection.execute("SELECT 1 as test")
        assert result.fetchone()[0] == 1