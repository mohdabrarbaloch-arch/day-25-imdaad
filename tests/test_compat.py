"""Unit tests for the ABO/Rh compatibility engine."""

from app.compat import (
    can_donate,
    compatible_donors_for,
    is_universal_donor,
    is_universal_recipient,
)


def test_identical_group_always_compatible():
    for group in ["A+", "A-", "B+", "B-", "AB+", "AB-", "O+", "O-"]:
        assert can_donate(group, group)


def test_o_negative_is_universal_donor():
    for group in ["A+", "A-", "B+", "B-", "AB+", "AB-", "O+", "O-"]:
        assert can_donate("O-", group)


def test_ab_positive_is_universal_recipient():
    for group in ["A+", "A-", "B+", "B-", "AB+", "AB-", "O+", "O-"]:
        assert can_donate(group, "AB+")


def test_ab_positive_can_only_donate_to_ab_positive():
    assert can_donate("AB+", "AB+")
    assert not can_donate("AB+", "A+")
    assert not can_donate("AB+", "O+")
    assert not can_donate("AB+", "B-")


def test_rh_negative_can_donate_to_positive_but_not_vice_versa():
    assert can_donate("A-", "A+")
    assert not can_donate("A+", "A-")


def test_o_positive_cannot_donate_to_a_negative():
    assert not can_donate("O+", "A-")
    assert not can_donate("O+", "B-")
    assert not can_donate("O+", "AB-")
    assert not can_donate("O+", "O-")


def test_b_donor_cannot_donate_to_a_recipient():
    assert not can_donate("B+", "A+")
    assert not can_donate("B-", "A+")
    assert not can_donate("A+", "B+")


def test_invalid_groups_return_false():
    assert not can_donate("X+", "A+")
    assert not can_donate("A+", "X+")
    assert not can_donate("", "A+")
    assert not can_donate("A+", "")


def test_compatible_donors_for_a_negative():
    donors = compatible_donors_for("A-")
    # Only A- and O- can donate to an A- recipient (A+ has Rh+ blood)
    assert set(donors) == {"A-", "O-"}


def test_compatible_donors_for_o_positive():
    donors = compatible_donors_for("O+")
    assert set(donors) == {"O+", "O-"}


def test_compatible_donors_for_ab_positive_includes_everyone():
    donors = compatible_donors_for("AB+")
    assert set(donors) == {"A+", "A-", "B+", "B-", "AB+", "AB-", "O+", "O-"}


def test_universal_flags():
    assert is_universal_donor("O-")
    assert not is_universal_donor("O+")
    assert is_universal_recipient("AB+")
    assert not is_universal_recipient("AB-")


def test_compatibility_matrix_spot_checks():
    # Known clinical facts
    assert can_donate("A+", "AB+")  # A+ → AB+
    assert not can_donate("A+", "B+")  # A+ can't give to B+
    assert can_donate("B-", "B+")  # B- → B+
    assert can_donate("B-", "AB+")  # B- → AB+
    assert not can_donate("B-", "A-")  # B- can't give to A-
    assert can_donate("O-", "AB-")  # universal donor to any Rh-
