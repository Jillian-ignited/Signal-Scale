// Simple vanilla controller for Signal & Scale

const qs = (s) => document.querySelector(s);
const qsa = (s) => Array.from(document.querySelectorAll(s));

const resultEl = qs("#result");
const apiKeyInput = qs("#apiKey");
const analyzeBtn = qs("#analyzeBtn");
const exportBtn = qs("#exportBtn");
const printBtn = qs("#printBtn");
const clearBtn = qs("#clearBtn");

const brandNameEl = qs("#brandName");
const brandUrlEl = qs("#brandUrl");
const competitorsEl = qs("#competitors");

const kpiSignals = qs("#kpiSignals");
const kpiComps = qs("#kpiComps");
const kpiStrength = qs("#kpiStrength");
const kpiGaps = qs("#kpiGaps");

const repStrengths = qs("#repStrengths");
const repGaps = qs("#repGaps");
const repPriorities = qs("#repPriorities");
const repTimestamp = qs("#repTimestamp");

const coverBrand = qs("#coverBrand");
const coverDate = qs("#coverDate");
const phDate = qs("#ph-date");

// nav
qsa(".navbtn").forEach((b) =>
  b.addEventListener("click", () => {
    qsa(".navbtn").forEach((x) => x.classList.remove("active"));
    b.classList.add("active");
    const page = b.dataset.page;
    qsa(".page").forEach((p) => p.classList.remove("show"));
    qs(`#${page}`).classList.add("show");
  })
);

// persist key locally
(function initKey() {
  const saved = localStorage.getItem("ss_api_key") || "";
  apiKeyInput.value = saved;
  apiKeyInput.addEventListener("blur", () => {
    localStorage.setItem("ss_api_key", (apiKeyInput.value || "").trim());
  });
})();

// Build payload
function buildPayload() {
  const brandName = brandNameEl.value.trim();
  const brandUrl = brandUrlEl.value.trim();
  const compLines = competitorsEl.value
    .split("\n")
    .map((l) => l.trim())
    .filter(Boolean);
  const competitors = compLines.map((line) => {
    const [name, url] = line.split("|").map((p) => (p || "").trim());
    return { name: name || null, url: url || null };
  });

  return { brand: { name: brandName || null, url: brandUrl || null, meta: null }, competitors };
}

// Robust POST: read text first to avoid JSON parse errors
async function postApi(path, payload, expectBlob = false) {
  const res = await fetch(path, {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
      "X-API-Key": localStorage.getItem("ss_api_key") || ""
    },
    body: JSON.stringify(payload)
  });

  if (expectBlob) {
    if (!res.ok) {
      const t = await res.text().catch(() => "");
      throw new Error(`API ${res.status} ${res.statusText}: ${t || "[no body]"}`);
    }
    return await res.blob();
  }

  const raw = await res.text().catch(() => "");
  let data = null;
  try {
    data = raw ? JSON.parse(raw) : null;
  } catch {}
  if (!res.ok) throw new Error(`API ${res.status} ${res.statusText}: ${data ? JSON.stringify(data) : raw || "[no body]"}`);
  return data ?? { ok: true, notice: "Empty JSON body returned." };
}

function show(x) {
  resultEl.textContent = JSON.stringify(x, null, 2);
}
function showError(err) {
  resultEl.textContent = `❌ ${err.message}`;
}

// KPIs + Report population
function summarize(result) {
  const signals = result?.signals || [];
  const comps = (result?.summary?.competitors || []).filter(Boolean);
  kpiSignals.textContent = String(signals.length);
  kpiComps.textContent = String(comps.length);

  const strengths = signals.filter((s) => /advantage/i.test(s.signal) || /strength/i.test(s.signal));
  const gaps = signals.filter((s) => /gap/i.test(s.signal));
  kpiStrength.textContent = strengths.length ? strengths.length : "—";
  kpiGaps.textContent = gaps.length ? gaps.length : "—";

  // Report sections
  repStrengths.innerHTML = strengths.length
    ? strengths.map((s) => `<li>${s.signal} — ${s.note}</li>`).join("")
    : `<li class="muted">No strengths identified yet.</li>`;
  repGaps.innerHTML = gaps.length
    ? gaps.map((s) => `<li>${s.signal} — ${s.note}</li>`).join("")
    : `<li class="muted">No gaps identified yet.</li>`;

  // Priorities: pick top 3 highest score
  const top3 = [...signals].sort((a, b) => (b.score || 0) - (a.score || 0)).slice(0, 3);
  repPriorities.innerHTML = top3.length
    ? top3.map((s) => `<li><strong>${s.signal}</strong>: ${s.note}</li>`).join("")
    : `<li class="muted">Run an analysis to generate priorities.</li>`;

  // Cover & footer dates
  const brand = result?.summary?.brand || "Brand";
  coverBrand.textContent = brand;
  const nowStr = new Date().toLocaleString();
  coverDate.textContent = nowStr;
  phDate.textContent = nowStr;
  repTimestamp.textContent = nowStr;

  // Chart
  renderChart(signals);
}

let chartInstance = null;
function renderChart(signals) {
  const byComp = {};
  signals.forEach((s) => {
    const k = s.competitor || "General";
    byComp[k] = (byComp[k] || 0) + 1;
  });
  const labels = Object.keys(byComp);
  const values = labels.map((k) => byComp[k]);
  const ctx = document.getElementById("chartByCompetitor");
  if (!ctx) return;
  if (chartInstance) chartInstance.destroy();
  chartInstance = new Chart(ctx, {
    type: "bar",
    data: {
      labels,
      datasets: [{ label: "Signals", data: values }]
    },
    options: {
      responsive: true,
      plugins: { legend: { display: false } },
      scales: {
        x: { ticks: { autoSkip: false } },
        y: { beginAtZero: true, precision: 0 }
      }
    }
  });
}

// Events
analyzeBtn?.addEventListener("click", async () => {
  const payload = buildPayload();
  show({ status: "sending", payload });
  try {
    const data = await postApi("/api/intelligence/analyze", payload);
    show(data);
    summarize(data);
  } catch (e) {
    showError(e);
  }
});

exportBtn?.addEventListener("click", async () => {
  const payload = buildPayload();
  show({ status: "exporting", payload });
  try {
    const blob = await postApi("/api/intelligence/export", payload, true);
    const url = URL.createObjectURL(blob);
    const a = document.createElement("a");
    a.href = url;
    a.download = "signal_scale_export.csv";
    document.body.appendChild(a);
    a.click();
    a.remove();
    URL.revokeObjectURL(url);
  } catch (e) {
    showError(e);
  }
});

printBtn?.addEventListener("click", () => {
  window.print();
});

clearBtn?.addEventListener("click", () => {
  brandNameEl.value = "";
  brandUrlEl.value = "";
  competitorsEl.value = "";
  show("—");
  kpiSignals.textContent = "0";
  kpiComps.textContent = "0";
  kpiStrength.textContent = "—";
  kpiGaps.textContent = "—";
  repStrengths.innerHTML = `<li class="muted">Run an analysis to populate.</li>`;
  repGaps.innerHTML = `<li class="muted">Run an analysis to populate.</li>`;
  repPriorities.innerHTML = `<li class="muted">Run an analysis to populate.</li>`;
  renderChart([]);
});

// Optional: preload with example values for faster testing
if (!brandNameEl.value && !competitorsEl.value) {
  brandNameEl.value = "Crooks & Castles";
  brandUrlEl.value = "crooksncastles.com";
  competitorsEl.value = "Stüssy | https://www.stussy.com\nHUF | https://hufworldwide.com";
}
