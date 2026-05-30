let priceChart = null;
let chartData  = null;
let activeTicker = null;

document.addEventListener("DOMContentLoaded", () => {
  loadTrending();

  document.getElementById("searchBtn").addEventListener("click", doSearch);
  document.getElementById("searchInput").addEventListener("keydown", e => {
    if (e.key === "Enter") doSearch();
  });

  document.getElementById("timeframeButtons").addEventListener("click", e => {
    const btn = e.target.closest("[data-tf]");
    if (!btn || !chartData) return;
    document.querySelectorAll("#timeframeButtons .btn").forEach(b => b.classList.remove("active"));
    btn.classList.add("active");
    drawChart(chartData[btn.dataset.tf], activeTicker);
  });
});

function doSearch() {
  const raw = document.getElementById("searchInput").value.trim();
  if (!raw) return;
  loadStock(raw.toUpperCase());
}

// ── Trending ─────────────────────────────────────────────────────────────────
async function loadTrending() {
  try {
    const data = await apiFetch("/api/trending");
    document.getElementById("trendingList").innerHTML = data.map(s => `
      <div class="trending-item" onclick="loadStock('${s.ticker}')">
        <div>
          <div class="trending-ticker">${s.ticker}</div>
          <div class="trending-name">${s.name}</div>
        </div>
        <div class="text-end">
          <div class="small fw-bold">$${s.price}</div>
          <div class="small ${s.change_pct >= 0 ? 'price-up' : 'price-down'}">
            ${s.change_pct >= 0 ? '+' : ''}${s.change_pct}%
          </div>
        </div>
      </div>
    `).join("");
  } catch (_) {
    document.getElementById("trendingList").innerHTML =
      '<p class="text-muted small text-center py-2">Failed to load</p>';
  }
}

// ── Stock data ────────────────────────────────────────────────────────────────
async function loadStock(ticker) {
  activeTicker = ticker;
  document.getElementById("searchInput").value = ticker;
  showPanel("none");

  try {
    const [stock, sentiment] = await Promise.all([
      apiFetch(`/api/stock/${ticker}`),
      apiFetch(`/api/sentiment/${ticker}`),
    ]);

    if (stock.error) { showPanel("error", stock.error); return; }

    renderStock(stock);
    renderSentiment(sentiment);
    showPanel("stock");
  } catch (e) {
    showPanel("error", "Network error — is the Flask server running?");
  }
}

function showPanel(which, msg = "") {
  document.getElementById("welcomeState").classList.add("d-none");
  document.getElementById("stockPanel").classList.add("d-none");
  document.getElementById("errorState").classList.add("d-none");
  if (which === "stock") document.getElementById("stockPanel").classList.remove("d-none");
  else if (which === "error") {
    document.getElementById("errorMessage").textContent = msg;
    document.getElementById("errorState").classList.remove("d-none");
  } else if (which === "welcome") {
    document.getElementById("welcomeState").classList.remove("d-none");
  }
}

// ── Render stock header + metrics ─────────────────────────────────────────────
function renderStock(d) {
  document.getElementById("stockName").textContent    = d.name;
  document.getElementById("stockTicker").textContent  = d.ticker;
  document.getElementById("stockSector").textContent  = d.sector || "N/A";

  document.getElementById("stockPrice").textContent =
    "$" + d.price.toLocaleString("en-US", { minimumFractionDigits: 2 });

  const up = d.change >= 0;
  const chEl = document.getElementById("stockChange");
  chEl.className = `fs-5 ${up ? 'price-up' : 'price-down'}`;
  chEl.innerHTML =
    `<i class="bi bi-caret-${up ? 'up' : 'down'}-fill"></i> ` +
    `${up ? '+' : ''}$${d.change} (${up ? '+' : ''}${d.change_pct}%)`;

  const metrics = [
    { label: "Volume",    value: fmtVol(d.volume) },
    { label: "Avg Vol",   value: fmtVol(d.avg_volume) },
    { label: "Mkt Cap",   value: fmtCap(d.market_cap) },
    { label: "P/E",       value: d.pe_ratio ? d.pe_ratio.toFixed(1) : "N/A" },
    { label: "52W High",  value: d.week_52_high ? `$${d.week_52_high}` : "N/A" },
    { label: "52W Low",   value: d.week_52_low  ? `$${d.week_52_low}`  : "N/A" },
  ];
  document.getElementById("stockMetrics").innerHTML = metrics.map(m => `
    <div class="col-6 col-md-4 col-xl-2">
      <div class="metric-card">
        <div class="metric-label">${m.label}</div>
        <div class="metric-value">${m.value}</div>
      </div>
    </div>
  `).join("");

  chartData = d.chart_data;
  // Default to 1M
  document.querySelectorAll("#timeframeButtons .btn").forEach(b => b.classList.remove("active"));
  document.querySelector('[data-tf="1m"]').classList.add("active");
  drawChart(d.chart_data["1m"], d.ticker);
}

