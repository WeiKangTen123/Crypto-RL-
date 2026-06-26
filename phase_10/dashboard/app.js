'use strict';
const API = location.protocol === 'file:' ? 'http://127.0.0.1:5001' : '';

let allData    = null;
let pairs      = [];
let sortKey    = 'sharpe';
let sortAsc    = false;
let activePair = null;
let allTrades  = [];
let pollTimer  = null;
let lastLogLen = 0;

// ── Load Results ──────────────────────────────────────────────────────────────
async function loadResults() {
  try {
    const modeSelect = document.getElementById('engine-mode');
    const mode = modeSelect ? modeSelect.value : 'advanced';
    const r = await fetch(`${API}/api/phase_10/results?mode=${mode}`);
    if (!r.ok) {
      document.getElementById('run-meta').textContent = 'No results yet — click Run All Pairs';
      clearUI();
      return;
    }
    document.getElementById('run-meta').textContent = '';
    allData = await r.json();
    pairs   = (allData.pairs || []).filter(p => !p.error);
    renderSummary();
    populatePairSelect();
    renderRankTable();
    const best = [...pairs].sort((a, b) => (b.sharpe || 0) - (a.sharpe || 0))[0];
    if (best) { document.getElementById('pair-select').value = best.pair; onPairChange(); }
    else { clearUI(); }
  } catch (e) {
    document.getElementById('run-meta').textContent = 'Could not load results.';
    clearUI();
  }
}

function clearUI() {
  allData = null;
  pairs = [];
  set('s-best-pair', '—');
  set('s-best-sharpe', '—');
  set('s-coint', '—');
  set('s-total-trades', '—');
  set('s-period', '—');
  const pairSelect = document.getElementById('pair-select');
  if (pairSelect) pairSelect.innerHTML = '<option value="">-- Select a Pair --</option>';
  const tbody = document.getElementById('rank-tbody');
  if (tbody) tbody.innerHTML = '';
  ['chart-dance', 'chart-zscore', 'chart-equity', 'chart-mfe', 'chart-mae', 'chart-monthly', 'chart-yearly']
    .forEach(cid => { const el = document.getElementById(cid); if (el) el.innerHTML = ''; });
  const detailStats = document.getElementById('detail-stats');
  if (detailStats) detailStats.innerHTML = '';
  const tcaStats = document.getElementById('tca-stats');
  if (tcaStats) tcaStats.innerHTML = '';
}

// ── Summary bar ───────────────────────────────────────────────────────────────
function renderSummary() {
  if (!allData) return;
  const best        = [...pairs].sort((a, b) => (b.sharpe || 0) - (a.sharpe || 0))[0];
  const coint       = pairs.filter(p => p.cointegrated).length;
  const totalTrades = pairs.reduce((s, p) => s + (p.total_trades || 0), 0);
  set('s-best-pair',    best ? best.pair : '—');
  set('s-best-sharpe',  best ? best.sharpe : '—', best && best.sharpe >= 0 ? 'pos' : 'neg');
  set('s-coint',        `${coint}/${pairs.length}`);
  set('s-total-trades', totalTrades.toLocaleString());
  const tfLabel = allData.signal_timeframe && allData.execution_timeframe
    ? ` · ${allData.signal_timeframe}->${allData.execution_timeframe}`
    : '';
  set('s-period',       `${allData.date_from} → ${allData.date_to}${tfLabel}`);
}

// ── Pair selector ─────────────────────────────────────────────────────────────
function populatePairSelect() {
  const sel    = document.getElementById('pair-select');
  const sorted = [...pairs].sort((a, b) => (b.sharpe || 0) - (a.sharpe || 0));
  sorted.forEach(p => {
    const opt       = document.createElement('option');
    opt.value       = p.pair;
    opt.textContent = `${p.pair}  (Sharpe: ${p.sharpe ?? '—'})`;
    sel.appendChild(opt);
  });
}

function onPairChange() {
  const val = document.getElementById('pair-select').value;
  if (!val) return;
  const p = pairs.find(x => x.pair === val);
  if (p) renderPairDetail(p);
}

