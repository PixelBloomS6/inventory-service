import os
import sys
import pytest
import asyncio
import json
import uuid
from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker
from urllib.parse import urlparse
from testcontainers.postgres import PostgresContainer
from testcontainers.rabbitmq import RabbitMqContainer
from fastapi.testclient import TestClient
import pika
import threading
import time
from unittest.mock import patch, MagicMock


@pytest.fixture(scope="module")
def test_infrastructure():
    """Setup test infrastructure with PostgreSQL and RabbitMQ"""
    
    # Start containers
    with PostgresContainer("postgres:15") as postgres, \
         RabbitMqContainer("rabbitmq:3-management") as rabbitmq:
        
        # Setup PostgreSQL
        database_url = postgres.get_connection_url()
        engine = create_engine(database_url)
        TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
        
        # Set PostgreSQL environment variables
        parsed_pg = urlparse(database_url)
        os.environ["POSTGRES_HOST"] = parsed_pg.hostname
        os.environ["POSTGRES_PORT"] = str(parsed_pg.port)
        os.environ["POSTGRES_USER"] = parsed_pg.username
        os.environ["POSTGRES_PASSWORD"] = parsed_pg.password
        os.environ["POSTGRES_DB"] = parsed_pg.path.lstrip("/")
        
        # Setup RabbitMQ
        rabbitmq_host = rabbitmq.get_container_host_ip()
        rabbitmq_port = rabbitmq.get_exposed_port(5672)
        rabbitmq_user = "guest"
        rabbitmq_password = "guest"
        
        os.environ["RABBITMQ_HOST"] = rabbitmq_host
        os.environ["RABBITMQ_PORT"] = str(rabbitmq_port)
        os.environ["RABBITMQ_USER"] = rabbitmq_user
        os.environ["RABBITMQ_PASSWORD"] = rabbitmq_password
        os.environ["TESTING"] = "true"
        
        # Wait for RabbitMQ to be ready
        time.sleep(5)
        
        # Setup RabbitMQ exchanges and queues
        connection = pika.BlockingConnection(
            pika.ConnectionParameters(
                host=rabbitmq_host,
                port=rabbitmq_port,
                credentials=pika.PlainCredentials(rabbitmq_user, rabbitmq_password)
            )
        )
        channel = connection.channel()
        
        # Declare exchanges and queues
        channel.exchange_declare(exchange='inventory_events', exchange_type='topic')
        channel.exchange_declare(exchange='shop_events', exchange_type='topic')
        
        # Queue for shop service responses
        channel.queue_declare(queue='shop_status_responses', durable=True)
        channel.queue_declare(queue='inventory_events_queue', durable=True)
        
        channel.queue_bind(
            exchange='inventory_events',
            queue='inventory_events_queue',
            routing_key='inventory.created'
        )
        
        connection.close()
        
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
        
        yield {
            'client': client,
            'database_url': database_url,
            'rabbitmq_host': rabbitmq_host,
            'rabbitmq_port': rabbitmq_port,
            'rabbitmq_user': rabbitmq_user,
            'rabbitmq_password': rabbitmq_password
        }
        
        # Cleanup
        app.dependency_overrides.clear()
        Base.metadata.drop_all(bind=engine)


