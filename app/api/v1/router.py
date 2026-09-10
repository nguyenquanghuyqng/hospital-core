"""
API v1 router — tổng hợp tất cả endpoint routers.

Tất cả routes được mount dưới prefix ``/api/v1``.
Thứ tự include không ảnh hưởng đến routing nhưng được giữ nhất quán
theo nhóm chức năng: auth → queue → patients → reception → doctor
→ examination → clinical → catalog → billing → appointments → export → admin.
"""
from fastapi import APIRouter

from app.api.v1.endpoints import (
    queue, patients, reception, auth, doctor,
    examination, catalog, admin, clinical, billing, appointments, export,
    prescription,
)

api_router = APIRouter(prefix="/api/v1")
"""Router gốc của API v1 — được mount vào FastAPI app trong ``main.py``."""

api_router.include_router(auth.router)
api_router.include_router(queue.router)
api_router.include_router(patients.router)
api_router.include_router(reception.router)
api_router.include_router(doctor.router)
api_router.include_router(examination.router)
api_router.include_router(clinical.router)
api_router.include_router(catalog.router)
api_router.include_router(billing.router)
api_router.include_router(appointments.router)
api_router.include_router(export.router)
api_router.include_router(admin.router)
api_router.include_router(prescription.router)
