import os
import time
import pytest
import pika
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from testcontainers.postgres import PostgresContainer
from testcontainers.rabbitmq import RabbitMqContainer

from fastapi.testclient import TestClient

from app.main import app  # Replace with actual FastAPI app entry
from app.db.base import Base  # Replace with your SQLAlchemy base
from app.dependencies import get_db  # Your db dependency override

# Override FastAPI DB session with test DB session
@pytest.fixture(scope="module")
def test_env():
    with PostgresContainer("postgres:15") as pg, RabbitMqContainer("rabbitmq:3-management") as rmq:
        # PostgreSQL
        db_url = pg.get_connection_url()
        engine = create_engine(db_url)
        TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
        Base.metadata.create_all(bind=engine)

        def override_get_db():
            db = TestingSessionLocal()
            try:
                yield db
            finally:
                db.close()

        app.dependency_overrides[get_db] = override_get_db

        # RabbitMQ
        rmq_host = rmq.get_container_host_ip()
        rmq_port = rmq.get_exposed_port(5672)

        os.environ["RABBITMQ_HOST"] = rmq_host
        os.environ["RABBITMQ_PORT"] = rmq_port
        os.environ["RABBITMQ_USER"] = "guest"
        os.environ["RABBITMQ_PASSWORD"] = "guest"
        os.environ["TESTING"] = "true"

        # Setup RabbitMQ
        connection = pika.BlockingConnection(pika.ConnectionParameters(
            host=rmq_host,
            port=int(rmq_port),
            credentials=pika.PlainCredentials("guest", "guest")
        ))
        channel = connection.channel()
        channel.exchange_declare(exchange="inventory_events", exchange_type="topic")
        channel.exchange_declare(exchange="shop_events", exchange_type="topic")
        connection.close()

        yield {
            "db_session": TestingSessionLocal,
            "rmq_host": rmq_host,
            "rmq_port": rmq_port
        }

@pytest.fixture()
def client(test_env):
    return TestClient(app)

def test_create_inventory_item(client):
    item_data = {
        "shop_id": "11111111-1111-1111-1111-111111111111",
        "name": "Test Bouquet",
        "category": "Roses",
        "price": 29.99,
        "quantity": 10
    }

    response = client.post("/inventory/items", json=item_data)
    assert response.status_code == 201, response.text
    data = response.json()
    assert data["name"] == item_data["name"]
    assert data["price"] == item_data["price"]
    assert data["quantity"] == item_data["quantity"]
