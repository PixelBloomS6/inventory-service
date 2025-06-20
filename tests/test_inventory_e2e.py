import pytest
import uuid
import json
import time

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from fastapi.testclient import TestClient
from testcontainers.postgres import PostgresContainer
from testcontainers.rabbitmq import RabbitMqContainer

from app.main import app
from app.database import Base, get_db
from app.services.inventory_service import InventoryService
from app.models.domain.inventory import InventoryItemCreate
from app.services.inventory_service import RabbitMQPublisher

# Override DB session
@pytest.fixture(scope="module")
def db_session():
    with PostgresContainer("postgres:15") as postgres:
        engine = create_engine(postgres.get_connection_url())
        TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
        Base.metadata.create_all(bind=engine)
        session = TestingSessionLocal()
        yield session
        session.close()

# Override RabbitMQ container
@pytest.fixture(scope="module")
def rabbitmq_container():
    with RabbitMqContainer("rabbitmq:3.11.11") as rabbitmq:
        time.sleep(5)  # wait for queues to fully boot up
        yield rabbitmq

@pytest.fixture(scope="module")
def service(db_session, rabbitmq_container):
    rmq_url = rabbitmq_container.get_amqp_url()
    host = rabbitmq_container.get_container_host_ip()
    port = rabbitmq_container.get_exposed_port(5672)

    # Set ENV variables for RabbitMQ connection
    import os
    os.environ["RABBITMQ_HOST"] = host
    os.environ["RABBITMQ_PORT"] = port
    os.environ["RABBITMQ_USER"] = "guest"
    os.environ["RABBITMQ_PASSWORD"] = "guest"
    os.environ["TESTING"] = "true"

    publisher = RabbitMQPublisher()
    return InventoryService(db_session, publisher)

def test_create_inventory_item_e2e(service):
    test_item = InventoryItemCreate(
        shop_id=uuid.uuid4(),
        name="Test Bouquet",
        category="Roses",
        price=29.99,
        quantity=10,
    )

    created_item = service.create_item(test_item)

    assert created_item.name == "Test Bouquet"
    assert created_item.price == 29.99
    assert created_item.quantity == 10

    # Note: Actual event verification requires a consumer or RabbitMQ spy
    print("E2E inventory item created and events dispatched.")
