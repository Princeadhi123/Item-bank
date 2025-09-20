const state = {
  page: 1,
  pageSize: 25,
  totalPages: 0,
  sortBy: 'id',
  sortDir: 'asc',
  search: '',
  filters: {
    itemTypes: new Set(),
    levels: new Set(),
    contentArea: '',
    targetAreas: new Set(),
    nutaSkillLevels: new Set(),
    sources: new Set(),
    meanpMin: '',
    meanpMax: '',
    aIrtMin: '',
    aIrtMax: '',
  }
};

const $ = (sel, root = document) => root.querySelector(sel);
const $$ = (sel, root = document) => Array.from(root.querySelectorAll(sel));

function debounce(fn, delay = 300) {
  let t;
  return (...args) => { clearTimeout(t); t = setTimeout(() => fn(...args), delay); };
}

// Sync sticky offsets with the actual header height (Bootstrap navbar)
function setupStickyOffsets() {
  const header = document.querySelector('.app-header');
  const toolbar = document.querySelector('.main .toolbar');
  if (!header) return;
  const apply = () => {
    const h = Math.ceil(header.getBoundingClientRect().height);
    document.documentElement.style.setProperty('--header-offset', `${h}px`);
    const t = toolbar ? Math.ceil(toolbar.getBoundingClientRect().height) : 0;
    document.documentElement.style.setProperty('--toolbar-offset', `${t}px`);
  };
  apply();
  try {
    const ro = new ResizeObserver(apply);
    ro.observe(header);
    if (toolbar) ro.observe(toolbar);
  } catch (_) {
    window.addEventListener('resize', debounce(apply, 100));
  }
}

async function fetchJSON(url) {
  const res = await fetch(url);
  if (!res.ok) throw new Error(`Request failed: ${res.status}`);
  return await res.json();
}

function buildQuery() {
  const p = new URLSearchParams();
  p.set('page', String(state.page));
  p.set('page_size', String(state.pageSize));
  p.set('sort_by', state.sortBy);
  p.set('sort_dir', state.sortDir);
  if (state.search) p.set('search', state.search);

  // Multi select filters
  for (const v of state.filters.itemTypes) p.append('item_type', v);
  for (const v of state.filters.levels) p.append('level', v);
  for (const v of state.filters.targetAreas) p.append('target_area', v);
  for (const v of state.filters.nutaSkillLevels) p.append('nuta_skill_level', v);
  for (const v of state.filters.sources) p.append('source', v);
  if (state.filters.contentArea) p.set('content_area', state.filters.contentArea);

  if (state.filters.meanpMin) p.set('meanp_min', state.filters.meanpMin);
  if (state.filters.meanpMax) p.set('meanp_max', state.filters.meanpMax);
  if (state.filters.aIrtMin) p.set('a_irt_min', state.filters.aIrtMin);
  if (state.filters.aIrtMax) p.set('a_irt_max', state.filters.aIrtMax);

  return p.toString();
}

function setSkeleton(visible) {
  $('#tableSkeleton').hidden = !visible;
  $('#itemsTable').style.opacity = visible ? 0.3 : 1;
}

function toFixedOrDash(v, d = 3) {
  if (v === null || v === undefined || isNaN(Number(v))) return '—';
  return Number(v).toFixed(d);
}

function badge(text, cls = '') {
  const span = document.createElement('span');
  let classes = 'badge rounded-pill text-bg-secondary';
  if (cls === 'type') classes = 'badge rounded-pill text-bg-primary';
  else if (cls === 'level') classes = 'badge rounded-pill text-bg-success';
  else if (cls === 'content') classes = 'badge rounded-pill text-bg-warning';
  span.className = classes;
  span.textContent = text;
  return span;
}

