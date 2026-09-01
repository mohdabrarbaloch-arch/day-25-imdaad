"""Donor endpoints: profile management, eligibility, compatibility search."""

from datetime import datetime, timedelta, timezone

from fastapi import APIRouter, Depends, HTTPException, Request, status
from slowapi import Limiter
from slowapi.util import get_remote_address
from sqlalchemy.orm import Session

from app.compat import can_donate
from app.config import get_settings
from app.database import get_db
from app.models import BLOOD_GROUPS, DonorProfile, User
from app.schemas import DonorOut, DonorProfileIn, DonorUpdateIn
from app.security import get_current_user, require_roles

router = APIRouter(prefix="/donors", tags=["donors"])
settings = get_settings()
limiter = Limiter(key_func=get_remote_address)


class DonorNotFoundError(Exception):
    pass


def _to_out(profile: DonorProfile) -> DonorOut:
    return DonorOut(
        id=profile.id,
        user_id=profile.user_id,
        full_name=profile.user.full_name,
        phone=profile.user.phone,
        city=profile.user.city,
        blood_group=profile.blood_group,
        is_available=profile.is_available,
        eligible=profile.eligible,
        donation_count=profile.donation_count,
        last_donation_date=profile.last_donation_date,
        created_at=profile.created_at,
    )


@router.post("/profile", response_model=DonorOut, status_code=status.HTTP_201_CREATED)
def create_profile(
    payload: DonorProfileIn,
    db: Session = Depends(get_db),
    user: User = Depends(require_roles("donor", "admin")),
):
    existing = db.query(DonorProfile).filter(DonorProfile.user_id == user.id).first()
    if existing:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Profile already exists")

    profile = DonorProfile(
        user_id=user.id,
        blood_group=payload.blood_group,
        last_donation_date=payload.last_donation_date,
        is_available=payload.is_available,
        medical_notes=payload.medical_notes.strip(),
    )
    db.add(profile)
    db.commit()
    db.refresh(profile)
    return _to_out(profile)


@router.get("/me", response_model=DonorOut)
def my_profile(
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    profile = db.query(DonorProfile).filter(DonorProfile.user_id == user.id).first()
    if profile is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="No donor profile yet")
    return _to_out(profile)


@router.patch("/me", response_model=DonorOut)
def update_profile(
    payload: DonorUpdateIn,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    profile = db.query(DonorProfile).filter(DonorProfile.user_id == user.id).first()
    if profile is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="No donor profile yet")
    data = payload.model_dump(exclude_unset=True)
    for key, value in data.items():
        setattr(profile, key, value)
    if "medical_notes" in data:
        profile.medical_notes = (profile.medical_notes or "").strip()
    db.commit()
    db.refresh(profile)
    return _to_out(profile)


@router.post("/me/donate", response_model=DonorOut)
@limiter.limit("10/minute")
def record_donation(
    request: Request,
    db: Session = Depends(get_db),
    user: User = Depends(require_roles("donor", "admin")),
):
    """Record a completed donation: sets last_donation_date and increments count."""
    profile = db.query(DonorProfile).filter(DonorProfile.user_id == user.id).first()
    if profile is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="No donor profile yet")
    profile.last_donation_date = datetime.now(timezone.utc)
    profile.donation_count += 1
    db.commit()
    db.refresh(profile)
    return _to_out(profile)


@router.get("/search", response_model=list[DonorOut])
def search_donors(
    blood_group: str | None = None,
    city: str | None = None,
    only_eligible: bool = True,
    db: Session = Depends(get_db),
    user: User = Depends(require_roles("donor", "requester", "admin")),
):
    """Search donors. If blood_group is given, returns donors compatible with a
    RECIPIENT of that blood group (i.e. donors whose blood can be given to it).
    """
    query = db.query(DonorProfile).join(User)
    if city:
        query = query.filter(User.city.ilike(f"%{city.strip()}%"))
    if blood_group:
        if blood_group not in BLOOD_GROUPS:
            raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail="Invalid blood group")
        compatible = [g for g in BLOOD_GROUPS if can_donate(g, blood_group)]
        query = query.filter(DonorProfile.blood_group.in_(compatible))
    if only_eligible:
        # eligible = available AND (no last donation OR >= 56 days ago)
        cutoff = datetime.now(timezone.utc) - timedelta(days=56)
        query = query.filter(
            DonorProfile.is_available.is_(True),
            (DonorProfile.last_donation_date.is_(None)) | (DonorProfile.last_donation_date <= cutoff),
        )
    profiles = query.order_by(DonorProfile.donation_count.desc()).limit(100).all()
    return [_to_out(p) for p in profiles]
