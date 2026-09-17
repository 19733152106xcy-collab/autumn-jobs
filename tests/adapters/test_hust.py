from pathlib import Path

import httpx
import respx


@respx.mock
def test_crawl_hust_reads_listing_and_public_detail(tmp_path: Path):
    from autumn_jobs.adapters.hust import LISTING_URL, crawl_hust_jobs

    detail_url = "https://job.hust.edu.cn/zpinfo1/2431921.htm"
    respx.get(LISTING_URL).mock(return_value=httpx.Response(200, text="""
        <ul class='nytzlist'><li><h4><a href='/zpinfo1/2431921.htm'>华润置地2027届校园招聘简章</a></h4>
        <time>[2026-09-10]</time></li></ul>
    """))
    respx.get(detail_url).mock(return_value=httpx.Response(200, text="""
        <div class='content'>2027届本科 建筑学相关专业 城市更新 设计管理</div>
    """))

    jobs = crawl_hust_jobs({"pages": 1, "max_items": 5})

    assert len(jobs) == 1
    assert jobs[0].source_id == "hust"
    assert jobs[0].source_job_id == "2431921"
    assert jobs[0].company == "华润置地"
    assert jobs[0].source_type == "university"
    assert jobs[0].verification_status == "verified"
    assert jobs[0].source_name == "华中科技大学就业信息网"
    assert jobs[0].publish_date.isoformat() == "2026-09-10"
    assert jobs[0].description == "2027届本科 建筑学相关专业 城市更新 设计管理"


@respx.mock
def test_crawl_hust_fetches_only_configured_priority_titles():
    from autumn_jobs.adapters.hust import LISTING_URL, crawl_hust_jobs

    selected_url = "https://job.hust.edu.cn/zpinfo1/2431921.htm"
    ignored_url = "https://job.hust.edu.cn/zpinfo1/2431922.htm"
    respx.get(LISTING_URL).mock(return_value=httpx.Response(200, text="""
        <ul class='nytzlist'>
          <li><h4><a href='/zpinfo1/2431921.htm'>华润置地2027届校园招聘简章</a></h4><time>[2026-09-10]</time></li>
          <li><h4><a href='/zpinfo1/2431922.htm'>某普通公司2027届校园招聘简章</a></h4><time>[2026-09-10]</time></li>
        </ul>
    """))
    respx.get(selected_url).mock(return_value=httpx.Response(200, text="<div class='content'>2027届本科</div>"))
    respx.get(ignored_url).mock(return_value=httpx.Response(200, text="<div class='content'>2027届本科</div>"))

    jobs = crawl_hust_jobs({"pages": 1, "max_items": 5, "title_keywords": ["华润置地"]})

    assert [job.source_job_id for job in jobs] == ["2431921"]
    assert respx.calls.call_count == 2