function renderRows(items) {
  const tbody = $('#tableBody');
  tbody.innerHTML = '';
  for (const it of items) {
    const tr = document.createElement('tr');
    tr.tabIndex = 0;
    tr.innerHTML = `
      <td>${it.id}</td>
      <td>
        <div class="cell-main">
          <div class="title">${it.label ?? ''}</div>
          <div class="sub">${it.name ?? ''}</div>
        </div>
      </td>
      <td>${it.item_type_all ? badge(it.item_type_all, 'type').outerHTML : ''}</td>
      <td>${it.hierarchical_level_all ? badge(it.hierarchical_level_all, 'level').outerHTML : ''}</td>
      <td>${toFixedOrDash(it.meanp_all_classical, 3)}</td>
      <td>${toFixedOrDash(it.meanrit_classical, 3)}</td>
      <td>${it.dominant_content_area ? badge(it.dominant_content_area, 'content').outerHTML : ''}</td>
    `;
    tr.addEventListener('click', () => openDetails(it.id));
    tr.addEventListener('keypress', (e) => { if (e.key === 'Enter') openDetails(it.id); });
    tbody.appendChild(tr);
  }
}

function renderPagination(page, totalPages) {
  const container = $('#pages');
  container.innerHTML = '';
  const maxButtons = 7;
  let start = Math.max(1, page - Math.floor(maxButtons/2));
  let end = Math.min(totalPages, start + maxButtons - 1);
  start = Math.max(1, end - maxButtons + 1);
  for (let p = start; p <= end; p++) {
    const btn = document.createElement('button');
    const isActive = p === page;
    btn.className = `btn btn-sm ${isActive ? 'btn-primary' : 'btn-outline-secondary'} page`;
    btn.textContent = String(p);
    btn.addEventListener('click', () => { state.page = p; loadItems(); });
    container.appendChild(btn);
  }
  $('#prevPage').disabled = page <= 1;
  $('#nextPage').disabled = page >= totalPages;
}

async function loadItems() {
  try {
    setSkeleton(true);
    const qs = buildQuery();
    const data = await fetchJSON(`/api/items?${qs}`);
    $('#totalCount').textContent = data.total;
    state.totalPages = data.total_pages;
    renderRows(data.items);
    renderPagination(state.page, state.totalPages);
  } catch (e) {
    console.error(e);
    alert('Failed to load items. See console for details.');
  } finally {
    setSkeleton(false);
  }
}

function filterSection(titleText) {
  const wrap = document.createElement('section');
  wrap.className = 'filter-section';
  const h = document.createElement('h3');
  h.textContent = titleText;
  wrap.appendChild(h);
  return wrap;
}

function checkbox(id, label, checked=false) {
  const div = document.createElement('div');
  div.className = 'form-check';
  const input = document.createElement('input');
  input.type = 'checkbox';
  input.id = id;
  input.checked = checked;
  input.className = 'form-check-input';
  const lab = document.createElement('label');
  lab.className = 'form-check-label';
  lab.setAttribute('for', id);
  lab.textContent = label;
  div.appendChild(input);
  div.appendChild(lab);
  return {root: div, input};
}

function chip(label, active=false) {
  const b = document.createElement('button');
  b.type = 'button';
  b.className = `chip btn btn-sm rounded-pill ${active ? 'btn-primary' : 'btn-outline-primary'}`;
  b.textContent = label;
  return b;
}

