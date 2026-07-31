from autumn_jobs.matching import match_job
from autumn_jobs.models import RawJob
from autumn_jobs.scoring import score_job


def _job(
    *,
    company: str = "中国建筑设计研究院",
    description: str = "2027届本科，建筑学及相关专业",
    source_type: str = "official",
    verification_status: str = "official",
) -> RawJob:
    return RawJob(
        source_id="example",
        company=company,
        title="建筑设计岗",
        location=["北京"],
        detail_url="https://example.test/jobs/1",
        official_apply_url="https://example.test/apply/1",
        description=description,
        source_type=source_type,
        verification_status=verification_status,
    )


def _score(raw: RawJob):
    return score_job(raw, match_job(raw.title, raw.description))


def test_score_is_a_transparent_hundred_point_total():
    result = _score(_job())

    assert result.score_total == sum(result.score_breakdown.values())
    assert set(result.score_breakdown) == {
        "compensation_platform",
        "interview_probability",
        "ability_match",
        "growth",
        "application_cost",
    }
    assert 0 <= result.score_total <= 100


def test_explicit_salary_takes_precedence_over_company_estimate():
    result = _score(_job(description="2027届本科，建筑学专业，月薪15k-20k"))

    assert result.salary_band == "A"
    assert result.salary_basis == "明确"
    assert "招聘信息明确薪资" in result.score_strengths


def test_missing_requirements_are_marked_for_confirmation():
    result = _score(_job(company="某设计公司", description="校园招聘"))

    assert result.eligibility_status == "needs_confirmation"
    assert result.eligibility_label == "需确认"
    assert "学历、届别或专业信息不完整" in result.score_risks


def test_company_estimate_is_labeled_and_explained():
    result = _score(_job())

    assert result.salary_band == "B"
    assert result.salary_basis == "估算"
    assert any("头部建筑设计平台" in strength for strength in result.score_strengths)
    assert "待遇为公司层级估算" in result.score_risks


def test_pure_internship_scores_below_equivalent_full_time_role():
    full_time = _job(description="2027届本科，建筑学及相关专业")
    internship = full_time.model_copy(update={"title": "建筑设计暑期实习生"})

    assert _score(internship).score_total < _score(full_time).score_total
