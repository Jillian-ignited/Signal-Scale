const qs = (s) => document.querySelector(s);
const qsa = (s) => [...document.querySelectorAll(s)];
let chart;

/* ---------- Nav ---------- */
qsa('.nav').forEach(btn => {
  btn.addEventListener('click', () => {
    qsa('.nav').forEach(b => b.classList.remove('active'));
    qsa('.page').forEach(p => p.classList.remove('active'));
    btn.classList.add('active');
    const target = btn.getAttribute('data-target');
    qs(target).classList.add('active');
  });
});

/* ---------- State ---------- */
const pill = qs('#pill');
const apiKeyInput = qs('#apiKey');
const statusEl = qs('#status');
const subtitle = qs('#subtitle');

/* Persist key */
(function initKey(){
  const saved = localStorage.getItem('ss_api_key') || '';
  apiKeyInput.value = saved;
  qs('#saveKeyBtn').addEventListener('click', () => {
    localStorage.setItem('ss_api_key', (apiKeyInput.value || '').trim());
    toast('API key saved.', true);
  });
})();

/* Health */
(async function health(){
  try{
    const r = await fetch('/api/health');
    const j = await r.json();
    pill.textContent = j.ok ? 'healthy' : 'check config';
    pill.style.background = j.ok ? '#22352a' : '#3b2525';
    qs('#kvData').textContent = `probes:${j.probes?'on':'off'} psi:${j.pagespeed?'on':'off'} yt:${j.youtube?'on':'off'}`;
  }catch{
    pill.textContent = 'no api';
    pill.style.background = '#3b2525';
  }
})();

function toast(text, ok=false){
  statusEl.innerHTML = ok ? `<span style="color:#79e09f">${text}</span>` : `<span style="color:#ff8a8a">${text}</span>`;
  setTimeout(() => statusEl.textContent = '', 2500);
}

/* ---------- Input building ---------- */
function buildPayload(){
  const brandName = qs('#brandName').value.trim();
  const brandUrl  = qs('#brandUrl').value.trim();
  const compLines = qs('#competitors').value.split('\n').map(l => l.trim()).filter(Boolean);
  const competitors = compLines.map(line => {
    const [name, url] = line.split('|').map(p => (p || '').trim());
    return { name: name || null, url: url || null };
  });
  const reportText = qs('#reportText').value.trim();
  const reports = reportText ? [reportText] : [];
  return { brand:{ name: brandName || null, url: brandUrl || null, meta: null }, competitors, reports, mode:'all', window_days:7 };
}

async function postApi(path, payload, expectBlob=false){
  const res = await fetch(path, {
    method: 'POST',
    headers: {
      'Content-Type': expectBlob ? 'application/octet-stream' : 'application/json',
      'X-API-Key': localStorage.getItem('ss_api_key') || ''
    },
    body: expectBlob ? payload : JSON.stringify(payload)
  });

  if (expectBlob){
    if (!res.ok) throw new Error(`${res.status} ${res.statusText}`);
    return await res.blob();
  }

  const raw = await res.text().catch(() => '');
  let data = null;
  try { data = raw ? JSON.parse(raw) : null; } catch {}
  if (!res.ok) throw new Error(data ? JSON.stringify(data) : (raw || `${res.status} ${res.statusText}`));
  return data ?? { ok:true, notice:'Empty JSON body returned.' };
}

/* ---------- Renderers ---------- */
function renderOverview(payload){
  const insights = (payload?.insights || payload?.results || []);
  const brand = payload?.summary?.brand || payload?.brand?.name || '—';
  const cat = payload?.summary?.category || payload?.category_inferred || '—';
  const count = insights.length;

  qs('#kvBrand').textContent = brand;
  qs('#kvCategory').textContent = cat;
  qs('#kvCount').textContent = count.toString();
  subtitle.textContent = count ? `${brand} • ${cat} • ${count} insights` : 'Set brand + peers → Analyze';

  // Chart: score sum by competitor/brand
  const grouped = insights.reduce((acc, it) => {
    const k = (it.competitor || 'Brand').trim() || 'Brand';
    acc[k] = (acc[k] || 0) + (Number(it.score) || 0);
    return acc;
  }, {});
  const labels = Object.keys(grouped);
  const data = Object.values(grouped);

  const ctx = qs('#chartByCompetitor');
  if (chart) chart.destroy();
  chart = new Chart(ctx, {
    type: 'bar',
    data: { labels, datasets: [{ label: 'Weighted signal sum', data }] },
    options: { responsive:true, plugins:{ legend:{ display:false }}, scales:{ y:{ beginAtZero:true } } }
  });
}

