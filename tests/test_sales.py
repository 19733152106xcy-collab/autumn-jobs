from datetime import date
from pathlib import Path

from autumn_jobs.models import RawJob
from autumn_jobs.sales import build_sales, classify_sales, expand_campaign


def job(**kw):
    return RawJob(source_id="test", company="深信服", title="2027客户经理", detail_url="https://example.com/job", **kw)


def test_bachelor_unrestricted():
    assert classify_sales(job(description="2027届，本科及以上，专业不限"))["eligibility"] == "eligible"


def test_preferred_master_not_excluded():
    assert classify_sales(job(description="2027届，本科及以上，硕士优先，专业不限"))


def test_masters_only_excluded():
    assert classify_sales(job(description="硕士及以上学历")) is None


def test_not_sales_and_internship_excluded():
    assert classify_sales(job().model_copy(update={"title": "软件工程师"})) is None
    assert classify_sales(job().model_copy(update={"title": "销售实习生"})) is None


def test_technical_major_is_not_eligible():
    assert classify_sales(job(description="本科及以上，计算机、电子相关专业"))["eligibility"] == "needs_confirmation"


def test_negated_unrestricted_is_not_eligible():
    assert classify_sales(job(description="本科及以上，计算机相关专业，不是专业不限"))["eligibility"] == "needs_confirmation"


def test_majors_preferred_not_required():
    assert classify_sales(job(description="本科及以上，计算机相关专业优先而非必须"))["eligibility"] == "eligible"


def test_campaign_not_misrepresented_as_specific_job():
    assert classify_sales(job(description="销售工程师，研发工程师").model_copy(update={"title": "2027校园招聘"}))["kind"] == "lead"


def test_campaign_can_supply_named_sales_leads_without_claiming_eligibility():
    rows = expand_campaign(job(description="销售工程师、渠道经理、研发工程师").model_copy(update={"title": "2027校园招聘"}))
    assert [row.title for row in rows] == ["销售工程师（2027公告列出）", "渠道经理（2027公告列出）"]
    assert all(classify_sales(row)["eligibility"] == "needs_confirmation" for row in rows)


def test_failure_preserves_old_data_and_expired_is_hidden(tmp_path):
    config = Path("config/sales_companies.yaml")
    output = tmp_path / "sales.json"
    today = date(2026, 10, 10)
    build_sales({"test": [job(description="本科专业不限")]}, config, output, today)
    result = build_sales({}, config, output, today)
    assert len(result["jobs"]) == 1
    result = build_sales({"test": [job(deadline=date(2026, 10, 9))]}, config, output, today)
    assert not result["jobs"]
