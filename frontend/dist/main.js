// main.js

const qs = (s) => document.querySelector(s);

// Elements
const resultTbl = qs('#resultsTable');
const resultBody = qs('#resultsBody');
const emptyState = qs('#emptyState');
const statusEl = qs('#status');
const apiKeyInput = qs('#apiKey');

// Persist API key
(function initKey() {
  const saved = localStorage.getItem('ss_api_key') || '';
  apiKeyInput.value = saved;
  qs('#saveKeyBtn').addEventListener('click', () => {
    localStorage.setItem('ss_api_key', (apiKeyInput.value || '').trim());
    msg('API key saved.', true);
  });
})();

// Health check
(async function health() {
  try {
    const r = await fetch('/api/health');
    const j = await r.json();
    qs('#healthPill').textContent = j.ok ? 'healthy' : 'check config';
    qs('#healthPill').style.background = j.ok ? '#253b2e' : '#3b2525';
    qs('#footerHealth').textContent = `providers: ${j.provider_order?.join(', ') || '-'}`;
  } catch {
    qs('#healthPill').textContent = 'no api';
    qs('#healthPill').style.background = '#3b2525';
  }
})();

function msg(text, ok=false) {
  statusEl.innerHTML = ok ? `<span class="ok">${text}</span>` : `<span class="err">${text}</span>`;
  setTimeout(() => { statusEl.textContent = ''; }, 3000);
}

function buildPayload() {
  const brandName = qs('#brandName').value.trim();
  const brandUrl = qs('#brandUrl').value.trim();
  const compLines = qs('#competitors').value.split('\n').map(l => l.trim()).filter(Boolean);
  const competitors = compLines.map(line => {
    const [name, url] = line.split('|').map(p => (p || '').trim());
    return { name: name || null, url: url || null };
  });
  const reportText = qs('#reportText')?.value.trim();
  const reports = reportText ? [reportText] : [];
  return { brand: { name: brandName || null, url: brandUrl || null, meta: null }, competitors, reports, mode: 'all', window_days: 7 };
}

async function postApi(path, payload, expectBlob=false) {
  const res = await fetch(path, {
    method: 'POST',
    headers: {
      'Content-Type': expectBlob ? 'application/octet-stream' : 'application/json',
      'X-API-Key': localStorage.getItem('ss_api_key') || ''
    },
    body: expectBlob ? payload : JSON.stringify(payload)
  });

  if (expectBlob) {
    if (!res.ok) throw new Error(`${res.status} ${res.statusText}`);
    return await res.blob();
  }

  const raw = await res.text().catch(() => '');
  let data = null;
  try { data = raw ? JSON.parse(raw) : null; } catch {}
  if (!res.ok) throw new Error(data ? JSON.stringify(data) : (raw || `${res.status} ${res.statusText}`));
  return data ?? { ok: true, notice: 'Empty JSON body returned.' };
}

function renderInsights(payload) {
  const insights = payload?.analysis?.trends || payload?.insights || payload?.results || [];
  const cat = payload?.summary?.category || payload?.category_inferred || 'unknown';
  const count = insights.length;

  qs('#category').textContent = `category: ${cat}`;
  qs('#summary').textContent = `${payload?.brand?.name || 'Unknown'} · ${count} insights`;

  if (!count) {
    resultTbl.style.display = 'none';
    emptyState.style.display = 'block';
    return;
  }

  resultBody.innerHTML = insights.map(it => `
    <tr>
      <td>${(it.competitor || it.name || '').toString()}</td>
      <td>${(it.title || it.signal || '').toString()}</td>
      <td>${(it.score ?? '').toString()}</td>
      <td>${(it.note || it.recommendation || '').toString()}</td>
    </tr>
  `).join('');
  emptyState.style.display = 'none';
  resultTbl.style.display = 'table';
}

// Actions
qs('#analyzeBtn').addEventListener('click', async () => {
  const payload = buildPayload();
  try {
    msg('Running…', true);
    const data = await postApi('/api/intelligence/analyze', payload);
    renderInsights(data);
    msg('Done', true);
  } catch (e) { msg(e.message || 'Error'); }
});

qs('#exportBtn').addEventListener('click', async () => {
  const payload = buildPayload();
  try {
    const blob = await postApi('/api/intelligence/export', payload, true);
    const url = URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url; a.download = 'signal_scale_export.csv';
    document.body.appendChild(a); a.click(); a.remove();
    URL.revokeObjectURL(url);
    msg('CSV downloaded.', true);
  } catch (e) { msg(e.message || 'Export failed'); }
});
