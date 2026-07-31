import assert from "node:assert/strict";

import {
  filterJobs,
  groupJobsByCompany,
  partitionJobsByCompanyStatus,
  partitionJobsByStatus,
  setCompanyStatus,
  setJobStatus,
  sortJobs,
} from "../site/assets/app.js";

const jobs = [
  { company: "甲设计院", title: "建筑设计岗", location: ["西安"], match_level: "A", category: "建筑设计", status: "active", opportunity_type: "full_time" },
  { company: "乙设计院", title: "暑期实习生", location: ["北京"], match_level: "A", category: "建筑设计", status: "active", opportunity_type: "internship" },
];

const visible = filterJobs(jobs, { opportunity: "full_time" });

assert.deepEqual(visible.map((job) => job.company), ["甲设计院"]);

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
