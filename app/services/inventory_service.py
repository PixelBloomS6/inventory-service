import uuid
import json
import pika
import os
from sqlalchemy.orm import Session
from ..models.domain.inventory import InventoryItem, InventoryItemCreate
from ..repositories.inventory_repository import InventoryRepository


class RabbitMQPublisher:
    """RabbitMQ publisher for inventory events"""
    
    def __init__(self):
        self.connection = None
        self.channel = None
        self._setup_connection()
    
    def _setup_connection(self):
        """Setup RabbitMQ connection"""
        try:
            connection_params = pika.ConnectionParameters(
                host=os.getenv("RABBITMQ_HOST", "localhost"),
                port=int(os.getenv("RABBITMQ_PORT", "5672")),
                credentials=pika.PlainCredentials(
                    os.getenv("RABBITMQ_USER", "guest"),
                    os.getenv("RABBITMQ_PASSWORD", "guest")
                )
            )
            
            self.connection = pika.BlockingConnection(connection_params)
            self.channel = self.connection.channel()
            
            # Declare exchanges
            self.channel.exchange_declare(exchange='inventory_events', exchange_type='topic')
            self.channel.exchange_declare(exchange='shop_events', exchange_type='topic')
            
        except Exception as e:
            print(f"Failed to setup RabbitMQ connection: {e}")
            self.connection = None
            self.channel = None
    
    def publish_event(self, exchange: str, routing_key: str, body: dict):
        """Publish event to RabbitMQ"""
        if not self.channel:
            print("RabbitMQ channel not available, skipping publish")
            return
        
        try:
            self.channel.basic_publish(
                exchange=exchange,
                routing_key=routing_key,
                body=json.dumps(body),
                properties=pika.BasicProperties(
                    delivery_mode=2,  # Make message persistent
                    content_type='application/json'
                )
            )
            print(f"Published event to {exchange}/{routing_key}: {body}")
        except Exception as e:
            print(f"Failed to publish event: {e}")
    
    def request_shop_status(self, shop_id: str, callback_queue: str) -> str:
        """Request shop status with correlation ID pattern"""
        if not self.channel:
            print("RabbitMQ channel not available")
            return None
        
        correlation_id = str(uuid.uuid4())
        
        try:
            request_body = {
                "shop_id": shop_id,
                "request_type": "status_check"
            }
            
            self.channel.basic_publish(
                exchange='shop_events',
                routing_key='shop.status.request',
                properties=pika.BasicProperties(
                    reply_to=callback_queue,
                    correlation_id=correlation_id,
                    content_type='application/json'
                ),
                body=json.dumps(request_body)
            )
            
            print(f"Requested shop status for {shop_id} with correlation_id: {correlation_id}")
            return correlation_id
            
        except Exception as e:
            print(f"Failed to request shop status: {e}")
            return None
    
    def close(self):
        """Close RabbitMQ connection"""
        if self.connection and not self.connection.is_closed:
            self.connection.close()


class InventoryService:
    def __init__(self, db: Session, publisher: RabbitMQPublisher = None):
        self.repository = InventoryRepository(db)
        self.publisher = publisher or RabbitMQPublisher()
    
    def create_item(self, item: InventoryItemCreate) -> InventoryItem:
        """Create inventory item and publish event"""
        # Create the item
        created_item = self.repository.create(item)
        
        # Publish inventory item created event
        if self.publisher:
            self.publisher.publish_event(
                exchange="inventory_events",
                routing_key="inventory.created",
                body={
                    "event_type": "inventory_item_created",
                    "item_id": str(created_item.id),
                    "shop_id": str(created_item.shop_id),
                    "name": created_item.name,
                    "category": created_item.category,
                    "price": float(created_item.price),
                    "quantity": created_item.quantity,
                    "timestamp": created_item.created_at.isoformat() if created_item.created_at else None
                }
            )
            
            # Request shop status validation (correlation ID pattern)
            callback_queue = "shop_status_responses"
            correlation_id = self.publisher.request_shop_status(
                shop_id=str(created_item.shop_id),
                callback_queue=callback_queue
            )
            
            if correlation_id:
                print(f"Shop status requested with correlation ID: {correlation_id}")
        
        return created_item
    
    def validate_shop_status(self, shop_id: str) -> bool:
        """Validate if shop is active (synchronous version for testing)"""
        # In real implementation, this would use the correlation ID pattern
        # For testing, we'll simulate the validation
        if os.getenv("TESTING") == "true":
            return True  # Mock successful validation in tests
        
        # Real implementation would:
        # 1. Send request with correlation ID
        # 2. Wait for response
        # 3. Return validation result
        return True
    
    def handle_shop_status_response(self, correlation_id: str, response: dict):
        """Handle shop status response from shop service"""
        print(f"Received shop status response for correlation ID {correlation_id}: {response}")
        
        if response.get("is_active"):
            print(f"Shop {response.get('shop_id')} is active")
            # Here you could update item status, send notifications, etc.
        else:
            print(f"Shop {response.get('shop_id')} is inactive - may need to disable items")
            # Handle inactive shop scenario
    
    def __del__(self):
        """Cleanup on service destruction"""
        if hasattr(self, 'publisher') and self.publisher:
            self.publisher.close()


