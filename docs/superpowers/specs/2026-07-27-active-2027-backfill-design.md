# Active 2027 Recruitment Backfill Design

## Goal

Expand the site from its initial six verified entries into a high-coverage index of public, currently open 2027-campus-recruitment jobs that match the configured profile. The scope is the configured source set and added official public systems; it does not promise all jobs on the internet.

## User-facing rule

Only jobs that can still be applied for are retained and displayed. A job is excluded when its official deadline has passed, its official page says recruitment is closed, or its official job ID is confirmed unavailable twice. Expired or closed historical jobs are not retained as a separate archive.

## Source strategy

1. Use enterprise official recruitment systems and official careers pages as the primary record.
2. Traverse portal search results, pagination, and public job-detail endpoints rather than only source home pages.
3. Use university employment boards and public aggregators only to discover an official detail or application URL; do not make a repost the final application destination when an official URL is available.
4. Add one focused adapter per portal family when the portal has structured public data. Keep simple static sources in the generic crawler.

## Backfill flow

```text
official portal lists/search pages
  -> collect all public 2027 candidates
  -> fetch official job detail and application URL
  -> reject closed, expired, non-2027, and hard-ineligible jobs
  -> normalize company/title/location
  -> deduplicate by company + title + location
  -> publish only active matches to site/data/jobs.json
```

## Filtering

The existing profile remains the matching baseline: 2027 undergraduate, architecture/historic-building-conservation related, design experience, and permitted cross-industry directions. Explicit master's-or-above requirements, non-2027 cohorts, social recruitment requiring experience, mandatory professional licenses, and unrelated medical/legal/finance roles are rejected. "Preferred" wording does not reject a job.

## Data and failure handling

- Each job must have an official `apply_url` when possible; otherwise retain its official `detail_url`.
- Store only the structured requirements required for matching; no raw HTML, credentials, cookies, personal identity, or complete historical archive.
- A source error, timeout, challenge page, or one-off 404 leaves existing active jobs untouched and marks source health as suspect/failed.
- A source adapter must expose its discovered count and test fixtures so a silent zero-result regression is visible.

## Acceptance criteria

1. The initial backfill scans every configured enabled source plus the new official adapters.
2. The public page contains every active, matching job successfully obtained from those sources after normalization and deduplication.
3. No closed or deadline-expired job appears in the public JSON or page.
4. Every visible job has an official application/detail link.
5. Source health identifies failures without deleting other source results.
6. Daily Actions reruns the same adapters for incremental updates and only republishes when public job data changes.

## Non-goals

- No claim of complete internet-wide coverage.
- No login, cookie, captcha, mini-program, or internal-referral scraping.
- No archive of expired positions and no manual resume submission.
