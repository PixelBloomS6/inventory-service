# inventory-service/app/messaging/publisher.py
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
        
        self.channel.exchange_declare(
            exchange="inventory_events",
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
            message_body = json.dumps(body, default=str)  # Handle UUID serialization
            
            self.channel.basic_publish(
                exchange=exchange,
                routing_key=routing_key,
                body=message_body,
                properties=pika.BasicProperties(
                    delivery_mode=2,  # make message persistent
                    content_type="application/json",
                    timestamp=int(time.time())
                )
            )
            print(f"Published event to {exchange}.{routing_key}: {body}")
            
        except (pika.exceptions.ConnectionClosed, pika.exceptions.ChannelClosed):
            # Reconnect and try again
            self.connection = self._create_connection()
            self.channel = self.connection.channel()
            
            # Re-declare exchanges to be safe
            self.channel.exchange_declare(
                exchange="shop_events",
                exchange_type="topic",
                durable=True
            )
            
            self.channel.exchange_declare(
                exchange="inventory_events",
                exchange_type="topic",
                durable=True
            )
            
            # Try again
            message_body = json.dumps(body, default=str)
            self.channel.basic_publish(
                exchange=exchange,
                routing_key=routing_key,
                body=message_body,
                properties=pika.BasicProperties(
                    delivery_mode=2,
                    content_type="application/json",
                    timestamp=int(time.time())
                )
            )
            print(f"Published event after reconnection to {exchange}.{routing_key}: {body}")

    def close(self):
        if self.connection and self.connection.is_open:
            self.connection.close()

    def publish_inventory_response(self, routing_key: str, order_id: str, event_type: str, success: bool, message: str = None, product_details: Dict = None):
        """Helper method specifically for inventory responses"""
        response_body = {
            "order_id": order_id,
            "event_type": event_type,
            "success": success,
            "timestamp": int(time.time()),
            "message": message
        }
        
        if product_details:
            response_body["product_details"] = product_details
            
        self.publish_event("inventory_events", routing_key, response_body)

    def publish_inventory_update(self, product_id: str, quantity_change: int, current_stock: int, reason: str = None):
        """Helper method for inventory stock updates"""
        update_body = {
            "product_id": product_id,
            "quantity_change": quantity_change,
            "current_stock": current_stock,
            "reason": reason or "stock_update",
            "timestamp": int(time.time()),
            "event_type": "inventory_updated"
        }
        
        self.publish_event("inventory_events", "inventory.stock.updated", update_body)