// ── Pair detail ──────────────────────────────────────────────────────────────
function renderPairDetail(p) {
  activePair = p;
  document.getElementById('pair-detail').style.display = 'block';

  const cointBadge = p.cointegrated
    ? '<span class="badge badge-green" style="margin-left:8px">COINTEGRATED</span>'
    : '<span class="badge badge-red"   style="margin-left:8px">NOT COINTEGRATED</span>';
  document.getElementById('pair-header-name').innerHTML = `${p.pair} ${cointBadge}`;
  document.getElementById('pair-header-meta').textContent =
    `${p.params?.signal_timeframe || p.params?.timeframe || '1h'} -> ${p.params?.execution_timeframe || p.params?.timeframe || '1h'}  ·  ${p.params?.date_from} → ${p.params?.date_to}  ·  OLS window: ${p.params?.ols_window} bars  ·  BB std: ${p.params?.bb_std}`;

  // Validation split bar
  const tot   = p.total_trades || 1;
  const isPct = Math.round((p.is_trades   / tot) * 100);
  const o1Pct = Math.round((p.oos1_trades / tot) * 100);
  const o2Pct = 100 - isPct - o1Pct;
  document.getElementById('split-bar').innerHTML =
    `<div style="width:${isPct}%;background:#1d4ed8;height:100%;"></div>
     <div style="width:${o1Pct}%;background:#7c3aed;height:100%;"></div>
     <div style="width:${o2Pct}%;background:#047857;height:100%;"></div>`;
  document.getElementById('split-labels').innerHTML =
    `<span style="color:#60a5fa">■ In-Sample: ${p.is_trades}t / $${p.is_pnl}</span>
     <span style="color:#a78bfa">■ OOS-1: ${p.oos1_trades}t / $${p.oos1_pnl}</span>
     <span style="color:#34d399">■ OOS-2: ${p.oos2_trades}t / $${p.oos2_pnl}</span>`;

  // Info pills
  document.getElementById('detail-pills').innerHTML = [
    pill('ADF p-value',      p.adf_pvalue),
    pill('Half-Life',        p.half_life_bars ? p.half_life_bars.toFixed(0) + ' bars' : 'N/A'),
    pill('Hedge Ratio β',    p.median_hedge_ratio ?? 'N/A'),
    pill('Capital/Leg',      '$' + (p.params?.capital_per_leg || 1000).toLocaleString()),
    pill('Leverage',         (p.params?.leverage || 1) + 'x'),
    pill('Fee/Leg',          ((p.params?.trading_fee || 0.0005) * 100).toFixed(3) + '%'),
    pill('Exit Z-threshold', p.params?.exit_zscore),
    pill('BB Window',        p.params?.bb_window + ' bars'),
    pill('Total Fees',       '$' + (p.total_fees || 0).toFixed(2)),
  ].join('');

  // ── Column 1: Pair Statistics ──────────────────────────────────────────────
  const trades = p.trades || [];

  setM('m-sharpe',  p.sharpe,                       p.sharpe >= 0 ? 'pos' : 'neg');
  setM('m-calmar',  p.calmar,                        p.calmar >= 0 ? 'pos' : 'neg');
  setM('m-pf',      p.profit_factor ?? 'N/A',        (p.profit_factor || 0) >= 1 ? 'pos' : 'neg');
  setM('m-mdd',     p.max_drawdown + '%',             'neg');
  setM('m-adf',     p.adf_pvalue,                    p.cointegrated ? 'pos' : 'neg');
  setM('m-hl',      p.half_life_bars ? p.half_life_bars.toFixed(1) + ' bars' : 'N/A');
  setM('m-beta',    p.median_hedge_ratio ?? 'N/A');
  setM('m-trades',  p.total_trades);
  setM('m-hold',    p.avg_hold_bars + ' bars');
  setM('m-fees',    '$' + (p.total_fees || 0).toFixed(2), 'neg');

  // Exit breakdown badges
  const mrPct    = p.exit_mr_pct    ?? 0;
  const tsPct    = p.exit_ts_pct    ?? 0;
  const revPct   = p.exit_rev_pct   ?? 0;
  const zstopPct = p.exit_zstop_pct ?? 0;
  const liqPct   = p.exit_liq_pct   ?? 0;
  document.getElementById('m-exit-mr').textContent    = `MR ${mrPct}%`;
  document.getElementById('m-exit-ts').textContent    = `TS ${tsPct}%`;
  document.getElementById('m-exit-rev').textContent   = `REV ${revPct}%`;
  document.getElementById('m-exit-zstop').textContent = `ZSTOP ${zstopPct}%`;
  document.getElementById('m-exit-liq').textContent   = `LIQ ${liqPct}%`;
  // Colour the REV badge red if it's the dominant exit (bad sign)
  document.getElementById('m-exit-rev').className =
    revPct > mrPct ? 'badge badge-red' : 'badge badge-blue';

  // ── Master Portfolio Wallet ───────────────────────────────────────────────
  const coinA = p.coin_a;
  const coinB = p.coin_b;
  document.getElementById('m-ca-name').textContent = coinA;
  document.getElementById('m-cb-name').textContent = coinB;
  document.getElementById('leg-a-tab-label').textContent = coinA;
  document.getElementById('leg-b-tab-label').textContent = coinB;

  const totalLongCount  = trades.filter(t => t.side_a === 'LONG').length;
  const totalShortCount = trades.filter(t => t.side_a === 'SHORT').length;
  document.getElementById('m-side-badge').textContent = `${totalLongCount}L / ${totalShortCount}S`;

  const pfGross = (p.coin_a_pnl || 0) + (p.coin_b_pnl || 0);
  const pfFees = (p.total_fees || 0);
  const pfNet = p.net_pnl;
  
  setM('m-pf-trades', p.total_trades);
  setM('m-pf-gross',  (pfGross >= 0 ? '+$' : '-$') + Math.abs(pfGross).toFixed(2), pfGross >= 0 ? 'pos' : 'neg');
  setM('m-pf-fees',   '-$' + pfFees.toFixed(2), 'neg');
  setM('m-pf-net',    (pfNet >= 0 ? '+$' : '-$') + Math.abs(pfNet).toFixed(2), pfNet >= 0 ? 'pos' : 'neg');
  setM('m-pf-roi',    (p.roi >= 0 ? '+' : '') + p.roi + '%', p.roi >= 0 ? 'pos' : 'neg');
  
  const wins = trades.filter(t => t.net_pnl > 0).length;
  const wr = trades.length ? Math.round(wins / trades.length * 100) : 0;
  setM('m-pf-wr',     wr + '%', wr >= 50 ? 'pos' : 'neg');
  setM('m-pf-pf',     p.profit_factor ?? 'N/A', (p.profit_factor || 0) >= 1 ? 'pos' : 'neg');
  
  setM('m-pf-ca-net', (p.coin_a_net >= 0 ? '+$' : '-$') + Math.abs(p.coin_a_net).toFixed(2), p.coin_a_net >= 0 ? 'pos' : 'neg');
  setM('m-pf-cb-net', (p.coin_b_net >= 0 ? '+$' : '-$') + Math.abs(p.coin_b_net).toFixed(2), p.coin_b_net >= 0 ? 'pos' : 'neg');
  setM('m-pf-ca-fees', '-$' + (p.coin_a_fees || 0).toFixed(2), 'neg');
  setM('m-pf-cb-fees', '-$' + (p.coin_b_fees || 0).toFixed(2), 'neg');

  // Charts + trade log
  allTrades = trades;
  renderDanceChart(p);
  renderZScore(p);
  renderEquity(p);
  renderExcursion(p);
  renderPeriodic(p);
  renderTradeLog(trades);

  document.getElementById('pair-detail').scrollIntoView({ behavior: 'smooth' });
}

