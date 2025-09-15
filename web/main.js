const qs = (s) => document.querySelector(s);
const resultEl = qs('#result');
const apiKeyInput = qs('#apiKey');

// persist key locally
(function initKey() {
  const saved = localStorage.getItem('ss_api_key') || '';
  apiKeyInput.value = saved;
  apiKeyInput.addEventListener('blur', () => {
    localStorage.setItem('ss_api_key', (apiKeyInput.value || '').trim());
  });
})();

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

/** Robust POST: read text first to avoid "Unexpected end of JSON input". */
async function postApi(path, payload, expectBlob = false) {
  const res = await fetch(path, {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
      'X-API-Key': localStorage.getItem('ss_api_key') || ''
    },
    body: JSON.stringify(payload)
  });

  if (expectBlob) {
    if (!res.ok) {
      const t = await res.text().catch(() => '');
      throw new Error(`API ${res.status} ${res.statusText}: ${t || '[no body]'}`);
    }
    return await res.blob();
  }

  const raw = await res.text().catch(() => '');
  let data = null;
  try { data = raw ? JSON.parse(raw) : null; } catch {}
  if (!res.ok) throw new Error(`API ${res.status} ${res.statusText}: ${data ? JSON.stringify(data) : (raw || '[no body]')}`);
  return data ?? { ok: true, notice: 'Empty JSON body returned.' };
}

function show(x) { resultEl.textContent = JSON.stringify(x, null, 2); }
function showError(err) { resultEl.textContent = `❌ ${err.message}`; }

qs('#analyzeBtn').addEventListener('click', async () => {
  const payload = buildPayload();
  show({ status: 'sending', payload });
  try {
    const data = await postApi('/api/intelligence/analyze', payload);
    show(data);
  } catch (e) { showError(e); }
});

qs('#exportBtn').addEventListener('click', async () => {
  const payload = buildPayload();
  show({ status: 'exporting', payload });
  try {
    const blob = await postApi('/api/intelligence/export', payload, true);
    const url = URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url; a.download = 'signal_scale_export.csv';
    document.body.appendChild(a); a.click(); a.remove();
    URL.revokeObjectURL(url);
    show({ ok: true, message: 'CSV downloaded.' });
  } catch (e) { showError(e); }
});
