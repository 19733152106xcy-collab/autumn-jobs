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
    match_reasons: list[str]
    requirements: StructuredRequirements
    apply_url: str | None = None
    detail_url: str
    alternate_sources: list[str] = Field(default_factory=list)
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
