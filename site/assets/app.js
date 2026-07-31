export function searchJobs(jobs, query) {
  const normalized = query.trim().toLowerCase();
  if (!normalized) return jobs;
  return jobs.filter((job) => `${job.company} ${job.title}`.toLowerCase().includes(normalized));
}

export function filterJobs(jobs, filters) {
  return jobs.filter((job) => {
    const cityOk = !filters.city || filters.city === "全部" || job.location.includes(filters.city);
    const levelOk = !filters.level || filters.level === "全部" || job.match_level === filters.level;
    const jobGroupOk = !filters.jobGroup || job.job_group === filters.jobGroup;
    const opportunityOk = !filters.opportunity || job.opportunity_type === filters.opportunity;
    const verificationOk = !filters.verification || (filters.verification === "verified" ? job.verification_status !== "pending" : job.verification_status === "pending");
    const categoryOk = !filters.category || filters.category === "全部" || job.category === filters.category;
    const todayOk = !filters.todayOnly || job.first_seen === new Date().toISOString().slice(0, 10);
    return cityOk && levelOk && jobGroupOk && opportunityOk && verificationOk && categoryOk && todayOk && job.status === "active";
  });
}

export function groupJobsByCompany(jobs) {
  const groups = new Map();
  jobs.forEach((job) => {
    const group = groups.get(job.company) || { company: job.company, jobs: [] };
    group.jobs.push(job);
    groups.set(job.company, group);
  });
  return [...groups.values()];
}

export function sortJobs(jobs, order) {
  return [...jobs].sort((left, right) => {
    if (order === "综合评分") {
      return (right.score_total ?? -1) - (left.score_total ?? -1)
        || Number(right.eligibility_status === "eligible") - Number(left.eligibility_status === "eligible")
        || (right.first_seen || "").localeCompare(left.first_seen || "");
    }
    if (order === "优先级") {
      return (left.priority_rank ?? 4) - (right.priority_rank ?? 4)
        || right.first_seen.localeCompare(left.first_seen);
    }
    return right.first_seen.localeCompare(left.first_seen);
  });
}

let savedStatuses = {};
let savedCompanyStatuses = {};

export function setJobStatus(statuses, fingerprint, status) {
  const next = { ...statuses };
  if (status) next[fingerprint] = status;
  else delete next[fingerprint];
  return next;
}

export function partitionJobsByStatus(jobs, statuses) {
  const groups = { pending: [], applied: [], not_interested: [] };
  jobs.forEach((job) => groups[statuses[job.fingerprint] || "pending"].push(job));
  return groups;
}

export function setCompanyStatus(statuses, company, status) {
  const next = { ...statuses };
  if (status) next[company] = status;
  else delete next[company];
  return next;
}

export function partitionJobsByCompanyStatus(jobs, statuses) {
  const groups = { pending: [], not_interested: [] };
  jobs.forEach((job) => groups[statuses[job.company] || "pending"].push(job));
  return groups;
}

export function resolveApplyUrl(job) {
  return job.official_apply_url || job.apply_url || job.detail_url;
}

function verificationLabel(job) { return job.verification_status === "pending" ? "待核验" : "已核验"; }
function opportunityLabel(job) { return { full_time: "正式岗", internship: "实习", mixed: "正式/实习" }[job.opportunity_type] || "机会"; }
function scoreLabel(job) { return Number.isFinite(job.score_total) ? `${job.score_total}分` : "暂未评分"; }
function eligibilityLabel(job) { return job.eligibility_label || (job.eligibility_status === "eligible" ? "可投" : "需确认"); }
function salaryLabel(job) {
  if (!job.salary_band || job.salary_band === "待确认") return "待遇待确认";
  return `${job.salary_band}档（${job.salary_basis || "估算"}）`;
}

function scoreDetails(job) {
  const breakdown = job.score_breakdown || {};
  const strengths = (job.score_strengths || []).map((item) => `<li>${item}</li>`).join("") || "<li>暂无明确加分依据</li>";
  const risks = (job.score_risks || []).map((item) => `<li>${item}</li>`).join("") || "<li>暂无额外风险提示</li>";
  return `<details class="score-details">
    <summary>评分明细</summary>
    <div class="score-grid">
      <span>待遇与平台 ${breakdown.compensation_platform ?? 0}/40</span>
      <span>进面概率 ${breakdown.interview_probability ?? 0}/25</span>
      <span>能力匹配 ${breakdown.ability_match ?? 0}/20</span>
      <span>发展空间 ${breakdown.growth ?? 0}/10</span>
      <span>投递成本 ${breakdown.application_cost ?? 0}/5</span>
    </div>
    <p>判断可信度：${job.score_confidence || "低"}</p>
    <div class="score-reasons"><div><strong>加分项</strong><ul>${strengths}</ul></div><div><strong>风险项</strong><ul>${risks}</ul></div></div>
  </details>`;
}

