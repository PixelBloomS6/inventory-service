from sqlalchemy.orm import Session
from typing import List, Optional
import uuid
from ..models.database.inventory import InventoryItemModel
from ..models.domain.inventory import InventoryItem, InventoryItemCreate, InventoryItemUpdate

class InventoryRepository:
    def __init__(self, db: Session):
        self.db = db
  

    def create(self, item: InventoryItemCreate) -> InventoryItem:
        db_item = InventoryItemModel(**item.model_dump())
        self.db.add(db_item)
        self.db.commit()
        self.db.refresh(db_item)
        return self._map_to_domain(db_item)

    def get_by_id(self, item_id: uuid.UUID) -> Optional[InventoryItem]:
        db_item = self.db.query(InventoryItemModel).filter(InventoryItemModel.id == item_id).first()
        if not db_item:
            return None
        return self._map_to_domain(db_item)

    def get_by_shop_id(self, shop_id: uuid.UUID, skip: int = 0, limit: int = 100) -> List[InventoryItem]:
        db_items = self.db.query(InventoryItemModel)\
            .filter(InventoryItemModel.shop_id == shop_id, InventoryItemModel.is_active == True)\
            .offset(skip).limit(limit).all()
        return [self._map_to_domain(item) for item in db_items]

    def get_all(self, skip: int = 0, limit: int = 100) -> List[InventoryItem]:
        db_items = self.db.query(InventoryItemModel).filter(InventoryItemModel.is_active == True).offset(skip).limit(limit).all()
        return [self._map_to_domain(item) for item in db_items]

    def update(self, item_id: uuid.UUID, item_update: InventoryItemUpdate) -> Optional[InventoryItem]:
        db_item = self.db.query(InventoryItemModel).filter(InventoryItemModel.id == item_id).first()
        if not db_item:
            return None
        
        update_data = item_update.model_dump(exclude_unset=True)
        for key, value in update_data.items():
            setattr(db_item, key, value)
        
        self.db.commit()
        self.db.refresh(db_item)
        return self._map_to_domain(db_item)

    def delete(self, item_id: uuid.UUID) -> bool:
        db_item = self.db.query(InventoryItemModel).filter(InventoryItemModel.id == item_id).first()
        if not db_item:
            return False
        
        db_item.is_active = False
        self.db.commit()
        return True

    def _map_to_domain(self, db_item: InventoryItemModel) -> InventoryItem:
        return InventoryItem(
            id=db_item.id,
            shop_id=db_item.shop_id,
            name=db_item.name,
            description=db_item.description,
            category=db_item.category,
            price=db_item.price,
            quantity=db_item.quantity,
            image_urls=db_item.image_urls,  # Changed from image_url to image_urls
            created_at=db_item.created_at,
            updated_at=db_item.updated_at,
            is_active=db_item.is_active
        )