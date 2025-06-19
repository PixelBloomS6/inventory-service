# inventory-service/app/messaging/consumer.py
import pika
import json
import uuid
import os
import threading
import time
from typing import Dict, Any
from sqlalchemy.orm import sessionmaker
from sqlalchemy import create_engine
from dotenv import load_dotenv
from ..db.database import SQLALCHEMY_DATABASE_URL
from ..services.inventory_service import InventoryService
from ..messaging.publisher import RabbitMQPublisher

class InventoryConsumer:
    def __init__(self):
        load_dotenv()
        
        self.rabbitmq_host = os.getenv("RABBITMQ_HOST", "rabbitmq")
        self.rabbitmq_port = int(os.getenv("RABBITMQ_PORT", "5672"))
        self.rabbitmq_user = os.getenv("RABBITMQ_USER", "guest")
        self.rabbitmq_password = os.getenv("RABBITMQ_PASSWORD", "guest")
        
        # Database setup
        self.engine = create_engine(SQLALCHEMY_DATABASE_URL)
        self.SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=self.engine)
        
        self.connection = None
        self.channel = None
        self.publisher = RabbitMQPublisher()
        
        self._setup_connection()
        pass
    
#     def _setup_connection(self):
#         """Setup RabbitMQ connection"""
#         credentials = pika.PlainCredentials(
#             username=self.rabbitmq_user,
#             password=self.rabbitmq_password
#         )
        
#         parameters = pika.ConnectionParameters(
#             host=self.rabbitmq_host,
#             port=self.rabbitmq_port,
#             credentials=credentials,
#             heartbeat=600,
#             blocked_connection_timeout=300
#         )
        
#         max_retries = 5
#         for attempt in range(max_retries):
#             try:
#                 self.connection = pika.BlockingConnection(parameters)
#                 self.channel = self.connection.channel()
                
#                 # Declare queues
#                 self.channel.queue_declare(queue='inventory_check_queue', durable=True)
#                 self.channel.queue_declare(queue='inventory_update_queue', durable=True)
                
#                 # Declare exchanges
#                 self.channel.exchange_declare(
#                     exchange='inventory_events',
#                     exchange_type='topic',
#                     durable=True
#                 )
                
#                 # Bind queue to exchange for inventory updates
#                 self.channel.queue_bind(
#                     exchange='inventory_events',
#                     queue='inventory_update_queue',
#                     routing_key='inventory.update_request'
#                 )
                
#                 self.channel.queue_bind(
#                     exchange='inventory_events',
#                     queue='inventory_update_queue',
#                     routing_key='inventory.restore_request'
#                 )
                
#                 print("Inventory consumer connected to RabbitMQ")
#                 break
                
#             except pika.exceptions.AMQPConnectionError as e:
#                 if attempt < max_retries - 1:
#                     print(f"Connection attempt {attempt+1} failed. Retrying in 5 seconds...")
#                     time.sleep(5)
#                 else:
#                     raise Exception(f"Failed to connect to RabbitMQ after {max_retries} attempts: {str(e)}")
    
#     def _handle_inventory_check(self, channel, method, properties, body):
#         """Handle inventory check requests (RPC pattern)"""
#         try:
#             request_data = json.loads(body)
#             correlation_id = properties.correlation_id
#             reply_to = properties.reply_to
            
#             print(f"Processing inventory check request: {request_data} (correlation_id: {correlation_id})")
            
#             # Create database session
#             db = self.SessionLocal()
#             inventory_service = InventoryService(db, self.publisher)
            
#             try:
#                 # Process the inventory check
#                 items = request_data.get("items", [])
#                 results = []
#                 all_available = True
                
#                 for item in items:
#                     product_id = uuid.UUID(item["product_id"])
#                     quantity = item["quantity"]
                    
#                     # Get inventory item
#                     inventory_item = inventory_service.get_item(product_id)
                    
#                     if not inventory_item:
#                         result = {
#                             "product_id": str(product_id),
#                             "available": False,
#                             "reason": "Product not found",
#                             "current_quantity": 0,
#                             "requested_quantity": quantity
#                         }
#                         all_available = False
#                     else:
#                         available = inventory_item.quantity >= quantity
#                         result = {
#                             "product_id": str(product_id),
#                             "available": available,
#                             "current_quantity": inventory_item.quantity,
#                             "requested_quantity": quantity,
#                             "product_name": inventory_item.name,
#                             "shop_id": str(inventory_item.shop_id)
#                         }
#                         if not available:
#                             result["reason"] = "Insufficient quantity"
#                             all_available = False
                    
#                     results.append(result)
                
#                 response = {
#                     "all_available": all_available,
#                     "results": results
#                 }
                
#                 print(f"Sending response: {response} (correlation_id: {correlation_id})")
                
