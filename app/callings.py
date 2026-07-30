"""Searchable list of common branch callings for speaker assignment."""

from __future__ import annotations

# Ordered for scan-ability; searchable UI re-filters this list.
BRANCH_CALLINGS: list[str] = [
    # Branch leadership
    "Branch President",
    "First Counselor in the Branch Presidency",
    "Second Counselor in the Branch Presidency",
    "Branch Clerk",
    "Assistant Branch Clerk",
    "Branch Executive Secretary",
    "Assistant Branch Executive Secretary",
    # Elders Quorum
    "Elders Quorum President",
    "First Counselor in the Elders Quorum Presidency",
    "Second Counselor in the Elders Quorum Presidency",
    "Elders Quorum Secretary",
    "Elders Quorum Teacher",
    "Elders Quorum Ministering Secretary",
    # Relief Society
    "Relief Society President",
    "First Counselor in the Relief Society Presidency",
    "Second Counselor in the Relief Society Presidency",
    "Relief Society Secretary",
    "Relief Society Teacher",
    "Relief Society Ministering Secretary",
    "Relief Society Compassionate Service Coordinator",
    # Young Women
    "Young Women President",
    "First Counselor in the Young Women Presidency",
    "Second Counselor in the Young Women Presidency",
    "Young Women Secretary",
    "Young Women Class Advisor",
    "Young Women Activity Specialist",
    # Primary
    "Primary President",
    "First Counselor in the Primary Presidency",
    "Second Counselor in the Primary Presidency",
    "Primary Secretary",
    "Primary Teacher",
    "Primary Music Leader",
    "Primary Activity Days Leader",
    "Nursery Leader",
    # Sunday School
    "Sunday School President",
    "First Counselor in the Sunday School Presidency",
    "Second Counselor in the Sunday School Presidency",
    "Sunday School Secretary",
    "Sunday School Teacher",
    # Aaronic Priesthood
    "Teachers Quorum President",
    "First Counselor in the Teachers Quorum Presidency",
    "Second Counselor in the Teachers Quorum Presidency",
    "Teachers Quorum Secretary",
    "Teachers Quorum Adviser",
    "Deacons Quorum President",
    "First Counselor in the Deacons Quorum Presidency",
    "Second Counselor in the Deacons Quorum Presidency",
    "Deacons Quorum Secretary",
    "Deacons Quorum Adviser",
    "Priests Quorum Assistant",
    "Priests Quorum Adviser",
    # Music & meetings
    "Music Chair",
    "Ward/Branch Organist",
    "Ward/Branch Pianist",
    "Choir Director",
    "Choir Accompanist",
    "Sacrament Meeting Chorister",
    # Other common branch callings
    "Mission Leader",
    "Temple and Family History Leader",
    "Public Affairs Specialist",
    "Employment Specialist",
    "Self-Reliance Specialist",
    "Ward Missionary",
    "Stake High Councilor",
    "Stake President",
    "First Counselor in the Stake Presidency",
    "Second Counselor in the Stake Presidency",
    "Stake Executive Secretary",
    "Full-Time Missionary",
    "Service Missionary",
    "Young Single Adult Representative",
    "Activity Committee Member",
]


def format_speaker_with_calling(name: str, calling: str | None = None) -> str:
    """Append calling to a speaker name: 'Alexander Hunt - Branch Executive Secretary'."""
    name = " ".join((name or "").strip().split()) or "—"
    calling = " ".join((calling or "").strip().split())
    if calling and name != "—":
        return f"{name} - {calling}"
    return name


def normalize_calling(value: str | None) -> str | None:
    text = " ".join((value or "").strip().split())
    return text or None
