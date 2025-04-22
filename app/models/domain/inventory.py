from pydantic import BaseModel, ConfigDict, Field
from datetime import datetime
from typing import Optional, List
from uuid import UUID, uuid4

class InventoryItemBase(BaseModel):
    shop_id: UUID
    name: str
    description: str
    category: str
    price: float = Field(gt=0)
    quantity: int = Field(ge=0)

class InventoryItemCreate(InventoryItemBase):
    pass

class InventoryItemUpdate(BaseModel):
    name: Optional[str] = None
    description: Optional[str] = None
    category: Optional[str] = None
    price: Optional[float] = Field(None, gt=0)
    quantity: Optional[int] = Field(None, ge=0)

class InventoryItem(InventoryItemBase):
    id: UUID
    image_urls: List[str] = []
    created_at: datetime
    updated_at: datetime
    is_active: bool

    class Config:
        model_config = ConfigDict(from_attributes=True)