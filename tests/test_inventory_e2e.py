import os
import pytest
import pika
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from testcontainers.postgres import PostgresContainer
from testcontainers.rabbitmq import RabbitMqContainer

from fastapi.testclient import TestClient

from app.main import app  # Your FastAPI app entry point
from app.db.base import Base  # Your SQLAlchemy declarative base
from app.dependencies import get_db  # The DB dependency to override


@pytest.fixture(scope="module")
def test_env():
    # Start Postgres and RabbitMQ containers
    with PostgresContainer("postgres:15") as pg, RabbitMqContainer("rabbitmq:3-management") as rmq:

        # Setup Postgres
        db_url = pg.get_connection_url()
        engine = create_engine(db_url)
        TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

        # Create tables
        Base.metadata.create_all(bind=engine)

        # Override FastAPI DB dependency to use test DB session
        def override_get_db():
            db = TestingSessionLocal()
            try:
                yield db
            finally:
                db.close()

        app.dependency_overrides[get_db] = override_get_db

        # Setup RabbitMQ environment variables
        rmq_host = rmq.get_container_host_ip()
        rmq_port = int(rmq.get_exposed_port(5672))

        os.environ["RABBITMQ_HOST"] = rmq_host
        os.environ["RABBITMQ_PORT"] = str(rmq_port)
        os.environ["RABBITMQ_USER"] = "guest"
        os.environ["RABBITMQ_PASSWORD"] = "guest"
        os.environ["TESTING"] = "true"

        # Wait a bit for RabbitMQ to be ready (optional, but helps stability)
        import time
        time.sleep(3)

        # Setup RabbitMQ exchanges/queues for your app's eventing
        connection = pika.BlockingConnection(pika.ConnectionParameters(
            host=rmq_host,
            port=rmq_port,
            credentials=pika.PlainCredentials("guest", "guest")
        ))
        channel = connection.channel()
        channel.exchange_declare(exchange="inventory_events", exchange_type="topic", durable=True)
        channel.exchange_declare(exchange="shop_events", exchange_type="topic", durable=True)
        connection.close()

        yield {
            "db_session": TestingSessionLocal,
            "rmq_host": rmq_host,
            "rmq_port": rmq_port,
        }

        # Cleanup: Drop tables after tests finish
        Base.metadata.drop_all(bind=engine)
        app.dependency_overrides.clear()


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
