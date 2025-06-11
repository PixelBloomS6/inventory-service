# inventory-service/app/main.py
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
import uvicorn
from .routers.inventory_router import router as inventory_router
from .db.database import Base, engine
# from .messaging.consumer import start_inventory_consumer # Import the consumer startup function

# Create tables in the database
Base.metadata.create_all(bind=engine)

app = FastAPI(
    title="Inventory Service",
    description="Manages inventory for shops in PixelBloom",
    version="1.0.0"
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(inventory_router)

@app.get("/health")
def health_check():
    return {"status": "healthy"}

# --- Add this section to start the consumer ---
# @app.on_event("startup")
# async def startup_event():
#     print("Starting Inventory Consumer...")
#     start_inventory_consumer()

if __name__ == "__main__":
    uvicorn.run("app.main:app", host="0.0.0.0", port=8001, reload=True)