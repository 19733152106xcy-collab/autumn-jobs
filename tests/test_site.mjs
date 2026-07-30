import assert from "node:assert/strict";

import { filterJobs, groupJobsByCompany } from "../site/assets/app.js";

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
