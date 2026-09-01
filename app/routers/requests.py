"""Blood request endpoints: lifecycle, offers, donor matching."""

from datetime import datetime, timedelta, timezone

from fastapi import APIRouter, Depends, HTTPException, Request, status
from slowapi import Limiter
from slowapi.util import get_remote_address
from sqlalchemy.orm import Session, joinedload

from app.config import get_settings
from app.database import get_db
from app.models import (
    REQUEST_STATUS,
    BloodRequest,
    DonorProfile,
    Offer,
    User,
)
from app.schemas import BloodRequestIn, BloodRequestOut, OfferIn, OfferOut
from app.security import get_current_user, require_roles

router = APIRouter(prefix="/requests", tags=["requests"])
settings = get_settings()
limiter = Limiter(key_func=get_remote_address)

VALID_REQUEST_TRANSITIONS = {
    "open": {"matched", "fulfilled", "cancelled", "expired"},
    "matched": {"fulfilled", "cancelled"},
    "fulfilled": set(),
    "cancelled": set(),
    "expired": set(),
}


def _to_out(req: BloodRequest) -> BloodRequestOut:
    return BloodRequestOut(
        id=req.id,
        request_number=req.request_number,
        patient_name=req.patient_name,
        blood_group=req.blood_group,
        units=req.units,
        city=req.city,
        hospital=req.hospital,
        urgency=req.urgency,
        status=req.status,
        note=req.note,
        created_by=req.created_by,
        created_at=req.created_at,
        updated_at=req.updated_at,
        expires_at=req.expires_at,
        offer_count=len(req.offers) if req.offers else 0,
    )


def _next_request_number(db: Session) -> str:
    year = datetime.now(timezone.utc).year
    prefix = f"IMD-{year}-"
    last = (
        db.query(BloodRequest)
        .filter(BloodRequest.request_number.like(f"{prefix}%"))
        .order_by(BloodRequest.request_number.desc())
        .first()
    )
    if last is None:
        return f"{prefix}000001"
    seq = int(last.request_number.split("-")[-1]) + 1
    return f"{prefix}{seq:06d}"


def get_request_or_404(db: Session, request_id: int) -> BloodRequest:
    req = db.query(BloodRequest).filter(BloodRequest.id == request_id).first()
    if req is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Request not found")
    return req


def _expire_stale(db: Session) -> None:
    now = datetime.now(timezone.utc)
    stale = (
        db.query(BloodRequest)
        .filter(BloodRequest.status == "open", BloodRequest.expires_at <= now)
        .all()
    )
    for req in stale:
        req.status = "expired"
    if stale:
        db.commit()


@router.post("", response_model=BloodRequestOut, status_code=status.HTTP_201_CREATED)
@limiter.limit(settings.RATE_LIMIT_REQUESTS)
def create_request(
    request: Request,
    payload: BloodRequestIn,
    db: Session = Depends(get_db),
    user: User = Depends(require_roles("requester", "admin")),
):
    req = BloodRequest(
        request_number=_next_request_number(db),
        patient_name=payload.patient_name,
        blood_group=payload.blood_group,
        units=payload.units,
        city=payload.city,
        hospital=payload.hospital,
        urgency=payload.urgency,
        note=payload.note.strip(),
        created_by=user.id,
        expires_at=datetime.now(timezone.utc) + timedelta(hours=settings.REQUEST_EXPIRY_HOURS),
    )
    db.add(req)
    db.commit()
    db.refresh(req)
    req.offers = []
    return _to_out(req)


@router.get("", response_model=list[BloodRequestOut])
def list_requests(
    status_filter: str | None = None,
    city: str | None = None,
    blood_group: str | None = None,
    mine: bool = False,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    _expire_stale(db)
    query = db.query(BloodRequest)
    if mine:
        query = query.filter(BloodRequest.created_by == user.id)
    else:
        query = query.filter(BloodRequest.status == "open")
    if status_filter:
        if status_filter not in REQUEST_STATUS:
            raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail="Invalid status")
        query = query.filter(BloodRequest.status == status_filter)
    if city:
        query = query.filter(BloodRequest.city.ilike(f"%{city.strip()}%"))
    if blood_group:
        query = query.filter(BloodRequest.blood_group == blood_group)
    reqs = query.order_by(BloodRequest.created_at.desc()).limit(100).all()
    return [_to_out(r) for r in reqs]


