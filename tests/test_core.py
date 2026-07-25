from datetime import UTC, date, datetime

import pytest


def test_package_exposes_version():
    import autumn_jobs

    assert autumn_jobs.__version__ == "0.1.0"


def test_normalize_url_removes_tracking_but_keeps_job_id():
    from autumn_jobs.normalization import normalize_url

    assert (
        normalize_url("https://jobs.example.cn/detail?id=123&utm_source=x&channel=y")
        == "https://jobs.example.cn/detail?id=123"
    )


def test_different_official_ids_do_not_merge():
    from autumn_jobs.deduplication import deduplicate_jobs
    from autumn_jobs.models import JobBusiness, StructuredRequirements

    base = {
        "company": "某设计院",
        "title": "建筑设计师",
        "location": ["西安"],
        "detail_url": "https://example.cn/detail",
        "first_seen": date(2026, 7, 25),
        "category": "建筑设计",
        "match_level": "A",
        "match_reasons": ["建筑设计"],
        "requirements": StructuredRequirements(),
    }
    a = JobBusiness(fingerprint="a", source_id="a", source_job_id="A1", **base)
    b = JobBusiness(fingerprint="b", source_id="b", source_job_id="B2", **base)

    assert len(deduplicate_jobs([a, b])) == 2


def test_merged_job_does_not_list_its_own_detail_as_an_alternate_source():
    from autumn_jobs.deduplication import deduplicate_jobs
    from autumn_jobs.models import JobBusiness, StructuredRequirements

    first = JobBusiness(
        fingerprint="a",
        source_id="official",
        company="某设计院",
        title="建筑设计师",
        location=["西安"],
        detail_url="https://official.example.cn/job/1",
        first_seen=date(2026, 7, 25),
        category="建筑设计",
        match_level="A",
        match_reasons=["建筑设计"],
        requirements=StructuredRequirements(),
    )
    repost = first.model_copy(update={"source_id": "school", "detail_url": "https://school.example.cn/post/1"})

    [merged] = deduplicate_jobs([first, repost])

    assert merged.alternate_sources == ["https://school.example.cn/post/1"]


@pytest.mark.parametrize("text", ["硕士及以上学历，必须取得硕士学位", "仅限博士研究生"])
def test_required_postgraduate_is_excluded(text):
    from autumn_jobs.matching import match_job

    assert match_job("建筑设计", text).included is False


def test_social_recruitment_is_excluded_even_when_the_role_is_relevant():
    from autumn_jobs.matching import match_job

    assert match_job("建筑设计师", "社会招聘，要求三年以上工作经验").included is False


def test_social_recruitment_title_is_excluded_even_when_description_is_incomplete():
    from autumn_jobs.matching import match_job

    assert match_job("社会招聘", "建筑设计相关工作").included is False


def test_research_student_requirement_is_excluded_for_an_undergraduate_candidate():
    from autumn_jobs.matching import match_job

    assert match_job("建筑设计师", "学历：研究生；应届生").included is False


def test_postgraduate_preferred_is_kept_as_a_match():
    from autumn_jobs.matching import match_job

    result = match_job("建筑设计", "本科及以上，硕士优先")

    assert result.included is True
    assert result.level == "A"


def test_unrelated_sales_is_not_kept_as_c_match():
    from autumn_jobs.matching import match_job

    assert match_job("电话销售", "负责客户开拓").included is False


def test_ai_solution_is_c_when_bachelor_and_major_unrestricted():
    from autumn_jobs.matching import match_job

    result = match_job("AI解决方案助理", "本科应届生，专业不限")

    assert result.included is True
    assert result.level == "C"


def test_runtime_observation_does_not_change_business_hash():
    from autumn_jobs.models import JobBusiness, JobObservation, StructuredRequirements
    from autumn_jobs.state import business_hash

    job = JobBusiness(
        fingerprint="x",
        source_id="cadg",
        company="中国建筑设计研究院",
        title="建筑设计岗",
        location=["北京"],
        detail_url="https://example.cn/detail",
        first_seen=date(2026, 7, 25),
        category="建筑设计",
        match_level="A",
        match_reasons=["建筑设计"],
        requirements=StructuredRequirements(),
    )
    observation = JobObservation(
        fingerprint="x",
        source_id="cadg",
        last_seen=datetime(2026, 7, 25, 7, 30, tzinfo=UTC),
    )
    first = business_hash(job)
    observation.last_seen = datetime(2026, 7, 26, 7, 30, tzinfo=UTC)

    assert business_hash(job) == first


@pytest.mark.parametrize(
    ("signal", "expected"),
    [
        ("deadline_passed", "inactive"),
        ("page_closed_text", "inactive"),
        ("http_404", "suspect"),
        ("http_403", "suspect"),
        ("captcha", "suspect"),
        ("homepage_redirect", "suspect"),
    ],
)
def test_link_policy_is_conservative(signal, expected):
    from autumn_jobs.link_checking import classify_link

    assert classify_link(signal, "active").state == expected
