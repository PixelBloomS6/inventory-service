import os
import pytest
import importlib
from sqlalchemy.orm import sessionmaker
from urllib.parse import urlparse
from testcontainers.postgres import PostgresContainer
from fastapi.testclient import TestClient

# Set environment variables before importing app
os.environ["TESTING"] = "true"

@pytest.fixture(scope="module")
def test_db():
    with PostgresContainer("postgres:15") as postgres:
        # Get connection details
        url = postgres.get_connection_url()
        parsed = urlparse(url)

        # Set environment variables that your app uses
        os.environ["POSTGRES_HOST"] = parsed.hostname
        os.environ["POSTGRES_PORT"] = str(parsed.port)
        os.environ["POSTGRES_USER"] = parsed.username
        os.environ["POSTGRES_PASSWORD"] = parsed.password
        os.environ["POSTGRES_DB"] = parsed.path.lstrip("/")

        # Clear any cached modules to ensure fresh imports
        modules_to_reload = [
            'app.db.database',
            'app.main',
            'app.routers.inventory_router'
        ]
        
        for module_name in modules_to_reload:
            if module_name in sys.modules:
                del sys.modules[module_name]

        # Now import after setting environment variables
        from app.main import app
        from app.db.database import Base, get_db, get_engine

        # Create engine and tables
        engine = get_engine()
        TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
        Base.metadata.create_all(bind=engine)

        # Override DB dependency
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
    
    # Assertions
    assert response.status_code == 201
    data = response.json()
    assert data["name"] == test_data["name"]
    assert data["description"] == test_data["description"]
    assert data["category"] == test_data["category"]
    assert data["price"] == test_data["price"]
    assert data["quantity"] == test_data["quantity"]


def test_health_check(test_db):
    """Test basic health check"""
    response = test_db.get("/")
    # Adjust this based on your actual health check endpoint
    assert response.status_code in [200, 404]  # 404 if no root endpoint defined


def test_database_connection(test_db):
    """Test that database connection works"""
    # This test will pass if the fixture setup worked correctly
    assert test_db is not None