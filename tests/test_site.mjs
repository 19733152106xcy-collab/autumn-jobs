import assert from "node:assert/strict";

import {
  companyActionMode,
  defaultViewState,
  filterJobs,
  groupJobsByCompany,
  optionValues,
  partitionJobsByCompanyStatus,
  partitionJobsByStatus,
  resetViewState,
  setCompanyStatus,
  setJobStatus,
  sortJobs,
  summarizeView,
} from "../site/assets/app.js";

const jobs = [
  { company: "甲设计院", title: "建筑设计岗", location: ["西安"], match_level: "A", category: "建筑设计", status: "active", opportunity_type: "full_time" },
  { company: "乙设计院", title: "暑期实习生", location: ["北京"], match_level: "A", category: "建筑设计", status: "active", opportunity_type: "internship" },
];

const visible = filterJobs(jobs, { opportunity: "full_time" });

assert.deepEqual(visible.map((job) => job.company), ["甲设计院"]);

const formalFirst = filterJobs([
  { ...jobs[0], fingerprint: "formal" },
  { ...jobs[1], fingerprint: "internship" },
  { ...jobs[0], fingerprint: "mixed", company: "丙设计院", opportunity_type: "mixed" },
], { opportunity: "formal" });

assert.deepEqual(formalFirst.map((job) => job.fingerprint), ["formal", "mixed"]);

const cityPartial = filterJobs([
  { ...jobs[0], location: ["北京，河北"] },
], { city: "北京" });
assert.equal(cityPartial.length, 1);
assert.deepEqual(optionValues([{ location: ["北京，河北", "上海、全国"] }], "location"), ["北京", "河北", "全国", "上海"]);

const initialState = defaultViewState("2026-07-31");
assert.equal(initialState.opportunity, "formal");
assert.equal(initialState.todayDate, "2026-07-31");

const resetState = resetViewState({
  ...initialState,
  query: "建筑",
  category: "建筑设计",
  city: "西安",
  level: "A",
  todayOnly: true,
});
assert.deepEqual(resetState, {
  ...defaultViewState("2026-07-31"),
  opportunity: "",
});

const grouped = groupJobsByCompany([
  { company: "甲设计院", title: "建筑设计" },
  { company: "甲设计院", title: "城市更新" },
  { company: "乙科技", title: "AI产品" },
]);

assert.equal(grouped.length, 2);
assert.equal(grouped[0].jobs.length, 2);

const statuses = setJobStatus({}, "job-1", "applied");
assert.deepEqual(statuses, { "job-1": "applied" });
assert.deepEqual(setJobStatus(statuses, "job-1", null), {});

const partitioned = partitionJobsByStatus([
  { fingerprint: "job-1", company: "甲设计院" },
  { fingerprint: "job-2", company: "乙科技" },
  { fingerprint: "job-3", company: "丙设计院" },
], { "job-1": "applied", "job-3": "not_interested" });

assert.deepEqual(partitioned.pending.map((job) => job.fingerprint), ["job-2"]);
assert.deepEqual(partitioned.applied.map((job) => job.fingerprint), ["job-1"]);
assert.deepEqual(partitioned.not_interested.map((job) => job.fingerprint), ["job-3"]);

const sorted = sortJobs([
  { company: "跨行公司", priority_rank: 3, first_seen: "2026-07-30" },
  { company: "建筑公司", priority_rank: 1, first_seen: "2026-07-29" },
], "优先级");

assert.deepEqual(sorted.map((job) => job.company), ["建筑公司", "跨行公司"]);

const scored = sortJobs([
  { company: "低分公司", score_total: 55, eligibility_status: "eligible", first_seen: "2026-07-31" },
  { company: "待确认公司", score_total: 88, eligibility_status: "needs_confirmation", first_seen: "2026-07-31" },
  { company: "高分公司", score_total: 88, eligibility_status: "eligible", first_seen: "2026-07-30" },
], "综合评分");

assert.deepEqual(scored.map((job) => job.company), ["高分公司", "待确认公司", "低分公司"]);

const companyStatuses = setCompanyStatus({}, "甲设计院", "not_interested");
assert.deepEqual(companyStatuses, { "甲设计院": "not_interested" });

const companyPartition = partitionJobsByCompanyStatus([
  { fingerprint: "job-1", company: "甲设计院" },
  { fingerprint: "job-2", company: "甲设计院" },
  { fingerprint: "job-3", company: "乙科技" },
], companyStatuses);

assert.deepEqual(companyPartition.pending.map((job) => job.fingerprint), ["job-3"]);
assert.deepEqual(companyPartition.not_interested.map((job) => job.fingerprint), ["job-1", "job-2"]);
assert.deepEqual(setCompanyStatus(companyStatuses, "甲设计院", null), {});

const summary = summarizeView(
  [
    { fingerprint: "job-1", company: "甲设计院", opportunity_type: "full_time" },
    { fingerprint: "job-2", company: "甲设计院", opportunity_type: "internship" },
    { fingerprint: "job-3", company: "乙科技", opportunity_type: "mixed" },
  ],
  [{ fingerprint: "job-3", company: "乙科技", opportunity_type: "mixed" }],
  { "job-1": "applied" },
  { "甲设计院": "not_interested" },
);

assert.deepEqual(summary, {
  totalJobs: 3,
  totalCompanies: 2,
  visibleJobs: 1,
  visibleCompanies: 1,
  hiddenCompanies: 1,
  handledJobs: 1,
  pureInternships: 1,
});

assert.equal(companyActionMode([{ fingerprint: "single" }]), "direct");
assert.equal(companyActionMode([{ fingerprint: "one" }, { fingerprint: "two" }]), "expand");
