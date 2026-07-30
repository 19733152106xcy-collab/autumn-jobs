import httpx
import respx


@respx.mock
def test_crawl_bucea_reads_public_job_board_details():
    from autumn_jobs.adapters.bucea import API_URL, CHANNEL_URL, crawl_bucea_jobs

    respx.get(CHANNEL_URL).mock(return_value=httpx.Response(200, text='<input name="rzcxt" value="token">'))
    respx.post(API_URL).mock(return_value=httpx.Response(200, json={
        "msg": "Y",
        "pageCount": 1,
        "data": [{
            "dwmc": "Example Design Institute",
            "dwszddm": "Beijing",
            "tid": "124328",
            "updateTime": 1783575405000,
            "xqzwList": [{"id": 24028, "xqzw": "Architecture designer"}],
        }],
    }))
    respx.get("https://job.bucea.edu.cn/front/zwxx.jspa?xqzwId=24028&zpxxId=124328").mock(
        return_value=httpx.Response(200, text="<nav>internships</nav><div class='content'>2027 cohort bachelor architecture</div>")
    )

    jobs = crawl_bucea_jobs({"max_pages": 1})

    assert len(jobs) == 1
    assert jobs[0].source_id == "bucea"
    assert jobs[0].source_type == "university"
    assert jobs[0].verification_status == "verified"
    assert jobs[0].detail_url.endswith("xqzwId=24028&zpxxId=124328")
    assert jobs[0].description == "2027 cohort bachelor architecture"
