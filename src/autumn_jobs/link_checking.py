from __future__ import annotations

from autumn_jobs.models import LinkDecision


def classify_link(signal: str, previous_status: str) -> LinkDecision:
    if signal in {"deadline_passed", "page_closed_text"}:
        return LinkDecision(state="inactive", reason=signal)
    if signal in {"http_404", "http_410", "http_403", "http_429", "captcha", "homepage_redirect", "timeout"}:
        return LinkDecision(state="suspect", reason=signal)
    return LinkDecision(state=previous_status if previous_status in {"active", "inactive"} else "active", reason="no_change")
