import uuid
import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from testcontainers.postgres import PostgresContainer
from fastapi.testclient import TestClient

from app.main import app  # Adjust if your FastAPI app is elsewhere
from app.db.database import Base, get_db

@pytest.fixture(scope="module")
def test_db():
    with PostgresContainer("postgres:15") as postgres:
        engine = create_engine(postgres.get_connection_url())
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
        yield TestClient(app)

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
