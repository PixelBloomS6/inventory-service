import pika
import json
import os
import time
from typing import Dict, Any
from dotenv import load_dotenv

class RabbitMQPublisher:
    def __init__(self):
        # Load environment variables
        load_dotenv()
        
        self.rabbitmq_host = os.getenv("RABBITMQ_HOST", "rabbitmq")
        self.rabbitmq_port = int(os.getenv("RABBITMQ_PORT", "5672"))
        self.rabbitmq_user = os.getenv("RABBITMQ_USER", "guest")
        self.rabbitmq_password = os.getenv("RABBITMQ_PASSWORD", "guest")
        
        self.connection = self._create_connection()
        self.channel = self.connection.channel()
        
        # Declare exchanges
        self.channel.exchange_declare(
            exchange="shop_events",
            exchange_type="topic",
            durable=True
        )

    def _create_connection(self):
        credentials = pika.PlainCredentials(
            username=self.rabbitmq_user,
            password=self.rabbitmq_password
        )
        
        parameters = pika.ConnectionParameters(
            host=self.rabbitmq_host,
            port=self.rabbitmq_port,
            credentials=credentials,
            heartbeat=600,
            blocked_connection_timeout=300
        )
        
        # Add retry logic for more robust connection handling
        max_retries = 5
        for attempt in range(max_retries):
            try:
                return pika.BlockingConnection(parameters)
            except pika.exceptions.AMQPConnectionError as e:
                if attempt < max_retries - 1:
                    print(f"Connection attempt {attempt+1} failed. Retrying in 5 seconds...")
                    time.sleep(5)
                else:
                    raise Exception(f"Failed to connect to RabbitMQ after {max_retries} attempts: {str(e)}")

    def publish_event(self, exchange: str, routing_key: str, body: Dict[str, Any]):
        try:
            self.channel.basic_publish(
                exchange=exchange,
                routing_key=routing_key,
                body=json.dumps(body),
                properties=pika.BasicProperties(
                    delivery_mode=2,  # make message persistent
                    content_type="application/json"
                )
            )
        except (pika.exceptions.ConnectionClosed, pika.exceptions.ChannelClosed):
            # Reconnect and try again
            self.connection = self._create_connection()
            self.channel = self.connection.channel()
            
            # Re-declare exchange to be safe
            self.channel.exchange_declare(
                exchange=exchange,
                exchange_type="topic",
                durable=True
            )
            
            # Try again
            self.channel.basic_publish(
                exchange=exchange,
                routing_key=routing_key,
                body=json.dumps(body),
                properties=pika.BasicProperties(
                    delivery_mode=2,
                    content_type="application/json"
                )
            )

    def close(self):
        if self.connection and self.connection.is_open:
            self.connection.close()