const qs = (s) => document.querySelector(s);
const resultTbl = qs('#resultsTable');
const resultBody = qs('#resultsBody');
const emptyState = qs('#emptyState');
const statusEl = qs('#status');
const apiKeyInput = qs('#apiKey');

(function initKey() {
  const saved = localStorage.getItem('ss_api_key') || '';
  apiKeyInput.value = saved;
  qs('#saveKeyBtn').addEventListener('click', () => {
    localStorage.setItem('ss_api_key', (apiKeyInput.value || '').trim());
    msg('API key saved.', true);
  });
})();

(async function health() {
  try {
    const r = await fetch('/api/health');
    const j = await r.json();
    qs('#healthPill').textContent = j.ok ? 'healthy' : 'check config';
    qs('#healthPill').style.background = j.ok ? '#253b2e' : '#3b2525';
    qs('#kvData').textContent = `data: probes:${j.probes ? 'on' : 'off'} psi:${j.pagespeed ? 'on' : 'off'} yt:${j.youtube ? 'on' : 'off'}`;
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
  const reportText = qs('#reportText').value.trim();
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
  const insights = payload?.insights || payload?.results || payload?.data || payload?.items || [];
  const brand = payload?.summary?.brand || payload?.brand?.name || 'Unknown';
  const cat = payload?.summary?.category || payload?.category_inferred || 'unknown';
  const count = insights.length;

  qs('#summaryBrand').textContent = brand;
  qs('#kvCategory').textContent = `category: ${cat}`;
  qs('#kvCount').textContent = `insights: ${count}`;

  if (!count) {
    resultTbl.style.display = 'none';
    emptyState.style.display = 'block';
    return;
  }

  resultBody.innerHTML = insights.map(it => `
    <tr>
      <td>${(it.competitor || '').toString()}</td>
      <td>${(it.title || '').toString()}</td>
      <td>${(it.score ?? '').toString()}</td>
      <td>${(it.note || '').toString()}</td>
    </tr>
  `).join('');
  emptyState.style.display = 'none';
  resultTbl.style.display = 'table';
}

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