// ── Pairs Dance Chart ─────────────────────────────────────────────────────────
function renderDanceChart(p) {
  const ps     = p.price_series || [];
  const trades = p.trades       || [];

  if (ps.length === 0) { Plotly.purge('chart-dance'); return; }

  // Normalisation bases — every marker uses these so it lands on the correct line
  const pa0   = ps[0].pa;
  const pb0   = ps[0].pb;
  const times = ps.map(x => x.time);
  const normA = ps.map(x => (x.pa / pa0) * 100);
  const normB = ps.map(x => (x.pb / pb0) * 100);

  // Per-leg normalised price helpers
  const yA_entry = t => (t.entry_pa / pa0) * 100;
  const yA_exit  = t => (t.exit_pa  / pa0) * 100;
  const yB_entry = t => (t.entry_pb / pb0) * 100;
  const yB_exit  = t => (t.exit_pb  / pb0) * 100;

  const longEntries  = trades.filter(t => t.side === 'LONG_SPREAD');
  const shortEntries = trades.filter(t => t.side === 'SHORT_SPREAD');
  const mrExits      = trades.filter(t => t.reason === 'MEAN_REVERT');
  const tsExits      = trades.filter(t => t.reason === 'TIME_STOP');
  const revExits     = trades.filter(t => t.reason === 'REVERSAL');
  const trailExits   = trades.filter(t => t.reason === 'REVERSAL_TRAIL');

  // Helper: build a marker trace — showlegend only on Coin A version
  const mkTrace = (events, xFn, yFn, name, symbol, color, showLegend = true) => ({
    x: events.map(xFn), y: events.map(yFn),
    name, mode: 'markers', showlegend: showLegend,
    marker: { symbol, size: symbol === 'triangle-up' || symbol === 'triangle-down' ? 9 : 7,
              color, opacity: 0.9, line: { color: '#0f172a', width: 0.5 } },
  });

  Plotly.react('chart-dance', [
    // ── Continuous price lines ────────────────────────────────────────────────
    { x: times, y: normA, name: p.coin_a + ' (normalized)', mode: 'lines',
      line: { color: '#3b82f6', width: 1.5 } },
    { x: times, y: normB, name: p.coin_b + ' (normalized)', mode: 'lines',
      line: { color: '#f97316', width: 1.5 } },

    // ── Long Spread Entry — on Coin A line (legend shown) + Coin B line ───────
    mkTrace(longEntries, t => t.entry_time, yA_entry, 'Long Spread Entry',  'triangle-up',   '#22c55e', true),
    mkTrace(longEntries, t => t.entry_time, yB_entry, 'Long Spread Entry B', 'triangle-up',  '#22c55e', false),

    // ── Short Spread Entry — on both lines ────────────────────────────────────
    mkTrace(shortEntries, t => t.entry_time, yA_entry, 'Short Spread Entry',  'triangle-down', '#ef4444', true),
    mkTrace(shortEntries, t => t.entry_time, yB_entry, 'Short Spread Entry B', 'triangle-down', '#ef4444', false),

    // ── Mean Revert exits — on both lines ─────────────────────────────────────
    mkTrace(mrExits, t => t.exit_time, yA_exit, 'Close — Mean Revert',  'diamond', '#e2e8f0', true),
    mkTrace(mrExits, t => t.exit_time, yB_exit, 'Close — Mean Revert B', 'diamond', '#e2e8f0', false),

    // ── Time Stop exits — on both lines ───────────────────────────────────────
    mkTrace(tsExits, t => t.exit_time, yA_exit, 'Close — Time Stop',  'x',     '#eab308', true),
    mkTrace(tsExits, t => t.exit_time, yB_exit, 'Close — Time Stop B', 'x',    '#eab308', false),

    // ── Reversal exits — on both lines ────────────────────────────────────────
    mkTrace(revExits, t => t.exit_time, yA_exit, 'Close — Reversal',  'cross', '#a78bfa', true),
    mkTrace(revExits, t => t.exit_time, yB_exit, 'Close — Reversal B', 'cross', '#a78bfa', false),

    // ── Reversal-trail exits — on both lines ─────────────────────────────────
    mkTrace(trailExits, t => t.exit_time, yA_exit, 'Close — Reversal Trail',  'star', '#38bdf8', true),
    mkTrace(trailExits, t => t.exit_time, yB_exit, 'Close — Reversal Trail B', 'star', '#38bdf8', false),
  ], {
    ...layoutBase('Pairs Price Dance — Normalized (base=100)', 'Normalized Price'),
    showlegend: true,
    legend: { bgcolor: '#1e293b', bordercolor: '#334155', borderwidth: 1,
              font: { color: '#94a3b8', size: 11 } },
  });
}

