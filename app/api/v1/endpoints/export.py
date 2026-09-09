"""
Export endpoints — xuất dữ liệu BHYT và báo cáo.

Routes:
  POST /export/bhyt-xml    — Xuất XML BHYT cho danh sách phiếu khám
  GET  /export/bhyt-xml/{exam_id} — Xuất XML BHYT cho 1 phiếu khám
"""
from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from fastapi.responses import Response
from sqlalchemy.ext.asyncio import AsyncSession
from pydantic import BaseModel

from app.db.session import get_db
from app.core.deps import require_cashier, require_admin
from app.models.user import User
from app.models.enums import ExaminationStatus
from app.models.examination import Examination
from app.services.bhyt_xml import build_bhyt_xml
from sqlalchemy import select

router = APIRouter(prefix="/export", tags=["Export - Xuất dữ liệu"])


class BhytExportRequest(BaseModel):
    examination_ids: List[int]
    batch_code: Optional[str] = None


@router.post(
    "/bhyt-xml",
    summary="Xuất XML BHYT cho danh sách phiếu khám",
    response_class=Response,
)
async def export_bhyt_xml_batch(
    obj_in: BhytExportRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_cashier),
):
    """
    Xuất file XML BHYT theo chuẩn Thông tư 48/2017/TT-BYT.

    Yêu cầu: tất cả phiếu khám phải ở trạng thái COMPLETED.

    Body:
        examination_ids: Danh sách ID phiếu khám.
        batch_code: Mã đợt xuất (tự sinh nếu không truyền, VD: DT20260909).

    Returns:
        File XML UTF-8, Content-Disposition: attachment.
    """
    if not obj_in.examination_ids:
        raise HTTPException(status_code=400, detail="Cần ít nhất một phiếu khám")
    if len(obj_in.examination_ids) > 500:
        raise HTTPException(status_code=400, detail="Tối đa 500 phiếu mỗi lần xuất")

    # Kiểm tra tất cả phiếu đã COMPLETED
    rows = await db.execute(
        select(Examination.id, Examination.status)
        .where(Examination.id.in_(obj_in.examination_ids))
    )
    found = {row[0]: row[1] for row in rows.all()}
    not_found = [i for i in obj_in.examination_ids if i not in found]
    if not_found:
        raise HTTPException(
            status_code=404,
            detail=f"Không tìm thấy phiếu khám: {not_found}",
        )
    not_completed = [i for i, s in found.items() if s != ExaminationStatus.COMPLETED]
    if not_completed:
        raise HTTPException(
            status_code=400,
            detail=f"Các phiếu chưa hoàn tất: {not_completed}",
        )

    xml_bytes = await build_bhyt_xml(
        db,
        obj_in.examination_ids,
        batch_code=obj_in.batch_code,
    )

    from datetime import date
    filename = f"BHYT_{obj_in.batch_code or date.today().strftime('%Y%m%d')}.xml"
    return Response(
        content=xml_bytes,
        media_type="application/xml; charset=utf-8",
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )


@router.get(
    "/bhyt-xml/{examination_id}",
    summary="Xuất XML BHYT cho 1 phiếu khám",
    response_class=Response,
)
async def export_bhyt_xml_single(
    examination_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_cashier),
):
    """Xuất XML BHYT cho một phiếu khám đơn lẻ (preview / in ngay)."""
    row = await db.execute(
        select(Examination).where(Examination.id == examination_id)
    )
    exam = row.scalar_one_or_none()
    if not exam:
        raise HTTPException(status_code=404, detail="Không tìm thấy phiếu khám")
    if exam.status != ExaminationStatus.COMPLETED:
        raise HTTPException(status_code=400, detail="Phiếu khám chưa hoàn tất")

    xml_bytes = await build_bhyt_xml(db, [examination_id])
    filename  = f"BHYT_exam_{examination_id}.xml"
    return Response(
        content=xml_bytes,
        media_type="application/xml; charset=utf-8",
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )
