/* Phase 11 Dashboard — app.js */

// ── State ─────────────────────────────────────────────────────────────────────
let allPairs      = [];
let activePair    = null;
let sortByROI     = true;
let logSortKey    = 'entry_time';
let logSortAsc    = true;
let charts        = {};
let phaseTradeIdx = 0;

const RESULTS_PATH = '../data/results.json';

// ── Chart colours ──────────────────────────────────────────────────────────────
const C = {
  accent:  '#6c5ce7',
  accent2: '#a29bfe',
  green:   '#00b894',
  red:     '#e17055',
  yellow:  '#fdcb6e',
  blue:    '#74b9ff',
  orange:  '#fd79a8',
  muted:   '#8888aa',
  bg2:     '#13131e',
  border:  '#2a2a3e',
};

const CHART_DEFAULTS = {
  responsive: true,
  maintainAspectRatio: false,
  animation: false,
  plugins: {
    legend: {
      labels: { color: C.muted, font: { size: 11, family: "'SF Mono', monospace" }, boxWidth: 12 },
    },
    tooltip: {
      backgroundColor: '#1a1a28',
      borderColor: C.border,
      borderWidth: 1,
      titleColor: C.accent2,
      bodyColor: '#c0c0d8',
      padding: 10,
    },
  },
  scales: {
    x: {
      type: 'time',
      time: { tooltipFormat: 'yyyy-MM-dd HH:mm' },
      grid: { color: '#1e1e30' },
      ticks: { color: C.muted, maxTicksLimit: 8, font: { size: 10 } },
    },
    y: {
      grid: { color: '#1e1e30' },
      ticks: { color: C.muted, font: { size: 10 } },
    },
  },
};

// ── Bootstrap ─────────────────────────────────────────────────────────────────
fetch(RESULTS_PATH)
  .then(r => r.json())
  .then(data => {
    allPairs = data.pairs || [];

    // Header summary
    const s = data.summary || {};
    setEl('chipROI',    fmt(s.total_roi, '%', true));
    setEl('chipPairs',  s.pairs_active || allPairs.filter(p => p.total_trades > 0).length);
    setEl('chipTrades', s.total_trades || 0);
    setEl('chipPeriod', `${(data.date_from||'').slice(0,10)} → ${(data.date_to||'').slice(0,10)}`);
    colorEl('chipROI', s.total_roi);

    renderSidebar();
    if (allPairs.length) selectPair(allPairs.slice().sort((a,b) => b.roi - a.roi)[0]);
  })
  .catch(e => {
    document.querySelector('.detail').innerHTML =
      `<div class="no-data">Could not load results.json — run backtest first.<br><small>${e}</small></div>`;
  });

// ── Sidebar ───────────────────────────────────────────────────────────────────
function renderSidebar() {
  const el   = document.getElementById('pairList');
  const list = allPairs.slice();
  if (sortByROI) list.sort((a, b) => b.roi - a.roi);
  else           list.sort((a, b) => a.pair.localeCompare(b.pair));

  el.innerHTML = list.map(p => {
    const cls  = (activePair && activePair.pair === p.pair) ? 'pair-item active' : 'pair-item';
    const sign = p.roi >= 0 ? '+' : '';
    const col  = p.roi >= 0 ? C.green : C.red;
    return `<div class="${cls}" onclick="selectPair(allPairs.find(x=>x.pair==='${p.pair}'))">
      <div>
        <div class="pair-name">${p.pair}</div>
        <div class="pair-meta">${p.total_trades || 0} trades · ${p.win_rate || 0}% WR</div>
      </div>
      <div class="pair-roi" style="color:${col}">${sign}${p.roi || 0}%</div>
    </div>`;
  }).join('');
}

function toggleSort() {
  sortByROI = !sortByROI;
  document.getElementById('sortBtn').textContent = sortByROI ? '▼ ROI' : '▼ Name';
  renderSidebar();
}

// ── Pair selection ─────────────────────────────────────────────────────────────
function selectPair(p) {
  activePair    = p;
  phaseTradeIdx = 0;
  renderSidebar();
  renderStats(p);
  renderCharts(p);
  renderTradeLog();
  // Zoom phase chart to first trade by default
  if ((p.trades || []).length) _applyPhaseZoom(0);
}