// ── Chart ─────────────────────────────────────────────────────────────────────
function drawChart(data, ticker) {
  if (!data || !data.prices.length) return;

  const ctx = document.getElementById("priceChart").getContext("2d");
  if (priceChart) priceChart.destroy();

  const prices = data.prices;
  const isUp   = prices[prices.length - 1] >= prices[0];
  const color  = isUp ? "#3fb950" : "#f85149";
  const min    = Math.min(...prices);
  const max    = Math.max(...prices);

  priceChart = new Chart(ctx, {
    type: "line",
    data: {
      labels: data.labels,
      datasets: [{
        label: ticker,
        data: prices,
        borderColor: color,
        borderWidth: 2,
        pointRadius: 0,
        pointHoverRadius: 4,
        fill: true,
        backgroundColor: ctx2 => {
          const g = ctx2.chart.ctx.createLinearGradient(0, 0, 0, ctx2.chart.height);
          g.addColorStop(0, color + "28");
          g.addColorStop(1, color + "00");
          return g;
        },
        tension: 0.3,
      }],
    },
    options: {
      responsive: true,
      interaction: { mode: "index", intersect: false },
      plugins: {
        legend: { display: false },
        tooltip: {
          backgroundColor: "#1c2128",
          borderColor: "#30363d",
          borderWidth: 1,
          titleColor: "#8b949e",
          bodyColor: "#e6edf3",
          callbacks: { label: c => ` $${c.parsed.y.toFixed(2)}` },
        },
      },
      scales: {
        x: {
          ticks: { color: "#8b949e", maxTicksLimit: 7, font: { size: 11 } },
          grid:  { color: "#21262d" },
        },
        y: {
          ticks: { color: "#8b949e", font: { size: 11 }, callback: v => `$${v}` },
          grid:  { color: "#21262d" },
          suggestedMin: min * 0.99,
          suggestedMax: max * 1.01,
        },
      },
    },
  });
}

// ── Sentiment + tweets ────────────────────────────────────────────────────────
function renderSentiment(d) {
  if (d.error) return;

  const { bullish, bearish, neutral } = d.sentiment_breakdown;
  const total    = bullish + bearish + neutral;
  const bullPct  = Math.round(bullish / total * 100);
  const bearPct  = Math.round(bearish / total * 100);
  const neutPct  = 100 - bullPct - bearPct;
  const cls      = { Bullish: "sentiment-bullish", Bearish: "sentiment-bearish", Neutral: "sentiment-neutral" };

  document.getElementById("sentimentPanel").innerHTML = `
    <div class="sentiment-gauge">
      <div class="sentiment-badge ${cls[d.overall_sentiment]}">${d.overall_sentiment}</div>
      <div class="w-100 px-1">
        <div class="d-flex justify-content-between mb-1" style="font-size:.72rem;color:var(--muted)">
          <span style="color:var(--green)">&#9650; ${bullPct}%</span>
          <span>${neutPct}% neutral</span>
          <span style="color:var(--red)">&#9660; ${bearPct}%</span>
        </div>
        <div class="sentiment-bar">
          <div class="bar-bull"    style="width:${bullPct}%"></div>
          <div class="bar-neutral" style="width:${neutPct}%"></div>
          <div class="bar-bear"    style="width:${bearPct}%"></div>
        </div>
      </div>
      <div class="text-muted" style="font-size:.75rem">Score: ${d.avg_score} &middot; ${total} posts analyzed</div>
    </div>
  `;

  document.getElementById("tweetsFeed").innerHTML = d.tweets.map(t => {
    const dot = t.sentiment === "bullish" ? "#3fb950" : t.sentiment === "bearish" ? "#f85149" : "#8b949e";
    return `
      <div class="tweet-card">
        <div class="d-flex justify-content-between">
          <span class="tweet-handle">${t.handle}</span>
          <span class="tweet-meta">${t.time_ago}</span>
        </div>
        <div class="tweet-meta mb-1">${t.followers} followers${t.verified ? ' &#10003;' : ''}</div>
        <p class="tweet-text mb-1">${t.text}</p>
        <div class="d-flex gap-3 tweet-meta align-items-center">
          <span><span class="tweet-dot" style="background:${dot}"></span>${t.sentiment}</span>
          <span><i class="bi bi-heart"></i> ${t.likes.toLocaleString()}</span>
          <span><i class="bi bi-repeat"></i> ${t.retweets.toLocaleString()}</span>
        </div>
      </div>
    `;
  }).join("");
}

// ── Helpers ───────────────────────────────────────────────────────────────────
async function apiFetch(url) {
  const res = await fetch(url);
  if (!res.ok) throw new Error(`HTTP ${res.status}`);
  return res.json();
}

function fmtVol(n) {
  if (!n) return "N/A";
  if (n >= 1e9) return (n / 1e9).toFixed(2) + "B";
  if (n >= 1e6) return (n / 1e6).toFixed(2) + "M";
  if (n >= 1e3) return (n / 1e3).toFixed(0)  + "K";
  return String(n);
}

function fmtCap(n) {
  if (!n) return "N/A";
  if (n >= 1e12) return "$" + (n / 1e12).toFixed(2) + "T";
  if (n >= 1e9)  return "$" + (n / 1e9) .toFixed(2) + "B";
  if (n >= 1e6)  return "$" + (n / 1e6) .toFixed(2) + "M";
  return "$" + n.toLocaleString();
}