// ── Z-Score chart ─────────────────────────────────────────────────────────────
function renderZScore(p) {
  const zs = p.zscore_series || [];
  const t  = zs.map(x => x.time);
  const z  = zs.map(x => x.z);
  const ub = zs.map(x => x.upper);
  const lb = zs.map(x => x.lower);

  Plotly.react('chart-zscore', [
    { x: t, y: ub,             name: 'Upper Band', mode: 'lines', line: { color: '#ef4444', dash: 'dot',  width: 1 } },
    { x: t, y: lb,             name: 'Lower Band', mode: 'lines', line: { color: '#22c55e', dash: 'dot',  width: 1 } },
    { x: t, y: z.map(() => 0), name: 'Zero',       mode: 'lines', line: { color: '#475569', dash: 'dash', width: 1 } },
    { x: t, y: z,              name: 'Z-Score',    mode: 'lines', line: { color: '#3b82f6',               width: 1.5 } },
  ], {
    ...layoutBase('Spread Z-Score + Dynamic Bollinger Bands', 'Z-Score'),
    showlegend: true,
    legend: { bgcolor: '#1e293b', bordercolor: '#334155', borderwidth: 1, font: { color: '#94a3b8', size: 11 } },
  });
}

// ── Equity curve (3 lines: combined + per leg) ────────────────────────────────
function renderEquity(p) {
  const eq    = p.equity_curve    || [];
  const eqA   = p.equity_curve_a  || [];
  const eqB   = p.equity_curve_b  || [];
  const init  = p.initial_balance || 2000;
  const init1 = (p.params?.capital_per_leg) || 1000;

  // Combined baseline reference
  const tC = eq.map(x => x.time);
  const vC = eq.map(x => x.equity);
  // Per-leg step functions (only at trade closes)
  const tA = eqA.map(x => x.time);
  const vA = eqA.map(x => x.equity);
  const tB = eqB.map(x => x.time);
  const vB = eqB.map(x => x.equity);

  Plotly.react('chart-equity', [
    // Baseline
    { x: tC, y: tC.map(() => init), name: 'Baseline ($2k)', mode: 'lines',
      line: { color: '#334155', dash: 'dash', width: 1 } },
    // Combined portfolio
    { x: tC, y: vC, name: `${p.coin_a}+${p.coin_b} Combined`, mode: 'lines',
      line: { color: '#94a3b8', width: 1.5 } },
    // Coin A leg
    { x: tA, y: vA, name: `${p.coin_a} leg ($1k)`, mode: 'lines+markers',
      line: { color: '#3b82f6', width: 2 },
      marker: { size: 3, color: '#3b82f6' } },
    // Coin B leg
    { x: tB, y: vB, name: `${p.coin_b} leg ($1k)`, mode: 'lines+markers',
      line: { color: '#f97316', width: 2 },
      marker: { size: 3, color: '#f97316' } },
    // Per-leg baseline
    { x: tA, y: tA.map(() => init1), name: 'Leg Baseline ($1k)', mode: 'lines',
      line: { color: '#1e3a5f', dash: 'dot', width: 1 }, showlegend: false },
  ], {
    ...layoutBase('Equity Curve — Combined vs Individual Legs', 'Equity ($)'),
    showlegend: true,
    legend: { bgcolor: '#1e293b', bordercolor: '#334155', borderwidth: 1, font: { color: '#94a3b8', size: 11 } },
  });
}