class MessageCollector:
    """Helper class to collect messages from RabbitMQ"""
    def __init__(self, connection_params):
        self.connection_params = connection_params
        self.messages = []
        self.correlation_responses = {}
        self.running = False
        self.thread = None
    
    def start_consuming(self):
        """Start consuming messages in a separate thread"""
        self.running = True
        self.thread = threading.Thread(target=self._consume)
        self.thread.daemon = True
        self.thread.start()
    
    def stop_consuming(self):
        """Stop consuming messages"""
        self.running = False
        if self.thread:
            self.thread.join(timeout=2)
    
    def _consume(self):
        """Consume messages from RabbitMQ"""
        try:
            connection = pika.BlockingConnection(self.connection_params)
            channel = connection.channel()
            
            def callback(ch, method, properties, body):
                message = {
                    'routing_key': method.routing_key,
                    'body': json.loads(body.decode()),
                    'properties': properties
                }
                self.messages.append(message)
                
                # If this is a shop status request, send a mock response
                if method.routing_key == 'shop.status.request':
                    self._send_shop_status_response(ch, properties, message['body'])
                
                ch.basic_ack(delivery_tag=method.delivery_tag)
            
            channel.basic_consume(
                queue='inventory_events_queue',
                on_message_callback=callback
            )
            
            # Also consume shop status requests (simulating shop service)
            channel.queue_declare(queue='shop_status_requests', durable=True)
            channel.basic_consume(
                queue='shop_status_requests',
                on_message_callback=callback
            )
            
            while self.running:
                connection.process_data_events(time_limit=0.1)
                
        except Exception as e:
            print(f"Error in message consumer: {e}")
        finally:
            try:
                connection.close()
            except:
                pass
    
    def _send_shop_status_response(self, channel, properties, request_body):
        """Send a mock shop status response"""
        if properties.correlation_id:
            response = {
                "shop_id": request_body.get("shop_id"),
                "is_active": True,  # Mock active shop
                "status": "active"
            }
            
            channel.basic_publish(
                exchange='',
                routing_key=properties.reply_to,
                properties=pika.BasicProperties(
                    correlation_id=properties.correlation_id
                ),
                body=json.dumps(response)
            )
            
            self.correlation_responses[properties.correlation_id] = response


@pytest.fixture
def message_collector(test_infrastructure):
    """Setup message collector for RabbitMQ"""
    connection_params = pika.ConnectionParameters(
        host=test_infrastructure['rabbitmq_host'],
        port=test_infrastructure['rabbitmq_port'],
        credentials=pika.PlainCredentials(
            test_infrastructure['rabbitmq_user'],
            test_infrastructure['rabbitmq_password']
        )
    )
    
    collector = MessageCollector(connection_params)
    collector.start_consuming()
    
    yield collector
    
    collector.stop_consuming()


def test_create_inventory_item_basic(test_infrastructure):
    """Test creating an inventory item - basic functionality"""
    client = test_infrastructure['client']
    
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
    response = client.post("/inventory/items/", data=test_data)
    
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


def test_create_inventory_item_with_shop_validation(test_infrastructure, message_collector):
    """Test creating inventory item with shop service validation via RabbitMQ"""
    client = test_infrastructure['client']
    
    # Mock the publisher in the inventory service
    with patch('app.services.inventory_service.InventoryService') as mock_service_class:
        # Create a real instance but mock the publisher
        from app.services.inventory_service import InventoryService
        from app.db.database import get_db
        
        # Get a real database session for the test
        db_gen = next(get_db())
        real_service = InventoryService(db_gen)
        
        # Create a mock publisher
        mock_publisher = MagicMock()
        real_service.publisher = mock_publisher
        
        # Mock the service class to return our configured instance
        mock_service_class.return_value = real_service
        
        # Test data
        shop_id = str(uuid.uuid4())
        test_data = {
            "shop_id": shop_id,
            "name": "Test Item with Shop Check",
            "description": "Test Description", 
            "category": "Electronics",
            "price": 99.99,
            "quantity": 10
        }
        
        # Make request
        response = client.post("/inventory/items/", data=test_data)
        
        # Verify the item was created
        assert response.status_code == 201
        data = response.json()
        item_id = data["id"]
        
        # Wait a moment for async processing
        time.sleep(1)
        
        # Verify that the publisher was called with correct parameters
        mock_publisher.publish_event.assert_called_once()
        call_args = mock_publisher.publish_event.call_args
        
        # Check the published event
        assert call_args[1]['exchange'] == 'inventory_events'
        assert call_args[1]['routing_key'] == 'inventory.created'
        
        event_body = call_args[1]['body']
        assert event_body['event_type'] == 'inventory_item_created'
        assert event_body['item_id'] == item_id
        assert event_body['shop_id'] == shop_id
        assert event_body['name'] == test_data['name']


