"""Stats endpoints: public overview + admin details."""

from datetime import datetime, timedelta, timezone

from fastapi import APIRouter, Depends
from sqlalchemy import func
from sqlalchemy.orm import Session

from app.database import get_db
from app.models import BLOOD_GROUPS, BloodRequest, DonorProfile, Offer, User
from app.schemas import StatsOut
from app.security import require_roles

router = APIRouter(tags=["stats"])


@router.get("/stats", response_model=StatsOut)
def public_stats(db: Session = Depends(get_db)):
    total_donors = db.query(DonorProfile).count()
    cutoff = datetime.now(timezone.utc) - timedelta(days=56)
    eligible = (
        db.query(DonorProfile)
        .filter(
            DonorProfile.is_available.is_(True),
            (DonorProfile.last_donation_date.is_(None)) | (DonorProfile.last_donation_date <= cutoff),
        )
        .count()
    )
    open_req = db.query(BloodRequest).filter(BloodRequest.status == "open").count()
    fulfilled = db.query(BloodRequest).filter(BloodRequest.status == "fulfilled").count()
    total_req = db.query(BloodRequest).count()

    req_by_group = dict(
        db.query(BloodRequest.blood_group, func.count(BloodRequest.id))
        .filter(BloodRequest.status == "open")
        .group_by(BloodRequest.blood_group)
        .all()
    )
    donors_by_group = dict(
        db.query(DonorProfile.blood_group, func.count(DonorProfile.id))
        .group_by(DonorProfile.blood_group)
        .all()
    )
    return StatsOut(
        total_donors=total_donors,
        eligible_donors=eligible,
        open_requests=open_req,
        fulfilled_requests=fulfilled,
        total_requests=total_req,
        requests_by_blood_group={g: req_by_group.get(g, 0) for g in BLOOD_GROUPS},
        donors_by_blood_group={g: donors_by_group.get(g, 0) for g in BLOOD_GROUPS},
    )


@router.get("/admin/stats")
def admin_stats(db: Session = Depends(get_db), user: User = Depends(require_roles("admin"))):
    cities = dict(db.query(User.city, func.count(User.id)).group_by(User.city).all())
    statuses = dict(
        db.query(BloodRequest.status, func.count(BloodRequest.id)).group_by(BloodRequest.status).all()
    )
    offers_total = db.query(Offer).count()
    return {
        "total_users": db.query(User).count(),
        "users_by_role": dict(db.query(User.role, func.count(User.id)).group_by(User.role).all()),
        "users_by_city": cities,
        "requests_by_status": statuses,
        "offers_total": offers_total,
    }