// ── Stats ─────────────────────────────────────────────────────────────────────
function renderStats(p) {
  const roi = p.roi || 0;
  setEl('sROI',      `${roi >= 0 ? '+' : ''}${roi}%`);
  colorEl('sROI', roi);
  setEl('sGrossROI', `Gross ${p.gross_roi >= 0 ? '+' : ''}${p.gross_roi || 0}%`);

  const sh = p.sharpe || 0;
  setEl('sSharpe',  sh.toFixed(3));
  colorEl('sSharpe', sh);
  setEl('sMaxDD',   `Max DD ${p.max_drawdown || 0}%`);

  setEl('sWR',    `${p.win_rate || 0}%`);
  colorEl('sWR', (p.win_rate || 0) - 50);
  setEl('sWRsub', `${p.total_trades || 0} trades`);

  setEl('sTrades',  p.total_trades || 0);
  setEl('sHold',    `Avg hold ${p.avg_hold_hours || 0}h`);

  const corr = p.avg_correlation || 0;
  setEl('sCorr', corr.toFixed(3));
  const corrEl = document.getElementById('sCorr');
  corrEl.style.color = Math.abs(corr) > 0.7 ? C.yellow : C.green;

  const er = p.exit_reasons || {};
  const parts = Object.entries(er).map(([k,v]) => `${k}:${v}`);
  setEl('sExitReasons', parts.join(' · ') || '—');
}

// ── Charts ─────────────────────────────────────────────────────────────────────
function destroyCharts() {
  Object.values(charts).forEach(c => { try { c.destroy(); } catch(e) {} });
  charts = {};
}

