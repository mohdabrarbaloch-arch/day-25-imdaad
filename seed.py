"""Seed script — creates demo accounts and sample data.

Usage:
    python seed.py
"""

from datetime import datetime, timedelta, timezone

from app.database import Base, SessionLocal, engine
from app.models import BloodRequest, DonorProfile, Offer, User
from app.security import hash_password

Base.metadata.create_all(bind=engine)
db = SessionLocal()


def seed_user(email, name, phone, role, city, password="password123", blood=None, last_donation_days_ago=None):
    existing = db.query(User).filter(User.email == email).first()
    if existing:
        return existing
    user = User(
        email=email,
        password_hash=hash_password(password),
        full_name=name,
        phone=phone,
        role=role,
        city=city,
    )
    db.add(user)
    db.flush()
    if blood:
        profile = DonorProfile(
            user_id=user.id,
            blood_group=blood,
            last_donation_date=(
                datetime.now(timezone.utc) - timedelta(days=last_donation_days_ago)
                if last_donation_days_ago
                else None
            ),
            is_available=True,
        )
        db.add(profile)
    return user


def main():
    seed_user("admin@imdaad.pk", "Admin Imdaad", "03001234567", "admin", "Karachi")
    seed_user(
        "ahmed@imdaad.pk",
        "Ahmed Raza",
        "03011111111",
        "donor",
        "Karachi",
        blood="O-",
        last_donation_days_ago=90,
    )
    seed_user(
        "fatima@imdaad.pk",
        "Fatima Noor",
        "03022222222",
        "donor",
        "Karachi",
        blood="A+",
        last_donation_days_ago=60,
    )
    seed_user(
        "bilal@imdaad.pk",
        "Bilal Hussain",
        "03033333333",
        "donor",
        "Lahore",
        blood="B+",
        last_donation_days_ago=120,
    )
    seed_user("sara@imdaad.pk", "Sara Khan", "03044444444", "donor", "Karachi", blood="O+")
    requester = seed_user(
        "hospital@imdaad.pk",
        "Karachi General Hospital",
        "03055555555",
        "requester",
        "Karachi",
    )

    if db.query(BloodRequest).count() == 0:
        req1 = BloodRequest(
            request_number="IMD-2026-000001",
            patient_name="Imran Sheikh",
            blood_group="B+",
            units=2,
            city="Karachi",
            hospital="Karachi General Hospital",
            urgency="urgent",
            note="Road accident, surgery scheduled tomorrow morning.",
            created_by=requester.id,
            expires_at=datetime.now(timezone.utc) + timedelta(hours=72),
        )
        req2 = BloodRequest(
            request_number="IMD-2026-000002",
            patient_name="Ayesha Malik",
            blood_group="A-",
            units=1,
            city="Lahore",
            hospital="Shaukat Khanum",
            urgency="emergency",
            note="Leukemia patient, platelet support needed.",
            created_by=requester.id,
            expires_at=datetime.now(timezone.utc) + timedelta(hours=48),
        )
        db.add_all([req1, req2])
        db.flush()
        db.add(Offer(request_id=req1.id, donor_id=3, message="I can come tomorrow morning."))

    db.commit()
    print("Seed complete.")
    print("Demo accounts:")
    print("  admin@imdaad.pk / password123 (admin)")
    print("  ahmed@imdaad.pk / password123 (donor, O-)")
    print("  hospital@imdaad.pk / password123 (requester)")


if __name__ == "__main__":
    main()