function renderTable(payload){
  const insights = (payload?.insights || payload?.results || []);
  const body = qs('#resultsBody');
  const tbl = qs('#resultsTable');
  const empty = qs('#emptyState');

  if (!insights.length){ tbl.classList.add('hide'); empty.classList.remove('hide'); body.innerHTML = ''; return; }

  body.innerHTML = insights.map(it => `
    <tr>
      <td>${escapeHtml(it.competitor || '')}</td>
      <td>${escapeHtml(it.title || '')}</td>
      <td>${Number(it.score ?? 0)}</td>
      <td>${escapeHtml(it.note || '')}</td>
    </tr>
  `).join('');
  empty.classList.add('hide');
  tbl.classList.remove('hide');
}

function renderReport(payload){
  const insights = (payload?.insights || []);
  const brand = payload?.summary?.brand || '—';
  const cat = payload?.summary?.category || '—';
  const date = new Date().toLocaleString();

  qs('#rBrand').textContent = `${brand} — Competitive Report`;
  qs('#rMeta').textContent = `Category: ${cat} • Insights: ${insights.length}`;
  qs('#rDate').textContent = date;

  // Exec summary (quick take)
  const top = rankTop(insights, 5);
  qs('#rSummary').textContent = top.length
    ? `${brand} sits in ${cat}. Priority moves: ${top.map(t => t.title).slice(0,3).join('; ')}.`
    : 'Run analysis to populate.';

  // Top recommendations
  qs('#rTop').innerHTML = top.map(t => `<li><b>${escapeHtml(t.title)}</b> — ${escapeHtml(t.note || '')}</li>`).join('');

  // Detailed table-like narrative
  const perComp = groupBy(insights, it => (it.competitor || 'Brand'));
  const blocks = Object.keys(perComp).sort().map(name => {
    const rows = perComp[name].map(r => `
      <div class="row">
        <div class="tag">${escapeHtml(name)}</div>
        <div>${escapeHtml(r.title || '')}</div>
        <div>${Number(r.score ?? 0)}</div>
      </div>
    `).join('');
    return rows;
  }).join('');
  qs('#rDetail').innerHTML = blocks || '<div class="muted">No details yet.</div>';
}

/* ---------- Helpers ---------- */
function escapeHtml(s){ return (s||'').toString().replace(/[&<>"']/g, c => ({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c])); }
function groupBy(arr, fn){ return arr.reduce((m,x)=>{ const k = fn(x); (m[k]=m[k]||[]).push(x); return m; },{}); }
function rankTop(insights, n=5){
  // simple rank: score desc, prefer items that mention media/checkout/collab
  const boost = (t='') => (/pdp|video|checkout|pay|collab|drop|ugc|speed|reviews/i.test(t) ? 8 : 0);
  return insights.slice().sort((a,b)=> (b.score+boost(b.title)) - (a.score+boost(a.title))).slice(0,n);
}

/* ---------- Actions ---------- */
qs('#analyzeBtn').addEventListener('click', async () => {
  const payload = buildPayload();
  toast('Running…', true);
  try{
    const data = await postApi('/api/intelligence/analyze', payload);
    renderOverview(data);
    renderTable(data);
    renderReport(data);
    // switch to Insights tab on first success
    qsa('.nav').forEach(b => b.classList.remove('active'));
    qsa('.page').forEach(p => p.classList.remove('active'));
    qs('.nav[data-target="#insights"]').classList.add('active');
    qs('#insights').classList.add('active');
    toast('Done', true);
  }catch(e){
    toast(e.message || 'Error');
  }
});

qs('#exportCsvBtn').addEventListener('click', async () => {
  const payload = buildPayload();
  try{
    const blob = await postApi('/api/intelligence/export', payload, true);
    const url = URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url; a.download = 'signal_scale_export.csv';
    document.body.appendChild(a); a.click(); a.remove();
    URL.revokeObjectURL(url);
    toast('CSV downloaded.', true);
  }catch(e){
    toast(e.message || 'Export failed');
  }
});

qs('#exportPdfBtn').addEventListener('click', () => {
  // Print the report tab (it’s print-optimized)
  qsa('.nav').forEach(b => b.classList.remove('active'));
  qsa('.page').forEach(p => p.classList.remove('active'));
  qs('.nav[data-target="#report"]').classList.add('active');
  qs('#report').classList.add('active');
  setTimeout(() => window.print(), 200);
});
