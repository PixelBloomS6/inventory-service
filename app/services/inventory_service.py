from typing import List, Optional
import uuid
from sqlalchemy.orm import Session
from ..repositories.inventory_repository import InventoryRepository
from ..models.domain.inventory import InventoryItem, InventoryItemCreate, InventoryItemUpdate
# from ..messaging.publisher import RabbitMQPublisher

class InventoryService:
    def __init__(self, db: Session):
        self.repository = InventoryRepository(db)
        # self.publisher = publisher

    def create_item(self, item: InventoryItemCreate) -> InventoryItem:
        created_item = self.repository.create(item)
        return created_item
        # Publish inventory item created event
        # self.publisher.publish_event(
        #     exchange="inventory_events",
        #     routing_key="inventory.created",
        #     body={
        #         "event_type": "inventory_item_created",
        #         "item_id": str(created_item.id),
        #         "shop_id": str(created_item.shop_id),
        #         "name": created_item.name
        #     }
        # )

    def get_item(self, item_id: uuid.UUID) -> Optional[InventoryItem]:
        return self.repository.get_by_id(item_id)

    def get_items_by_shop(self, shop_id: uuid.UUID, skip: int = 0, limit: int = 100) -> List[InventoryItem]:
        return self.repository.get_by_shop_id(shop_id, skip, limit)

    def get_all_items(self, skip: int = 0, limit: int = 100) -> List[InventoryItem]:
        return self.repository.get_all(skip, limit)

    def update_item(self, item_id: uuid.UUID, item_update: InventoryItemUpdate) -> Optional[InventoryItem]:
        updated_item = self.repository.update(item_id, item_update)
        
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
        
        return updated_item

    def delete_item(self, item_id: uuid.UUID) -> bool:
        item = self.repository.get_by_id(item_id)
        if not item:
            return False
            
        success = self.repository.delete(item_id)
        
        # if success:
        #     # Publish inventory item deleted event
        #     self.publisher.publish_event(
        #         exchange="inventory_events",
        #         routing_key="inventory.deleted",
        #         body={
        #             "event_type": "inventory_item_deleted",
        #             "item_id": str(item_id),
        #             "shop_id": str(item.shop_id)
        # #         }
        #     )
        
        return success
    
    
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