function renderCharts(p) {
  destroyCharts();
  if (!p.ts || !p.ts.times || !p.ts.times.length) return;

  const ts     = p.ts;
  const times  = ts.times.map(t => new Date(t));
  const spread = ts.spread;
  const corr   = ts.corr;
  const priceA = ts.price_a;
  const priceB = ts.price_b;
  const equity = ts.equity;
  const trades = p.trades || [];

  // ── Spread chart ──────────────────────────────────────────────────────────
  const spreadCtx = document.getElementById('chartSpread').getContext('2d');
  const entryMarkers = trades.map(t => ({
    x: new Date(t.entry_time),
    y: t.entry_spread,
    side: t.trade_side,
    reason: t.exit_reason,
    pnl: t.net_pnl,
  }));

  charts.spread = new Chart(spreadCtx, {
    type: 'line',
    data: {
      labels: times,
      datasets: [
        {
          label: 'Rel. Spread S (A vs B)',
          data: spread,
          borderColor: C.accent,
          borderWidth: 1.5,
          pointRadius: 0,
          tension: 0.1,
          fill: {
            target: { value: 0 },
            above: `${C.blue}30`,
            below: `${C.orange}30`,
          },
        },
        {
          label: `Min Div +${(p.params||{}).min_divergence||0.14}`,
          data: times.map(() => (p.params||{}).min_divergence||0.14),
          borderColor: `${C.green}60`, borderWidth: 1, borderDash: [4, 4],
          pointRadius: 0,
        },
        {
          label: `−Min Div`,
          data: times.map(() => -((p.params||{}).min_divergence||0.14)),
          borderColor: `${C.red}60`, borderWidth: 1, borderDash: [4, 4],
          pointRadius: 0,
        },
        {
          label: 'Entries',
          data: entryMarkers,
          type: 'scatter',
          borderColor: C.yellow,
          backgroundColor: C.yellow,
          pointRadius: 5,
          pointHoverRadius: 7,
          showLine: false,
        },
      ],
    },
    options: {
      ...CHART_DEFAULTS,
      plugins: {
        ...CHART_DEFAULTS.plugins,
        legend: { ...CHART_DEFAULTS.plugins.legend, display: true },
        tooltip: {
          ...CHART_DEFAULTS.plugins.tooltip,
          callbacks: {
            label: ctx => {
              if (ctx.datasetIndex === 3) {
                const t = entryMarkers[ctx.dataIndex];
                return [
                  `Side: ${t.side === 1 ? 'Long A / Short B' : 'Short A / Long B'}`,
                  `Spread: ${(t.y*100).toFixed(1)}%`,
                  `Result: ${t.reason}  P&L: $${t.pnl.toFixed(0)}`,
                ];
              }
              return `${(ctx.parsed.y * 100).toFixed(2)}%`;
            },
          },
        },
      },
      scales: {
        ...CHART_DEFAULTS.scales,
        y: {
          ...CHART_DEFAULTS.scales.y,
          ticks: {
            color: C.muted, font: { size: 10 },
            callback: v => `${(v*100).toFixed(0)}%`,
          },
        },
      },
    },
  });

  // ── Price chart ────────────────────────────────────────────────────────────
  const priceCtx = document.getElementById('chartPrice').getContext('2d');
  const p0a = priceA.find(v => v != null) || 1;
  const p0b = priceB.find(v => v != null) || 1;
  const normA = priceA.map(v => v != null ? v / p0a * 100 : null);
  const normB = priceB.map(v => v != null ? v / p0b * 100 : null);

  const tradeAnnotationDS = trades.map(t => ({
    x: new Date(t.entry_time), y: null,
  }));

  charts.price = new Chart(priceCtx, {
    type: 'line',
    data: {
      labels: times,
      datasets: [
        {
          label: `${p.coin_a || 'A'} (normalised to 100)`,
          data: normA,
          borderColor: C.blue,
          borderWidth: 1.5,
          pointRadius: 0,
          tension: 0.1,
        },
        {
          label: `${p.coin_b || 'B'} (normalised to 100)`,
          data: normB,
          borderColor: C.orange,
          borderWidth: 1.5,
          pointRadius: 0,
          tension: 0.1,
        },
      ],
    },
    options: {
      ...CHART_DEFAULTS,
      plugins: {
        ...CHART_DEFAULTS.plugins,
        tooltip: {
          ...CHART_DEFAULTS.plugins.tooltip,
          callbacks: { label: ctx => `${ctx.dataset.label}: ${ctx.parsed.y.toFixed(1)}` },
        },
      },
    },
  });

  // ── Correlation chart ──────────────────────────────────────────────────────
  const corrCtx = document.getElementById('chartCorr').getContext('2d');
  charts.corr = new Chart(corrCtx, {
    type: 'line',
    data: {
      labels: times,
      datasets: [
        {
          label: 'Rolling Correlation (120h)',
          data: corr,
          borderColor: C.accent2,
          borderWidth: 1.5,
          pointRadius: 0,
          tension: 0.1,
          fill: { target: { value: 0 }, above: `${C.green}25`, below: `${C.red}25` },
        },
        {
          label: 'Zero line',
          data: times.map(() => 0),
          borderColor: `${C.muted}80`, borderWidth: 1, borderDash: [4, 4],
          pointRadius: 0,
        },
      ],
    },
    options: {
      ...CHART_DEFAULTS,
      plugins: {
        ...CHART_DEFAULTS.plugins,
        tooltip: {
          ...CHART_DEFAULTS.plugins.tooltip,
          callbacks: { label: ctx => ctx.parsed.y != null ? ctx.parsed.y.toFixed(3) : '' },
        },
      },
      scales: {
        ...CHART_DEFAULTS.scales,
        y: {
          ...CHART_DEFAULTS.scales.y,
          min: -1, max: 1,
          ticks: { color: C.muted, font: { size: 10 } },
        },
      },
    },
  });

  // ── Phase / Crossover chart ───────────────────────────────────────────────
  // Shows coin A and coin B 5-day rolling returns over time as two crossing lines.
  // The moment the two lines cross = zero-cross entry signal.
  const phaseCtx = document.getElementById('chartPhase').getContext('2d');
  const retA = ts.ret_a || [];
  const retB = ts.ret_b || [];

  // Find closest ts index for each trade's entry / exit time (used only for Y-value lookup)
  const tsMs = times.map(t => t.getTime());
  function closestTsIdx(isoStr) {
    const ms = new Date(isoStr).getTime();
    let best = 0, bestDiff = Infinity;
    for (let i = 0; i < tsMs.length; i++) {
      const d = Math.abs(tsMs[i] - ms);
      if (d < bestDiff) { bestDiff = d; best = i; }
    }
    return best;
  }

  // Entry scatter: placed at Y=0 (the zero-crossing level) with EXACT entry timestamp
  const phaseEntryLongA  = []; // Long A / Short B — triangle up, blue
  const phaseEntryShortA = []; // Short A / Long B — triangle down, orange
  // Exit scatter: at exact exit timestamp
  const phaseExitProfit  = [];
  const phaseExitStop    = [];

  trades.forEach(t => {
    const eRa = t.entry_ret_a;
    const eRb = t.entry_ret_b;
    const xRa = t.exit_ret_a;
    // Entry at exact timestamp, Y = midpoint of ret_a and ret_b at entry bar.
    // When the spread crosses zero, ret_a == ret_b, so their midpoint is the visual crossing level.
    const entryY = (eRa != null && eRb != null) ? (eRa + eRb) / 2 : 0;
    const entryPt = {
      x: new Date(t.entry_time),
      y: entryY,
      pnl: t.net_pnl, reason: t.exit_reason, ra: eRa, rb: eRb, dir: t.direction,
    };
    // Exit at exact timestamp, Y = ret_a at exit bar (marker sits on coin A line)
    const exitPt = {
      x: new Date(t.exit_time),
      y: xRa != null ? xRa : entryY,
      pnl: t.net_pnl, reason: t.exit_reason,
    };
    if (t.trade_side === 1)  phaseEntryLongA.push(entryPt);
    else                     phaseEntryShortA.push(entryPt);
    if (t.net_pnl >= 0) phaseExitProfit.push(exitPt);
    else                phaseExitStop.push(exitPt);
  });

  // Background plugin — amber shading for prior divergence build-up, then green/red for trade period
  const tradeShadePlugin = {
    id: 'tradeShade',
    beforeDraw(chart) {
      const { ctx: c2, scales: { x, y } } = chart;
      // prior_div_window is in bars; convert to ms using bars_per_hour from params
      const params = activePair.params || {};
      const pdwH = (params.prior_div_window || 96) / (params.bars_per_hour || 1);
      const divWindowMs = pdwH * 3600 * 1000;
      // Amber: divergence build-up window before each entry
      trades.forEach(t => {
        const entryMs = new Date(t.entry_time).getTime();
        const x1 = x.getPixelForValue(entryMs - divWindowMs);
        const x2 = x.getPixelForValue(entryMs);
        c2.fillStyle = '#fdcb6e12';
        c2.fillRect(x1, y.top, x2 - x1, y.bottom - y.top);
      });
      // Green/red: active trade period (drawn on top of amber)
      trades.forEach(t => {
        const x1 = x.getPixelForValue(new Date(t.entry_time));
        const x2 = x.getPixelForValue(new Date(t.exit_time));
        c2.fillStyle = t.net_pnl >= 0 ? '#00b89422' : '#e1705522';
        c2.fillRect(x1, y.top, x2 - x1, y.bottom - y.top);
      });
    },
  };

  charts.phase = new Chart(phaseCtx, {
    type: 'line',
    plugins: [tradeShadePlugin],
    data: {
      labels: times,
      datasets: [
        {
          label: `${activePair.coin_a}  5-day return`,
          data: retA,
          borderColor: C.blue,
          borderWidth: 2,
          pointRadius: 0,
          tension: 0.2,
          fill: false,
        },
        {
          label: `${activePair.coin_b}  5-day return`,
          data: retB,
          borderColor: C.orange,
          borderWidth: 2,
          pointRadius: 0,
          tension: 0.2,
          fill: false,
        },
        {
          label: 'Zero (equal performance)',
          data: times.map(() => 0),
          borderColor: `${C.muted}50`,
          borderWidth: 1,
          borderDash: [4, 4],
          pointRadius: 0,
          fill: false,
        },
        {
          // Long A / Short B entries — blue triangle up on coin A line
          label: `Entry: Long ${activePair.coin_a} / Short ${activePair.coin_b}`,
          data: phaseEntryLongA,
          type: 'scatter',
          pointStyle: 'triangle',
          pointRadius: 8,
          backgroundColor: C.blue,
          borderColor: '#fff',
          borderWidth: 1.5,
          showLine: false,
        },
        {
          // Short A / Long B entries — orange inverted triangle on coin A line
          label: `Entry: Short ${activePair.coin_a} / Long ${activePair.coin_b}`,
          data: phaseEntryShortA,
          type: 'scatter',
          pointStyle: 'triangle',
          rotation: 180,
          pointRadius: 8,
          backgroundColor: C.orange,
          borderColor: '#fff',
          borderWidth: 1.5,
          showLine: false,
        },
        {
          label: 'Exit: Profit',
          data: phaseExitProfit,
          type: 'scatter',
          pointStyle: 'circle',
          pointRadius: 6,
          backgroundColor: C.green,
          borderColor: '#fff',
          borderWidth: 1.5,
          showLine: false,
        },
        {
          label: 'Exit: Stop / Time',
          data: phaseExitStop,
          type: 'scatter',
          pointStyle: 'crossRot',
          pointRadius: 6,
          backgroundColor: C.red,
          borderColor: C.red,
          borderWidth: 2,
          showLine: false,
        },
      ],
    },
    options: {
      responsive: true,
      maintainAspectRatio: false,
      animation: false,
      plugins: {
        legend: {
          labels: { color: C.muted, font: { size: 11, family: "'SF Mono', monospace" }, boxWidth: 12 },
        },
        tooltip: {
          backgroundColor: '#1a1a28',
          borderColor: C.border,
          borderWidth: 1,
          titleColor: C.accent2,
          bodyColor: '#c0c0d8',
          padding: 10,
          callbacks: {
            title: items => fmtTime(items[0].parsed.x ? new Date(items[0].parsed.x).toISOString() : ''),
            label: ctx => {
              const v = ctx.parsed.y;
              if (ctx.datasetIndex <= 2) {
                return `${ctx.dataset.label}: ${v >= 0 ? '+' : ''}${(v * 100).toFixed(1)}%`;
              }
              const d = ctx.raw;
              return [
                `P&L: ${d.pnl >= 0 ? '+' : ''}$${d.pnl.toFixed(0)}`,
                `Exit: ${d.reason}`,
                d.ra != null ? `${activePair.coin_a}: ${(d.ra*100).toFixed(1)}%  ${activePair.coin_b}: ${(d.rb*100).toFixed(1)}%` : '',
              ].filter(Boolean);
            },
          },
        },
      },
      scales: {
        x: {
          type: 'time',
          time: { tooltipFormat: 'yyyy-MM-dd HH:mm' },
          grid: { color: '#1e1e30' },
          ticks: { color: C.muted, maxTicksLimit: 8, font: { size: 10 } },
        },
        y: {
          grid: { color: '#1e1e30' },
          ticks: {
            color: C.muted, font: { size: 10 },
            callback: v => `${(v * 100).toFixed(0)}%`,
          },
        },
      },
    },
  });

  // Clear the sidebar legend (not needed for this chart style)
  const legendEl = document.getElementById('phaseLegend');
  if (legendEl) legendEl.innerHTML = `
    <div class="phase-info">
      <div class="phase-info-row" style="color:var(--muted);font-size:10px;line-height:1.6">
        When the two lines <b style="color:var(--text)">cross</b>, the spread S = 0.<br><br>
        <span style="color:var(--blue)">▲ Blue triangle</span> = Long ${activePair.coin_a} / Short ${activePair.coin_b}<br>
        <span style="color:var(--orange)">▽ Orange triangle</span> = Short ${activePair.coin_a} / Long ${activePair.coin_b}<br>
        <i style="font-size:9px">Markers placed at Y=0 (the exact crossing point)</i><br><br>
        <span style="color:var(--green)">● Green circle</span> = Profitable exit<br>
        <span style="color:var(--red)">✕ Red cross</span> = Stop / time exit<br><br>
        <span style="background:#fdcb6e;opacity:0.25;padding:1px 6px">  </span> Amber = prior divergence build-up (60h)<br>
        <span style="background:var(--green);opacity:0.3;padding:1px 6px">  </span> Green = winning trade<br>
        <span style="background:var(--red);opacity:0.3;padding:1px 6px">  </span> Red = losing trade
      </div>
    </div>`;

  // ── Equity chart ──────────────────────────────────────────────────────────
  const eqCtx = document.getElementById('chartEquity').getContext('2d');
  charts.equity = new Chart(eqCtx, {
    type: 'line',
    data: {
      labels: times,
      datasets: [
        {
          label: 'Cumulative Net P&L ($)',
          data: equity,
          borderColor: (ctx) => {
            const val = ctx.parsed?.y ?? 0;
            return val >= 0 ? C.green : C.red;
          },
          borderWidth: 2,
          pointRadius: 0,
          fill: { target: { value: 0 }, above: `${C.green}25`, below: `${C.red}25` },
          segment: {
            borderColor: ctx => ctx.p0.parsed.y >= 0 && ctx.p1.parsed.y >= 0
              ? C.green : C.red,
          },
        },
      ],
    },
    options: {
      ...CHART_DEFAULTS,
      plugins: {
        ...CHART_DEFAULTS.plugins,
        tooltip: {
          ...CHART_DEFAULTS.plugins.tooltip,
          callbacks: { label: ctx => `$${ctx.parsed.y.toFixed(0)}` },
        },
      },
      scales: {
        ...CHART_DEFAULTS.scales,
        y: {
          ...CHART_DEFAULTS.scales.y,
          ticks: { color: C.muted, font: { size: 10 }, callback: v => `$${v}` },
        },
      },
    },
  });
}

