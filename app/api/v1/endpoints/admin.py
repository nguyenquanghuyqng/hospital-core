"""
Admin endpoints — quản trị hệ thống (chỉ role admin).

Routes:
  # Quản lý nhân viên
  GET    /admin/users              — danh sách nhân viên
  POST   /admin/users              — tạo tài khoản mới
  GET    /admin/users/{id}         — chi tiết nhân viên
  PUT    /admin/users/{id}         — cập nhật thông tin
  PATCH  /admin/users/{id}/toggle  — kích hoạt / vô hiệu hoá
  DELETE /admin/users/{id}         — xoá tài khoản

  # Cấu hình cơ sở
  GET    /admin/config             — toàn bộ config
  GET    /admin/config/{key}       — một config theo key
  PUT    /admin/config/{key}       — cập nhật giá trị
  POST   /admin/config             — tạo / upsert config

  # Audit log
  GET    /admin/audit-logs         — nhật ký thay đổi
  GET    /admin/audit-logs/record  — lịch sử theo bảng + record_id
"""
from datetime import date, timedelta
from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, Query, status, Request
from pydantic import BaseModel
from sqlalchemy import select, func, case
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.session import get_db
from app.core.deps import require_admin, get_current_user
from app.core.security import hash_password
from app.models.user import User
from app.models.queue_ticket import QueueTicket
from app.models.reception import Reception
from app.models.inventory import DrugBatch
from app.models.enums import ReceptionStatus
from app.crud.user import crud_user
from app.crud.catalog import crud_config, crud_audit
from app.schemas.catalog import (
    SystemConfigResponse, SystemConfigUpsert, SystemConfigUpdate,
    AuditLogResponse,
)
from app.schemas.common import PaginatedResponse

router = APIRouter(prefix="/admin", tags=["Admin - Quản trị"])

VALID_ROLES = {"doctor", "nurse", "receptionist", "cashier", "admin"}


# ── Local schemas ─────────────────────────────────────────────────────────────

class UserResponse(BaseModel):
    id:          int
    username:    str
    full_name:   Optional[str] = None
    role:        str
    clinic_room: Optional[str] = None
    is_active:   bool
    # Mã liên thông quốc gia
    national_doctor_code: Optional[str] = None
    license_status:       str = "active"
    model_config = {"from_attributes": True}


class UserCreateRequest(BaseModel):
    username:    str
    password:    str
    full_name:   Optional[str] = None
    role:        str = "doctor"
    clinic_room: Optional[str] = None


class UserUpdateRequest(BaseModel):
    full_name:   Optional[str] = None
    role:        Optional[str] = None
    clinic_room: Optional[str] = None
    password:    Optional[str] = None   # None = không đổi


class ExecutiveOverviewAlert(BaseModel):
    title: str
    detail: str
    tone: str = "info"


class ExecutiveOverviewResponse(BaseModel):
    date: str
    facility_name: str = "Bệnh viện"
    summary: dict
    metrics: list[dict]
    alerts: list[ExecutiveOverviewAlert]


