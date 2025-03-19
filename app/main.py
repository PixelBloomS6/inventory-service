from fastapi import FastAPI
from app.routes import router

app = FastAPI(title="Service API")

app.include_router(router)

@app.get("/")
def health_check():
    return {"status": "ok"}