const $ = id => document.getElementById(id);
const storeKey = 'autumn-sales-status-v1';
let saved = {};
try { saved = JSON.parse(localStorage.getItem(storeKey) || '{}'); } catch { /* recover malformed storage */ }
let data;
const el = (tag, text, cls) => { const n = document.createElement(tag); if (text !== undefined) n.textContent = text; if (cls) n.className = cls; return n; };
export function safeUrl(value) { try { const url = new URL(value); return ['http:', 'https:'].includes(url.protocol) ? url.href : null; } catch { return null; } }
function link(text, url) { const a = el('a', text); a.href = safeUrl(url); a.target = '_blank'; a.rel = 'noopener noreferrer'; return a; }
function mark(key, value) { if (value) saved[key] = value; else delete saved[key]; try { localStorage.setItem(storeKey, JSON.stringify(saved)); } catch { $('sales-update').textContent = '浏览器不允许保存状态；本次标记仅在当前页面有效。'; } render(); }
function button(text, action) { const b = el('button', text); b.type = 'button'; b.onclick = action; return b; }
function status(row) { return saved[`company:${row.company}`] || saved[row.id]; }
function render() {
  const search = $('sales-search').value.trim().toLowerCase();
  const kind = $('sales-kind').value;
  const rows = [...data.jobs, ...data.leads].filter(row =>
    (kind === 'all' || row.kind === kind) &&
    (!search || `${row.company} ${row.title}`.toLowerCase().includes(search)) &&
    (!$('sales-industry').value || row.industry === $('sales-industry').value) &&
    (!$('sales-city').value || row.location.includes($('sales-city').value)) &&
    (!$('sales-eligibility').value || row.eligibility === $('sales-eligibility').value) &&
    ($('sales-saved').value === 'all' || ($('sales-saved').value === 'saved' ? status(row) : !status(row)))
  );
  const groups = new Map();
  for (const row of rows) { if (!groups.has(row.company)) groups.set(row.company, []); groups.get(row.company).push(row); }
  $('sales-count').textContent = `当前 ${groups.size} 家公司 · ${rows.filter(r => r.kind === 'job').length} 条岗位信息 · ${rows.filter(r => r.kind === 'lead').length} 条校招公告`;
  const list = $('sales-list'); list.replaceChildren();
  if (!rows.length) list.append(el('p', '此筛选下暂无结果。可以切换“销售方向校招公告”查看仍需核验的机会。'));
  for (const [company, jobs] of groups) {
    const group = el('section', undefined, 'sales-company');
    const heading = el('div', undefined, 'sales-heading'); heading.append(el('h2', `${company} · ${jobs.length} 条`));
    heading.append(button(saved[`company:${company}`] ? '恢复整家公司' : '公司不感兴趣', () => mark(`company:${company}`, saved[`company:${company}`] ? null : '不感兴趣')));
    group.append(heading);
    const details = el('details'); details.open = jobs.length <= 2;
    details.append(el('summary', `${jobs[0].industry} · 展开/收起岗位`));
    for (const row of jobs) {
      const card = el('article', undefined, 'sales-row'); card.append(el('h3', row.title));
      card.append(el('span', row.kind === 'lead' ? '校招公告，非具体岗' : (row.eligibility === 'eligible' ? '本科专业条件符合' : '资格待确认'), 'sales-tag'));
      card.append(el('span', row.verification === 'pending' ? '聚合线索待核验' : '官方 / 高校来源', 'sales-tag'));
      card.append(el('p', `${row.location.join(' / ')} · 截止：${row.deadline || '未公布'}`));
      card.append(el('p', row.requirements)); card.append(el('p', `待遇：${row.salary}`));
      card.append(el('p', `来源：${row.source_name} · 首次收录：${row.first_seen}`, 'muted'));
      const actions = el('div', undefined, 'sales-actions');
      if (safeUrl(row.apply_url)) actions.append(link('投递入口', row.apply_url));
      if (safeUrl(row.detail_url)) actions.append(link('查看原文', row.detail_url));
      if (status(row)) actions.append(button(`已标记${status(row)} · 恢复`, () => mark(saved[`company:${row.company}`] ? `company:${row.company}` : row.id, null)));
      else { actions.append(button('已投递', () => mark(row.id, '已投递'))); actions.append(button('不感兴趣', () => mark(row.id, '不感兴趣'))); }
      card.append(actions); details.append(card);
    }
    group.append(details); list.append(group);
  }
}
async function init() {
  try {
    const response = await fetch('data/sales.json', {cache:'no-cache'}); if (!response.ok) throw new Error('DataUnavailable'); data = await response.json();
    const industries = [...new Set(data.companies.map(r => r.industry))];
    const cities = [...new Set([...data.jobs, ...data.leads].flatMap(r => r.location))].sort();
    for (const [id, values] of [['sales-industry', industries], ['sales-city', cities]]) for (const value of values) { const option = el('option', value); option.value = value; $(id).append(option); }
    $('sales-update').textContent = `检索日期 ${data.updated} · ${data.companies.length} 家目标企业 · ${data.jobs.length} 条岗位信息（其中 ${data.jobs.filter(r => r.eligibility === 'eligible').length} 条本科专业条件符合；公告拆出的岗仍需核验）· ${data.leads.length} 条校招公告`;
    $('sales-audit-title').textContent = `公司检索清单（${data.companies.length} 家，包括截图60家）`;
    for (const row of data.companies) { const audit = el('div', undefined, 'sales-audit-row'); audit.append(el('p', `${row.company} · ${row.industry} · ${row.status}`)); for (const [i, url] of row.sources.entries()) if (safeUrl(url)) { audit.append(link(`来源 ${i + 1}`, url), document.createTextNode('　')); } if (safeUrl(row.search_url)) audit.append(link('继续检索这家公司', row.search_url)); $('sales-audit-list').append(audit); }
    for (const id of ['sales-search', 'sales-industry', 'sales-city', 'sales-eligibility', 'sales-kind', 'sales-saved']) $(id).addEventListener('input', render);
    render();
  } catch { $('sales-update').textContent = '销售数据加载失败，请刷新重试。原岗位库仍可使用。'; }
}
if (typeof document !== 'undefined') init();
