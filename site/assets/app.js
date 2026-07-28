export function searchJobs(jobs, query) {
  const normalized = query.trim().toLowerCase();
  if (!normalized) return jobs;
  return jobs.filter((job) => `${job.company} ${job.title}`.toLowerCase().includes(normalized));
}

export function filterJobs(jobs, filters) {
  return jobs.filter((job) => {
    const cityOk = !filters.city || filters.city === "全部" || job.location.includes(filters.city);
    const levelOk = !filters.level || filters.level === "全部" || job.match_level === filters.level;
    const verificationOk = !filters.verification || (filters.verification === "verified" ? job.verification_status !== "pending" : job.verification_status === "pending");
    const categoryOk = !filters.category || filters.category === "全部" || job.category === filters.category;
    const todayOk = !filters.todayOnly || job.first_seen === new Date().toISOString().slice(0, 10);
    return cityOk && levelOk && verificationOk && categoryOk && todayOk && job.status === "active";
  });
}

export function resolveApplyUrl(job) {
  return job.official_apply_url || job.apply_url || job.detail_url;
}

function verificationLabel(job) { return job.verification_status === "pending" ? "待核验" : "已核验"; }

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

function render(jobs, state) {
  const visible = filterJobs(searchJobs(jobs, state.query), state);
  if (state.order === "更新时间") visible.sort((a, b) => b.first_seen.localeCompare(a.first_seen));
  const body = document.querySelector("#jobs-body");
  body.innerHTML = visible.map((job) => `
    <tr>
      <td>${job.company}</td>
      <td>${job.title}<span class="verification-${job.verification_status === "pending" ? "pending" : "official"}">${verificationLabel(job)}</span>${job.first_seen === new Date().toISOString().slice(0, 10) ? '<span class="badge">今日新增</span>' : ""}</td>
      <td>${job.location.join("、")}</td>
      <td>${formatDeadline(job.deadline)}</td>
      <td><a class="apply" href="${resolveApplyUrl(job)}" target="_blank" rel="noopener noreferrer">立即投递</a></td>
    </tr>`).join("");
  document.querySelector("#empty").hidden = visible.length !== 0;
  document.querySelector("#count").textContent = `共 ${visible.length} 个岗位`;
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
  document.querySelector("#updated").textContent = `最近更新：${status.updated_date || "未更新"}`;
  fillSelect(document.querySelector("#category"), optionValues(jobs, "category"));
  fillSelect(document.querySelector("#city"), optionValues(jobs, "location"));
  const state = { query: "", category: "全部", city: "全部", level: "全部", verification: "", order: "更新时间", todayOnly: false };
  const controls = { query: "#search", category: "#category", city: "#city", level: "#level", verification: "#verification-filter", order: "#order" };
  Object.entries(controls).forEach(([key, selector]) => document.querySelector(selector).addEventListener("input", (event) => { state[key] = event.target.value; render(jobs, state); }));
  document.querySelector("#today").addEventListener("click", () => { state.todayOnly = !state.todayOnly; render(jobs, state); });
  document.querySelector("#all").addEventListener("click", () => { state.todayOnly = false; state.query = ""; document.querySelector("#search").value = ""; render(jobs, state); });
  render(jobs, state);
}

if (typeof document !== "undefined") {
  boot().catch(() => { document.querySelector("#error").hidden = false; });
}