def test_shop_status_correlation_pattern(test_infrastructure):
    """Test the correlation ID pattern for shop status validation"""
    
    # Setup RabbitMQ connection
    connection = pika.BlockingConnection(
        pika.ConnectionParameters(
            host=test_infrastructure['rabbitmq_host'],
            port=test_infrastructure['rabbitmq_port'],
            credentials=pika.PlainCredentials(
                test_infrastructure['rabbitmq_user'],
                test_infrastructure['rabbitmq_password']
            )
        )
    )
    channel = connection.channel()
    
    # Create a temporary queue for responses
    result = channel.queue_declare(queue='', exclusive=True)
    callback_queue = result.method.queue
    
    # Generate correlation ID
    correlation_id = str(uuid.uuid4())
    shop_id = str(uuid.uuid4())
    
    # Prepare shop status request
    request_message = {
        "shop_id": shop_id,
        "request_type": "status_check"
    }
    
    # Track response
    response_received = {}
    
    def on_response(ch, method, props, body):
        if props.correlation_id == correlation_id:
            response_received['data'] = json.loads(body.decode())
            response_received['received'] = True
    
    channel.basic_consume(
        queue=callback_queue,
        on_message_callback=on_response,
        auto_ack=True
    )
    
    # Send shop status request with correlation ID
    channel.basic_publish(
        exchange='shop_events',
        routing_key='shop.status.request',
        properties=pika.BasicProperties(
            reply_to=callback_queue,
            correlation_id=correlation_id,
        ),
        body=json.dumps(request_message)
    )
    
    # Simulate shop service response (in real scenario, shop service would do this)
    def simulate_shop_response():
        time.sleep(0.5)  # Simulate processing time
        response = {
            "shop_id": shop_id,
            "is_active": True,
            "status": "active",
            "last_updated": "2025-06-20T10:00:00Z"
        }
        
        channel.basic_publish(
            exchange='',
            routing_key=callback_queue,
            properties=pika.BasicProperties(
                correlation_id=correlation_id
            ),
            body=json.dumps(response)
        )
    
    # Start response simulation in background
    response_thread = threading.Thread(target=simulate_shop_response)
    response_thread.start()
    
    # Wait for response
    start_time = time.time()
    while not response_received.get('received') and time.time() - start_time < 5:
        connection.process_data_events(time_limit=0.1)
    
    response_thread.join()
    connection.close()
    
    # Verify correlation pattern worked
    assert response_received.get('received'), "No response received via correlation ID"
    assert response_received['data']['shop_id'] == shop_id
    assert response_received['data']['is_active'] is True
    assert response_received['data']['status'] == 'active'


def test_database_connection(test_infrastructure):
    """Test that database connection works"""
    # Test a simple database operation
    from app.db.database import get_engine
    engine = get_engine()
    
    # Try to connect to the database
    with engine.connect() as connection:
        result = connection.execute(text("SELECT 1 as test"))
        assert result.fetchone()[0] == 1


def test_rabbitmq_connection(test_infrastructure):
    """Test that RabbitMQ connection works"""
    connection = pika.BlockingConnection(
        pika.ConnectionParameters(
            host=test_infrastructure['rabbitmq_host'],
            port=test_infrastructure['rabbitmq_port'],
            credentials=pika.PlainCredentials(
                test_infrastructure['rabbitmq_user'],
                test_infrastructure['rabbitmq_password']
            )
        )
    )
    
    # Test basic connection
    assert connection.is_open
    
    # Test channel creation
    channel = connection.channel()
    assert channel.is_open
    
    # Test queue declaration
    channel.queue_declare(queue='test_queue', durable=False)
    
    connection.close()