function optionValues(jobs, field) {
  const values = new Set();
  jobs.forEach((job) => (Array.isArray(job[field]) ? job[field] : [job[field]]).forEach((value) => value && values.add(value)));
  return [...values].sort((a, b) => String(a).localeCompare(String(b), "zh-CN"));
}

function fillSelect(select, values) {
  select.innerHTML = "<option>全部</option>" + values.map((value) => `<option>${value}</option>`).join("");
}

function formatDeadline(value) {
  return value || "未公布";
}

function jobRow(job, groupId) {
  return `<tr class="job-detail" data-group="${groupId}" hidden>
    <td></td>
    <td>${job.title}<span class="score-badge">${scoreLabel(job)}</span><span class="eligibility-${job.eligibility_status === "eligible" ? "eligible" : "confirm"}">${eligibilityLabel(job)}</span><span class="salary-badge">${salaryLabel(job)}</span><span class="opportunity-${job.opportunity_type || "full_time"}">${opportunityLabel(job)}</span><span class="verification-${job.verification_status === "pending" ? "pending" : "official"}">${verificationLabel(job)}</span><p class="score-summary">${job.score_summary || "评分信息待更新"}</p>${scoreDetails(job)}</td>
    <td>${job.location.join("、")}</td>
    <td>${formatDeadline(job.deadline)}</td>
    <td><a class="apply" href="${resolveApplyUrl(job)}" target="_blank" rel="noopener noreferrer">立即投递</a><button class="mark-job" type="button" data-status="applied" data-fingerprint="${job.fingerprint}">已投递</button><button class="mark-job" type="button" data-status="not_interested" data-fingerprint="${job.fingerprint}">不感兴趣</button></td>
  </tr>`;
}

function renderSavedJobs(jobs, selector, label) {
  const container = document.querySelector(selector);
  const section = container.parentElement;
  section.querySelector("summary").textContent = `${label}（${jobs.length}）`;
  container.innerHTML = groupJobsByCompany(jobs).map((group) => `<div class="saved-company"><strong>${group.company}</strong>${group.jobs.map((job) => `<div>${job.title}<button class="undo-job" type="button" data-fingerprint="${job.fingerprint}">撤销</button></div>`).join("")}</div>`).join("") || "<p class=\"muted\">暂无岗位</p>";
}

function loadJobStatuses() {
  try {
    const saved = JSON.parse(localStorage.getItem("autumn-jobs-statuses") || "{}");
    return saved && typeof saved === "object" ? saved : {};
  } catch {
    return {};
  }
}

function saveJobStatuses(statuses) {
  localStorage.setItem("autumn-jobs-statuses", JSON.stringify(statuses));
}

function loadCompanyStatuses() {
  try {
    const saved = JSON.parse(localStorage.getItem("autumn-jobs-company-statuses") || "{}");
    return saved && typeof saved === "object" ? saved : {};
  } catch {
    return {};
  }
}

function saveCompanyStatuses(statuses) {
  localStorage.setItem("autumn-jobs-company-statuses", JSON.stringify(statuses));
}

function renderSavedCompanies(jobs) {
  const container = document.querySelector("#not-interested-companies-list");
  const groups = groupJobsByCompany(jobs);
  document.querySelector("#not-interested-companies-section summary").textContent = `不感兴趣公司（${groups.length}）`;
  container.innerHTML = groups.map((group) => `<div class="saved-company"><strong>${group.company}</strong><span class="company-count">共 ${group.jobs.length} 个岗位</span><button class="undo-company" type="button" data-company="${group.company}">撤销</button></div>`).join("") || "<p class=\"muted\">暂无公司</p>";
}

