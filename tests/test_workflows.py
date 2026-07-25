from pathlib import Path


def test_daily_workflow_declares_permissions_and_pages_actions():
    workflow = Path(".github/workflows/daily-update.yml").read_text(encoding="utf-8")

    assert "contents: write" in workflow
    assert "pages: write" in workflow
    assert "id-token: write" in workflow
    assert 'cron: "30 7 * * *"' in workflow
    assert 'timezone: "Asia/Shanghai"' in workflow
    assert "actions/configure-pages" in workflow
    assert "actions/upload-pages-artifact" in workflow
    assert "actions/deploy-pages" in workflow
    assert "commit_sha" in workflow
    assert "ref: ${{ needs.crawl.outputs.commit_sha }}" in workflow
    assert "state_changed" in workflow
    assert "data/state/source_status.json" in workflow
