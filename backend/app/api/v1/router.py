from fastapi import APIRouter

from app.api.v1.routes import investigations, messages

api_router = APIRouter()
api_router.include_router(investigations.router)
api_router.include_router(messages.router)
