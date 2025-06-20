from fastapi import FastAPI, Request, Response
from fastapi.middleware.cors import CORSMiddleware
from prometheus_client import Counter, Histogram, Gauge, generate_latest, CONTENT_TYPE_LATEST
import uvicorn
import time
from .routers.inventory_router import router as inventory_router
from .db.database import Base, get_engine


# Create tables in the database
Base.metadata.create_all(bind=get_engine())

# Prometheus metrics
REQUEST_COUNT = Counter(
    'fastapi_requests_total',
    'Total requests',
    ['method', 'endpoint', 'status_code']
)

REQUEST_DURATION = Histogram(
    'fastapi_request_duration_seconds',
    'Request duration in seconds',
    ['method', 'endpoint']
)

ACTIVE_REQUESTS = Gauge(
    'fastapi_active_requests',
    'Number of active requests'
)

INVENTORY_ITEMS = Gauge(
    'inventory_items_total',
    'Total number of inventory items',
    ['shop_id', 'category']
)

DATABASE_CONNECTIONS = Gauge(
    'database_connections_active',
    'Number of active database connections'
)

app = FastAPI(
    title="Inventory Service",
    description="Manages inventory for shops in PixelBloom with Prometheus monitoring",
    version="1.0.0"
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.middleware("http")
async def prometheus_middleware(request: Request, call_next):
    """Middleware to collect Prometheus metrics"""
    start_time = time.time()
    ACTIVE_REQUESTS.inc()
    
    try:
        response = await call_next(request)
        
        # Record metrics
        duration = time.time() - start_time
        REQUEST_DURATION.labels(
            method=request.method,
            endpoint=request.url.path
        ).observe(duration)
        
        REQUEST_COUNT.labels(
            method=request.method,
            endpoint=request.url.path,
            status_code=response.status_code
        ).inc()
        
        return response
    
    finally:
        ACTIVE_REQUESTS.dec()


@app.get("/metrics")
async def get_metrics():
    """Prometheus metrics endpoint"""
    return Response(
        generate_latest(),
        media_type=CONTENT_TYPE_LATEST
    )


@app.get("/health")
def health_check():
    """Enhanced health check with metrics"""
    return {
        "status": "healthy",
        "service": "inventory-service",
        "metrics_enabled": True
    }


# Include routers
app.include_router(inventory_router)


if __name__ == "__main__":
    uvicorn.run("app.main:app", host="0.0.0.0", port=8001, reload=True)