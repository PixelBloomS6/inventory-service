from typing import List, Optional
import uuid
from sqlalchemy.orm import Session
from ..repositories.inventory_repository import InventoryRepository
from ..models.domain.inventory import InventoryItem, InventoryItemCreate, InventoryItemUpdate
from ..messaging.publisher import RabbitMQPublisher

class InventoryService:
    def __init__(self, db: Session, publisher: RabbitMQPublisher):
        self.repository = InventoryRepository(db)
        self.publisher = publisher

    def create_item(self, item: InventoryItemCreate) -> InventoryItem:
        created_item = self.repository.create(item)
        
        # Publish inventory item created event
        self.publisher.publish_event(
            exchange="shop_events",  # Changed from inventory_events to shop_events
            routing_key="inventory.created",
            body={
                "event_type": "inventory_item_created",
                "item_id": str(created_item.id),
                "shop_id": str(created_item.shop_id),
                "name": created_item.name
            }
        )
        
        return created_item

    def get_item(self, item_id: uuid.UUID) -> Optional[InventoryItem]:
        return self.repository.get_by_id(item_id)

    def get_items_by_shop(self, shop_id: uuid.UUID, skip: int = 0, limit: int = 100) -> List[InventoryItem]:
        return self.repository.get_by_shop_id(shop_id, skip, limit)

    def get_all_items(self, skip: int = 0, limit: int = 100) -> List[InventoryItem]:
        return self.repository.get_all(skip, limit)

    def update_item(self, item_id: uuid.UUID, item_update: InventoryItemUpdate) -> Optional[InventoryItem]:
        updated_item = self.repository.update(item_id, item_update)
        
        if updated_item:
            # Publish inventory item updated event
            self.publisher.publish_event(
                exchange="shop_events",  # Changed from inventory_events to shop_events
                routing_key="inventory.updated",
                body={
                    "event_type": "inventory_item_updated",
                    "item_id": str(updated_item.id),
                    "shop_id": str(updated_item.shop_id),
                    "name": updated_item.name
                }
            )
        
        return updated_item

    def delete_item(self, item_id: uuid.UUID) -> bool:
        item = self.repository.get_by_id(item_id)
        if not item:
            return False
            
        success = self.repository.delete(item_id)
        
        if success:
            # Publish inventory item deleted event
            self.publisher.publish_event(
                exchange="shop_events",  # Changed from inventory_events to shop_events
                routing_key="inventory.deleted",
                body={
                    "event_type": "inventory_item_deleted",
                    "item_id": str(item_id),
                    "shop_id": str(item.shop_id)
                }
            )
        
        return success
        
    # Add missing methods for image handling
    def update_item_images(self, item_id: uuid.UUID, image_urls: List[str]) -> Optional[InventoryItem]:
        """Update the item with new image URLs, replacing existing ones"""
        item_update = InventoryItemUpdate(image_urls=image_urls)
        return self.update_item(item_id, item_update)
        
    def add_item_images(self, item_id: uuid.UUID, new_image_urls: List[str]) -> Optional[InventoryItem]:
        """Add additional image URLs to an item"""
        # Get current item
        item = self.get_item(item_id)
        if not item:
            return None
            
        # Combine existing and new image URLs
        current_urls = item.image_urls if item.image_urls else []
        updated_urls = current_urls + new_image_urls
        
        # Update the item
        item_update = InventoryItemUpdate(image_urls=updated_urls)
        return self.update_item(item_id, item_update)
        
    def remove_item_image(self, item_id: uuid.UUID, image_url: str) -> Optional[InventoryItem]:
        """Remove a specific image URL from an item"""
        # Get current item
        item = self.get_item(item_id)
        if not item:
            return None
            
        # Remove the specific URL
        current_urls = item.image_urls if item.image_urls else []
        updated_urls = [url for url in current_urls if url != image_url]
        
        # Update the item
        item_update = InventoryItemUpdate(image_urls=updated_urls)
        return self.update_item(item_id, item_update)