async function buildFilters() {
  const data = await fetchJSON('/api/filters');
  const root = $('#filtersContainer');
  root.innerHTML = '';

  // Item Types
  const secType = filterSection('Item Type');
  for (const t of data.item_types) {
    const id = `type-${t}`;
    const {root: r, input} = checkbox(id, t);
    input.addEventListener('change', () => {
      if (input.checked) state.filters.itemTypes.add(t); else state.filters.itemTypes.delete(t);
      state.page = 1; loadItems();
    });
    secType.appendChild(r);
  }
  root.appendChild(secType);

  // Levels
  const secLvl = filterSection('Hierarchical Level');
  for (const lv of data.hierarchical_levels) {
    const id = `lv-${lv}`;
    const {root: r, input} = checkbox(id, lv);
    input.addEventListener('change', () => {
      if (input.checked) state.filters.levels.add(lv); else state.filters.levels.delete(lv);
      state.page = 1; loadItems();
    });
    secLvl.appendChild(r);
  }
  root.appendChild(secLvl);

  // Content area (single select chips)
  const secCA = filterSection('Content Area');
  const caWrap = document.createElement('div');
  caWrap.className = 'chips';
  for (const ca of data.content_areas) {
    const b = chip(ca.label);
    b.addEventListener('click', () => {
      if (state.filters.contentArea === ca.key) {
        state.filters.contentArea = '';
        b.classList.remove('btn-primary');
        b.classList.add('btn-outline-primary');
      } else {
        state.filters.contentArea = ca.key;
        $$('.chips .chip', secCA).forEach(x => { x.classList.remove('btn-primary'); x.classList.add('btn-outline-primary'); });
        b.classList.add('btn-primary');
        b.classList.remove('btn-outline-primary');
      }
      state.page = 1; loadItems();
    });
    caWrap.appendChild(b);
  }
  secCA.appendChild(caWrap);
  root.appendChild(secCA);

  // Target areas (multi select chips)
  const secTA = filterSection('Target Areas');
  const taWrap = document.createElement('div');
  taWrap.className = 'chips';
  for (const t of data.target_areas) {
    const b = chip(t.label);
    b.addEventListener('click', () => {
      const willSelect = !b.classList.contains('btn-primary');
      if (willSelect) {
        b.classList.remove('btn-outline-primary');
        b.classList.add('btn-primary');
        state.filters.targetAreas.add(t.key);
      } else {
        b.classList.remove('btn-primary');
        b.classList.add('btn-outline-primary');
        state.filters.targetAreas.delete(t.key);
      }
      state.page = 1; loadItems();
    });
    taWrap.appendChild(b);
  }
  secTA.appendChild(taWrap);
  root.appendChild(secTA);

  // NuTa skill levels
  const secNu = filterSection('NuTa Skill Level');
  for (const n of data.nuta_skill_levels) {
    const id = `nu-${n}`;
    const {root: r, input} = checkbox(id, n);
    input.addEventListener('change', () => {
      if (input.checked) state.filters.nutaSkillLevels.add(n); else state.filters.nutaSkillLevels.delete(n);
      state.page = 1; loadItems();
    });
    secNu.appendChild(r);
  }
  root.appendChild(secNu);

  // Sources
  const secSrc = filterSection('Source');
  for (const s of data.sources) {
    const id = `src-${s}`;
    const {root: r, input} = checkbox(id, s);
    input.addEventListener('change', () => {
      if (input.checked) state.filters.sources.add(s); else state.filters.sources.delete(s);
      state.page = 1; loadItems();
    });
    secSrc.appendChild(r);
  }
  root.appendChild(secSrc);

  // Numeric range filters
  const secNum = filterSection('Numeric Filters');
  const numGrid = document.createElement('div');
  numGrid.className = 'num-grid';
  numGrid.innerHTML = `
    <label>meanp min <input id="meanpMin" type="number" step="0.01" placeholder="0"/></label>
    <label>meanp max <input id="meanpMax" type="number" step="0.01" placeholder="1"/></label>
    <label>a_irt min <input id="aIrtMin" type="number" step="0.01" placeholder=""/></label>
    <label>a_irt max <input id="aIrtMax" type="number" step="0.01" placeholder=""/></label>
  `;
  secNum.appendChild(numGrid);
  root.appendChild(secNum);

  $('#meanpMin').addEventListener('input', debounce((e) => { state.filters.meanpMin = e.target.value; state.page = 1; loadItems(); }, 400));
  $('#meanpMax').addEventListener('input', debounce((e) => { state.filters.meanpMax = e.target.value; state.page = 1; loadItems(); }, 400));
  $('#aIrtMin').addEventListener('input', debounce((e) => { state.filters.aIrtMin = e.target.value; state.page = 1; loadItems(); }, 400));
  $('#aIrtMax').addEventListener('input', debounce((e) => { state.filters.aIrtMax = e.target.value; state.page = 1; loadItems(); }, 400));
}

function setupSort() {
  $$('#itemsTable thead th[data-sort]').forEach(th => {
    th.addEventListener('click', () => {
      const key = th.getAttribute('data-sort');
      if (state.sortBy === key) {
        state.sortDir = state.sortDir === 'asc' ? 'desc' : 'asc';
      } else {
        state.sortBy = key; state.sortDir = 'asc';
      }
      loadItems();
    });
  });
}

