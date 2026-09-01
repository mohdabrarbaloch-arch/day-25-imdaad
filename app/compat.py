"""ABO/Rh blood compatibility engine — pure functions, fully tested."""

from app.models import BLOOD_GROUPS

# donor -> set of compatible recipients
_COMPAT: dict[str, set[str]] = {
    "A+": {"A+", "AB+"},
    "A-": {"A+", "A-", "AB+", "AB-"},
    "B+": {"B+", "AB+"},
    "B-": {"B+", "B-", "AB+", "AB-"},
    "AB+": {"AB+"},
    "AB-": {"AB+", "AB-"},
    "O+": {"A+", "B+", "AB+", "O+"},
    "O-": set(BLOOD_GROUPS),  # universal donor
}


def can_donate(donor_blood: str, recipient_blood: str) -> bool:
    """True if a donor of `donor_blood` can donate to a recipient of `recipient_blood`."""
    if donor_blood not in _COMPAT or recipient_blood not in BLOOD_GROUPS:
        return False
    return recipient_blood in _COMPAT[donor_blood]


def compatible_donors_for(recipient_blood: str) -> list[str]:
    """All blood groups that can donate to a recipient of `recipient_blood`."""
    if recipient_blood not in BLOOD_GROUPS:
        return []
    return [g for g in BLOOD_GROUPS if can_donate(g, recipient_blood)]


def is_universal_donor(blood: str) -> bool:
    return blood == "O-"


def is_universal_recipient(blood: str) -> bool:
    return blood == "AB+"
