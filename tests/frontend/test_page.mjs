import assert from "node:assert/strict";
import { escapeHtml, filterJobs, resolveApplyUrl, searchJobs } from "../../site/assets/app.js";

const jobs = [
  { company: "某设计院", title: "建筑设计岗", location: ["西安"], category: "建筑设计", match_level: "A", first_seen: "2026-07-25", status: "active" },
  { company: "某科技公司", title: "AI解决方案助理", location: ["深圳"], category: "AI解决方案", match_level: "C", first_seen: "2026-07-24", status: "active" },
];

assert.equal(searchJobs(jobs, "设计院").length, 1);
assert.equal(filterJobs(jobs, { city: "西安", level: "A", category: "全部", todayOnly: false }).length, 1);
assert.equal(resolveApplyUrl({ apply_url: null, detail_url: "https://example.cn/detail" }), "https://example.cn/detail");
assert.equal(resolveApplyUrl({ apply_url: "javascript:alert(1)", detail_url: "https://example.cn/detail" }), "#");
assert.equal(escapeHtml('<img src=x onerror="alert(1)">'), "&lt;img src=x onerror=&quot;alert(1)&quot;&gt;");

const formal = filterJobs([
  { ...jobs[0], opportunity_type: "full_time" },
  { ...jobs[1], opportunity_type: "internship" },
], { opportunity: "formal" });
assert.deepEqual(formal.map((job) => job.company), ["某设计院"]);