// ── Trade log ──────────────────────────────────────────────────────────────────
function renderTradeLog() {
  if (!activePair) return;
  let trades = (activePair.trades || []).slice();

  const filterReason = document.getElementById('tlFilter').value;
  const filterDir    = document.getElementById('tlDir').value;
  if (filterReason) trades = trades.filter(t => t.exit_reason === filterReason);
  if (filterDir)    trades = trades.filter(t => t.direction === filterDir);

  trades.sort((a, b) => {
    let va = a[logSortKey], vb = b[logSortKey];
    if (typeof va === 'string') va = va.toLowerCase();
    if (typeof vb === 'string') vb = vb.toLowerCase();
    if (va < vb) return logSortAsc ? -1 : 1;
    if (va > vb) return logSortAsc ?  1 : -1;
    return 0;
  });

  document.getElementById('tlCount').textContent = `${trades.length} trade${trades.length !== 1 ? 's' : ''}`;

  const body = document.getElementById('tradeBody');
  body.innerHTML = trades.map((t, idx) => {
    const isLongA  = t.direction === 'long_a_short_b';
    const sideA    = isLongA ? 'LONG'  : 'SHORT';
    const sideB    = isLongA ? 'SHORT' : 'LONG';
    const dir      = isLongA
      ? `↑${activePair.coin_a} ↓${activePair.coin_b}`
      : `↓${activePair.coin_a} ↑${activePair.coin_b}`;
    const dirCls   = isLongA ? 'dir-long_a' : 'dir-long_b';
    const rowCls   = idx % 2 === 0 ? 'trade-even' : 'trade-odd';
    const netCls   = t.net_pnl  >= 0 ? 'pos' : 'neg';
    const netSign  = t.net_pnl  >= 0 ? '+' : '';
    const pnlAcls  = t.pnl_a    >= 0 ? 'pos' : 'neg';
    const pnlAsign = t.pnl_a    >= 0 ? '+' : '';
    const pnlBcls  = t.pnl_b    >= 0 ? 'pos' : 'neg';
    const pnlBsign = t.pnl_b    >= 0 ? '+' : '';
    return `
    <tr class="trade-row-main ${rowCls}">
      <td rowspan="2">${idx + 1}. ${fmtTime(t.entry_time)}</td>
      <td rowspan="2">${fmtTime(t.exit_time)}</td>
      <td rowspan="2">${(t.hold_hours ?? t.hold_bars)}h</td>
      <td rowspan="2" class="${dirCls}">${dir}</td>
      <td class="coin-cell">${activePair.coin_a}</td>
      <td class="side-${sideA.toLowerCase()}">${sideA}</td>
      <td class="price-cell">${fmtPrice(t.entry_pa)} → ${fmtPrice(t.exit_pa)}</td>
      <td class="${pnlAcls}">${pnlAsign}$${(t.pnl_a||0).toFixed(0)}</td>
      <td rowspan="2">${(t.prior_peak*100).toFixed(1)}%</td>
      <td rowspan="2" class="${t.s_trade_exit >= 0 ? 'pos' : 'neg'}">${(t.s_trade_exit*100).toFixed(1)}%</td>
      <td rowspan="2" class="${netCls}">${netSign}$${t.net_pnl.toFixed(0)}</td>
      <td rowspan="2" class="reason-${t.exit_reason}">${t.exit_reason}</td>
    </tr>
    <tr class="trade-row-leg ${rowCls}">
      <td class="coin-cell">${activePair.coin_b}</td>
      <td class="side-${sideB.toLowerCase()}">${sideB}</td>
      <td class="price-cell">${fmtPrice(t.entry_pb)} → ${fmtPrice(t.exit_pb)}</td>
      <td class="${pnlBcls}">${pnlBsign}$${(t.pnl_b||0).toFixed(0)}</td>
    </tr>`;
  }).join('');
}

