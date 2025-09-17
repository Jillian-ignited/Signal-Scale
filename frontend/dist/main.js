const qs = (s) => document.querySelector(s);
const resultTbl = qs('#resultsTable');
const resultBody = qs('#resultsBody');
const emptyState = qs('#emptyState');
const statusEl = qs('#status');
const apiKeyInput = qs('#apiKey');
let chart;

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
    const pill = qs('#healthPill');
    pill.textContent = j.ok ? 'healthy' : 'check config';
    pill.classList.toggle('bg-[#253b2e]', j.ok);
    qs('#kvData').textContent = `data: probes:${j.probes?'on':'off'} psi:${j.pagespeed?'on':'off'} yt:${j.youtube?'on':'off'}`;
  } catch {
    qs('#healthPill').textContent = 'no api';
  }
})();

function msg(text, ok=false) {
  statusEl.innerHTML = ok ? `<span class="text-[#7bd489]">${text}</span>` : `<span class="text-[#ff8a8a]">${text}</span>`;
  setTimeout(() => { statusEl.textContent = ''; }, 2500);
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

function renderChart(insights) {
  const ctx = qs('#insightsChart');
  const grouped = insights.reduce((acc, it) => {
    const k = (it.competitor || 'Brand').trim() || 'Brand';
    acc[k] = (acc[k] || 0) + (Number(it.score) || 0);
    return acc;
  }, {});
  const labels = Object.keys(grouped);
  const data = Object.values(grouped);

  if (chart) chart.destroy();
  chart = new Chart(ctx, {
    type: 'bar',
    data: { labels, datasets: [{ label: 'Score sum', data }] },
    options: {
      responsive: true,
      plugins: { legend: { display: false } },
      scales: { y: { beginAtZero: true } }
    }
  });
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
    resultTbl.classList.add('hidden');
    emptyState.classList.remove('hidden');
    return;
  }

  resultBody.innerHTML = insights.map(it => `
    <tr>
      <td class="border-b border-border py-2 pr-3">${(it.competitor || '').toString()}</td>
      <td class="border-b border-border py-2 pr-3">${(it.title || '').toString()}</td>
      <td class="border-b border-border py-2 pr-3">${(it.score ?? '').toString()}</td>
      <td class="border-b border-border py-2">${(it.note || '').toString()}</td>
    </tr>
  `).join('');
  emptyState.classList.add('hidden');
  resultTbl.classList.remove('hidden');

  renderChart(insights);
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

qs('#exportCsvBtn').addEventListener('click', async () => {
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

// PDF export (print-optimized stylesheet)
qs('#exportPdfBtn').addEventListener('click', () => {
  window.print();
});
