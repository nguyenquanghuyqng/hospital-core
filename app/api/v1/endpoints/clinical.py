"""
Clinical endpoints — kết quả CLS và kiểm tra tương tác thuốc.

Routes:
  GET    /clinical/cls-results/pending           — Danh sách CLS chờ kết quả (KTV/Điều dưỡng)
  GET    /clinical/cls-results/by-exam/{exam_id} — Kết quả CLS của phiếu khám
  GET    /clinical/cls-results/{id}              — Chi tiết một kết quả
  PUT    /clinical/cls-results/{id}              — Điền / cập nhật kết quả
  POST   /clinical/drug-interactions/check       — Kiểm tra tương tác thuốc (mã thuốc)
  GET    /clinical/drug-interactions/exam/{id}   — Kiểm tra tương tác cho phiếu khám hiện tại
"""
from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.session import get_db
from app.core.deps import require_clinical, require_doctor, get_current_user
from app.models.user import User
from app.models.enums import ClsResultStatus
from app.crud.clinical import crud_cls_result, check_drug_interactions, check_drug_interactions_for_exam
from app.crud.catalog import crud_audit
from app.schemas.clinical import (
    ClsResultResponse, ClsResultListItem, ClsResultUpdate,
    DrugInteractionCheck, DrugInteractionResponse,
)

router = APIRouter(prefix="/clinical", tags=["Clinical - Kết quả CLS & Thuốc"])


# ── CLS Results ────────────────────────────────────────────────────────────────

@router.get(
    "/cls-results/pending",
    response_model=List[ClsResultListItem],
    summary="Danh sách CLS đang chờ kết quả",
)
async def list_pending_cls(
    department: Optional[str] = Query(None, description="Lọc theo khoa"),
    skip: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=200),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_clinical),
):
    """
    Danh sách CLS đang ở trạng thái PENDING hoặc IN_PROCESS.
    Dùng cho màn hình khoa xét nghiệm / CĐHA.
    """
    items, _ = await crud_cls_result.list_pending(
        db, department=department, skip=skip, limit=limit
    )
    return items


@router.get(
    "/cls-results/by-exam/{examination_id}",
    response_model=List[ClsResultResponse],
    summary="Kết quả CLS của phiếu khám",
)
async def list_cls_by_exam(
    examination_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_clinical),
):
    """Lấy tất cả kết quả CLS đã/đang thực hiện trong phiếu khám."""
    return await crud_cls_result.list_by_examination(db, examination_id)


@router.get(
    "/cls-results/{result_id}",
    response_model=ClsResultResponse,
    summary="Chi tiết kết quả CLS",
)
async def get_cls_result(
    result_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_clinical),
):
    result = await crud_cls_result.get_full(db, result_id)
    if not result:
        raise HTTPException(status_code=404, detail="Không tìm thấy kết quả CLS")
    return result


@router.put(
    "/cls-results/{result_id}",
    response_model=ClsResultResponse,
    summary="Điền / cập nhật kết quả CLS",
)
async def update_cls_result(
    result_id: int,
    obj_in: ClsResultUpdate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_clinical),
):
    """
    KTV hoặc bác sĩ điền kết quả xét nghiệm.

    - Truyền ``status=in_process`` khi bắt đầu thực hiện.
    - Truyền ``status=completed`` + ``values`` khi có kết quả.
    - ``values`` là danh sách chỉ số — replace-all nếu được truyền.
    - Tự động đánh dấu ``is_abnormal`` nếu chỉ số nằm ngoài khoảng ref.
    """
    result = await crud_cls_result.get_full(db, result_id)
    if not result:
        raise HTTPException(status_code=404, detail="Không tìm thấy kết quả CLS")

    if result.status == ClsResultStatus.CANCELLED:
        raise HTTPException(status_code=400, detail="Kết quả CLS đã huỷ, không thể cập nhật")

    old_status = result.status
    updated = await crud_cls_result.update_result(db, db_obj=result, obj_in=obj_in)

    # Ghi audit log
    await crud_audit.log_change(
        db,
        user_id=current_user.id,
        username=current_user.username,
        action="UPDATE",
        table_name="cls_results",
        record_id=result_id,
        old_data={"status": old_status.value if old_status else None},
        new_data={
            "status": updated.status.value,
            "performed_by": updated.performed_by,
            "is_abnormal": updated.is_abnormal,
        },
        description=f"Cập nhật kết quả CLS: {updated.service_name}",
    )
    await db.commit()
    return updated


# ── Drug Interaction ───────────────────────────────────────────────────────────

@router.post(
    "/drug-interactions/check",
    response_model=DrugInteractionResponse,
    summary="Kiểm tra tương tác thuốc theo mã thuốc",
)
async def check_interactions(
    obj_in: DrugInteractionCheck,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_doctor),
):
    """
    Kiểm tra tương tác / trùng hoạt chất giữa danh sách mã thuốc.

    Trả về danh sách cảnh báo. ``has_warnings=false`` nghĩa là an toàn.
    """
    warnings = await check_drug_interactions(db, obj_in.drug_codes)
    return DrugInteractionResponse(
        has_warnings=len(warnings) > 0,
        warnings=warnings,
    )


@router.get(
    "/drug-interactions/exam/{examination_id}",
    response_model=DrugInteractionResponse,
    summary="Kiểm tra tương tác thuốc trong phiếu khám",
)
async def check_interactions_for_exam(
    examination_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_doctor),
):
    """
    Kiểm tra tất cả thuốc đang kê trong phiếu khám hiện tại.
    Gọi sau khi thêm / xóa thuốc để hiển thị cảnh báo tức thì.
    """
    warnings = await check_drug_interactions_for_exam(db, examination_id)
    return DrugInteractionResponse(
        has_warnings=len(warnings) > 0,
        warnings=warnings,
    )