function sortLog(key) {
  if (logSortKey === key) logSortAsc = !logSortAsc;
  else { logSortKey = key; logSortAsc = key !== 'net_pnl'; }
  renderTradeLog();
}

// ── Tab switching ──────────────────────────────────────────────────────────────
function showTab(name) {
  document.querySelectorAll('.tab').forEach((t, i) => {
    const names = ['spread', 'price', 'corr', 'equity', 'phase', 'log', 'rulebook', 'workflow'];
    t.classList.toggle('active', names[i] === name);
  });
  if (name === 'rulebook') { renderRulebook(); }
  document.querySelectorAll('.tab-pane').forEach(p => {
    p.classList.toggle('active', p.id === `pane-${name}`);
  });
  // Resize charts when tab becomes visible
  setTimeout(() => {
    Object.values(charts).forEach(c => { try { c.resize(); } catch(e) {} });
  }, 50);
}

// ── Phase navigation ──────────────────────────────────────────────────────
function phaseNav(delta) {
  if (!activePair || !charts.phase) return;
  const trades = activePair.trades || [];
  if (!trades.length) return;
  phaseTradeIdx = Math.max(0, Math.min(trades.length - 1, phaseTradeIdx + delta));
  _applyPhaseZoom(phaseTradeIdx);
}