function render(jobs, state, statuses, companyStatuses) {
  const companyPartition = partitionJobsByCompanyStatus(jobs, companyStatuses);
  const partitioned = partitionJobsByStatus(companyPartition.pending, statuses);
  const visible = sortJobs(filterJobs(searchJobs(partitioned.pending, state.query), state), state.order);
  const groups = groupJobsByCompany(visible);
  const body = document.querySelector("#jobs-body");
  body.innerHTML = groups.map((group, index) => {
    const primary = group.jobs[0];
    const locations = [...new Set(group.jobs.flatMap((job) => job.location))].join("、");
    const priorityCount = group.jobs.filter((job) => (job.score_total ?? 0) >= 75 && job.eligibility_status === "eligible").length;
    return `
    <tr>
      <td>${group.company}</td>
      <td>${primary.title}<span class="score-badge">${scoreLabel(primary)}</span><span class="eligibility-${primary.eligibility_status === "eligible" ? "eligible" : "confirm"}">${eligibilityLabel(primary)}</span><span class="salary-badge">${salaryLabel(primary)}</span><span class="company-count">共 ${group.jobs.length} 个岗位</span>${priorityCount ? `<span class="priority-count">建议优先投 ${priorityCount} 个</span>` : ""}<p class="score-summary">${primary.score_summary || "评分信息待更新"}</p></td>
      <td>${locations}</td>
      <td>${formatDeadline(primary.deadline)}</td>
      <td><button class="expand" type="button" data-group="${index}">展开</button><button class="mark-company" type="button" data-company="${group.company}">不感兴趣</button></td>
    </tr>${group.jobs.map((job) => jobRow(job, index)).join("")}`;
  }).join("");
  body.querySelectorAll(".expand").forEach((button) => button.addEventListener("click", () => {
    const details = body.querySelectorAll(`.job-detail[data-group="${button.dataset.group}"]`);
    const expanded = [...details].some((row) => !row.hidden);
    details.forEach((row) => { row.hidden = expanded; });
    button.textContent = expanded ? "展开" : "收起";
  }));
  body.querySelectorAll(".mark-job").forEach((button) => button.addEventListener("click", () => {
    const next = setJobStatus(statuses, button.dataset.fingerprint, button.dataset.status);
    saveJobStatuses(next);
    savedStatuses = next;
    render(jobs, state, next, companyStatuses);
  }));
  body.querySelectorAll(".mark-company").forEach((button) => button.addEventListener("click", () => {
    const next = setCompanyStatus(companyStatuses, button.dataset.company, "not_interested");
    saveCompanyStatuses(next);
    savedCompanyStatuses = next;
    render(jobs, state, statuses, next);
  }));
  renderSavedJobs(partitioned.applied, "#applied-list", "已投递");
  renderSavedJobs(partitioned.not_interested, "#not-interested-list", "不感兴趣");
  renderSavedCompanies(companyPartition.not_interested);
  document.querySelectorAll(".undo-job").forEach((button) => button.addEventListener("click", () => {
    const next = setJobStatus(statuses, button.dataset.fingerprint, null);
    saveJobStatuses(next);
    savedStatuses = next;
    render(jobs, state, next, companyStatuses);
  }));
  document.querySelectorAll(".undo-company").forEach((button) => button.addEventListener("click", () => {
    const next = setCompanyStatus(companyStatuses, button.dataset.company, null);
    saveCompanyStatuses(next);
    savedCompanyStatuses = next;
    render(jobs, state, statuses, next);
  }));
  document.querySelector("#empty").hidden = groups.length !== 0;
  document.querySelector("#count").textContent = `共 ${visible.length} 个岗位，${groups.length} 家公司`;
}

async function boot() {
  const requestOptions = { cache: "no-store" };
  const [jobsResponse, statusResponse] = await Promise.all([
    fetch("data/jobs.json", requestOptions),
    fetch("data/update_status.json", requestOptions),
  ]);
  if (!jobsResponse.ok) throw new Error("jobs data unavailable");
  const payload = await jobsResponse.json();
  const status = statusResponse.ok ? await statusResponse.json() : { updated_date: "未更新" };
  const jobs = payload.jobs || [];
  savedStatuses = loadJobStatuses();
  savedCompanyStatuses = loadCompanyStatuses();
  document.querySelector("#updated").textContent = `最近更新：${status.updated_date || "未更新"}`;
  fillSelect(document.querySelector("#category"), optionValues(jobs, "category"));
  fillSelect(document.querySelector("#city"), optionValues(jobs, "location"));
  const state = { query: "", category: "全部", jobGroup: "", city: "全部", level: "全部", opportunity: "", verification: "", order: "综合评分", todayOnly: false };
  const controls = { query: "#search", category: "#category", jobGroup: "#job-group", city: "#city", level: "#level", opportunity: "#opportunity-filter", verification: "#verification-filter", order: "#order" };
  Object.entries(controls).forEach(([key, selector]) => document.querySelector(selector).addEventListener("input", (event) => { state[key] = event.target.value; render(jobs, state, savedStatuses, savedCompanyStatuses); }));
  document.querySelector("#today").addEventListener("click", () => { state.todayOnly = !state.todayOnly; render(jobs, state, savedStatuses, savedCompanyStatuses); });
  document.querySelector("#all").addEventListener("click", () => { state.todayOnly = false; state.query = ""; document.querySelector("#search").value = ""; render(jobs, state, savedStatuses, savedCompanyStatuses); });
  render(jobs, state, savedStatuses, savedCompanyStatuses);
}

if (typeof document !== "undefined") {
  boot().catch(() => { document.querySelector("#error").hidden = false; });
}