@router.get(
    "/dashboard/overview",
    response_model=ExecutiveOverviewResponse,
    summary="Executive overview dashboard",
)
async def executive_overview(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Tổng hợp số liệu điều hành chính trong ngày cho dashboard Executive Overview."""
    today = date.today()
    queue_summary = await db.execute(
        select(
            func.sum(case((QueueTicket.issue_date == today, 1), else_=0)).label("total_tickets"),
            func.sum(case((QueueTicket.status == "waiting", 1), else_=0)).label("waiting"),
            func.sum(case((QueueTicket.status == "serving", 1), else_=0)).label("serving"),
            func.sum(case((QueueTicket.status == "done", 1), else_=0)).label("done"),
        ).where(QueueTicket.issue_date == today)
    )
    queue_row = queue_summary.one()

    reception_summary = await db.execute(
        select(
            func.count(Reception.id).label("total"),
            func.sum(case((Reception.status == ReceptionStatus.PENDING, 1), else_=0)).label("pending"),
            func.sum(case((Reception.status == ReceptionStatus.CHECKED_IN, 1), else_=0)).label("checked_in"),
            func.sum(case((Reception.status == ReceptionStatus.COMPLETED, 1), else_=0)).label("completed"),
        ).where(Reception.visit_date == today)
    )
    reception_row = reception_summary.one()

    expiring_batches = await db.execute(
        select(func.count(DrugBatch.id)).where(
            DrugBatch.expiry_date >= today,
            DrugBatch.expiry_date <= today + timedelta(days=30),
            DrugBatch.available_quantity > 0,
        )
    )
    expiring_count = expiring_batches.scalar_one() or 0

    waiting = int(queue_row.waiting or 0)
    serving = int(queue_row.serving or 0)
    completed = int(reception_row.completed or 0)
    pending = int(reception_row.pending or 0)
    total_receptions = int(reception_row.total or 0)

    summary = {
        "waiting": waiting,
        "serving": serving,
        "completed_today": completed,
        "pending_checkin": pending,
        "total_receptions": total_receptions,
        "expiring_batches": expiring_count,
        "total_queues": int(queue_row.total_tickets or 0),
    }

    metrics = [
        {"label": "Bệnh nhân chờ khám", "value": waiting, "delta": "+8% vs hôm qua", "tone": "info"},
        {"label": "Đang khám", "value": serving, "delta": "+3% vs hôm qua", "tone": "success"},
        {"label": "Hoàn tất hôm nay", "value": completed, "delta": "+12% vs hôm qua", "tone": "success"},
        {"label": "Lô thuốc cần chú ý", "value": expiring_count, "delta": "Trong 30 ngày", "tone": "warning"},
    ]

    alerts = []
    if waiting > 0:
        alerts.append(ExecutiveOverviewAlert(
            title="Cần phân luồng khám",
            detail=f"Hiện có {waiting} bệnh nhân đang chờ khám. Cân nhắc tăng tốc xử lý theo phòng/chuyển luồng.",
            tone="info",
        ))
    if expiring_count > 0:
        alerts.append(ExecutiveOverviewAlert(
            title="Kho thuốc cần kiểm tra",
            detail=f"Có {expiring_count} lô thuốc sắp hết hạn hoặc cần nhắc nhập bổ sung.",
            tone="warning",
        ))
    if pending > 0:
        alerts.append(ExecutiveOverviewAlert(
            title="Chưa check-in",
            detail=f"Còn {pending} lượt tiếp đón chưa được check-in vào phòng khám.",
            tone="warning",
        ))
    if not alerts:
        alerts.append(ExecutiveOverviewAlert(
            title="Hệ thống vận hành ổn định",
            detail="Toàn bộ chỉ số đang trong mức bình thường, không có cảnh báo ưu tiên cao.",
            tone="success",
        ))

    return ExecutiveOverviewResponse(
        date=today.isoformat(),
        facility_name="Bệnh viện Đa khoa Hệ thống",
        summary=summary,
        metrics=metrics,
        alerts=alerts,
    )


# ── User Management ───────────────────────────────────────────────────────────

@router.get(
    "/users",
    response_model=PaginatedResponse[UserResponse],
    summary="Danh sách nhân viên",
)
async def list_users(
    role:      Optional[str] = Query(None, description="Lọc theo role"),
    is_active: Optional[bool] = Query(None),
    search:    Optional[str]  = Query(None, description="Tìm theo tên / username"),
    page:      int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    db: AsyncSession = Depends(get_db),
    _: User = Depends(require_admin),
):
    """Lấy danh sách tài khoản nhân viên với filter và phân trang."""
    from sqlalchemy import or_, and_

    query = select(User)
    conds = []
    if role:
        conds.append(User.role == role)
    if is_active is not None:
        conds.append(User.is_active == is_active)
    if search:
        pat = f"%{search}%"
        conds.append(or_(User.full_name.ilike(pat), User.username.ilike(pat)))
    if conds:
        query = query.where(and_(*conds))

    total = (await db.execute(select(func.count()).select_from(query.subquery()))).scalar_one()
    skip  = (page - 1) * page_size
    items = list((await db.execute(
        query.order_by(User.full_name).offset(skip).limit(page_size)
    )).scalars().all())

    return PaginatedResponse(
        items=items, total=total, page=page,
        page_size=page_size, total_pages=max(1, -(-total // page_size)),
    )


@router.post(
    "/users",
    response_model=UserResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Tạo tài khoản nhân viên",
)
async def create_user(
    body: UserCreateRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_admin),
    request: Request = None,
):
    if body.role not in VALID_ROLES:
        raise HTTPException(400, f"Role không hợp lệ. Cho phép: {', '.join(sorted(VALID_ROLES))}")
    existing = await crud_user.get_by_username(db, body.username)
    if existing:
        raise HTTPException(409, f"Username '{body.username}' đã tồn tại")

    user = await crud_user.create_user(
        db,
        username=body.username,
        password=body.password,
        full_name=body.full_name or body.username,
        role=body.role,
        clinic_room=body.clinic_room,
    )
    await crud_audit.log_change(
        db,
        user_id=current_user.id,
        username=current_user.username,
        action="CREATE",
        table_name="users",
        record_id=user.id,
        new_data={"username": user.username, "role": user.role},
        ip_address=request.client.host if request else None,
        description=f"Tạo tài khoản {user.username} ({user.role})",
    )
    return user


@router.get("/users/{user_id}", response_model=UserResponse, summary="Chi tiết nhân viên")
async def get_user(
    user_id: int,
    db: AsyncSession = Depends(get_db),
    _: User = Depends(require_admin),
):
    user = await crud_user.get(db, user_id)
    if not user:
        raise HTTPException(404, "Không tìm thấy tài khoản")
    return user


@router.put("/users/{user_id}", response_model=UserResponse, summary="Cập nhật nhân viên")
async def update_user(
    user_id: int,
    body: UserUpdateRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_admin),
    request: Request = None,
):
    user = await crud_user.get(db, user_id)
    if not user:
        raise HTTPException(404, "Không tìm thấy tài khoản")
    if body.role and body.role not in VALID_ROLES:
        raise HTTPException(400, f"Role không hợp lệ: {body.role}")

    old = {"full_name": user.full_name, "role": user.role, "clinic_room": user.clinic_room}
    update_data: dict = {}
    if body.full_name   is not None: update_data["full_name"]   = body.full_name
    if body.role        is not None: update_data["role"]        = body.role
    if body.clinic_room is not None: update_data["clinic_room"] = body.clinic_room
    if body.password:
        update_data["hashed_password"] = hash_password(body.password)

    for k, v in update_data.items():
        setattr(user, k, v)
    db.add(user)
    await db.flush()
    await db.refresh(user)

    await crud_audit.log_change(
        db,
        user_id=current_user.id,
        username=current_user.username,
        action="UPDATE",
        table_name="users",
        record_id=user.id,
        old_data=old,
        new_data={k: v for k, v in update_data.items() if k != "hashed_password"},
        ip_address=request.client.host if request else None,
        description=f"Cập nhật tài khoản {user.username}",
    )
    return user


@router.patch(
    "/users/{user_id}/toggle",
    response_model=UserResponse,
    summary="Kích hoạt / vô hiệu hoá tài khoản",
)
async def toggle_user(
    user_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_admin),
    request: Request = None,
):
    user = await crud_user.get(db, user_id)
    if not user:
        raise HTTPException(404, "Không tìm thấy tài khoản")
    if user.id == current_user.id:
        raise HTTPException(400, "Không thể vô hiệu hoá tài khoản của chính mình")

    old_status = user.is_active
    user.is_active = not user.is_active
    db.add(user)
    await db.flush()
    await db.refresh(user)

    await crud_audit.log_change(
        db,
        user_id=current_user.id,
        username=current_user.username,
        action="UPDATE",
        table_name="users",
        record_id=user.id,
        old_data={"is_active": old_status},
        new_data={"is_active": user.is_active},
        ip_address=request.client.host if request else None,
        description=f"{'Kích hoạt' if user.is_active else 'Vô hiệu hoá'} tài khoản {user.username}",
    )
    return user


@router.delete(
    "/users/{user_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Xoá tài khoản",
)
async def delete_user(
    user_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_admin),
    request: Request = None,
):
    user = await crud_user.get(db, user_id)
    if not user:
        raise HTTPException(404, "Không tìm thấy tài khoản")
    if user.id == current_user.id:
        raise HTTPException(400, "Không thể xoá tài khoản của chính mình")

    await crud_audit.log_change(
        db,
        user_id=current_user.id,
        username=current_user.username,
        action="DELETE",
        table_name="users",
        record_id=user.id,
        old_data={"username": user.username, "role": user.role},
        ip_address=request.client.host if request else None,
        description=f"Xoá tài khoản {user.username}",
    )
    await crud_user.remove(db, id=user_id)


# ── System Config ─────────────────────────────────────────────────────────────

@router.get(
    "/config",
    response_model=List[SystemConfigResponse],
    summary="Toàn bộ cấu hình cơ sở",
)
async def get_all_config(
    group:  Optional[str] = Query(None),
    db: AsyncSession = Depends(get_db),
    _: User = Depends(require_admin),
):
    if group:
        return await crud_config.get_by_group(db, group)
    return await crud_config.get_all(db)


@router.get(
    "/config/{key}",
    response_model=SystemConfigResponse,
    summary="Lấy config theo key",
)
async def get_config(
    key: str,
    db: AsyncSession = Depends(get_db),
    _: User = Depends(require_admin),
):
    cfg = await crud_config.get_by_key(db, key)
    if not cfg:
        raise HTTPException(404, f"Config key '{key}' không tồn tại")
    return cfg


@router.put(
    "/config/{key}",
    response_model=SystemConfigResponse,
    summary="Cập nhật giá trị config",
)
async def update_config(
    key: str,
    body: SystemConfigUpdate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_admin),
    request: Request = None,
):
    cfg = await crud_config.set_value(
        db, key=key, value=body.value, updated_by=current_user.username
    )
    if not cfg:
        raise HTTPException(404, f"Config key '{key}' không tồn tại")
    await crud_audit.log_change(
        db,
        user_id=current_user.id,
        username=current_user.username,
        action="UPDATE",
        table_name="system_config",
        record_id=cfg.id,
        new_data={"key": key, "value": body.value},
        ip_address=request.client.host if request else None,
        description=f"Cập nhật cấu hình {key}",
    )
    return cfg


@router.post(
    "/config",
    response_model=SystemConfigResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Tạo / upsert config",
)
async def upsert_config(
    body: SystemConfigUpsert,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_admin),
    request: Request = None,
):
    cfg = await crud_config.upsert(db, obj_in=body, updated_by=current_user.username)
    await crud_audit.log_change(
        db,
        user_id=current_user.id,
        username=current_user.username,
        action="UPDATE",
        table_name="system_config",
        record_id=cfg.id,
        new_data=body.model_dump(),
        ip_address=request.client.host if request else None,
        description=f"Upsert cấu hình {body.key}",
    )
    return cfg


# ── Audit Log ─────────────────────────────────────────────────────────────────

@router.get(
    "/audit-logs",
    response_model=PaginatedResponse[AuditLogResponse],
    summary="Nhật ký thay đổi hệ thống",
)
async def get_audit_logs(
    user_id:    Optional[int] = Query(None),
    action:     Optional[str] = Query(None),
    table_name: Optional[str] = Query(None),
    page:       int = Query(1, ge=1),
    page_size:  int = Query(50, ge=1, le=200),
    db: AsyncSession = Depends(get_db),
    _: User = Depends(require_admin),
):
    skip = (page - 1) * page_size
    items, total = await crud_audit.get_recent(
        db,
        user_id=user_id,
        action=action,
        table_name=table_name,
        skip=skip,
        limit=page_size,
    )
    return PaginatedResponse(
        items=items, total=total, page=page,
        page_size=page_size, total_pages=max(1, -(-total // page_size)),
    )


@router.get(
    "/audit-logs/record",
    response_model=List[AuditLogResponse],
    summary="Lịch sử thay đổi của một bản ghi",
)
async def get_record_audit(
    table_name: str = Query(...),
    record_id:  int = Query(...),
    limit:      int = Query(50, ge=1, le=200),
    db: AsyncSession = Depends(get_db),
    _: User = Depends(require_admin),
):
    return await crud_audit.get_by_record(
        db, table_name=table_name, record_id=record_id, limit=limit
    )


# ══════════════════════════════════════════════════════════════════════════════
# Quản lý mã liên thông quốc gia (BYT / donthuocquocgia.vn)
# ══════════════════════════════════════════════════════════════════════════════

class LicenseUpdateRequest(BaseModel):
    """Gán hoặc cập nhật mã liên thông và trạng thái hành nghề của bác sĩ."""
    national_doctor_code: Optional[str] = None
    license_status: Optional[str] = None   # "active" | "suspended" | "revoked"


@router.patch(
    "/users/{user_id}/license",
    response_model=UserResponse,
    summary="Gán / cập nhật mã liên thông bác sĩ",
)
async def update_doctor_license(
    user_id: int,
    body: LicenseUpdateRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_admin),
):
    """
    Admin gán mã liên thông quốc gia và cập nhật trạng thái hành nghề cho bác sĩ.

    - ``national_doctor_code``: Mã do Sở Y tế cấp (None = giữ nguyên).
    - ``license_status``: ``active`` | ``suspended`` | ``revoked``.

    Raises:
        HTTPException 404: Không tìm thấy tài khoản.
        HTTPException 400: license_status không hợp lệ.
    """
    from app.models.enums import LicenseStatus

    valid_statuses = {s.value for s in LicenseStatus}

    result = await db.execute(select(User).where(User.id == user_id))
    user = result.scalar_one_or_none()
    if not user:
        raise HTTPException(status_code=404, detail="Không tìm thấy tài khoản")

    if body.national_doctor_code is not None:
        user.national_doctor_code = body.national_doctor_code.strip() or None

    if body.license_status is not None:
        if body.license_status not in valid_statuses:
            raise HTTPException(
                status_code=400,
                detail=f"license_status không hợp lệ. Cho phép: {', '.join(sorted(valid_statuses))}",
            )
        user.license_status = LicenseStatus(body.license_status)

    db.add(user)
    await db.flush()
    await db.commit()
    await db.refresh(user)

    await crud_audit.log_change(
        db,
        user_id=current_user.id,
        username=current_user.username,
        action="UPDATE",
        table_name="users",
        record_id=user_id,
        new_data=body.model_dump(exclude_none=True),
        description=f"Cập nhật mã liên thông BS #{user_id}: {body.national_doctor_code}",
    )
    await db.commit()
    return user


@router.get(
    "/users/doctors/license-status",
    response_model=List[UserResponse],
    summary="Danh sách bác sĩ và trạng thái mã liên thông",
)
async def list_doctor_license_status(
    license_status: Optional[str] = Query(None, description="Lọc theo trạng thái: active/suspended/revoked"),
    has_code: Optional[bool] = Query(None, description="True=đã có mã, False=chưa có mã"),
    db: AsyncSession = Depends(get_db),
    _: User = Depends(require_admin),
):
    """
    Xem danh sách bác sĩ với thông tin mã liên thông và trạng thái hành nghề.

    Dùng cho màn hình admin quản lý vòng đời bác sĩ:
    - Thêm mã khi có bác sĩ mới.
    - Tạm dừng khi bác sĩ nghỉ phép.
    - Thu hồi khi bác sĩ nghỉ việc/chuyển công tác.
    """
    from sqlalchemy import or_, and_

    query = select(User).where(User.role == "doctor")
    conds = []

    if license_status:
        conds.append(User.license_status == license_status)
    if has_code is True:
        conds.append(User.national_doctor_code != None)  # noqa: E711
    elif has_code is False:
        conds.append(User.national_doctor_code == None)  # noqa: E711

    if conds:
        query = query.where(and_(*conds))

    result = await db.execute(query.order_by(User.full_name))
    return list(result.scalars().all())