function setupToolbar() {
  $('#searchInput').addEventListener('input', debounce((e) => {
    state.search = e.target.value.trim();
    state.page = 1; loadItems();
  }, 300));

  $('#pageSize').addEventListener('change', (e) => {
    state.pageSize = Number(e.target.value);
    state.page = 1; loadItems();
  });

  $('#prevPage').addEventListener('click', () => { if (state.page > 1) { state.page--; loadItems(); } });
  $('#nextPage').addEventListener('click', () => { if (state.page < state.totalPages) { state.page++; loadItems(); } });

  $('#toggleFilters').addEventListener('click', () => {
    const panel = $('#filtersPanel');
    panel.classList.toggle('open');
    $('#toggleFilters').setAttribute('aria-expanded', String(panel.classList.contains('open')));
  });

  $('#clearFilters').addEventListener('click', () => {
    state.filters = { itemTypes: new Set(), levels: new Set(), contentArea: '', targetAreas: new Set(), nutaSkillLevels: new Set(), sources: new Set(), meanpMin: '', meanpMax: '', aIrtMin: '', aIrtMax: '' };
    buildFilters();
    state.page = 1; loadItems();
  });

  // Theme toggle (sync our theme and Bootstrap)
  const prefersDark = window.matchMedia && window.matchMedia('(prefers-color-scheme: dark)').matches;
  const setTheme = (mode) => {
    document.documentElement.dataset.theme = mode; // for our custom CSS vars
    document.documentElement.setAttribute('data-bs-theme', mode); // for Bootstrap 5.3
  };
  setTheme(prefersDark ? 'dark' : 'light');
  $('#themeToggle').addEventListener('click', () => {
    const curr = document.documentElement.getAttribute('data-bs-theme') || document.documentElement.dataset.theme || 'light';
    setTheme(curr === 'dark' ? 'light' : 'dark');
  });
}

async function openDetails(id) {
  try {
    const data = await fetchJSON(`/api/items/${id}`);
    renderDetails(data);
    const drawer = $('#detailsDrawer');
    drawer.classList.add('open');
    drawer.setAttribute('aria-hidden', 'false');
    // Prevent background scroll and ensure details start at top
    document.body.classList.add('no-scroll');
    const dr = $('#detailsRoot');
    if (dr) dr.scrollTop = 0;
  } catch (e) {
    console.error(e);
    alert('Failed to load item details');
  }
}

function closeDetails() {
  const drawer = $('#detailsDrawer');
  drawer.classList.remove('open');
  drawer.setAttribute('aria-hidden', 'true');
  // Re-enable background scroll
  document.body.classList.remove('no-scroll');
}

function barRow(label, value, max=1) {
  const pct = Math.max(0, Math.min(100, (max !== 0 ? (value / max) : 0) * 100));
  return `
    <div class="bar-row">
      <div class="bar-label">${label}</div>
      <div class="bar-track"><div class="bar-fill" style="width:${pct.toFixed(1)}%"></div></div>
      <div class="bar-value">${Number(value).toFixed(3)}</div>
    </div>
  `;
}