// ── MFE / MAE ─────────────────────────────────────────────────────────────────
function renderExcursion(p) {
  const trades = p.trades || [];
  const net    = trades.map(t => t.net_pnl);
  const colors = net.map(n => n >= 0 ? '#22c55e' : '#ef4444');
  const base   = {
    paper_bgcolor: '#1e293b', plot_bgcolor: '#0f172a',
    font: { color: '#94a3b8', size: 11 },
    margin: { t: 40, r: 20, b: 50, l: 60 },
    xaxis: { gridcolor: '#334155' }, yaxis: { gridcolor: '#334155' },
  };

  Plotly.react('chart-mfe', [{
    x: trades.map(t => t.mfe), y: net, mode: 'markers',
    marker: { color: colors, size: 5, opacity: 0.7 }, name: 'MFE vs Net PnL',
  }], { ...base,
    title: { text: 'MFE vs Net PnL (spread)', font: { color: '#f1f5f9', size: 13 } },
    xaxis: { ...base.xaxis, title: 'Max Favourable Excursion ($)' },
    yaxis: { ...base.yaxis, title: 'Net PnL ($)' },
  });

  Plotly.react('chart-mae', [{
    x: trades.map(t => t.mae), y: net, mode: 'markers',
    marker: { color: colors, size: 5, opacity: 0.7 }, name: 'MAE vs Net PnL',
  }], { ...base,
    title: { text: 'MAE vs Net PnL (spread)', font: { color: '#f1f5f9', size: 13 } },
    xaxis: { ...base.xaxis, title: 'Max Adverse Excursion ($)' },
    yaxis: { ...base.yaxis, title: 'Net PnL ($)' },
  });
}

