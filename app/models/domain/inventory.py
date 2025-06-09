from pydantic import BaseModel, ConfigDict, Field
from datetime import datetime
from typing import Optional, List
from uuid import UUID, uuid4

class InventoryItemBase(BaseModel):
    shop_id: UUID
    name: str
    description: str
    category: str
    price: float = Field(..., gt=0, description="Price must be greater than 0")
    quantity: int = Field(..., ge=0, description="Quantity must be non-negative")

class InventoryItemCreate(InventoryItemBase):
    pass

class InventoryItemUpdate(BaseModel):
    name: Optional[str] = None
    description: Optional[str] = None
    category: Optional[str] = None
    price: Optional[float] = Field(None, gt=0)
    quantity: Optional[int] = Field(None, ge=0)
    image_urls: Optional[List[str]] = None

class InventoryItem(InventoryItemBase):
    """Full inventory item schema including metadata."""
    id: UUID = Field(default_factory=uuid4)
    image_urls: Optional[List[str]] = Field(default_factory=list)
    created_at: datetime
    updated_at: datetime
    is_active: bool

    class Config:
        model_config = ConfigDict(from_attributes=True)
