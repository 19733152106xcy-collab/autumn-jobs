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

let savedStatuses = {};

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

export function resolveApplyUrl(job) {
  return job.official_apply_url || job.apply_url || job.detail_url;
}

function verificationLabel(job) { return job.verification_status === "pending" ? "待核验" : "已核验"; }
function opportunityLabel(job) { return { full_time: "正式岗", internship: "实习", mixed: "正式/实习" }[job.opportunity_type] || "机会"; }

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
    <td>${job.title}<span class="opportunity-${job.opportunity_type || "full_time"}">${opportunityLabel(job)}</span><span class="verification-${job.verification_status === "pending" ? "pending" : "official"}">${verificationLabel(job)}</span></td>
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

function render(jobs, state, statuses) {
  const partitioned = partitionJobsByStatus(jobs, statuses);
  const visible = filterJobs(searchJobs(partitioned.pending, state.query), state);
  if (state.order === "更新时间") visible.sort((a, b) => b.first_seen.localeCompare(a.first_seen));
  const groups = groupJobsByCompany(visible);
  const body = document.querySelector("#jobs-body");
  body.innerHTML = groups.map((group, index) => {
    const primary = group.jobs[0];
    const locations = [...new Set(group.jobs.flatMap((job) => job.location))].join("、");
    return `
    <tr>
      <td>${group.company}</td>
      <td>${primary.title}<span class="company-count">共 ${group.jobs.length} 个岗位</span></td>
      <td>${locations}</td>
      <td>${formatDeadline(primary.deadline)}</td>
      <td><button class="expand" type="button" data-group="${index}">展开</button></td>
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
    render(jobs, state, next);
  }));
  renderSavedJobs(partitioned.applied, "#applied-list", "已投递");
  renderSavedJobs(partitioned.not_interested, "#not-interested-list", "不感兴趣");
  document.querySelectorAll(".undo-job").forEach((button) => button.addEventListener("click", () => {
    const next = setJobStatus(statuses, button.dataset.fingerprint, null);
    saveJobStatuses(next);
    savedStatuses = next;
    render(jobs, state, next);
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
  document.querySelector("#updated").textContent = `最近更新：${status.updated_date || "未更新"}`;
  fillSelect(document.querySelector("#category"), optionValues(jobs, "category"));
  fillSelect(document.querySelector("#city"), optionValues(jobs, "location"));
  const state = { query: "", category: "全部", jobGroup: "", city: "全部", level: "全部", opportunity: "", verification: "", order: "更新时间", todayOnly: false };
  const controls = { query: "#search", category: "#category", jobGroup: "#job-group", city: "#city", level: "#level", opportunity: "#opportunity-filter", verification: "#verification-filter", order: "#order" };
  Object.entries(controls).forEach(([key, selector]) => document.querySelector(selector).addEventListener("input", (event) => { state[key] = event.target.value; render(jobs, state, savedStatuses); }));
  document.querySelector("#today").addEventListener("click", () => { state.todayOnly = !state.todayOnly; render(jobs, state, savedStatuses); });
  document.querySelector("#all").addEventListener("click", () => { state.todayOnly = false; state.query = ""; document.querySelector("#search").value = ""; render(jobs, state, savedStatuses); });
  render(jobs, state, savedStatuses);
}

if (typeof document !== "undefined") {
  boot().catch(() => { document.querySelector("#error").hidden = false; });
}
