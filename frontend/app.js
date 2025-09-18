// frontend/app.js
const qs = (s) => document.querySelector(s);
const resultEl = qs('#result');
const cardsEl = qs('#cards');
const apiKeyInput = qs('#apiKey');
const debugToggle = qs('#debugToggle');

(function initKey() {
  const saved = localStorage.getItem('ss_api_key') || '';
  apiKeyInput.value = saved;
  apiKeyInput.addEventListener('blur', () => {
    localStorage.setItem('ss_api_key', (apiKeyInput.value || '').trim());
  });
  const dbg = localStorage.getItem('ss_debug') === '1';
  debugToggle.checked = dbg;
})();

debugToggle.addEventListener('change', () => {
  localStorage.setItem('ss_debug', debugToggle.checked ? '1' : '0');
  renderRaw(null); // clear raw if turning off
});

function buildPayload() {
  const brandName = qs('#brandName').value.trim();
  const brandUrl = qs('#brandUrl').value.trim();
  const compLines = qs('#competitors').value.split('\n').map(l => l.trim()).filter(Boolean);
  const competitors = compLines.map(line => {
    const [name, url] = line.split('|').map(p => (p || '').trim());
    return { name: name || null, url: url || null };
  });
  return { brand: { name: brandName || null, url: brandUrl || null, meta: null }, competitors };
}

async function postApi(path, payload) {
  const res = await fetch(path, {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
      'X-API-Key': localStorage.getItem('ss_api_key') || ''
    },
    body: JSON.stringify(payload)
  });
  const raw = await res.text().catch(() => '');
  let data = null;
  try { data = raw ? JSON.parse(raw) : null; } catch {}
  if (!res.ok) throw new Error(`API ${res.status} ${res.statusText}: ${data ? JSON.stringify(data) : (raw || '[no body]')}`);
  return data ?? { ok: true, notice: 'Empty JSON body returned.' };
}

function renderRaw(obj) {
  const dbg = localStorage.getItem('ss_debug') === '1';
  resultEl.textContent = dbg && obj ? JSON.stringify(obj, null, 2) : '';
}

function chip(label, value) {
  return `<div class="chip"><span>${label}</span><strong>${value}</strong></div>`;
}

function renderCards(data) {
  if (!data || !data.ok) { cardsEl.innerHTML = ''; return; }
  const s = data.summary || {};
  const ev = data.evidence || {};
  const brand = ev.brand || {};
  const site = (brand.site || {});
  const sigs = (data.signals || []).slice(0, 6);

  const top =
    `<div class="card">
       <h3>${s.brand || 'Brand'}</h3>
       <div class="chips">
         ${chip('Domain', s.resolved_domain || '—')}
         ${chip('Category', s.category || '—')}
         ${chip('Brand Posts', (s.counts && s.counts.brand_posts) || 0)}
         ${chip('Comp Posts', (s.counts && s.counts.comp_posts) || 0)}
       </div>
     </div>`;

  const perf =
    `<div class="card">
       <h4>Site</h4>
       <div class="chips">
         ${chip('Reachable', site.reachable ? 'Yes' : 'No')}
         ${chip('Status', site.status ?? '—')}
         ${chip('Latency (ms)', site.latency_ms ?? '—')}
         ${chip('Platform', Object.keys(site.platform || {}).filter(k => site.platform[k]).join(', ') || '—')}
       </div>
       <div class="chips">
         ${chip('Shop Pay', site.payments?.shop_pay ? 'Yes' : 'No')}
         ${chip('Apple Pay', site.payments?.apple_pay ? 'Yes' : 'No')}
         ${chip('Klarna', site.payments?.klarna ? 'Yes' : 'No')}
       </div>
     </div>`;

  const sig =
    `<div class="card">
       <h4>Signals</h4>
       <ul class="list">
         ${
           sigs.length
            ? sigs.map(sg => `<li><strong>${sg.signal}</strong> — ${sg.note}</li>`).join('')
            : '<li>No high-signal differences yet.</li>'
         }
       </ul>
     </div>`;

  cardsEl.innerHTML = top + perf + sig;
}

qs('#analyzeBtn').addEventListener('click', async () => {
  const payload = buildPayload();
  cardsEl.innerHTML = `<div class="card"><em>Analyzing…</em></div>`;
  renderRaw(null);
  try {
    const data = await postApi('/api/intelligence/analyze', payload);
    renderCards(data);
    renderRaw(data);
  } catch (e) {
    cardsEl.innerHTML = `<div class="card error">❌ ${e.message}</div>`;
    renderRaw({ error: e.message });
  }
});

qs('#exportBtn').addEventListener('click', async () => {
  const payload = buildPayload();
  try {
    const res = await fetch('/api/intelligence/export', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json', 'X-API-Key': localStorage.getItem('ss_api_key') || '' },
      body: JSON.stringify(payload)
    });
    if (!res.ok) throw new Error(`Export failed: ${res.status}`);
    const blob = await res.blob();
    const url = URL.createObjectURL(blob);
    const a = document.createElement('a'); a.href = url; a.download = 'signal_scale_export.csv';
    document.body.appendChild(a); a.click(); a.remove(); URL.revokeObjectURL(url);
  } catch (e) {
    cardsEl.innerHTML = `<div class="card error">❌ ${e.message}</div>`;
  }
});
