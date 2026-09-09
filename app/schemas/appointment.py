"""
Pydantic schemas cho lịch hẹn khám.

Schemas::

    AppointmentCreate / AppointmentUpdate / AppointmentResponse / AppointmentList
"""
from datetime import date, datetime
from typing import Optional, List
from pydantic import BaseModel, Field

from app.models.enums import AppointmentStatus


class AppointmentCreate(BaseModel):
    patient_id:       int
    doctor_id:        Optional[int]  = None
    examination_id:   Optional[int]  = None
    scheduled_date:   date           = Field(..., description="Ngày hẹn")
    scheduled_time:   Optional[str]  = Field(None, max_length=10, description="HH:MM")
    appointment_type: str            = Field("new", pattern="^(new|revisit|followup)$")
    reason:           Optional[str]  = None
    doctor_name:      Optional[str]  = Field(None, max_length=100)
    department:       Optional[str]  = Field(None, max_length=100)
    clinic_room:      Optional[str]  = Field(None, max_length=50)
    note:             Optional[str]  = None
    patient_note:     Optional[str]  = None


class AppointmentUpdate(BaseModel):
    scheduled_date:   Optional[date]               = None
    scheduled_time:   Optional[str]                = None
    status:           Optional[AppointmentStatus]  = None
    appointment_type: Optional[str]                = Field(None, pattern="^(new|revisit|followup)$")
    reason:           Optional[str]                = None
    doctor_id:        Optional[int]                = None
    doctor_name:      Optional[str]                = None
    department:       Optional[str]                = None
    clinic_room:      Optional[str]                = None
    note:             Optional[str]                = None
    patient_note:     Optional[str]                = None
    cancel_reason:    Optional[str]                = None


class AppointmentResponse(BaseModel):
    id:               int
    appointment_no:   str
    patient_id:       int
    doctor_id:        Optional[int]  = None
    examination_id:   Optional[int]  = None
    scheduled_date:   date
    scheduled_time:   Optional[str]  = None
    status:           AppointmentStatus
    appointment_type: str
    reason:           Optional[str]  = None
    doctor_name:      Optional[str]  = None
    department:       Optional[str]  = None
    clinic_room:      Optional[str]  = None
    note:             Optional[str]  = None
    patient_note:     Optional[str]  = None
    created_by:       Optional[str]  = None
    confirmed_at:     Optional[datetime] = None
    arrived_at:       Optional[datetime] = None
    completed_at:     Optional[datetime] = None
    cancelled_at:     Optional[datetime] = None
    cancel_reason:    Optional[str]  = None
    is_reminded:      bool = False
    created_at:       datetime
    updated_at:       datetime
    model_config = {"from_attributes": True}


class AppointmentList(BaseModel):
    """Tóm tắt cho danh sách lịch hẹn."""
    id:             int
    appointment_no: str
    patient_id:     int
    doctor_name:    Optional[str] = None
    scheduled_date: date
    scheduled_time: Optional[str] = None
    status:         AppointmentStatus
    appointment_type: str
    reason:         Optional[str] = None
    created_at:     datetime
    model_config = {"from_attributes": True}