function phaseNavOverview() {
  if (!charts.phase) return;
  charts.phase.options.scales.x.min = undefined;
  charts.phase.options.scales.x.max = undefined;
  charts.phase.update();
  document.getElementById('phaseTradeLabel').textContent =
    `All ${(activePair.trades || []).length} trades — full period`;
}

function _applyPhaseZoom(idx) {
  if (!charts.phase) return;
  const trades = activePair.trades || [];
  if (!trades.length) return;
  phaseTradeIdx = idx;
  const t = trades[idx];
  const DAY = 24 * 3600 * 1000;
  charts.phase.options.scales.x.min = new Date(t.entry_time).getTime() - 5 * DAY;
  charts.phase.options.scales.x.max = new Date(t.exit_time).getTime()  + 3 * DAY;
  charts.phase.update();

  const dir = t.direction === 'long_a_short_b'
    ? `↑${activePair.coin_a} ↓${activePair.coin_b}`
    : `↓${activePair.coin_a} ↑${activePair.coin_b}`;
  const pnlStr  = `${t.net_pnl >= 0 ? '+' : ''}$${t.net_pnl.toFixed(0)}`;
  const holdStr = `${t.hold_hours ?? t.hold_bars}h`;
  document.getElementById('phaseTradeLabel').textContent =
    `Trade ${idx + 1} / ${trades.length}  ·  ${dir}  ·  ${fmtTime(t.entry_time)} → ${fmtTime(t.exit_time)}  ·  ${holdStr}  ·  ${pnlStr}  [${t.exit_reason}]`;
}

