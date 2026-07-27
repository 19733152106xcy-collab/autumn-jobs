from datetime import date

import httpx
import respx

from autumn_jobs.adapters.cscec8 import (
    crawl_cscec8_jobs,
    load_cscec8_settings,
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


DIRECTORY_BODY = """
{
  "list": [
    {"id": "1000", "jobApi": "/api/job/getIndexPublishJob.json?company=28"},
    {"id": "1001", "jobApi": ""}
  ]
}
"""

LIST_BODY = """
{
  "errno": 200,
  "data": {
    "list": [
      {
        "job_id": "3001",
        "job_name_show": "设计管理总院2027届校园招聘",
        "ws_company_orgnize_id_user_name": "中建八局设计管理总院",
        "job_address_name": "上海",
        "show_time": "2026-07-01",
        "job_desc": "2027届本科，建筑学及相关专业"
      }
    ]
  }
}
"""


@respx.mock
def test_crawl_cscec8_jobs_discovers_jobs_from_each_public_unit():
    respx.get("https://job.cscec8b.com.cn/cscec8b/data/names.json").mock(
        return_value=httpx.Response(200, text=DIRECTORY_BODY)
    )
    respx.get("https://job.cscec8b.com.cn/api/job/getIndexPublishJob.json?company=28").mock(
        return_value=httpx.Response(200, text=LIST_BODY)
    )

    jobs = crawl_cscec8_jobs({"max_companies": 100})

    assert [job.source_job_id for job in jobs] == ["3001"]
    assert jobs[0].detail_url == "https://job.cscec8b.com.cn/recruitment/job/detail/id/3001"
    assert jobs[0].apply_url == jobs[0].detail_url
    assert jobs[0].official_status == "open"


def test_load_cscec8_settings_reads_public_adapter_limits(tmp_path):
    path = tmp_path / "cscec8.yaml"
    path.write_text("max_companies: 50\n", encoding="utf-8")

    assert load_cscec8_settings(path) == {"max_companies": 50}
