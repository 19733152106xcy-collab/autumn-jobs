import httpx
import respx

TABLE_HTML = """
<table><tbody>
  <tr>
    <td>某城市建设集团</td><td>国企</td>
    <td>建筑设计岗,城市更新岗、建筑学及相关专业,本科</td>
    <td>西安,北京</td><td>秋招</td><td>2027届,2028届</td>
    <td>2026-07-31</td><td>2026-08-30</td><td>登录后查看</td><td>登录后查看</td><td>加入投递进展表</td>
  </tr>
  <tr>
    <td>某旧批次公司</td><td>国企</td><td>建筑设计岗</td><td>上海</td>
    <td>春招</td><td>2026届</td><td>2026-07-30</td><td>招满为止</td><td>登录后查看</td><td>登录后查看</td><td></td>
  </tr>
  <tr>
    <td>某科技集团</td><td>国企</td><td>AI产品助理、专业不限,本科</td><td>深圳</td>
    <td>实习</td><td>2027届</td><td>2026-07-30</td><td>招满为止</td><td>登录后查看</td><td>登录后查看</td><td></td>
  </tr>
</tbody></table>
"""


def test_parse_public_campus_table_keeps_2027_rows_and_structures_dates():
    from autumn_jobs.adapters.gankinterview import parse_gankinterview_jobs

    jobs = parse_gankinterview_jobs(TABLE_HTML)

    assert len(jobs) == 3
    assert jobs[0].company == "某城市建设集团"
    assert jobs[0].title == "建筑设计岗"
    assert jobs[0].location == ["西安", "北京"]
    assert jobs[0].deadline.isoformat() == "2026-08-30"
    assert jobs[0].publish_date.isoformat() == "2026-07-31"
    assert jobs[0].verification_status == "pending"
    assert jobs[0].source_name == "Gank Interview 国央企校招汇总"
    assert jobs[1].title == "城市更新岗"
    assert jobs[2].title == "AI产品助理（实习）"


@respx.mock
def test_crawl_gankinterview_uses_only_the_public_latest_page():
    from autumn_jobs.adapters.gankinterview import PUBLIC_URL, crawl_gankinterview_jobs

    respx.get(PUBLIC_URL).mock(return_value=httpx.Response(200, text=TABLE_HTML))

    jobs = crawl_gankinterview_jobs({"max_rows": 50})

    assert len(jobs) == 3
    assert all(job.detail_url == PUBLIC_URL for job in jobs)
