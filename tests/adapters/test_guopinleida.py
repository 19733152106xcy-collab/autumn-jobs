import httpx
import respx

from autumn_jobs.adapters.guopinleida import crawl_guopinleida_jobs


@respx.mock
def test_crawl_guopinleida_reads_pending_27_cohort_jobs():
    respx.get("https://guopinleida.com/api/jobs").mock(return_value=httpx.Response(200, json={
        "data": {"data": [{"id": "one", "title": "某设计院2027届建筑设计招聘", "description": "2027届本科建筑学", "locations": ["北京"], "detailUrl": "https://example.test/post/one", "company": {"name": "某设计院"}}], "meta": {"hasMore": False}}
    }))

    jobs = crawl_guopinleida_jobs({"max_pages": 17, "page_size": 100})

    assert len(jobs) == 1
    assert jobs[0].verification_status == "pending"
    assert jobs[0].source_type == "job_board"
    assert jobs[0].source_name == "国聘雷达"
