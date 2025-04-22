# inventory-service/app/models/database/inventory.py
from sqlalchemy import Column, String, Boolean, DateTime, Integer, Float, ForeignKey, func, ARRAY
from sqlalchemy.dialects.postgresql import UUID, JSONB
import uuid
from ...db.database import Base

class InventoryItemModel(Base):
    __tablename__ = "inventory_items"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    shop_id = Column(UUID(as_uuid=True), nullable=False, index=True)
    name = Column(String, nullable=False)
    description = Column(String, nullable=False)
    category = Column(String, nullable=False)
    price = Column(Float, nullable=False)
    quantity = Column(Integer, nullable=False)
    image_urls = Column(ARRAY(String), nullable=True)  # Array of image URLs from blob storage
    created_at = Column(DateTime, server_default=func.now())
    updated_at = Column(DateTime, server_default=func.now(), onupdate=func.now())
    is_active = Column(Boolean, default=True)