// ── Helpers ───────────────────────────────────────────────────────────────────
function setEl(id, val) {
  const el = document.getElementById(id);
  if (el) el.textContent = val;
}

function colorEl(id, val) {
  const el = document.getElementById(id);
  if (!el) return;
  const v = typeof val === 'string' ? parseFloat(val) : val;
  el.className = el.className.replace(/ ?(positive|negative|neutral)/g, '');
  if (v > 0)       el.classList.add('positive');
  else if (v < 0)  el.classList.add('negative');
  else             el.classList.add('neutral');
}

function fmt(val, suffix='', sign=false) {
  const v = parseFloat(val) || 0;
  return `${sign && v > 0 ? '+' : ''}${v}${suffix}`;
}

function fmtTime(s) {
  if (!s) return '—';
  return s.replace('T', ' ').slice(0, 16);
}

function fmtPrice(v) {
  if (v == null || isNaN(v)) return '—';
  if (v >= 10000) return `$${(v/1000).toFixed(1)}k`;
  if (v >= 1000)  return `$${(v/1000).toFixed(2)}k`;
  if (v >= 10)    return `$${v.toFixed(2)}`;
  if (v >= 1)     return `$${v.toFixed(3)}`;
  return `$${v.toFixed(4)}`;
}

// ── Rulebook ──────────────────────────────────────────────────────────────────

