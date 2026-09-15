"""Provider-neutral BHYT eligibility and claim lifecycle service."""
import hashlib
import json
from datetime import date, datetime, timezone
from decimal import Decimal
from typing import Optional

import httpx
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.core.config import settings
from app.models.bhyt import BhytClaim, BhytClaimAttempt, BhytClaimLine, BhytEligibilityCheck
from app.models.billing import Bill
from app.models.reception import Reception
from app.services.bhyt_xml import build_bhyt_xml


async def check_eligibility(db: AsyncSession, reception: Reception, insurance_number: str, user_id: int) -> BhytEligibilityCheck:
    today = date.today()
    valid = (
        insurance_number == reception.insurance_number
        and (reception.insurance_valid_from is None or reception.insurance_valid_from <= today)
        and (reception.insurance_valid_to is None or reception.insurance_valid_to >= today)
    )
    result = BhytEligibilityCheck(
        patient_id=reception.patient_id,
        reception_id=reception.id,
        insurance_number=insurance_number,
        status="eligible" if valid else "ineligible",
        response_code="LOCAL_VALIDATION",
        response_payload=json.dumps({"source": "local_validation", "checked_at": today.isoformat()}),
        valid_from=reception.insurance_valid_from,
        valid_to=reception.insurance_valid_to,
        coverage_percent=Decimal("80") if valid else Decimal("0"),
        checked_by=user_id,
    )
    db.add(result)
    await db.flush()
    return result


async def prepare_claim(db: AsyncSession, bill: Bill, user_id: int) -> BhytClaim:
    if not bill.examination_id:
        raise ValueError("Hóa đơn chưa liên kết phiếu khám.")
    if not bill.insurance_number:
        raise ValueError("Hóa đơn chưa có số thẻ BHYT.")
    existing = await db.scalar(
        select(BhytClaim).where(BhytClaim.bill_id == bill.id).order_by(BhytClaim.created_at.desc())
    )
    if existing and existing.status not in {"rejected", "correction"}:
        return existing

    payload = await build_bhyt_xml(db, [bill.examination_id])
    claim = BhytClaim(
        bill_id=bill.id,
        examination_id=bill.examination_id,
        claim_number=f"BH{datetime.now(timezone.utc):%Y%m%d}{bill.id:08d}",
        status="ready",
        payload_xml=payload.decode("utf-8"),
        created_by=user_id,
    )
    db.add(claim)
    await db.flush()
    for item in bill.items or []:
        db.add(BhytClaimLine(
            claim_id=claim.id,
            bill_item_id=item.id,
            item_code=item.item_code,
            item_name=item.item_name,
            quantity=item.quantity,
            total_amount=item.total_amount or Decimal("0"),
            bhyt_amount=item.bhyt_amount or Decimal("0"),
        ))
    await db.flush()
    return claim


async def submit_claim(db: AsyncSession, claim: BhytClaim) -> BhytClaim:
    if claim.status not in {"ready", "error"}:
        raise ValueError(f"Claim đang ở trạng thái {claim.status}.")
    payload = claim.payload_xml or ""
    request_hash = hashlib.sha256(payload.encode("utf-8")).hexdigest()
    attempt_no = (await db.scalar(
        select(BhytClaimAttempt.attempt_no)
        .where(BhytClaimAttempt.claim_id == claim.id)
        .order_by(BhytClaimAttempt.attempt_no.desc())
        .limit(1)
    ) or 0) + 1
    attempt = BhytClaimAttempt(
        claim_id=claim.id,
        attempt_no=attempt_no,
        status="sending",
        request_hash=request_hash,
    )
    db.add(attempt)
    claim.status = "sending"
    await db.flush()

    api_url = getattr(settings, "bhyt_api_url", "")
    if not api_url:
        attempt.status = "not_configured"
        attempt.response_payload = json.dumps({"reason": "BHYT_API_URL is not configured"})
        claim.status = "error"
        await db.flush()
        return claim

    try:
        async with httpx.AsyncClient(timeout=getattr(settings, "bhyt_api_timeout", 20)) as client:
            response = await client.post(
                f"{api_url.rstrip('/')}/claims",
                content=payload.encode("utf-8"),
                headers={
                    "Authorization": f"Bearer {getattr(settings, 'bhyt_api_key', '')}",
                    "Content-Type": "application/xml",
                    "X-Idempotency-Key": request_hash,
                },
            )
            response.raise_for_status()
        attempt.status = "accepted"
        attempt.response_payload = response.text[:10000]
        attempt.external_ref = response.headers.get("X-Claim-Id")
        claim.status = "submitted"
        claim.external_ref = attempt.external_ref
        claim.submitted_at = datetime.now(timezone.utc)
        claim.response_payload = response.text[:10000]
    except Exception as exc:
        attempt.status = "error"
        attempt.response_payload = json.dumps({"error": str(exc)}, ensure_ascii=False)
        claim.status = "error"
    await db.flush()
    return claim


async def reconcile_claim(db: AsyncSession, claim: BhytClaim, status: str, accepted_amount: Decimal, rejected_amount: Decimal, external_ref: Optional[str], response_payload: Optional[str]) -> BhytClaim:
    if claim.status not in {"submitted", "accepted", "partial", "rejected"}:
        raise ValueError("Claim chưa có phản hồi để đối soát.")
    claim.status = status
    claim.accepted_amount = accepted_amount
    claim.rejected_amount = rejected_amount
    claim.external_ref = external_ref or claim.external_ref
    claim.response_payload = response_payload or claim.response_payload
    return claim
