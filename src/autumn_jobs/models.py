from __future__ import annotations

from datetime import date, datetime
from pathlib import Path
from typing import Literal

from pydantic import BaseModel, Field


class StructuredRequirements(BaseModel):
    education: str | None = None
    graduation_year: int | None = None
    majors: list[str] = Field(default_factory=list)
    experience_required: bool = False
    qualification_required: bool = False


class RawJob(BaseModel):
    source_id: str
    company: str
    title: str
    location: list[str] = Field(default_factory=lambda: ["未公布"])
    detail_url: str
    apply_url: str | None = None
    source_job_id: str | None = None
    description: str = ""
    deadline: date | None = None
    publish_date: date | None = None
    official_status: Literal["open", "closed", "unknown", "suspect"] = "unknown"
    source_type: Literal["official", "state_owned_platform", "university", "job_board", "public_article"] = "public_article"
    verification_status: Literal["official", "verified", "pending"] = "pending"
    source_name: str | None = None
    official_apply_url: str | None = None
    opportunity_type: Literal["full_time", "internship", "mixed"] = "full_time"


class JobBusiness(BaseModel):
    fingerprint: str
    source_id: str
    source_job_id: str | None = None
    company: str
    title: str
    location: list[str]
    deadline: date | None = None
    publish_date: date | None = None
    first_seen: date
    category: str
    match_level: Literal["A", "B", "C"]
    job_group: Literal["architecture", "other"] = "other"
    priority_rank: Literal[1, 2, 3, 4] = 4
    priority_label: str = "备选关注"
    match_reasons: list[str]
    requirements: StructuredRequirements
    apply_url: str | None = None
    detail_url: str
    alternate_sources: list[str] = Field(default_factory=list)
    source_type: Literal["official", "state_owned_platform", "university", "job_board", "public_article"] = "public_article"
    verification_status: Literal["official", "verified", "pending"] = "pending"
    source_name: str | None = None
    official_apply_url: str | None = None
    opportunity_type: Literal["full_time", "internship", "mixed"] = "full_time"
    status: Literal["active", "inactive"] = "active"


class JobObservation(BaseModel):
    fingerprint: str
    source_id: str
    last_seen: datetime | None = None
    link_last_checked: datetime | None = None
    link_state: Literal["unknown", "valid", "suspect"] = "unknown"
    missing_count: int = 0


class MatchResult(BaseModel):
    included: bool
    level: Literal["A", "B", "C"] | None = None
    category: str | None = None
    job_group: Literal["architecture", "other"] | None = None
    reasons: list[str] = Field(default_factory=list)
    requirements: StructuredRequirements = Field(default_factory=StructuredRequirements)


class LinkDecision(BaseModel):
    state: Literal["active", "inactive", "suspect"]
    reason: str


class PipelineResult(BaseModel):
    publish_required: bool
    public_path: Path
    jobs_count: int
    duplicate_count: int
