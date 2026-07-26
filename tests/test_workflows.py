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


def test_manual_dispatch_deploys_without_forcing_a_data_commit():
    workflow = Path(".github/workflows/daily-update.yml").read_text(encoding="utf-8")

    assert 'if [ "${{ github.event_name }}" = "workflow_dispatch" ]; then' in workflow
    assert 'echo "publish=true" >> "$GITHUB_OUTPUT"' in workflow
    assert "business_changed: ${{ steps.changed.outputs.business_changed }}" in workflow
    assert (
        "if: steps.changed.outputs.business_changed == 'true' || "
        "steps.changed.outputs.state_changed == 'true'"
    ) in workflow