const RULEBOOK_PATH = '../data/rulebook.json';

const TIER_META = {
  T0: { label: 'Tier 0 · Prerequisites', color: '#a29bfe', dot: '#6c5ce7' },
  T1: { label: 'Tier 1 · Fatal Gates',   color: '#e17055', dot: '#e17055' },
  T2: { label: 'Tier 2 · Quality Gates', color: '#fdcb6e', dot: '#fdcb6e' },
  T3: { label: 'Tier 3 · Robustness',    color: '#74b9ff', dot: '#74b9ff' },
  CR: { label: 'Crypto Pack',             color: '#00b894', dot: '#00b894' },
};

function renderRulebook() {
  const wrap = document.getElementById('rulebookWrap');

  fetch(RULEBOOK_PATH)
    .then(r => r.json())
    .then(rb => {
      const verdictClass = {
        'PASS': 'pass', 'PASS WITH WARNINGS': 'warn',
        'FAIL': 'fail', 'REJECTED': 'reject',
      }[rb.verdict] || 'fail';

      const s = rb.summary || {};
      let html = `
        <div class="rb-header">
          <div class="rb-verdict ${verdictClass}">${rb.verdict}</div>
          <div class="rb-score">${rb.score}<span>/100</span></div>
          <div class="rb-meta">${rb.years?.toFixed(1)}y · ${rb.total_trades} trades · $${(rb.total_capital||0).toLocaleString()}</div>
          <div class="rb-counters">
            <div class="rb-counter"><span class="cnt-val cnt-pass">${s.pass||0}</span><span class="cnt-lbl">Pass</span></div>
            <div class="rb-counter"><span class="cnt-val cnt-fail">${s.fail||0}</span><span class="cnt-lbl">Fail</span></div>
            <div class="rb-counter"><span class="cnt-val cnt-warn">${s.warn||0}</span><span class="cnt-lbl">Warn</span></div>
            <div class="rb-counter"><span class="cnt-val cnt-skip">${s.skip||0}</span><span class="cnt-lbl">Skip</span></div>
          </div>
          ${!rb.run_full ? '<div class="rb-meta" style="color:var(--yellow)">⚡ Run with --full for walk-forward & param sensitivity</div>' : ''}
        </div>`;

      const tiers = ['T0', 'T1', 'T2', 'T3', 'CR'];
      for (const tier of tiers) {
        const tierRules = (rb.rules || []).filter(r => r.tier === tier);
        if (!tierRules.length) continue;
        const meta = TIER_META[tier];
        const count = tierRules.length;
        const passCount = tierRules.filter(r => r.status === 'PASS').length;

        html += `<div class="rb-tier">
          <div class="rb-tier-header">
            <div class="tier-dot" style="background:${meta.dot}"></div>
            <span style="color:${meta.color}">${meta.label}</span>
            <span class="tier-count">${passCount}/${count}</span>
          </div>
          <div class="rb-grid">`;

        for (const r of tierRules) {
          const sc = r.status.toLowerCase();
          const thClass = r.status === 'PASS' ? 'pass' : r.status === 'FAIL' ? 'fail' : r.status === 'WARN' ? 'warn' : 'skip';
          html += `
            <div class="rb-card s-${sc}">
              <div class="rb-card-top">
                <span class="rb-rule-id">${r.id}</span>
                <span class="rb-rule-name">${r.name}</span>
                <span class="rb-badge ${r.severity}">${r.severity}</span>
              </div>
              <div class="rb-desc">${r.desc}</div>
              <div class="rb-card-bottom">
                <span class="rb-metric-name">${r.metric_name}</span>
                <div class="rb-value-row">
                  <span class="rb-value-str">${r.value_str}</span>
                  <span class="rb-threshold ${thClass}">${r.status === 'SKIP' ? 'NOT RUN' : r.threshold_str}</span>
                  <span class="rb-status ${r.status}">${r.status}</span>
                </div>
              </div>
            </div>`;
        }
        html += '</div></div>';
      }

      wrap.innerHTML = html;
    })
    .catch(() => {
      wrap.innerHTML = `<div class="no-data">rulebook.json not found — run <code>python phase_11/rulebook.py</code> first</div>`;
    });
}

