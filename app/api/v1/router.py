from fastapi import APIRouter

from app.api.v1.endpoints import queue, patients, reception, auth, doctor, examination

api_router = APIRouter(prefix="/api/v1")

api_router.include_router(auth.router)
api_router.include_router(queue.router)
api_router.include_router(patients.router)
api_router.include_router(reception.router)
api_router.include_router(doctor.router)
api_router.include_router(examination.router)