# from typing import List, Optional
# import uuid
# from sqlalchemy.orm import Session
# from ..repositories.inventory_repository import InventoryRepository
# from ..models.domain.inventory import InventoryItem, InventoryItemCreate, InventoryItemUpdate
# # from ..messaging.publisher import RabbitMQPublisher

# class InventoryService:
#     def __init__(self, db: Session):
#         self.repository = InventoryRepository(db)
#         # self.publisher = publisher

#     def create_item(self, item: InventoryItemCreate) -> InventoryItem:
#         created_item = self.repository.create(item)
#         return created_item
#         # Publish inventory item created event
#         # self.publisher.publish_event(
#         #     exchange="inventory_events",
#         #     routing_key="inventory.created",
#         #     body={
#         #         "event_type": "inventory_item_created",
#         #         "item_id": str(created_item.id),
#         #         "shop_id": str(created_item.shop_id),
#         #         "name": created_item.name
#         #     }
#         # )

#     def get_item(self, item_id: uuid.UUID) -> Optional[InventoryItem]:
#         return self.repository.get_by_id(item_id)

#     def get_items_by_shop(self, shop_id: uuid.UUID, skip: int = 0, limit: int = 100) -> List[InventoryItem]:
#         return self.repository.get_by_shop_id(shop_id, skip, limit)

#     def get_all_items(self, skip: int = 0, limit: int = 100) -> List[InventoryItem]:
#         return self.repository.get_all(skip, limit)

#     def update_item(self, item_id: uuid.UUID, item_update: InventoryItemUpdate) -> Optional[InventoryItem]:
#         updated_item = self.repository.update(item_id, item_update)
        
        # if updated_item:
            # Publish inventory item updated event
            # self.publisher.publish_event(
            #     exchange="inventory_events",
            #     routing_key="inventory.updated",
            #     body={
            #         "event_type": "inventory_item_updated",
            #         "item_id": str(updated_item.id),
            #         "shop_id": str(updated_item.shop_id),
            #         "name": updated_item.name
            #     }
            # )
        
    #     return updated_item

    # def delete_item(self, item_id: uuid.UUID) -> bool:
    #     item = self.repository.get_by_id(item_id)
    #     if not item:
    #         return False
            
    #     success = self.repository.delete(item_id)
        
    #     # if success:
    #     #     # Publish inventory item deleted event
    #     #     self.publisher.publish_event(
    #     #         exchange="inventory_events",
    #     #         routing_key="inventory.deleted",
    #     #         body={
    #     #             "event_type": "inventory_item_deleted",
    #     #             "item_id": str(item_id),
    #     #             "shop_id": str(item.shop_id)
    #     # #         }
    #     #     )
        
    #     return success
    
    
    # def update_item_images(self, item_id: uuid.UUID, image_urls: List[str]) -> Optional[InventoryItem]:
    #     """Update an item's images with new URLs"""
    #     db_item = self.db.query(InventoryItemModel).filter(InventoryItemModel.id == item_id).first()
    #     if not db_item:
    #         return None
        
    #     db_item.image_urls = image_urls
    #     self.db.commit()
    #     self.db.refresh(db_item)
    #     return self._map_to_domain(db_item)

    # def add_item_images(self, item_id: uuid.UUID, new_image_urls: List[str]) -> Optional[InventoryItem]:
    #     """Add more image URLs to an existing item"""
    #     db_item = self.db.query(InventoryItemModel).filter(InventoryItemModel.id == item_id).first()
    #     if not db_item:
    #         return None
        
    #     # Combine existing images with new ones
    #     if db_item.image_urls:
    #         db_item.image_urls = db_item.image_urls + new_image_urls
    #     else:
    #         db_item.image_urls = new_image_urls
        
    #     self.db.commit()
    #     self.db.refresh(db_item)
    #     return self._map_to_domain(db_item)

    # def remove_item_image(self, item_id: uuid.UUID, image_url: str) -> Optional[InventoryItem]:
    #     """Remove an image URL from an item"""
    #     db_item = self.db.query(InventoryItemModel).filter(InventoryItemModel.id == item_id).first()
    #     if not db_item or not db_item.image_urls:
    #         return None
        
    #     # Remove the specified URL
    #     db_item.image_urls = [url for url in db_item.image_urls if url != image_url]
        
    #     self.db.commit()
    #     self.db.refresh(db_item)
    #     return self._map_to_domain(db_item)