from datetime import date

import httpx
import respx

from autumn_jobs.adapters.cscec8 import (
    crawl_cscec8_jobs,
    load_cscec8_job_ids,
    parse_cscec8_job,
)

DETAIL_HTML = """
<html><head><title>设计管理总院2027届校园招聘 - 中国建筑第八工程局有限公司</title></head>
<body>
  <div class="job-title-row"><div class="title">设计管理总院2027届校园招聘</div></div>
  <div class="com-or-brc-name">中建八局设计管理总院<span class="pub-time">更新：2026-06-18</span></div>
  <ul class="require"><li>上海浦东新区</li><li class="spr">|</li><li>校招</li><li class="spr">|</li><li>本科及以上学历</li></ul>
</body></html>
"""


def test_parse_cscec8_job_extracts_business_fields():
    job = parse_cscec8_job(
        "https://job.cscec8b.com.cn/recruitment/job/detail/id/2757",
        DETAIL_HTML,
        "<p>招聘专业：建筑学专业</p><p>2027届大学本科及以上学历，CET-4及以上</p>",
    )

    assert job.source_job_id == "2757"
    assert job.company == "中建八局设计管理总院"
    assert job.title == "设计管理总院2027届校园招聘"
    assert job.location == ["上海浦东新区"]
    assert job.publish_date == date(2026, 6, 18)
    assert "建筑学专业" in job.description


@respx.mock
def test_crawl_cscec8_jobs_fetches_detail_and_description():
    respx.get("https://job.cscec8b.com.cn/recruitment/job/detail/id/2757").mock(
        return_value=httpx.Response(200, text=DETAIL_HTML)
    )
    respx.get("https://job.cscec8b.com.cn/headhunter/showjobdesc/id/2757").mock(
        return_value=httpx.Response(200, text="<p>招聘专业：建筑学专业</p>")
    )

    jobs = crawl_cscec8_jobs([2757])

    assert [job.source_job_id for job in jobs] == ["2757"]


def test_load_cscec8_job_ids_reads_configured_official_ids(tmp_path):
    path = tmp_path / "cscec8.yaml"
    path.write_text("job_ids: [2753, 2757]\n", encoding="utf-8")

    assert load_cscec8_job_ids(path) == [2753, 2757]