function renderDetails(item) {
  const root = $('#detailsRoot');
  root.innerHTML = '';

  const header = document.createElement('div');
  header.className = 'detail-header';
  header.innerHTML = `
    <div class="id">ID ${item.id}</div>
    <h2>${item.label ?? ''}</h2>
    <div class="sub">${item.name ?? ''}</div>
    <div class="meta">
      ${item.type ? `<span class="badge type">${item.type}</span>` : ''}
      ${item.hierarchical_level ? `<span class="badge level">${item.hierarchical_level}</span>` : ''}
      ${item.dominant_content_area ? `<span class="badge content">${item.dominant_content_area}</span>` : ''}
      ${item.source ? `<span class="badge">${item.source}</span>` : ''}
    </div>
  `;
  root.appendChild(header);

  // Content areas (normalize by max among s1..s6 for this item)
  const secCA = document.createElement('section');
  secCA.className = 'detail-section';
  secCA.innerHTML = '<h3>Content Areas</h3>';
  const maxCA = Math.max(...Object.values(item.content_area).map(v => Number(v) || 0));
  secCA.innerHTML += Object.entries(item.content_area).map(([k,v]) => barRow(k, Number(v)||0, maxCA||1)).join('');
  root.appendChild(secCA);

  // NuTa breakdown
  const secNu = document.createElement('section');
  secNu.className = 'detail-section';
  secNu.innerHTML = `<h3>NuTa Breakdown ${item.nuta?.nuta_skill_level ? `- ${item.nuta.nuta_skill_level}` : ''}</h3>`;
  const maxNu = Math.max(...Object.values(item.nuta?.weights || {}).map(v => Number(v) || 0));
  secNu.innerHTML += Object.entries(item.nuta?.weights || {}).map(([k,v]) => barRow(k.toUpperCase(), Number(v)||0, maxNu||1)).join('');
  if (item.nuta?.contents) {
    const p = document.createElement('p');
    p.className = 'note';
    p.textContent = item.nuta.contents;
    secNu.appendChild(p);
  }
  root.appendChild(secNu);

  // Difficulty & Discrimination
  const secDiff = document.createElement('section');
  secDiff.className = 'detail-section grid2';
  const d = item.difficulty || {}; const disc = item.discrimination || {};
  secDiff.innerHTML = `
    <div>
      <h3>Difficulty (Classical & IRT)</h3>
      <ul class="kv">
        <li><span>meanp_all_classical</span><b>${toFixedOrDash(d.meanp_all_classical)}</b></li>
        <li><span>p_g3_classical</span><b>${toFixedOrDash(d.p_g3_classical)}</b></li>
        <li><span>p_g6_classical</span><b>${toFixedOrDash(d.p_g6_classical)}</b></li>
        <li><span>p_g8_classical</span><b>${toFixedOrDash(d.p_g8_classical)}</b></li>
        <li><span>p_g9_classical</span><b>${toFixedOrDash(d.p_g9_classical)}</b></li>
        <li><span>b_0_1_irt</span><b>${toFixedOrDash(d.b_0_1_irt)}</b></li>
        <li><span>b01_2_irt</span><b>${toFixedOrDash(d.b01_2_irt)}</b></li>
        <li><span>b012_3_irt</span><b>${toFixedOrDash(d.b012_3_irt)}</b></li>
        <li><span>b0123_4_irt</span><b>${toFixedOrDash(d.b0123_4_irt)}</b></li>
      </ul>
    </div>
    <div>
      <h3>Discrimination (Classical & IRT)</h3>
      <ul class="kv">
        <li><span>meanrit_classical</span><b>${toFixedOrDash(disc.meanrit_classical)}</b></li>
        <li><span>meang_classical</span><b>${toFixedOrDash(disc.meang_classical)}</b></li>
        <li><span>meand_classical</span><b>${toFixedOrDash(disc.meand_classical)}</b></li>
        <li><span>meanstd_classical</span><b>${toFixedOrDash(disc.meanstd_classical)}</b></li>
        <li><span>a_irt</span><b>${toFixedOrDash(disc.a_irt)}</b></li>
      </ul>
    </div>
  `;
  root.appendChild(secDiff);

  // Targets
  const secT = document.createElement('section');
  secT.className = 'detail-section';
  secT.innerHTML = '<h3>Target Areas</h3>';
  const tVals = Object.entries(item.targets || {});
  const maxT = Math.max(...tVals.map(([,v]) => Number(v)||0));
  secT.innerHTML += tVals.map(([k,v]) => barRow(k.toUpperCase(), Number(v)||0, maxT||1)).join('');
  root.appendChild(secT);
}

function initEvents() {
  setupSort();
  setupToolbar();
  $('#closeDrawer').addEventListener('click', closeDetails);
  $('.drawer-backdrop').addEventListener('click', closeDetails);
}

async function init() {
  setupStickyOffsets();
  initEvents();
  await buildFilters();
  await loadItems();
}

init();
