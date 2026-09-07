from fastapi import APIRouter

from app.api.v1.endpoints import queue, patients, reception

api_router = APIRouter(prefix="/api/v1")

api_router.include_router(queue.router)
api_router.include_router(patients.router)
api_router.include_router(reception.router)