// ── Periodic returns ──────────────────────────────────────────────────────────
function renderPeriodic(p) {
  const trades  = p.trades || [];
  const monthly = {}, yearly = {};

  trades.forEach(t => {
    const d = t.exit_time?.slice(0, 7) || '';
    const y = t.exit_time?.slice(0, 4) || '';
    monthly[d] = (monthly[d] || 0) + t.net_pnl;
    yearly[y]  = (yearly[y]  || 0) + t.net_pnl;
  });

  const mKeys = Object.keys(monthly).sort();
  const yKeys = Object.keys(yearly).sort();
  const base2 = {
    paper_bgcolor: '#1e293b', plot_bgcolor: '#0f172a',
    font: { color: '#94a3b8', size: 11 },
    margin: { t: 40, r: 20, b: 60, l: 60 },
    xaxis: { gridcolor: '#334155', tickangle: -45 }, yaxis: { gridcolor: '#334155' },
  };

  Plotly.react('chart-monthly', [{
    x: mKeys, y: mKeys.map(k => monthly[k]),
    type: 'bar', marker: { color: mKeys.map(k => monthly[k] >= 0 ? '#22c55e' : '#ef4444') }, name: 'Monthly PnL',
  }], { ...base2, title: { text: 'Monthly Net PnL ($)', font: { color: '#f1f5f9', size: 13 } } });

  Plotly.react('chart-yearly', [{
    x: yKeys, y: yKeys.map(k => yearly[k]),
    type: 'bar', marker: { color: yKeys.map(k => yearly[k] >= 0 ? '#22c55e' : '#ef4444') }, name: 'Yearly PnL',
  }], { ...base2, title: { text: 'Yearly Net PnL ($)', font: { color: '#f1f5f9', size: 13 } } });
}

// ── Trade log (two-leg split) ─────────────────────────────────────────────────
function renderTradeLog(trades) {
  allTrades = trades;
  document.getElementById('trade-search').value = '';
  document.getElementById('trade-reason-filter').value = '';
  filterTrades();
}

function filterTrades() {
  const q      = document.getElementById('trade-search').value.toLowerCase();
  const reason = document.getElementById('trade-reason-filter').value;
  const filtered = allTrades.filter(t => {
    if (reason && t.reason !== reason) return false;
    if (q && !JSON.stringify(t).toLowerCase().includes(q)) return false;
    return true;
  });
  document.getElementById('trade-count').textContent = `${filtered.length} trades`;

  const rows = filtered.slice().reverse().slice(0, 500);

  const reasonCl = r => r === 'MEAN_REVERT' ? 'pos' : (r === 'TIME_STOP' || r === 'REVERSAL_TRAIL') ? 'neu' : 'neg';

  // ── Leg A table ────────────────────────────────────────────────────────────
  document.getElementById('trade-tbody-a').innerHTML = rows.map((t, i) => {
    const net_cl  = t.net_pnl_a >= 0 ? 'pos' : 'neg';
    const side_cl = t.side_a === 'LONG' ? 'badge-green' : 'badge-red';
    return `<tr class="row-hover">
      <td class="neu">${filtered.length - i}</td>
      <td>${t.entry_time?.slice(0, 16)}</td>
      <td>${t.exit_time?.slice(0, 16)}</td>
      <td><span class="badge ${side_cl}">${t.side_a}</span></td>
      <td>$${t.entry_pa?.toFixed(2)}</td>
      <td>$${t.exit_pa?.toFixed(2)}</td>
      <td>${t.hold_bars}h</td>
      <td>${t.entry_z?.toFixed(3)}</td>
      <td class="neu">${t.entry_r2 != null ? t.entry_r2.toFixed(3) : '—'}</td>
      <td>${t.exit_z != null ? t.exit_z.toFixed(3) : '—'}</td>
      <td class="${t.pnl_a >= 0 ? 'pos' : 'neg'}">$${t.pnl_a?.toFixed(2)}</td>
      <td class="neg">-$${t.fee_a?.toFixed(2)}</td>
      <td class="${net_cl}"><strong>$${t.net_pnl_a?.toFixed(2)}</strong></td>
      <td class="pos">$${t.mfe?.toFixed(2)}</td>
      <td class="neg">$${t.mae?.toFixed(2)}</td>
      <td class="${reasonCl(t.reason)}">${t.reason}</td>
    </tr>`;
  }).join('');

  // ── Leg B table ────────────────────────────────────────────────────────────
  document.getElementById('trade-tbody-b').innerHTML = rows.map((t, i) => {
    const net_cl  = t.net_pnl_b >= 0 ? 'pos' : 'neg';
    const side_cl = t.side_b === 'LONG' ? 'badge-green' : 'badge-red';
    return `<tr class="row-hover">
      <td class="neu">${filtered.length - i}</td>
      <td>${t.entry_time?.slice(0, 16)}</td>
      <td>${t.exit_time?.slice(0, 16)}</td>
      <td><span class="badge ${side_cl}">${t.side_b}</span></td>
      <td>$${t.entry_pb?.toFixed(2)}</td>
      <td>$${t.exit_pb?.toFixed(2)}</td>
      <td>${t.hold_bars}h</td>
      <td>${t.entry_z?.toFixed(3)}</td>
      <td class="neu">${t.entry_r2 != null ? t.entry_r2.toFixed(3) : '—'}</td>
      <td>${t.exit_z != null ? t.exit_z.toFixed(3) : '—'}</td>
      <td class="${t.pnl_b >= 0 ? 'pos' : 'neg'}">$${t.pnl_b?.toFixed(2)}</td>
      <td class="neg">-$${t.fee_b?.toFixed(2)}</td>
      <td class="${net_cl}"><strong>$${t.net_pnl_b?.toFixed(2)}</strong></td>
      <td class="pos">$${t.mfe?.toFixed(2)}</td>
      <td class="neg">$${t.mae?.toFixed(2)}</td>
      <td class="${reasonCl(t.reason)}">${t.reason}</td>
    </tr>`;
  }).join('');
}

