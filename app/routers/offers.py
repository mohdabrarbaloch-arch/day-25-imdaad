"""Offer management endpoints (accept / decline / withdraw)."""

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.database import get_db
from app.models import BloodRequest, DonorProfile, Offer, User
from app.schemas import OfferOut
from app.security import get_current_user

router = APIRouter(prefix="/offers", tags=["offers"])

ACTION_TO_STATUS = {"accept": "accepted", "decline": "declined", "withdraw": "withdrawn"}


@router.patch("/{offer_id}", response_model=OfferOut)
def update_offer(
    offer_id: int,
    action: str,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    offer = db.query(Offer).filter(Offer.id == offer_id).first()
    if offer is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Offer not found")
    req = db.get(BloodRequest, offer.request_id)

    if action == "withdraw":
        if offer.donor_id != user.id and user.role != "admin":
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Not your offer")
    else:  # accept / decline
        if req.created_by != user.id and user.role != "admin":
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Not your request")

    if action not in ACTION_TO_STATUS:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail="Invalid action")
    if offer.status != "pending":
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"Cannot {action} an offer in status '{offer.status}'",
        )
    offer.status = ACTION_TO_STATUS[action]
    if action == "accept":
        req.status = "matched"
        db.add(req)
    db.commit()
    db.refresh(offer)

    donor = db.get(User, offer.donor_id)
    profile = db.query(DonorProfile).filter(DonorProfile.user_id == offer.donor_id).first()
    return OfferOut(
        id=offer.id,
        request_id=offer.request_id,
        donor_id=offer.donor_id,
        donor_name=donor.full_name if donor else "",
        blood_group=profile.blood_group if profile else "",
        status=offer.status,
        message=offer.message,
        created_at=offer.created_at,
    )