@router.get("/{request_id}", response_model=BloodRequestOut)
def get_request(
    request_id: int,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    req = db.query(BloodRequest).filter(BloodRequest.id == request_id).first()
    if req is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Request not found")
    # Public can see open requests; owner/admin can see everything
    if req.status != "open" and req.created_by != user.id and user.role != "admin":
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Request not found")
    return _to_out(req)


@router.post("/{request_id}/offers", response_model=OfferOut, status_code=status.HTTP_201_CREATED)
@limiter.limit("10/minute")
def make_offer(
    request: Request,
    request_id: int,
    payload: OfferIn,
    db: Session = Depends(get_db),
    user: User = Depends(require_roles("donor", "admin")),
):
    req = get_request_or_404(db, request_id)
    if req.status != "open":
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Request is not open for offers")
    profile = db.query(DonorProfile).filter(DonorProfile.user_id == user.id).first()
    if profile is None:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Create a donor profile first")
    from app.compat import can_donate

    if not can_donate(profile.blood_group, req.blood_group):
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=f"Blood group {profile.blood_group} cannot donate to {req.blood_group}",
        )
    existing = (
        db.query(Offer)
        .filter(Offer.request_id == request_id, Offer.donor_id == user.id)
        .first()
    )
    if existing:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="You already offered on this request")

    offer = Offer(request_id=req.id, donor_id=user.id, message=payload.message.strip())
    db.add(offer)
    db.commit()
    db.refresh(offer)
    return OfferOut(
        id=offer.id,
        request_id=offer.request_id,
        donor_id=offer.donor_id,
        donor_name=user.full_name,
        blood_group=profile.blood_group,
        status=offer.status,
        message=offer.message,
        created_at=offer.created_at,
    )


@router.get("/{request_id}/offers", response_model=list[OfferOut])
def list_offers(
    request_id: int,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    req = get_request_or_404(db, request_id)
    if req.created_by != user.id and user.role != "admin":
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Request not found")
    offers = (
        db.query(Offer)
        .options(joinedload(Offer.request))
        .filter(Offer.request_id == request_id)
        .order_by(Offer.created_at.asc())
        .all()
    )
    donor_ids = [o.donor_id for o in offers]
    donors = {u.id: u for u in db.query(User).filter(User.id.in_(donor_ids)).all()} if donor_ids else {}
    profiles = (
        {
            p.user_id: p
            for p in db.query(DonorProfile).filter(DonorProfile.user_id.in_(donor_ids)).all()
        }
        if donor_ids
        else {}
    )
    out = []
    for o in offers:
        d = donors.get(o.donor_id)
        p = profiles.get(o.donor_id)
        out.append(
            OfferOut(
                id=o.id,
                request_id=o.request_id,
                donor_id=o.donor_id,
                donor_name=d.full_name if d else "",
                blood_group=p.blood_group if p else "",
                status=o.status,
                message=o.message,
                created_at=o.created_at,
            )
        )
    return out


@router.post("/{request_id}/fulfill", response_model=BloodRequestOut)
def fulfill_request(
    request_id: int,
    db: Session = Depends(get_db),
    user: User = Depends(require_roles("requester", "admin")),
):
    req = get_request_or_404(db, request_id)
    if req.created_by != user.id and user.role != "admin":
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Request not found")
    if req.status not in ("open", "matched"):
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"Cannot fulfill a request in status '{req.status}'",
        )
    req.status = "fulfilled"
    # Record donation for accepted donors
    accepted = db.query(Offer).filter(Offer.request_id == req.id, Offer.status == "accepted").all()
    from datetime import datetime, timezone

    for offer in accepted:
        profile = db.query(DonorProfile).filter(DonorProfile.user_id == offer.donor_id).first()
        if profile:
            profile.last_donation_date = datetime.now(timezone.utc)
            profile.donation_count += 1
    db.commit()
    db.refresh(req)
    return _to_out(req)


@router.post("/{request_id}/cancel", response_model=BloodRequestOut)
def cancel_request(
    request_id: int,
    db: Session = Depends(get_db),
    user: User = Depends(require_roles("requester", "admin")),
):
    req = get_request_or_404(db, request_id)
    if req.created_by != user.id and user.role != "admin":
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Request not found")
    if req.status in ("fulfilled", "cancelled", "expired"):
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"Cannot cancel a request in status '{req.status}'",
        )
    req.status = "cancelled"
    db.commit()
    db.refresh(req)
    return _to_out(req)


@router.post("/{request_id}/expire", response_model=BloodRequestOut)
def expire_request(
    request_id: int,
    db: Session = Depends(get_db),
    user: User = Depends(require_roles("admin")),
):
    req = get_request_or_404(db, request_id)
    if req.status != "open":
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Only open requests can be expired")
    req.status = "expired"
    db.commit()
    db.refresh(req)
    return _to_out(req)