// ── Inner leg-tab switching ───────────────────────────────────────────────────
function switchLegTab(id, btn) {
  document.querySelectorAll('#t-trades .inner-tab-content').forEach(el => {
    el.classList.remove('active');
    el.style.display = 'none';
  });
  document.querySelectorAll('#t-trades .sub-tab-btn').forEach(el => el.classList.remove('active'));
  const target = document.getElementById(id);
  target.classList.add('active');
  target.style.display = 'block';
  btn.classList.add('active');
}

// ── Rank table ────────────────────────────────────────────────────────────────
function sortBy(key) {
  if (sortKey === key) sortAsc = !sortAsc;
  else { sortKey = key; sortAsc = false; }
  renderRankTable();
}

function renderRankTable() {
  const sorted = [...pairs].sort((a, b) => {
    let va = a[sortKey], vb = b[sortKey];
    if (va == null) va = sortAsc ? Infinity : -Infinity;
    if (vb == null) vb = sortAsc ? Infinity : -Infinity;
    return sortAsc ? (va > vb ? 1 : -1) : (va < vb ? 1 : -1);
  });

  const tbody = document.getElementById('rank-tbody');
  tbody.innerHTML = sorted.map((p, idx) => {
    const rank = idx + 1;
    const rk   = rank <= 3
      ? `<span class="rank-badge rank-${rank}">${rank}</span>`
      : `<span class="rank-badge rank-n">${rank}</span>`;
    const act  = activePair?.pair === p.pair ? 'row-active' : '';
    const cb   = p.cointegrated
      ? '<span class="badge badge-green">YES</span>'
      : '<span class="badge badge-red">NO</span>';
    const hl = p.half_life_bars ? p.half_life_bars.toFixed(0) + 'h' : '—';
    const saCl  = (p.sharpe_a || 0) >= 0 ? 'pos' : 'neg';
    const sbCl  = (p.sharpe_b || 0) >= 0 ? 'pos' : 'neg';
    const calCl = (p.calmar   || 0) >= 0 ? 'pos' : 'neg';
    const revCl = (p.exit_rev_pct || 0) > 50 ? 'neg' : 'neu';
    return `<tr class="row-hover ${act}" onclick="selectPair('${p.pair}')">
      <td>${rk}</td>
      <td><strong>${p.pair}</strong></td>
      <td>${cb}</td>
      <td>${p.adf_pvalue}</td>
      <td>${hl}</td>
      <td>${p.median_hedge_ratio ?? '—'}</td>
      <td class="${p.roi >= 0 ? 'pos' : 'neg'}">${p.roi?.toFixed(2)}%</td>
      <td class="${p.sharpe >= 0 ? 'pos' : 'neg'}">${p.sharpe}</td>
      <td class="${saCl}">${p.sharpe_a ?? '—'}</td>
      <td class="${sbCl}">${p.sharpe_b ?? '—'}</td>
      <td class="${calCl}">${p.calmar ?? '—'}</td>
      <td class="neg">${p.max_drawdown?.toFixed(2)}%</td>
      <td class="${p.win_rate >= 50 ? 'pos' : 'neg'}">${p.win_rate?.toFixed(1)}%</td>
      <td>${p.total_trades}</td>
      <td class="${revCl}">${p.exit_rev_pct ?? '—'}%</td>
      <td class="neg">$${p.total_fees?.toFixed(0)}</td>
    </tr>`;
  }).join('');
}

