# inventory-service/app/controllers/inventory_controller.py
from fastapi import APIRouter, Depends, HTTPException, status, UploadFile, File, Form
from sqlalchemy.orm import Session
from typing import List, Optional
import uuid
import json
from ..db.database import get_db
from ..models.domain.inventory import InventoryItem, InventoryItemCreate, InventoryItemUpdate
from ..services.inventory_service import InventoryService
from ..services.blob_storage_service import BlobStorageService
from ..messaging.publisher import RabbitMQPublisher

router = APIRouter(
    prefix="/inventory",
    tags=["inventory"],
    responses={404: {"description": "Not found"}},
)

def get_publisher():
    publisher = RabbitMQPublisher()
    try:
        yield publisher
    finally:
        publisher.close()

# Create inventory item with images
@router.post("/items/", response_model=InventoryItem, status_code=status.HTTP_201_CREATED)
async def create_inventory_item(
    shop_id: uuid.UUID = Form(...),
    name: str = Form(...),
    description: str = Form(...),
    category: str = Form(...),
    price: float = Form(...),
    quantity: int = Form(...),
    images: List[UploadFile] = File(None),
    db: Session = Depends(get_db),
    publisher: RabbitMQPublisher = Depends(get_publisher)
):
    # Create inventory item
    item_data = InventoryItemCreate(
        shop_id=shop_id,
        name=name,
        description=description,
        category=category,
        price=price,
        quantity=quantity
    )
    
    inventory_service = InventoryService(db, publisher)
    created_item = inventory_service.create_item(item_data)
    
    # Upload images if provided
    if images:
        blob_service = BlobStorageService()
        image_urls = await blob_service.upload_images(images, created_item.id)
        
        # Update item with image URLs
        item_update = InventoryItemUpdate()
        updated_item = inventory_service.update_item_images(created_item.id, image_urls)
        return updated_item
    
    return created_item

# Add images to existing inventory item
@router.post("/items/{item_id}/images", response_model=InventoryItem)
async def add_images(
    item_id: uuid.UUID,
    images: List[UploadFile] = File(...),
    db: Session = Depends(get_db),
    publisher: RabbitMQPublisher = Depends(get_publisher)
):
    inventory_service = InventoryService(db, publisher)
    item = inventory_service.get_item(item_id)
    if item is None:
        raise HTTPException(status_code=404, detail="Inventory item not found")
    
    # Upload images
    blob_service = BlobStorageService()
    new_image_urls = await blob_service.upload_images(images, item_id)
    
    # Update item with additional image URLs
    updated_item = inventory_service.add_item_images(item_id, new_image_urls)
    return updated_item

# Delete an image from an inventory item
@router.delete("/items/{item_id}/images")
async def delete_image(
    item_id: uuid.UUID,
    image_url: str,
    db: Session = Depends(get_db),
    publisher: RabbitMQPublisher = Depends(get_publisher)
):
    inventory_service = InventoryService(db, publisher)
    item = inventory_service.get_item(item_id)
    if item is None:
        raise HTTPException(status_code=404, detail="Inventory item not found")
    
    # Delete image from blob storage
    blob_service = BlobStorageService()
    blob_service.delete_images([image_url])
    
    # Remove image URL from item
    updated_item = inventory_service.remove_item_image(item_id, image_url)
    return updated_item