#                 # Send response back
#                 if reply_to and correlation_id:
#                     channel.basic_publish(
#                         exchange='',
#                         routing_key=reply_to,
#                         properties=pika.BasicProperties(
#                             correlation_id=correlation_id,
#                             content_type="application/json"
#                         ),
#                         body=json.dumps(response)
#                     )
                
#                 # Acknowledge message
#                 channel.basic_ack(delivery_tag=method.delivery_tag)
                
#             finally:
#                 db.close()
                
#         except Exception as e:
#             print(f"Error processing inventory check: {str(e)}")
            
#             # Send error response
#             error_response = {
#                 "all_available": False,
#                 "error": str(e)
#             }
            
#             if properties.reply_to and properties.correlation_id:
#                 channel.basic_publish(
#                     exchange='',
#                     routing_key=properties.reply_to,
#                     properties=pika.BasicProperties(
#                         correlation_id=properties.correlation_id,
#                         content_type="application/json"
#                     ),
#                     body=json.dumps(error_response)
#                 )
            
#             channel.basic_ack(delivery_tag=method.delivery_tag)
    
#     def _handle_inventory_update(self, channel, method, properties, body):
#         """Handle inventory update requests"""
#         try:
#             request_data = json.loads(body)
#             print(f"Processing inventory update request: {request_data}")
            
#             # Create database session
#             db = self.SessionLocal()
#             inventory_service = InventoryService(db, self.publisher)
            
#             try:
#                 order_id = request_data.get("order_id")
#                 updates = request_data.get("updates", [])
                
#                 update_results = []
                
#                 for update in updates:
#                     product_id = uuid.UUID(update["product_id"])
#                     quantity_change = update["quantity_change"]
                    
#                     # Get current inventory item
#                     inventory_item = inventory_service.get_item(product_id)
                    
#                     if inventory_item:
#                         new_quantity = inventory_item.quantity + quantity_change
                        
#                         if new_quantity >= 0:
#                             # Update inventory
#                             from ..models.domain.inventory import InventoryItemUpdate
#                             update_data = InventoryItemUpdate(quantity=new_quantity)
#                             updated_item = inventory_service.update_item(product_id, update_data)
                            
#                             update_results.append({
#                                 "product_id": str(product_id),
#                                 "success": True,
#                                 "previous_quantity": inventory_item.quantity,
#                                 "new_quantity": new_quantity,
#                                 "change": quantity_change
#                             })
#                         else:
#                             update_results.append({
#                                 "product_id": str(product_id),
#                                 "success": False,
#                                 "reason": "Insufficient inventory",
#                                 "current_quantity": inventory_item.quantity,
#                                 "attempted_change": quantity_change
#                             })
#                     else:
#                         update_results.append({
#                             "product_id": str(product_id),
#                             "success": False,
#                             "reason": "Product not found"
#                         })
                
#                 # Publish inventory update completed event
#                 self.publisher.publish_event(
#                     exchange="inventory_events",
#                     routing_key="inventory.updated",
#                     body={
#                         "event_type": "inventory_bulk_updated",
#                         "order_id": order_id,
#                         "update_results": update_results
#                     }
#                 )
                
#                 print(f"Inventory update completed for order {order_id}")
                
#                 # Acknowledge message
#                 channel.basic_ack(delivery_tag=method.delivery_tag)
                
#             finally:
#                 db.close()
                
#         except Exception as e:
#             print(f"Error processing inventory update: {str(e)}")
#             channel.basic_ack(delivery_tag=method.delivery_tag)
    
#     def start_consuming(self):
#         """Start consuming messages"""
#         try:
#             # Set up consumers
#             self.channel.basic_qos(prefetch_count=1)
            
#             # RPC consumer for inventory checks
#             self.channel.basic_consume(
#                 queue='inventory_check_queue',
#                 on_message_callback=self._handle_inventory_check
#             )
            
#             # Event consumer for inventory updates
#             self.channel.basic_consume(
#                 queue='inventory_update_queue',
#                 on_message_callback=self._handle_inventory_update
#             )
            
#             print("Starting to consume messages...")
#             self.channel.start_consuming()
            
#         except KeyboardInterrupt:
#             print("Stopping consumer...")
#             self.channel.stop_consuming()
#             if self.connection and not self.connection.is_closed:
#                 self.connection.close()
    
#     def stop_consuming(self):
#         """Stop consuming messages"""
#         if self.channel:
#             self.channel.stop_consuming()
#         if self.connection and not self.connection.is_closed:
#             self.connection.close()

# # Function to start consumer in background thread
# def start_inventory_consumer():
#     """Start the inventory consumer in a separate thread"""
#     consumer = InventoryConsumer()
    
#     def run_consumer():
#         try:
#             consumer.start_consuming()
#         except Exception as e:
#             print(f"Consumer error: {str(e)}")
    
#     consumer_thread = threading.Thread(target=run_consumer, daemon=True)
#     consumer_thread.start()
#     print("Inventory consumer started in background thread")
#     return consumer