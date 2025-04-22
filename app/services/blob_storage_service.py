# inventory-service/app/services/blob_storage_service.py
from azure.storage.blob import BlobServiceClient, ContentSettings
import os
import uuid
from typing import List, Optional

class BlobStorageService:
    def __init__(self):
        connection_string = os.getenv("AZURE_STORAGE_CONNECTION_STRING")
        self.blob_service_client = BlobServiceClient.from_connection_string(connection_string)
        self.container_name = "inventory-images"

        try:
            container_client = self.blob_service_client.get_container_client(self.container_name)
            if not container_client.exists():
                self.blob_service_client.create_container(self.container_name, public_access="blob")
        except Exception as e:
            print(f"Error creating container: {str(e)}")
    
    async def upload_images(self, files: List, item_id: uuid.UUID) -> List[str]:
        urls = []
        
        for file in files:
            # Generate a unique blob name
            blob_name = f"{item_id}/{uuid.uuid4()}-{file.filename}"
            blob_client = self.blob_service_client.get_blob_client(
                container=self.container_name, 
                blob=blob_name
            )
            
            # Set content type based on file extension
            content_settings = ContentSettings(content_type=file.content_type)
            
            # Upload the file
            file_contents = await file.read()
            blob_client.upload_blob(
                data=file_contents, 
                overwrite=True,
                content_settings=content_settings
            )
            
            # Get the URL
            urls.append(blob_client.url)
            
        return urls
    
    def delete_images(self, image_urls: List[str]) -> None:
        """Delete images from blob storage"""
        for url in image_urls:
            # Extract blob name from URL
            blob_name = url.split(f"{self.container_name}/")[1]
            
            # Delete the blob
            blob_client = self.blob_service_client.get_blob_client(
                container=self.container_name,
                blob=blob_name
            )
            blob_client.delete_blob()