function selectPair(pairName) {
  document.getElementById('pair-select').value = pairName;
  onPairChange();
}

// ── Outer tab switching ───────────────────────────────────────────────────────
function switchTab(id, btn) {
  document.querySelectorAll('#pair-detail .tab-content').forEach(el => el.classList.remove('active'));
  document.querySelectorAll('#pair-detail .tab-btn').forEach(el => el.classList.remove('active'));
  document.getElementById(id).classList.add('active');
  btn.classList.add('active');
  setTimeout(() => {
    ['chart-dance', 'chart-zscore', 'chart-equity', 'chart-mfe', 'chart-mae', 'chart-monthly', 'chart-yearly']
      .forEach(cid => { try { Plotly.Plots.resize(cid); } catch (e) {} });
  }, 50);
}

// ── Run backtest ──────────────────────────────────────────────────────────────
async function runBacktest() {
  const mode = document.getElementById('engine-mode') ? document.getElementById('engine-mode').value : 'advanced';
  document.getElementById('run-status').textContent = 'Starting…';
  document.getElementById('run-prog-text').textContent = '';
  document.getElementById('prog-fill').style.width = '0%';
  document.getElementById('run-log').innerHTML = '';
  document.getElementById('btn-run').disabled = true;
  document.getElementById('btn-stop').style.display = 'inline-block';
  document.getElementById('run-block').style.display = 'block';

  try {
    const signalTf = document.getElementById('signal-tf')?.value || '1h';
    const executionTf = document.getElementById('execution-tf')?.value || '15m';
    await fetch(API + '/api/phase_10/run_backtest', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ signal_timeframe: signalTf, timeframe: executionTf, mode: mode }),
    });
    pollTimer = setInterval(pollStatus, 1800);
  } catch (e) { appendLog('ERROR: ' + e.message); resetRunUI(); }
}

async function stopBacktest() {
  await fetch(API + '/api/phase_10/stop', { method: 'POST' });
  clearInterval(pollTimer);
  resetRunUI();
}

async function pollStatus() {
  try {
    const d = await (await fetch(API + '/api/phase_10/status')).json();
    const logs = d.logs || [];
    logs.slice(lastLogLen).forEach(appendLog);
    lastLogLen = logs.length;
    const m = logs.join('\n').match(/\[(\d+)\/(\d+)\]/g);
    if (m) {
      const parts = m[m.length - 1].match(/\[(\d+)\/(\d+)\]/);
      const done = parseInt(parts[1]);
      const total = parseInt(parts[2]);
      document.getElementById('run-prog-text').textContent = done + '/' + total + ' pairs';
      document.getElementById('prog-fill').style.width = (done / total * 100) + '%';
    }
    if (!d.is_running && d.last_run) {
      clearInterval(pollTimer); pollTimer = null;
      document.getElementById('run-status').textContent = 'Finished';
      document.getElementById('btn-run').disabled = false;
      loadResults();
    }
  } catch (e) {}
}

function appendLog(line) {
  const el = document.getElementById('run-log');
  el.textContent += line + '\n';
  el.scrollTop = el.scrollHeight;
}

function resetRunUI() {
  document.getElementById('btn-run').disabled = false;
  document.getElementById('btn-stop').style.display = 'none';
  document.getElementById('run-block').style.display = 'none';
}

// ── Helpers ───────────────────────────────────────────────────────────────────
const layoutBase = (title, yaxis) => ({
  paper_bgcolor: '#1e293b', plot_bgcolor: '#0f172a',
  font:   { color: '#94a3b8', size: 11 },
  margin: { t: 40, r: 20, b: 40, l: 60 },
  title:  { text: title, font: { color: '#f1f5f9', size: 13 } },
  xaxis:  { gridcolor: '#334155', linecolor: '#334155' },
  yaxis:  { gridcolor: '#334155', linecolor: '#334155', title: yaxis },
});

function set(id, val, cls) {
  const el = document.getElementById(id);
  if (!el) return;
  el.textContent = val ?? '—';
  if (cls) el.className = 'sum-value ' + cls;
}

function setM(id, val, cls) {
  const el = document.getElementById(id);
  if (!el) return;
  el.textContent = val ?? '—';
  if (cls) el.className = 'mv ' + cls;
}

function pill(label, val) {
  return `<div class="pill">${label}: <span>${val}</span></div>`;
}

function pct(n, tot) { return tot ? Math.round(n / tot * 100) : 0; }

loadResults();
