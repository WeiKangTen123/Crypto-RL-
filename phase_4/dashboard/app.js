'use strict';

// ── API base: use relative path when served by Flask, absolute when opened as file ──
const API_BASE = location.protocol === 'file:' ? 'http://127.0.0.1:5001' : '';

document.addEventListener('DOMContentLoaded', function () {

  // ── State variables (must be declared before any function calls) ──
  let _stratListLoaded = false;
  let _stratResults    = [];
  let _gradeFilter     = 'ALL';
  let _fullStratList   = [];

  // ═══════════════════════════════════════════════════════════════════
  // MODE TOGGLE
  // ═══════════════════════════════════════════════════════════════════

  document.querySelectorAll('.mode-btn').forEach(function (btn) {
    btn.addEventListener('click', function () {
      document.querySelectorAll('.mode-btn').forEach(function (b) { b.classList.remove('active'); });
      btn.classList.add('active');

      const mode = btn.dataset.mode;
      document.getElementById('mode-drl-content').style.display       = mode === 'drl'       ? '' : 'none';
      document.getElementById('mode-strategy-content').style.display   = mode === 'strategy'  ? '' : 'none';
      document.getElementById('mode-multicoin-content').style.display  = mode === 'multicoin' ? '' : 'none';
      document.getElementById('drl-summary-bar').style.display         = mode === 'drl'       ? '' : 'none';

      if (mode === 'strategy' && !_stratListLoaded) {
        loadStrategyList();
      }
      if (mode === 'multicoin') {
        fetchMcForgeFiles();
      }
    });
  });

  // Auto-start in strategy mode on load
  loadStrategyList();

  // ═══════════════════════════════════════════════════════════════════
  // DRL MODE — load data.js and populate everything
  // ═══════════════════════════════════════════════════════════════════

  const D = window.BACKTEST_DATA;
  if (!D) {
    document.getElementById('mode-drl-content').innerHTML =
      '<div class="no-trades" style="padding:40px;text-align:center;color:#dc2626">' +
      '⚠️ data.js not found — run <code>phase_4/backtest.py</code> first to generate DRL backtest data.</div>';
  } else {
    initDrlMode(D);
  }

  function initDrlMode(D) {
    const m = D.metrics;

    // ── Header metadata ───────────────────────────────────────────────
    document.getElementById('h-result').textContent    = '📁 ' + D.metadata.result_name;
    document.getElementById('h-tickers').textContent   = '🪙 ' + D.metadata.tickers.join(' · ');
    document.getElementById('h-period').textContent    = '📅 ' + D.metadata.trade_start + ' → ' + D.metadata.trade_end;
    document.getElementById('h-generated').textContent = '🕒 ' + D.metadata.generated;

    const botTitleEl = document.getElementById('drl-bot-title');
    if (botTitleEl && D.metadata.model_name) {
      botTitleEl.textContent = '🤖 DRL Bot (' + D.metadata.model_name.toUpperCase() + ')';
    }

    // ── Summary Bar ───────────────────────────────────────────────────
    const sProfit = document.getElementById('s-profit');
    const sReturn = document.getElementById('s-return');
    const sMDD    = document.getElementById('s-mdd');
    const sTrades = document.getElementById('s-trades');
    const sWin    = document.getElementById('s-winrate');

    sProfit.textContent = (D.advanced.account.net_profit >= 0 ? '+$' : '-$') + Math.abs(D.advanced.account.net_profit).toLocaleString();
    sProfit.style.color = D.advanced.account.net_profit >= 0 ? '#16a34a' : '#dc2626';
    sReturn.textContent = m.drl.cumulative_return.toFixed(2) + '%';
    sReturn.style.color = m.drl.cumulative_return >= 0 ? '#16a34a' : '#dc2626';
    sMDD.textContent    = m.drl.mdd.toFixed(2) + '%';
    sMDD.style.color    = '#dc2626';
    sTrades.textContent = D.advanced.trades.total_trades;
    sWin.textContent    = D.advanced.trades.win_rate + '%';
    sWin.style.color    = D.advanced.trades.win_rate >= 50 ? '#16a34a' : '#ca8a04';

    // ── Alert banner ──────────────────────────────────────────────────
    if (D.trades.length === 0 || m.drl.cumulative_return === 0) {
      document.getElementById('alert-banner').style.display = 'block';
    }

    // ── Helpers ───────────────────────────────────────────────────────
    function colour(el, val, goodIfPositive) {
      if (!el || val === null || val === undefined || isNaN(val)) return;
      el.style.color = (goodIfPositive ? val > 0 : val < 0) ? '#16a34a' : val === 0 ? '#64748b' : '#dc2626';
    }
    function fmt(val, suffix, decimals) {
      if (val === null || val === undefined) return '—';
      return val.toFixed(decimals !== undefined ? decimals : 2) + (suffix || '');
    }
    const setMetric = function (id, val, suffix, goodIfPos, decimals) {
      const el = document.getElementById(id);
      if (el) { el.textContent = fmt(val, suffix, decimals); colour(el, val, goodIfPos); }
    };

    // ── DRL vs HODL ───────────────────────────────────────────────────
    setMetric('d-annret',  m.drl.annual_return,     '%', true);
    setMetric('d-cumret',  m.drl.cumulative_return, '%', true);
    setMetric('d-sharpe',  m.drl.sharpe,            '',  true, 4);
    setMetric('d-sortino', m.drl.sortino,           '',  true, 4);
    setMetric('d-mdd',     m.drl.mdd,               '%', false);
    setMetric('h-annret',  m.hodl.annual_return,    '%', true);
    setMetric('h-cumret',  m.hodl.cumulative_return,'%', true);
    setMetric('h-sharpe',  m.hodl.sharpe,            '', true, 4);
    setMetric('h-sortino', m.hodl.sortino,           '', true, 4);
    setMetric('h-mdd',     m.hodl.mdd,               '%', false);

    // ── Advanced Metrics ──────────────────────────────────────────────
    const adv = D.advanced;
    if (adv) {
      const set = function (id, val, formatFunc) {
        const el = document.getElementById(id);
        if (el) el.textContent = formatFunc ? formatFunc(val) : val;
        return el;
      };
      set('m-init-bal',     adv.account.initial_balance, function (v) { return '$' + v.toLocaleString(); });
      set('m-final-bal',    adv.account.final_balance,   function (v) { return '$' + v.toLocaleString(); });
      const netEl = set('m-net-profit', adv.account.net_profit, function (v) { return (v >= 0 ? '+$' : '-$') + Math.abs(v).toLocaleString(); });
      colour(netEl, adv.account.net_profit, true);
      set('m-gross-profit', adv.account.gross_profit, function (v) { return '$' + v.toLocaleString(); });
      set('m-gross-loss',   adv.account.gross_loss,   function (v) { return '$' + v.toLocaleString(); });
      set('m-fees',         adv.account.total_fees,   function (v) { return '$' + v.toLocaleString(); });

      set('m-expectancy',   adv.efficiency.expectancy,    function (v) { return '$' + v.toFixed(2); });
      const pfEl = set('m-profit-factor', adv.efficiency.profit_factor);
      colour(pfEl, adv.efficiency.profit_factor - 1.0, true);
      set('m-calmar',    adv.efficiency.calmar_ratio);
      set('m-recovery',  adv.efficiency.recovery_factor);
      set('m-sharpe',    adv.efficiency.sharpe.toFixed(4));
      set('m-sortino',   adv.efficiency.sortino.toFixed(4));

      set('m-win-rate',      adv.trades.win_rate + '%');
      set('m-total-trades',  adv.trades.total_trades);
      set('m-avg-win-loss',  '$' + adv.trades.avg_win.toLocaleString() + ' / $' + adv.trades.avg_loss.toLocaleString());
      set('m-best-worst',    '$' + adv.trades.best_trade.toLocaleString() + ' / $' + adv.trades.worst_trade.toLocaleString());
      set('m-consec',        adv.trades.max_consec_wins + ' / ' + adv.trades.max_consec_losses);
      set('m-duration',      adv.trades.avg_duration_hours + ' hrs');
    }

    // ── Tab Management ────────────────────────────────────────────────
    document.querySelectorAll('#mode-drl-content .tab-btn').forEach(function (btn) {
      btn.addEventListener('click', function () {
        document.querySelectorAll('#mode-drl-content .tab-btn').forEach(function (b) { b.classList.remove('active'); });
        document.querySelectorAll('#mode-drl-content .tab-content').forEach(function (c) { c.classList.remove('active'); });
        btn.classList.add('active');
        document.getElementById('tab-' + btn.dataset.tab).classList.add('active');
        if (btn.dataset.tab === 'price')    renderPriceChart();
        if (btn.dataset.tab === 'periodic') renderPeriodicCharts();
        if (btn.dataset.tab === 'equity')   Plotly.Plots.resize('chart-equity');
        if (btn.dataset.tab === 'drawdown') Plotly.Plots.resize('chart-drawdown');
        if (btn.dataset.tab === 'log')      renderTradeLog();
      });
    });

    // ── Trade Log ─────────────────────────────────────────────────────
    function renderTradeLog() {
      const tbody = document.getElementById('log-tbody');
      if (!tbody) return;
      tbody.innerHTML = '';
      D.trades.forEach(function (t) {
        const row = document.createElement('tr');
        const sc  = t.side === 'BUY' ? 'badge-buy' : 'badge-sell';
        row.innerHTML =
          '<td>' + t.time + '</td>' +
          '<td><strong>' + t.asset + '</strong></td>' +
          '<td><span class="' + sc + '">' + t.side + '</span></td>' +
          '<td>' + t.amount.toLocaleString(undefined, {maximumFractionDigits: 8}) + '</td>' +
          '<td>$' + t.price.toLocaleString() + '</td>' +
          '<td>$' + t.value_usd.toLocaleString() + '</td>' +
          '<td style="color:#64748b">$' + (t.fee_usd || (t.value_usd * 0.001)).toLocaleString() + '</td>';
        tbody.appendChild(row);
      });
    }

    // ── Asset Selector ────────────────────────────────────────────────
    const assetSelector = document.getElementById('asset-selector');
    D.metadata.tickers.forEach(function (ticker) {
      const opt = document.createElement('option');
      opt.value = ticker; opt.textContent = ticker;
      assetSelector.appendChild(opt);
    });
    assetSelector.addEventListener('change', renderPriceChart);

    // ── Plots ─────────────────────────────────────────────────────────
    function renderPeriodicCharts() {
      if (!D.periodic || !D.periodic.monthly || !D.periodic.monthly.labels.length) {
        document.getElementById('chart-monthly').innerHTML =
          '<p style="text-align:center;padding-top:100px;color:#64748b">No data available.</p>';
        return;
      }
      const pm = D.periodic.monthly;
      const py = D.periodic.yearly;
      const layout = { template: 'plotly_white', margin: {t:10,b:40,l:50,r:10}, yaxis: {title:'Return (%)'} };
      Plotly.newPlot('chart-monthly', [{x:pm.labels,y:pm.values,type:'bar',
        marker:{color:pm.values.map(function(v){return v>=0?'#16a34a':'#dc2626';})}}], layout, {responsive:true});
      Plotly.newPlot('chart-yearly', [{x:py.labels,y:py.values,type:'bar',
        marker:{color:py.values.map(function(v){return v>=0?'#16a34a':'#dc2626';})}}], layout, {responsive:true});
    }

    const eqLayout = {
      template:'plotly_white', hovermode:'x unified',
      yaxis:{title:'Cumulative Return', tickformat:'.1%'},
      xaxis:{title:'Date'}, legend:{orientation:'h', y:1.12},
      margin:{t:20,b:50,l:70,r:20}
    };

    const eqTraces = [
      {x:D.equity.times, y:D.equity.hodl, name:'Buy & Hold', type:'scatter', mode:'lines',
       line:{color:'#ef4444',width:2}, fill:'tozeroy', fillcolor:'rgba(239,68,68,.05)'},
      {x:D.equity.times, y:D.equity.drl,  name:'DRL Bot',   type:'scatter', mode:'lines',
       line:{color:'#3b82f6',width:2.5}, fill:'tozeroy', fillcolor:'rgba(59,130,246,.05)'}
    ];

    // Per-coin dotted lines
    const coinColors = ['#7c3aed','#d69e2e','#059669','#e11d48'];
    if (D.equity.coins) {
      Object.entries(D.equity.coins).forEach(function (_a, idx) {
        eqTraces.push({
          x: D.equity.times, y: _a[1], name: _a[0] + ' holding',
          type:'scatter', mode:'lines',
          line:{color: coinColors[idx % coinColors.length], width:1.5, dash:'dot'}
        });
      });
    }
    Plotly.newPlot('chart-equity', eqTraces, eqLayout, {responsive:true});

    const ddLayout = JSON.parse(JSON.stringify(eqLayout));
    ddLayout.yaxis.title = 'Drawdown';
    Plotly.newPlot('chart-drawdown', [
      {x:D.drawdown.times, y:D.drawdown.hodl, name:'Buy & Hold', type:'scatter', mode:'lines', line:{color:'#ef4444',width:2}},
      {x:D.drawdown.times, y:D.drawdown.drl,  name:'DRL Bot',   type:'scatter', mode:'lines', line:{color:'#3b82f6',width:2.5}}
    ], ddLayout, {responsive:true});

    function renderPriceChart() {
      const ticker = assetSelector.value || D.metadata.tickers[0];
      const buys  = D.trades.filter(function (t) { return t.asset === ticker && t.side === 'BUY'; });
      const sells = D.trades.filter(function (t) { return t.asset === ticker && t.side === 'SELL'; });
      Plotly.newPlot('chart-price', [
        {x:D.equity.times, y:D.equity.prices[ticker], name:ticker, type:'scatter', mode:'lines', line:{color:'#94a3b8',width:1.5}},
        {x:buys.map(function(t){return t.time;}),  y:buys.map(function(t){return t.price;}),
         name:'BUY',  mode:'markers', marker:{color:'#16a34a',size:10,symbol:'triangle-up'}},
        {x:sells.map(function(t){return t.time;}), y:sells.map(function(t){return t.price;}),
         name:'SELL', mode:'markers', marker:{color:'#dc2626',size:10,symbol:'triangle-down'}}
      ], {template:'plotly_white', margin:{t:20,b:50,l:80,r:20}}, {responsive:true});
    }

    // ── Round-Trip Trade Table ─────────────────────────────────────────
    const tbody    = document.getElementById('trade-tbody');
    const search   = document.getElementById('trade-search');

    function renderRows(list) {
      if (!tbody) return;
      tbody.innerHTML = '';
      list.forEach(function (t) {
        const row      = document.createElement('tr');
        const netProfit = t.net_profit_usd || 0;
        const badge    = netProfit >= 0 ? '<span class="badge-win">WIN</span>' : '<span class="badge-loss">LOSS</span>';
        const pc       = netProfit >= 0 ? '#16a34a' : '#dc2626';
        row.innerHTML =
          '<td><strong>' + t.asset + '</strong> ' + badge + '</td>' +
          '<td style="font-size:0.8rem">' + t.entry_time + '</td>' +
          '<td style="font-size:0.8rem">' + t.exit_time  + '</td>' +
          '<td style="font-family:monospace;color:#94a3b8">' + (t.qty != null ? t.qty.toLocaleString(undefined, {maximumFractionDigits:4}) : '—') + '</td>' +
          '<td>$' + t.entry_price.toLocaleString() + '</td>' +
          '<td>$' + t.exit_price.toLocaleString()  + '</td>' +
          '<td style="color:#64748b">$' + t.total_fees_usd.toLocaleString() + '</td>' +
          '<td style="color:#f59e0b;font-size:0.8rem">-$' + (t.total_slippage_usd || 0).toLocaleString(undefined, {maximumFractionDigits:4}) + ' <span style="opacity:0.6;font-size:0.7rem">(' + (t.slippage_pct || 0).toFixed(3) + '%)</span></td>' +
          '<td style="color:' + (t.gross_profit_usd>=0?'#16a34a':'#dc2626') + ';opacity:0.6">$' + t.gross_profit_usd.toLocaleString() + '</td>' +
          '<td style="color:' + pc + ';font-weight:bold">$' + netProfit.toLocaleString() + '</td>' +
          '<td style="color:' + pc + ';font-weight:bold">' + t.profit_pct.toFixed(2) + '%</td>' +
          '<td style="font-size:0.8rem">' + t.duration + '</td>';
        tbody.appendChild(row);
      });
      document.getElementById('trade-count-badge').textContent = list.length + ' trades';
    }

    if (D.round_trips && D.round_trips.length === 0) {
      document.getElementById('no-trades-msg').style.display = 'block';
    }
    renderRows(D.round_trips || []);
    search.addEventListener('input', function () {
      const q = search.value.toLowerCase();
      renderRows(D.round_trips.filter(function (t) { return t.asset.toLowerCase().includes(q); }));
    });
  }


  // ═══════════════════════════════════════════════════════════════════
  // STRATEGY MODE
  // ═══════════════════════════════════════════════════════════════════

  let _stratActiveIdx  = -1;

  const PALETTE = [
    '#7c3aed','#db2777','#b45309','#047857','#0369a1','#6d28d9',
    '#be123c','#92400e','#065f46','#1e40af','#4c1d95','#9d174d',
    '#78350f','#064e3b','#1e3a8a','#5b21b6','#831843','#166534'
  ];

  function loadStrategyList() {
    const grid    = document.getElementById('strat-grid');
    const runBtn  = document.getElementById('btn-run-strat');
    const noteEl  = document.getElementById('strat-server-note');

    fetch(API_BASE + '/api/strategy_list')
      .then(function (r) {
        if (!r.ok) throw new Error('HTTP ' + r.status);
        return r.json();
      })
      .then(function (list) {
        _stratListLoaded = true;
        noteEl.textContent = '✅ Connected to Flask server';
        noteEl.style.color = '#16a34a';
        renderStrategyGrid(list);
        runBtn.disabled = false;
      })
      .catch(function (err) {
        _stratListLoaded = false;
        noteEl.textContent = '⚠️ Flask server not reachable — start main_controller/main.py on port 5001';
        noteEl.style.color = '#dc2626';
        grid.innerHTML =
          '<div class="strat-loading" style="color:#dc2626">' +
          'Cannot connect to Flask server at <strong>http://127.0.0.1:5001</strong>.<br>' +
          'Run: <code>./venv/bin/python main_controller/main.py</code></div>';
      });
  }

  // Strategy date lookup: sid → {date_from, date_to}
  var _stratDateMap = {};

  function updateDatePickers() {
    const checked = Array.from(document.querySelectorAll('.strat-checkbox:checked'));
    const noteEl  = document.getElementById('strat-date-note');
    const fromEl  = document.getElementById('strat-date-from');
    const toEl    = document.getElementById('strat-date-to');

    if (checked.length === 0) {
      noteEl.textContent = '';
      return;
    }

    const dates = checked.map(function (cb) { return _stratDateMap[cb.dataset.sid] || {}; });
    const froms = dates.map(function (d) { return d.date_from || '2021-01-01'; });
    const tos   = dates.map(function (d) { return d.date_to   || '2026-05-31'; });

    const allSameFrom = froms.every(function (f) { return f === froms[0]; });
    const allSameTo   = tos.every(function (t)   { return t === tos[0];   });

    if (checked.length === 1) {
      // Single strategy — use its own configured dates exactly
      fromEl.value = froms[0];
      toEl.value   = tos[0];
      noteEl.style.color = '#6b7280';
      noteEl.textContent = '📅 Dates auto-set from strategy config (matches scan period)';
    } else if (allSameFrom && allSameTo) {
      // Multiple strategies, all same dates
      fromEl.value = froms[0];
      toEl.value   = tos[0];
      noteEl.style.color = '#6b7280';
      noteEl.textContent = '📅 All selected strategies share the same date range';
    } else {
      // Multiple strategies with different date ranges — use widest span for comparison
      const minFrom = froms.slice().sort()[0];
      const maxTo   = tos.slice().sort().reverse()[0];
      fromEl.value = minFrom;
      toEl.value   = maxTo;
      noteEl.style.color = '#b45309';
      noteEl.textContent = '⚠ Selected strategies have different date ranges — using widest span (' + minFrom + ' → ' + maxTo + '). Results may not be comparable.';
    }
  }

  function renderStrategyGrid(list) {
    _fullStratList = list;
    const grid = document.getElementById('strat-grid');

    // Build date lookup
    _stratDateMap = {};
    list.forEach(function (s) {
      _stratDateMap[s.sid] = { date_from: s.date_from, date_to: s.date_to };
    });

    // Sort by numeric ID ascending (1, 2, 3 ...)
    list.sort(function (a, b) { return parseInt(a.sid) - parseInt(b.sid); });

    // Count by grade
    var counts = { GOOD: 0, MEDIOCRE: 0, BAD: 0, OTHER: 0 };
    list.forEach(function (s) {
      if (s.grade === 'GOOD')         counts.GOOD++;
      else if (s.grade === 'MEDIOCRE') counts.MEDIOCRE++;
      else if (s.grade === 'BAD')      counts.BAD++;
      else                             counts.OTHER++;
    });

    // Build filter bar
    var filterBar = document.getElementById('strat-filter-bar');
    filterBar.innerHTML =
      '<div class="strat-filter-bar">' +
        '<div class="strat-grade-count">' +
          '<span class="sgc-good">' + counts.GOOD + ' GOOD</span> · ' +
          '<span class="sgc-med">' + counts.MEDIOCRE + ' MEDIOCRE</span> · ' +
          '<span class="sgc-bad">' + counts.BAD + ' BAD</span>' +
          (counts.OTHER ? ' · <span class="sgc-other">' + counts.OTHER + ' NO DATA</span>' : '') +
        '</div>' +
        '<div class="strat-filter-pills">' +
          ['ALL', 'GOOD', 'MEDIOCRE', 'BAD', 'NO DATA'].map(function (f) {
            return '<button class="filter-pill' + (f === _gradeFilter ? ' fp-active' : '') +
                   '" data-grade="' + f + '">' + f + '</button>';
          }).join('') +
        '</div>' +
      '</div>';

    filterBar.querySelectorAll('.filter-pill').forEach(function (pill) {
      pill.addEventListener('click', function () {
        _gradeFilter = pill.dataset.grade;
        filterBar.querySelectorAll('.filter-pill').forEach(function (p) {
          p.classList.toggle('fp-active', p.dataset.grade === _gradeFilter);
        });
        applyFilter();
      });
    });

    // Helper: colour value
    function metricColor(val, greenThresh, yellowThresh, higherIsBetter) {
      if (val == null) return '';
      if (higherIsBetter) {
        return val >= greenThresh ? 'color:#16a34a' : val >= yellowThresh ? 'color:#ca8a04' : 'color:#dc2626';
      } else {
        return val < greenThresh ? 'color:#16a34a' : val < yellowThresh ? 'color:#ca8a04' : 'color:#dc2626';
      }
    }

    function buildCard(s) {
      var gradeCls = s.grade === 'GOOD' ? 'sg-good'
                   : s.grade === 'MEDIOCRE' ? 'sg-med'
                   : s.grade === 'BAD' ? 'sg-bad'
                   : 'sg-none';
      var gradeLabel = s.grade || 'NO SCAN';
      var gradeBadge = '<span class="strat-grade-badge ' + gradeCls + '">' + gradeLabel + '</span>';

      var hasMetrics = s.sharpe != null || s.total_return != null;
      var metricsHtml = '';
      if (hasMetrics) {
        var sharpe = s.sharpe != null ? s.sharpe.toFixed(2) : '—';
        var ret    = s.total_return != null ? (s.total_return >= 0 ? '+' : '') + s.total_return + '%' : '—';
        var dd     = s.max_drawdown != null ? s.max_drawdown + '%' : '—';
        var tr     = s.total_trades != null ? s.total_trades : '—';
        var pf     = s.profit_factor != null ? (s.profit_factor >= 99 ? '∞' : Number(s.profit_factor).toFixed(2)) : '—';
        metricsHtml =
          '<div class="strat-metrics-row">' +
            '<span class="sm-item"><span class="sm-label">Sharpe</span>' +
              '<span class="sm-val" style="' + metricColor(s.sharpe, 1.0, 0.3, true) + '">' + sharpe + '</span></span>' +
            '<span class="sm-item"><span class="sm-label">Return</span>' +
              '<span class="sm-val" style="' + metricColor(s.total_return, 100, 0, true) + '">' + ret + '</span></span>' +
            '<span class="sm-item"><span class="sm-label">Max DD</span>' +
              '<span class="sm-val" style="' + metricColor(s.max_drawdown, 20, 50, false) + '">' + dd + '</span></span>' +
            '<span class="sm-item"><span class="sm-label">Trades</span>' +
              '<span class="sm-val" style="' + metricColor(s.total_trades, 100, 30, true) + '">' + tr + '</span></span>' +
            '<span class="sm-item"><span class="sm-label">PF</span>' +
              '<span class="sm-val" style="' + metricColor(s.profit_factor, 1.5, 1.0, true) + '">' + pf + '</span></span>' +
          '</div>';
      } else {
        metricsHtml = '<div class="strat-no-scan">Not scanned yet — run ⟳ RUN SCAN in Agent Monitor</div>';
      }

      var card = document.createElement('div');
      card.className = 'strat-card';
      card.dataset.sid = s.sid;
      var dateRange = (s.date_from && s.date_to)
        ? s.date_from.slice(0, 7) + ' → ' + s.date_to.slice(0, 7)
        : '';
      card.innerHTML =
        '<input type="checkbox" class="strat-checkbox" data-sid="' + s.sid + '">' +
        '<div class="strat-card-info">' +
          '<div class="strat-card-title">' +
            '<span class="strat-num">#' + parseInt(s.sid) + '</span> ' + s.class +
          '</div>' +
          '<div class="strat-card-meta">' +
            (gradeBadge ? gradeBadge + ' ' : '') +
            '<span class="strat-tag coin-tag">' + s.coin + '</span>' +
            '<span class="strat-tag tf-tag">' + s.timeframe + '</span>' +
            '<span class="strat-tag bal-tag">$' + Number(s.init_bal).toLocaleString() + '</span>' +
            (dateRange ? '<span class="strat-tag date-tag">' + dateRange + '</span>' : '') +
          '</div>' +
          metricsHtml +
        '</div>';

      var cb = card.querySelector('input[type=checkbox]');
      card.addEventListener('click', function (e) {
        if (e.target === cb) return;
        cb.checked = !cb.checked;
        card.classList.toggle('selected', cb.checked);
        updateDatePickers();
      });
      cb.addEventListener('change', function () {
        card.classList.toggle('selected', cb.checked);
        updateDatePickers();
      });
      return card;
    }

    function applyFilter() {
      grid.innerHTML = '';
      var filtered = list.filter(function (s) {
        if (_gradeFilter === 'ALL')     return true;
        if (_gradeFilter === 'NO DATA') return !s.grade || s.grade === 'PENDING' || s.grade === 'ERROR';
        return s.grade === _gradeFilter;
      });
      if (filtered.length === 0) {
        grid.innerHTML = '<div class="strat-loading">No strategies match this filter.</div>';
        return;
      }
      filtered.forEach(function (s) { grid.appendChild(buildCard(s)); });
    }

    applyFilter();

    // Select All / Clear — operate on currently visible cards only
    document.getElementById('btn-select-all').addEventListener('click', function () {
      grid.querySelectorAll('.strat-checkbox').forEach(function (cb) {
        cb.checked = true;
        cb.closest('.strat-card').classList.add('selected');
      });
      updateDatePickers();
    });
    document.getElementById('btn-clear-all').addEventListener('click', function () {
      grid.querySelectorAll('.strat-checkbox').forEach(function (cb) {
        cb.checked = false;
        cb.closest('.strat-card').classList.remove('selected');
      });
      document.getElementById('strat-date-note').textContent = '';
    });
  }

  // ── Run Button ────────────────────────────────────────────────────
  document.getElementById('btn-run-strat').addEventListener('click', function () {
    const selected = Array.from(document.querySelectorAll('.strat-checkbox:checked'))
                          .map(function (cb) { return cb.dataset.sid; });
    if (selected.length === 0) {
      alert('Please select at least one strategy.');
      return;
    }

    const dateFrom = document.getElementById('strat-date-from').value;
    const dateTo   = document.getElementById('strat-date-to').value;

    document.getElementById('strat-results').style.display  = 'none';
    document.getElementById('strat-detail-panel').style.display = 'none';
    document.getElementById('strat-running').style.display  = 'block';

    fetch(API_BASE + '/api/strategy_backtest', {
      method: 'POST',
      headers: {'Content-Type': 'application/json'},
      body: JSON.stringify({strategy_ids: selected, date_from: dateFrom, date_to: dateTo})
    })
      .then(function (r) {
        if (!r.ok) throw new Error('HTTP ' + r.status);
        return r.json();
      })
      .then(function (data) {
        document.getElementById('strat-running').style.display = 'none';
        if (data.error) { alert('Error: ' + data.error); return; }
        _stratResults = data.results || [];
        renderStrategyResults(_stratResults);
      })
      .catch(function (err) {
        document.getElementById('strat-running').style.display = 'none';
        alert('Request failed: ' + err.message);
      });
  });

  // ── Render results (chart + table) ────────────────────────────────
  function renderStrategyResults(results) {
    if (!results.length) {
      alert('No results — the strategy produced no trades in the selected date range.\n\nPossible causes:\n• Strategy not yet scanned (run ⊕ SCAN NEW in the Agent Monitor)\n• Date range has no overlap with the strategy\'s configured period\n• Strategy parameters are too restrictive for this period');
      return;
    }

    // Sort by Sharpe descending
    results.sort(function (a, b) { return b.metrics['Sharpe Ratio'] - a.metrics['Sharpe Ratio']; });

    document.getElementById('strat-results').style.display = '';
    document.getElementById('strat-result-count').textContent = results.length + ' strategies';

    // ── Comparison Chart ────────────────────────────────────────────
    const traces = results.map(function (s, i) {
      return {
        x: s.equity_times, y: s.equity_cumret,
        name: s.class + ' (' + s.coin + ' ' + s.timeframe + ')',
        type: 'scatter', mode: 'lines',
        line: {color: PALETTE[i % PALETTE.length], width: 1.6},
        opacity: 0.85,
        customdata: [i], meta: {idx: i}
      };
    });
    Plotly.newPlot('chart-strat-compare', traces, {
      template: 'plotly_white', hovermode: 'x unified',
      yaxis: {title: 'Cumulative Return', tickformat: '.1%'},
      xaxis: {title: 'Date'},
      legend: {orientation: 'h', y: 1.14, font: {size: 10}},
      margin: {t:20, b:50, l:70, r:20}
    }, {responsive: true});

    // ── Ranking Table ───────────────────────────────────────────────
    const tbody = document.getElementById('strat-rank-tbody');
    tbody.innerHTML = '';
    results.forEach(function (s, i) {
      const mt = s.metrics;
      const tr = document.createElement('tr');
      tr.style.cursor = 'pointer';
      tr.dataset.idx  = i;

      const retColor = mt['Total Return'] >= 0  ? '#16a34a' : '#dc2626';
      const shColor  = mt['Sharpe Ratio'] >= 0  ? '#16a34a' : '#dc2626';
      const wrColor  = mt['Win Rate']     >= 50  ? '#16a34a' : '#ca8a04';
      const pfColor  = mt['Profit Factor'] >= 1  ? '#16a34a' : '#dc2626';

      tr.innerHTML =
        '<td><strong style="color:' + PALETTE[i % PALETTE.length] + '">● </strong><span style="color:#6b7280;font-size:0.8em;font-family:monospace">#' + parseInt(s.sid) + '</span> <strong>' + s.class + '</strong></td>' +
        '<td>' + s.coin + '</td>' +
        '<td>' + s.timeframe + '</td>' +
        '<td style="color:' + retColor + '">' + (mt['Total Return'] >= 0 ? '+' : '') + mt['Total Return'].toFixed(1) + '%</td>' +
        '<td style="color:' + shColor  + '">' + mt['Sharpe Ratio'].toFixed(2) + '</td>' +
        '<td style="color:' + shColor  + '">' + mt['Sortino Ratio'].toFixed(2) + '</td>' +
        '<td style="color:#dc2626">'  + Math.abs(mt['Max Drawdown %']).toFixed(1) + '%</td>' +
        '<td style="color:' + wrColor + '">' + mt['Win Rate'].toFixed(1) + '%</td>' +
        '<td>' + mt['Total Trades'] + '</td>' +
        '<td style="font-family:monospace;color:#94a3b8">' + (s.leverage || '—') + 'x</td>' +
        '<td style="color:' + pfColor + '">' + mt['Profit Factor'].toFixed(2) + '</td>';

      tr.addEventListener('click', function () {
        document.querySelectorAll('#strat-rank-tbody tr').forEach(function (r) { r.classList.remove('row-active'); });
        tr.classList.add('row-active');
        showStrategyDetail(s, i);
      });
      tbody.appendChild(tr);
    });

    // Scroll to results
    document.getElementById('strat-results').scrollIntoView({behavior: 'smooth', block: 'start'});
  }

  // ── Per-strategy detail panel ─────────────────────────────────────
  function showStrategyDetail(s, colorIdx) {
    const panel = document.getElementById('strat-detail-panel');
    panel.style.display = '';

    document.getElementById('strat-detail-title').textContent = s.class;
    document.getElementById('strat-detail-meta').textContent  =
      s.desc + '  |  ' + s.coin + ' ' + s.timeframe + '  |  Initial: $' + s.initial_balance.toLocaleString();

    // Reset sub-tabs
    panel.querySelectorAll('.tab-btn').forEach(function (b) { b.classList.remove('active'); });
    panel.querySelectorAll('.tab-content').forEach(function (c) { c.classList.remove('active'); });
    panel.querySelector('[data-stab="s-metrics"]').classList.add('active');
    document.getElementById('stab-s-metrics').classList.add('active');

    // Sub-tab switching
    panel.querySelectorAll('.tab-btn[data-stab]').forEach(function (btn) {
      btn.onclick = function () {
        panel.querySelectorAll('.tab-btn').forEach(function (b) { b.classList.remove('active'); });
        panel.querySelectorAll('.tab-content').forEach(function (c) { c.classList.remove('active'); });
        btn.classList.add('active');
        document.getElementById('stab-' + btn.dataset.stab).classList.add('active');
        if (btn.dataset.stab === 's-equity')   renderDetailEquity(s, colorIdx);
        if (btn.dataset.stab === 's-price')    renderDetailPriceMarkers(s, colorIdx);
        if (btn.dataset.stab === 's-periodic') renderDetailPeriodic(s);
        if (btn.dataset.stab === 's-trades')   renderDetailTrades(s);
        if (btn.dataset.stab === 's-rulebook') renderRulebook(s);
      };
    });

    // Render Metrics cards
    renderDetailMetrics(s);

    panel.scrollIntoView({behavior: 'smooth', block: 'start'});
  }

  document.getElementById('btn-close-detail').addEventListener('click', function () {
    document.getElementById('strat-detail-panel').style.display = 'none';
    document.querySelectorAll('#strat-rank-tbody tr').forEach(function (r) { r.classList.remove('row-active'); });
  });

  function renderDetailMetrics(s) {
    const grid = document.getElementById('strat-metrics-grid');
    const mt   = s.metrics;
    const fmt  = s.fmt_metrics || {};

    const blocks = [
      {title: '💰 Account', icon:'💰', items: [
        ['Initial Balance',  fmt['Initial Balance'] || '—'],
        ['Final Balance',    fmt['Final Balance']   || '—'],
        ['Net Profit',       fmt['Net Profit']      || '—'],
        ['Total Fees',       fmt['Total Fees']      || '—'],
        ['Leverage',         (s.leverage || '—') + 'x'],
      ]},
      {title: '⚡ Edge & Efficiency', icon:'⚡', items: [
        ['Total Return',     (mt['Total Return']   >= 0 ? '+' : '') + mt['Total Return'].toFixed(2)   + '%'],
        ['Annual Return',    (mt['Annual Return']  >= 0 ? '+' : '') + mt['Annual Return'].toFixed(2)  + '%'],
        ['Sharpe Ratio',     mt['Sharpe Ratio'].toFixed(2)],
        ['Sortino Ratio',    mt['Sortino Ratio'].toFixed(2)],
        ['Calmar Ratio',     mt['Calmar Ratio'].toFixed(2)],
        ['Profit Factor',    mt['Profit Factor'].toFixed(2)],
        ['Expectancy',       fmt['Expectancy'] || '—'],
        ['Recovery Factor',  mt['Recovery Factor'].toFixed(2)],
        ['Max Drawdown',     Math.abs(mt['Max Drawdown %']).toFixed(2) + '%'],
      ]},
      {title: '📊 Trade Statistics', icon:'📊', items: [
        ['Total Trades',     mt['Total Trades']],
        ['Win Rate',         mt['Win Rate'].toFixed(1) + '%'],
        ['Avg Win',          fmt['Avg Win']     || '—'],
        ['Avg Loss',         fmt['Avg Loss']    || '—'],
        ['Best Trade',       fmt['Best Trade']  || '—'],
        ['Worst Trade',      fmt['Worst Trade'] || '—'],
        ['Max Consec. Wins', fmt['Max Consec. Wins']   || '—'],
        ['Max Consec. Loss', fmt['Max Consec. Losses'] || '—'],
        ['Avg Duration',     fmt['Avg Duration (days)'] || '—'],
      ]},
    ];

    grid.innerHTML = '';
    blocks.forEach(function (block) {
      const sec = document.createElement('section');
      sec.className = 'card';
      sec.style.marginTop = '0';
      let rows = block.items.map(function (item) {
        return '<div class="metric-row"><span class="ml">' + item[0] + '</span><span class="mv">' + item[1] + '</span></div>';
      }).join('');
      sec.innerHTML =
        '<div class="card-header"><span class="icon">' + block.icon + '</span><h2>' + block.title.split(' ').slice(1).join(' ') + '</h2></div>' +
        '<div class="metric-list">' + rows + '</div>';
      grid.appendChild(sec);
    });
  }

  function renderDetailEquity(s, colorIdx) {
    Plotly.newPlot('chart-strat-detail-equity', [{
      x: s.equity_times, y: s.equity_cumret,
      name: s.class, type: 'scatter', mode: 'lines',
      line: {color: PALETTE[colorIdx % PALETTE.length], width: 2},
      fill: 'tozeroy', fillcolor: 'rgba(59,130,246,.06)'
    }], {
      template: 'plotly_white', hovermode: 'x unified',
      yaxis: {title: 'Cumulative Return', tickformat: '.1%'},
      xaxis: {title: 'Date'},
      margin: {t:20, b:50, l:70, r:20}
    }, {responsive: true});
  }

  function renderDetailPriceMarkers(s, colorIdx) {
    const trips = s.round_trips || [];

    const longEntries  = trips.filter(function (t) { return t.side === 'LONG'; });
    const shortEntries = trips.filter(function (t) { return t.side === 'SHORT'; });
    const longExits    = trips.filter(function (t) { return t.side === 'LONG'; });
    const shortExits   = trips.filter(function (t) { return t.side === 'SHORT'; });

    const traces = [
      // Price line
      {
        x: s.equity_times, y: s.equity_prices,
        name: s.coin + ' Close',
        type: 'scatter', mode: 'lines',
        line: {color: '#94a3b8', width: 1.5},
        hovertemplate: '%{x}<br>$%{y:,.2f}<extra></extra>'
      },
      // Long Entry — green triangle-up
      {
        x: longEntries.map(function (t) { return t.entry_time; }),
        y: longEntries.map(function (t) { return t.entry_price; }),
        name: 'Long Entry',
        mode: 'markers',
        marker: {color: '#16a34a', size: 12, symbol: 'triangle-up', line: {color: '#fff', width: 1}},
        hovertemplate: 'LONG ENTRY<br>%{x}<br>$%{y:,.4f}<extra></extra>'
      },
      // Short Entry — red triangle-down
      {
        x: shortEntries.map(function (t) { return t.entry_time; }),
        y: shortEntries.map(function (t) { return t.entry_price; }),
        name: 'Short Entry',
        mode: 'markers',
        marker: {color: '#dc2626', size: 12, symbol: 'triangle-down', line: {color: '#fff', width: 1}},
        hovertemplate: 'SHORT ENTRY<br>%{x}<br>$%{y:,.4f}<extra></extra>'
      },
      // Exit Long — green X
      {
        x: longExits.map(function (t) { return t.exit_time; }),
        y: longExits.map(function (t) { return t.exit_price; }),
        name: 'Exit Long',
        mode: 'markers',
        marker: {color: '#16a34a', size: 11, symbol: 'x', line: {color: '#16a34a', width: 2}},
        hovertemplate: 'EXIT LONG<br>%{x}<br>$%{y:,.4f}<extra></extra>'
      },
      // Exit Short — red X
      {
        x: shortExits.map(function (t) { return t.exit_time; }),
        y: shortExits.map(function (t) { return t.exit_price; }),
        name: 'Exit Short',
        mode: 'markers',
        marker: {color: '#dc2626', size: 11, symbol: 'x', line: {color: '#dc2626', width: 2}},
        hovertemplate: 'EXIT SHORT<br>%{x}<br>$%{y:,.4f}<extra></extra>'
      }
    ];

    Plotly.newPlot('chart-strat-detail-price', traces, {
      template: 'plotly_white', hovermode: 'x unified',
      yaxis: {title: 'Price (USD)', tickprefix: '$'},
      xaxis: {title: 'Date'},
      legend: {orientation: 'h', y: 1.14, font: {size: 11}},
      margin: {t: 20, b: 50, l: 80, r: 20}
    }, {responsive: true});
  }

  function renderDetailPeriodic(s) {
    const p = s.periodic;
    if (!p || !p.monthly || !p.monthly.labels.length) {
      document.getElementById('chart-strat-monthly').innerHTML =
        '<p style="text-align:center;padding-top:80px;color:#64748b">No data available.</p>';
      return;
    }
    const layout = {template:'plotly_white', margin:{t:10,b:40,l:50,r:10}, yaxis:{title:'Return (%)'}};
    Plotly.newPlot('chart-strat-monthly', [{
      x: p.monthly.labels, y: p.monthly.values, type: 'bar',
      marker: {color: p.monthly.values.map(function(v){return v>=0?'#16a34a':'#dc2626';})}
    }], layout, {responsive:true});
    if (p.yearly && p.yearly.labels.length) {
      Plotly.newPlot('chart-strat-yearly', [{
        x: p.yearly.labels, y: p.yearly.values, type: 'bar',
        marker: {color: p.yearly.values.map(function(v){return v>=0?'#16a34a':'#dc2626';})}
      }], layout, {responsive:true});
    }
  }

  function renderDetailTrades(s) {
    const tbody = document.getElementById('strat-detail-trades-tbody');
    tbody.innerHTML = '';
    const trips = s.round_trips || [];
    if (!trips.length) {
      tbody.innerHTML = '<tr><td colspan="16" style="text-align:center;color:#64748b;padding:20px">No completed round-trip trades.</td></tr>';
      return;
    }

    // Running balance for display (use balance_after if available)
    trips.forEach(function (t) {
      const tr      = document.createElement('tr');
      const pc      = t.net_profit >= 0 ? '#16a34a' : '#dc2626';
      const badge   = t.net_profit >= 0 ? '<span class="badge-win">WIN</span>' : '<span class="badge-loss">LOSS</span>';
      const roeCol  = (t.roe_pct || 0) >= 0 ? '#16a34a' : '#dc2626';
      const mktCol  = (t.mkt_pct || 0) >= 0 ? '#16a34a' : '#dc2626';

      // Reason badge colour
      const reason  = t.reason || '—';
      const reasonColor = reason === 'TP' ? '#16a34a' : reason === 'SL' ? '#dc2626' : '#64748b';

      const grossPnl = t.gross_pnl || 0;
      const grossCol = grossPnl >= 0 ? '#16a34a' : '#dc2626';

      tr.innerHTML =
        '<td style="font-size:0.8rem">' + t.entry_time + '</td>' +
        '<td style="font-size:0.8rem">' + t.exit_time  + '</td>' +
        '<td><span class="strat-side-' + t.side.toLowerCase() + '">' + t.side + '</span></td>' +
        '<td style="font-family:monospace;color:#94a3b8">' + (t.qty != null ? t.qty.toLocaleString(undefined, {maximumFractionDigits:4}) : '—') + '</td>' +
        '<td>$' + t.entry_price.toLocaleString() + '</td>' +
        '<td>$' + t.exit_price.toLocaleString()  + '</td>' +
        '<td style="color:' + grossCol + ';opacity:0.8">' + (grossPnl >= 0 ? '+$' : '-$') + Math.abs(grossPnl).toLocaleString() + '</td>' +
        '<td style="color:#64748b">-$' + (t.total_fees || 0).toLocaleString() + '</td>' +
        '<td style="color:#f59e0b;font-size:0.8rem">-$' + (t.slippage_usd || 0).toLocaleString(undefined, {maximumFractionDigits:4}) + ' <span style="opacity:0.6;font-size:0.7rem">(' + (t.slippage_pct || 0).toFixed(3) + '%)</span></td>' +
        '<td style="color:' + pc + ';font-weight:bold">' + badge + ' ' + (t.net_profit >= 0 ? '+$' : '-$') + Math.abs(t.net_profit).toLocaleString() + '</td>' +
        '<td style="color:' + mktCol + '">' + ((t.mkt_pct || 0) >= 0 ? '+' : '') + (t.mkt_pct || 0).toFixed(2) + '%</td>' +
        '<td>' + (t.duration_days || 0) + 'd</td>' +
        '<td style="font-family:monospace;color:#94a3b8">' + (t.leverage || '—') + 'x</td>' +
        '<td style="color:' + roeCol + ';font-weight:bold">' + ((t.roe_pct || 0) >= 0 ? '+' : '') + (t.roe_pct || 0).toFixed(1) + '%</td>' +
        '<td><span style="color:' + reasonColor + ';font-weight:700;font-size:0.8rem">' + reason + '</span></td>' +
        '<td style="font-family:monospace">$' + (t.balance_after || 0).toLocaleString() + '</td>';
      tbody.appendChild(tr);
    });
  }

  // ── Rulebook tab ──────────────────────────────────────────────────────────

  function renderRulebook(s) {
    var cont = document.getElementById('rulebook-content');
    var mt   = s.metrics    || {};
    var fmt  = s.fmt_metrics || {};

    // ── Compute instant checks (from already-loaded data) ────────────────
    var checks = [];

    function ck(code, tier, label, pass, detail, pts) {
      checks.push({code: code, tier: tier, label: label, pass: pass, detail: detail, pts: pts});
    }

    var W1 = 4, W2 = 5, W3 = 4;

    ck('T1-01', 'T1', 'Sharpe ≥ 0.5',
       mt['Sharpe Ratio'] >= 0.5,
       'Sharpe = ' + (mt['Sharpe Ratio'] || 0).toFixed(2), W1);

    ck('T1-02', 'T1', 'Total Return > 0',
       mt['Total Return'] > 0,
       'Return = ' + ((mt['Total Return'] || 0) >= 0 ? '+' : '') + (mt['Total Return'] || 0).toFixed(2) + '%', W1);

    ck('T1-03', 'T1', 'Max Drawdown < 20%',
       Math.abs(mt['Max Drawdown %'] || 0) < 20,
       'MDD = ' + Math.abs(mt['Max Drawdown %'] || 0).toFixed(2) + '%', W1);

    ck('T1-04', 'T1', 'Win Rate ≥ 40%',
       (mt['Win Rate'] || 0) >= 40,
       'Win Rate = ' + (mt['Win Rate'] || 0).toFixed(1) + '%', W1);

    ck('T1-05', 'T1', 'Profit Factor ≥ 1.0',
       (mt['Profit Factor'] || 0) >= 1.0,
       'PF = ' + (mt['Profit Factor'] || 0).toFixed(2), W1);

    ck('T1-05b', 'T1', 'Trades ≥ 30',
       (mt['Total Trades'] || 0) >= 30,
       'Trades = ' + (mt['Total Trades'] || 0), W1);

    var wdlRaw = fmt['Worst Daily Loss'];
    if (wdlRaw) {
      var wdl = parseFloat(wdlRaw.replace('%', ''));
      ck('T1-06', 'T1', 'Worst Daily Loss ≥ −4%', wdl >= -4,
         'Worst day = ' + wdl.toFixed(2) + '%', W1);
    } else {
      ck('T1-06', 'T1', 'Worst Daily Loss ≥ −4%', null, 'N/A', W1);
    }

    var crRaw = fmt['Cost Ratio'];
    if (crRaw) {
      var cr = parseFloat(crRaw.replace('%', ''));
      ck('T1-07', 'T1', 'Cost Ratio < 30%', cr < 30,
         'Cost ratio = ' + cr.toFixed(1) + '%', W1);
    } else {
      ck('T1-07', 'T1', 'Cost Ratio < 30%', null, 'N/A (zero profit)', W1);
    }

    var dsrRaw = fmt['DSR p-value'];
    if (dsrRaw) {
      var dsrP = parseFloat(dsrRaw);
      ck('T2-04', 'T2', 'DSR p-value < 0.05', dsrP < 0.05,
         'p = ' + dsrP.toFixed(4), W2);
    } else {
      ck('T2-04', 'T2', 'DSR p-value < 0.05', null, 'N/A', W2);
    }

    var gtpRaw = fmt['Monthly GTP'];
    var pfVal  = mt['Profit Factor'] || 0;
    var pfOk   = pfVal >= 1.5;
    if (gtpRaw) {
      var gtpOk = gtpRaw === '∞' || parseFloat(gtpRaw) >= 1.0;
      ck('T2-06', 'T2', 'GTP ≥ 1.0 OR PF ≥ 1.5', gtpOk || pfOk,
         'GTP = ' + gtpRaw + '  |  PF = ' + pfVal.toFixed(2), W2);
    } else {
      ck('T2-06', 'T2', 'GTP ≥ 1.0 OR PF ≥ 1.5', pfOk,
         'GTP = N/A  |  PF = ' + pfVal.toFixed(2), W2);
    }

    var rdRaw = fmt['Regime MDD'];
    if (rdRaw && typeof rdRaw === 'object') {
      var rdVals  = Object.values(rdRaw);
      var rdWorst = Math.min.apply(null, rdVals);
      var rdStr   = Object.entries(rdRaw).map(function(e) {
        return e[0].replace('_', ' ') + ': ' + e[1].toFixed(1) + '%';
      }).join('  ');
      ck('T3-03', 'T3', 'Regime MDD > −30%', rdWorst > -30, rdStr, W3);
    } else {
      ck('T3-03', 'T3', 'Regime MDD > −40%', null, 'N/A', W3);
    }

    var wkdRaw  = fmt['Weekday Sharpe'];
    var wkndRaw = fmt['Weekend Sharpe'];
    if (wkdRaw && wkndRaw) {
      var wkd    = parseFloat(wkdRaw);
      var wknd   = parseFloat(wkndRaw);
      var divPct = Math.abs(wkd) > 0.001 ? Math.abs(wknd - wkd) / Math.abs(wkd) : 999;
      ck('CR-03', 'CR', 'Weekend/Weekday Sharpe divergence ≤ 100%', divPct <= 1.0,
         'Weekday = ' + wkd.toFixed(2) + '  Weekend = ' + wknd.toFixed(2) + '  divergence = ' + (divPct * 100).toFixed(0) + '%', W3);
    } else {
      ck('CR-03', 'CR', 'Weekend/Weekday Sharpe divergence ≤ 100%', null, 'N/A', W3);
    }

    // ── Score ─────────────────────────────────────────────────────────────
    var iScore  = checks.filter(function(c){return c.pass===true;}).reduce(function(a,c){return a+c.pts;},0);
    var iMax    = checks.reduce(function(a,c){return a+c.pts;},0);
    var iPass   = checks.filter(function(c){return c.pass===true;}).length;
    var iNA     = checks.filter(function(c){return c.pass===null;}).length;
    var iTotal  = checks.length - iNA;

    var scoreColor = iScore >= iMax * 0.7 ? '#16a34a' : iScore >= iMax * 0.5 ? '#d97706' : '#dc2626';
    var barPct = Math.round(iScore / iMax * 100);

    // ── HTML ──────────────────────────────────────────────────────────────
    var html = '<div class="rb-wrap">';

    // Score header
    html += '<div class="rb-score-bar">' +
      '<div>' +
        '<div class="rb-score-title">Instant Score <span style="font-size:0.75rem;color:#64748b;font-weight:400">(from loaded data)</span></div>' +
        '<div class="rb-score-num" style="color:' + scoreColor + '">' + iScore + '<span class="rb-score-denom"> / ' + iMax + ' pts</span></div>' +
        '<div class="rb-score-sub">' + iPass + ' / ' + iTotal + ' checks passed' + (iNA ? '  (' + iNA + ' N/A)' : '') + '</div>' +
      '</div>' +
      '<div class="rb-bar-wrap">' +
        '<div class="rb-bar-track"><div class="rb-bar-fill" style="width:' + barPct + '%;background:' + scoreColor + '"></div></div>' +
        '<div style="text-align:right;font-size:0.75rem;color:#94a3b8;margin-top:4px">' + barPct + '% of instant checks</div>' +
      '</div>' +
    '</div>';

    // Tier groups
    var tiers = [
      {key: 'T1', label: 'Tier 1 — Fatal Gates', pts: W1},
      {key: 'T2', label: 'Tier 2 — Quality Gates', pts: W2},
      {key: 'T3', label: 'Tier 3 — Warnings', pts: W3},
      {key: 'CR', label: 'Crypto Pack', pts: W3},
    ];

    tiers.forEach(function(tier) {
      var tChecks = checks.filter(function(c){return c.tier===tier.key;});
      var tPass   = tChecks.filter(function(c){return c.pass===true;}).length;
      var tTotal  = tChecks.filter(function(c){return c.pass!==null;}).length;

      html += '<div class="rb-tier">' +
        '<div class="rb-tier-header"><span>' + tier.label + '</span><span class="rb-tier-count">' + tPass + '/' + tTotal + '</span></div>';

      tChecks.forEach(function(c) {
        var icon, cls;
        if      (c.pass === true)  { icon = '✅'; cls = 'rb-pass'; }
        else if (c.pass === false) { icon = '❌'; cls = 'rb-fail'; }
        else                       { icon = '⚪'; cls = 'rb-na';   }

        html += '<div class="rb-check-row ' + cls + '">' +
          '<span class="rb-check-code">' + c.code + '</span>' +
          '<span class="rb-check-icon">' + icon + '</span>' +
          '<span class="rb-check-label">' + c.label + '</span>' +
          '<span class="rb-check-detail">' + c.detail + '</span>' +
          '<span class="rb-check-pts">+' + c.pts + 'pt</span>' +
        '</div>';
      });

      html += '</div>';
    });

    // Deep validation section
    html += '<div class="rb-deep">' +
      '<div class="rb-deep-header">' +
        '<span>🔬 Deep Validation</span>' +
        '<span class="rb-deep-note">WFO · Lookahead probe · Bootstrap · Regime survival · PBO · Truncation · Crypto Pack</span>' +
      '</div>' +
      '<div class="rb-deep-body">' +
        '<button id="btn-run-validate" class="rb-run-btn" onclick="runDeepValidation(\'' + s.sid + '\')">▶ Run Validation <span style="font-size:0.75rem;opacity:0.7">(quick mode · 30–90 sec)</span></button>' +
        '<div id="rulebook-deep-results"></div>' +
      '</div>' +
    '</div>';

    html += '</div>';
    cont.innerHTML = html;
  }

  window.runDeepValidation = function(strategyId) {
    var btn        = document.getElementById('btn-run-validate');
    var resultsDiv = document.getElementById('rulebook-deep-results');
    if (!btn || !resultsDiv) return;

    btn.disabled    = true;
    btn.innerHTML   = '⏳ Running... <span style="font-size:0.75rem;opacity:0.7">may take 30–90 sec</span>';
    resultsDiv.innerHTML = '<div class="alert-warn" style="margin-top:12px">Running WFO, lookahead probe, bootstrap MC, regime survival — please wait...</div>';

    fetch('/api/validate_strategy?strategy_id=' + encodeURIComponent(strategyId) + '&quick=true')
      .then(function(r) { return r.json(); })
      .then(function(data) {
        btn.disabled  = false;
        btn.innerHTML = '↺ Re-run Validation';
        if (data.error) {
          resultsDiv.innerHTML = '<div class="alert-warn" style="margin-top:12px">Error: ' + data.error + '</div>';
          return;
        }
        renderDeepResults(data, resultsDiv);
      })
      .catch(function(err) {
        btn.disabled  = false;
        btn.innerHTML = '▶ Run Validation';
        resultsDiv.innerHTML = '<div class="alert-warn" style="margin-top:12px">Request failed: ' + err + '</div>';
      });
  };

  // ═══════════════════════════════════════════════════════════════════
  // MULTI-COIN FORGE MODE
  // ═══════════════════════════════════════════════════════════════════

  var _mcData       = null;   // loaded JSON
  var _mcTfFilter   = 'ALL';
  var _mcResults    = [];     // backtest results from server

  // ── File list from server ─────────────────────────────────────────

  function _mcNote(msg, color) {
    var el = document.getElementById('mc-load-note');
    el.textContent = msg; el.style.color = color || '#16a34a';
  }

  function fetchMcForgeFiles() {
    var listEl = document.getElementById('mc-file-list');
    listEl.innerHTML = '<div style="color:#94a3b8;font-size:0.85rem;padding:8px 0">Loading…</div>';
    fetch(API_BASE + '/api/multicoin_forge_files')
      .then(function(r) { return r.json(); })
      .then(function(data) {
        var files = data.files || [];
        listEl.innerHTML = '';
        if (!files.length) {
          listEl.innerHTML = '<div style="color:#94a3b8;font-size:0.85rem;padding:12px 0">' +
            'No <code>multi_forge_*.json</code> files found in <code>strategy_forge/results/</code>. ' +
            'Run <code>multi_forge_search.py</code> first.</div>';
          return;
        }
        var TF_BG = {'5m':'#f3f0ff','15m':'#fdf2f8','1h':'#f0fdf4','4h':'#eff6ff','1d':'#fefce8'};
        var TF_CL = {'5m':'#7c3aed','15m':'#db2777','1h':'#15803d','4h':'#1d4ed8','1d':'#b45309'};
        files.forEach(function(f) {
          var row = document.createElement('div');
          row.style.cssText = 'display:flex;align-items:center;gap:10px;padding:10px 14px;border:1px solid #e2e8f0;border-radius:10px;cursor:pointer;background:#fff;transition:all .15s';
          row.onmouseover = function(){ row.style.borderColor='#2563eb'; row.style.background='#eff6ff'; };
          row.onmouseout  = function(){ row.style.borderColor='#e2e8f0'; row.style.background='#fff'; };

          var tfTags = (f.tfs || []).map(function(tf){
            var bg = TF_BG[tf] || '#f1f5f9';
            var cl = TF_CL[tf] || '#475569';
            return '<span style="background:' + bg + ';color:' + cl + ';font-size:0.7rem;font-weight:800;padding:2px 7px;border-radius:5px">' + tf + '</span>';
          }).join(' ');

          var hitColor = f.hits > 0 ? '#16a34a' : '#dc2626';
          var coinStr  = (f.coins || []).slice(0,6).map(function(c){ return c.replace('USDT',''); }).join(' · ');
          if ((f.coins||[]).length > 6) coinStr += ' + ' + ((f.coins.length - 6)) + ' more';

          row.innerHTML =
            '<span style="font-size:1.4rem">📄</span>' +
            '<div style="flex:1;min-width:0">' +
              '<div style="font-family:monospace;font-size:0.82rem;font-weight:700;color:#1e293b;white-space:nowrap;overflow:hidden;text-overflow:ellipsis">' + f.filename + '</div>' +
              '<div style="font-size:0.75rem;color:#64748b;margin-top:2px">' + (f.run_at || '—') + '  ·  n=' + f.n + '  ·  ' + coinStr + '</div>' +
            '</div>' +
            '<div style="display:flex;align-items:center;gap:6px;flex-shrink:0">' +
              tfTags +
              '<span style="font-size:0.8rem;font-weight:800;color:' + hitColor + ';min-width:50px;text-align:right">' + f.hits + ' hit' + (f.hits !== 1 ? 's' : '') + '</span>' +
            '</div>' +
            '<span style="color:#2563eb;font-size:1rem;flex-shrink:0">›</span>';

          row.addEventListener('click', function() {
            _mcNote('Loading ' + f.filename + '…', '#2563eb');
            listEl.querySelectorAll('div[data-selected]').forEach(function(el){ delete el.dataset.selected; el.style.borderColor='#e2e8f0'; el.style.background='#fff'; });
            row.dataset.selected = '1'; row.style.borderColor='#2563eb'; row.style.background='#eff6ff';
            fetch(API_BASE + '/api/multicoin_forge_load?filename=' + encodeURIComponent(f.filename))
              .then(function(r){ return r.json(); })
              .then(function(data){ loadMcForgeData(data, f.filename); })
              .catch(function(err){ _mcNote('❌ Failed: ' + err.message, '#dc2626'); });
          });
          listEl.appendChild(row);
        });
      })
      .catch(function(err) {
        listEl.innerHTML = '<div style="color:#dc2626;font-size:0.85rem">❌ Could not reach Flask server: ' + err.message + '</div>';
      });
  }

  document.getElementById('mc-refresh-files-btn').addEventListener('click', fetchMcForgeFiles);

  // ── Load & build strategy card grid ──────────────────────────────

  function loadMcForgeData(data, sourceName) {
    _mcData = data;
    var results = data.results || [];
    _mcNote('✅ ' + sourceName + ' — ' + results.length + ' hit' + (results.length !== 1 ? 's' : ''),
            results.length > 0 ? '#16a34a' : '#ca8a04');

    if (results.length === 0) {
      document.getElementById('mc-picker-wrap').style.display = 'none';
      return;
    }

    // Populate coins from JSON
    var coins = data.coins || [];
    var coinWrap = document.getElementById('mc-coin-checkboxes');
    coinWrap.innerHTML = '';
    coins.forEach(function (coin) {
      var lbl = document.createElement('label');
      lbl.style.cssText = 'display:flex;align-items:center;gap:4px;font-size:0.8rem;font-weight:600;color:#475569;cursor:pointer';
      lbl.innerHTML = '<input type="checkbox" class="mc-coin-cb" value="' + coin +
                      '" checked style="accent-color:#2563eb;width:14px;height:14px"> ' + coin;
      coinWrap.appendChild(lbl);
    });

    // Build TF pills
    var tfs = ['ALL'].concat(
      results.map(function(r){ return r.tf; })
             .filter(function(v,i,a){ return a.indexOf(v) === i; }).sort()
    );
    var pillWrap = document.getElementById('mc-tf-pills');
    pillWrap.innerHTML = '';
    _mcTfFilter = 'ALL';
    tfs.forEach(function (tf) {
      var pill = document.createElement('button');
      pill.className = 'filter-pill' + (tf === 'ALL' ? ' fp-active' : '');
      pill.textContent = tf;
      pill.addEventListener('click', function () {
        _mcTfFilter = tf;
        pillWrap.querySelectorAll('.filter-pill').forEach(function(p){
          p.classList.toggle('fp-active', p.textContent === tf);
        });
        buildMcCards(_mcData.results || []);
      });
      pillWrap.appendChild(pill);
    });

    buildMcCards(results);

    document.getElementById('mc-picker-wrap').style.display = '';
    document.getElementById('mc-results').style.display     = 'none';
    document.getElementById('mc-detail-panel').style.display = 'none';
    document.getElementById('mc-run-btn').disabled = false;
    document.getElementById('mc-picker-wrap').scrollIntoView({behavior:'smooth', block:'start'});
  }

  function buildMcCards(allResults) {
    var grid    = document.getElementById('mc-strat-grid');
    var countEl = document.getElementById('mc-card-count');
    grid.innerHTML = '';

    var filtered = allResults.filter(function(r){
      return _mcTfFilter === 'ALL' || r.tf === _mcTfFilter;
    });

    countEl.textContent = filtered.length + ' strateg' + (filtered.length === 1 ? 'y' : 'ies');

    if (filtered.length === 0) {
      grid.innerHTML = '<div class="strat-loading">No strategies for this TF.</div>';
      return;
    }

    var TF_BG = {'5m':'#f3f0ff','15m':'#fdf2f8','1h':'#f0fdf4','4h':'#eff6ff','1d':'#fefce8'};
    var TF_CL = {'5m':'#7c3aed','15m':'#db2777','1h':'#15803d','4h':'#1d4ed8','1d':'#b45309'};

    filtered.forEach(function(r) {
      var shColor = r.sharpe >= 1.5 ? '#16a34a' : r.sharpe >= 1.0 ? '#ca8a04' : '#dc2626';
      var moColor = (r.monthly_roi >= 1.8 && r.monthly_roi <= 4.0) ? '#16a34a' : '#ca8a04';
      var ddColor = r.mdd <= 10 ? '#16a34a' : r.mdd <= 20 ? '#ca8a04' : '#dc2626';
      var tfBg = TF_BG[r.tf] || '#f8fafc';
      var tfCl = TF_CL[r.tf] || '#64748b';

      var filtersStr = (r.filters || []).join(', ') || '—';
      var card = document.createElement('div');
      card.className = 'strat-card';
      card.dataset.rank = r.rank;
      card.innerHTML =
        '<input type="checkbox" class="strat-checkbox mc-strat-cb" data-rank="' + r.rank + '" checked>' +
        '<div class="strat-card-info">' +
          '<div class="strat-card-title">' +
            '<span class="strat-num">#' + r.rank + '</span> ' + r.entry +
          '</div>' +
          '<div class="strat-card-meta">' +
            '<span class="strat-tag" style="background:' + tfBg + ';color:' + tfCl + '">' + r.tf + '</span>' +
            '<span class="strat-tag tf-tag" style="font-size:0.65rem">' + r.exit + '</span>' +
          '</div>' +
          '<div class="strat-card-desc" style="font-size:0.72rem;color:#64748b;margin-top:4px">' + filtersStr + '</div>' +
          '<div class="strat-metrics-row">' +
            '<span class="sm-item"><span class="sm-label">Sharpe</span>' +
              '<span class="sm-val" style="color:' + shColor + '">' + (r.sharpe||0).toFixed(2) + '</span></span>' +
            '<span class="sm-item"><span class="sm-label">Mo ROI</span>' +
              '<span class="sm-val" style="color:' + moColor + '">' + (r.monthly_roi||0).toFixed(2) + '%</span></span>' +
            '<span class="sm-item"><span class="sm-label">MDD</span>' +
              '<span class="sm-val" style="color:' + ddColor + '">' + (r.mdd||0).toFixed(1) + '%</span></span>' +
            '<span class="sm-item"><span class="sm-label">Trades</span>' +
              '<span class="sm-val">' + (r.trades||0) + '</span></span>' +
            '<span class="sm-item"><span class="sm-label">WR</span>' +
              '<span class="sm-val">' + (r.win_rate||0).toFixed(0) + '%</span></span>' +
          '</div>' +
        '</div>';

      var cb = card.querySelector('input[type=checkbox]');
      card.addEventListener('click', function(e) {
        if (e.target === cb) return;
        cb.checked = !cb.checked;
        card.classList.toggle('selected', cb.checked);
      });
      cb.addEventListener('change', function() {
        card.classList.toggle('selected', cb.checked);
      });
      card.classList.toggle('selected', cb.checked);
      grid.appendChild(card);
    });
  }

  // ── Select All / Clear ────────────────────────────────────────────

  document.getElementById('mc-btn-select-all').addEventListener('click', function () {
    document.querySelectorAll('.mc-strat-cb').forEach(function(cb) {
      cb.checked = true;
      cb.closest('.strat-card').classList.add('selected');
    });
  });

  document.getElementById('mc-btn-clear-all').addEventListener('click', function () {
    document.querySelectorAll('.mc-strat-cb').forEach(function(cb) {
      cb.checked = false;
      cb.closest('.strat-card').classList.remove('selected');
    });
  });

  // ── Run Backtest ──────────────────────────────────────────────────

  document.getElementById('mc-run-btn').addEventListener('click', function () {
    var selectedRanks = Array.from(document.querySelectorAll('.mc-strat-cb:checked'))
                             .map(function(cb){ return parseInt(cb.dataset.rank); });
    if (selectedRanks.length === 0) { alert('Select at least one strategy.'); return; }

    var selectedCoins = Array.from(document.querySelectorAll('.mc-coin-cb:checked'))
                             .map(function(cb){ return cb.value; });
    if (selectedCoins.length === 0) { alert('Select at least one coin.'); return; }

    var allResults = _mcData.results || [];
    var dnas = allResults.filter(function(r){ return selectedRanks.indexOf(r.rank) !== -1; })
                         .map(function(r){
                           return {rank:r.rank, entry:r.entry, filters:r.filters||[], exit:r.exit, params:r.params||{}, tf:r.tf};
                         });

    var dateFrom = document.getElementById('mc-date-from').value;
    var dateTo   = document.getElementById('mc-date-to').value;

    document.getElementById('mc-results').style.display = 'none';
    document.getElementById('mc-detail-panel').style.display = 'none';
    document.getElementById('mc-running').style.display = '';

    fetch(API_BASE + '/api/multicoin_backtest', {
      method: 'POST',
      headers: {'Content-Type': 'application/json'},
      body: JSON.stringify({dnas: dnas, coins: selectedCoins, date_from: dateFrom, date_to: dateTo})
    })
      .then(function(r) {
        if (!r.ok) throw new Error('HTTP ' + r.status);
        return r.json();
      })
      .then(function(data) {
        document.getElementById('mc-running').style.display = 'none';
        if (data.error) { alert('Error: ' + data.error); return; }
        _mcResults = data.results || [];
        renderMcResults(_mcResults);
      })
      .catch(function(err) {
        document.getElementById('mc-running').style.display = 'none';
        alert('Request failed: ' + err.message);
      });
  });

  // ── Render results — mirrors renderStrategyResults ────────────────

  var _mcActiveIdx = -1;

  function renderMcResults(results) {
    if (!results.length) {
      alert('No results — no trades in the selected date range or strategy failed.\nCheck that the Flask server can access the dataset for the selected coins.');
      return;
    }

    results.sort(function(a, b){ return b.metrics['Sharpe Ratio'] - a.metrics['Sharpe Ratio']; });

    document.getElementById('mc-results').style.display = '';
    document.getElementById('mc-result-count').textContent = results.length + ' runs';

    // Equity chart
    var traces = results.map(function(s, i) {
      return {
        x: s.equity_times, y: s.equity_cumret,
        name: s.class + ' (' + s.coin + ' ' + s.timeframe + ')',
        type:'scatter', mode:'lines',
        line:{color: PALETTE[i % PALETTE.length], width:1.6}, opacity:0.85
      };
    });
    Plotly.newPlot('chart-mc-compare', traces, {
      template:'plotly_white', hovermode:'x unified',
      yaxis:{title:'Cumulative Return', tickformat:'.1%'},
      xaxis:{title:'Date'},
      legend:{orientation:'h', y:1.14, font:{size:10}},
      margin:{t:20, b:50, l:70, r:20}
    }, {responsive:true});

    // Ranking table
    var tbody = document.getElementById('mc-rank-tbody');
    tbody.innerHTML = '';
    results.forEach(function(s, i) {
      var mt = s.metrics;
      var tr = document.createElement('tr');
      tr.style.cursor = 'pointer';
      tr.dataset.idx  = i;
      var retColor = mt['Total Return']  >= 0 ? '#16a34a' : '#dc2626';
      var shColor  = mt['Sharpe Ratio']  >= 1 ? '#16a34a' : '#ca8a04';
      var wrColor  = mt['Win Rate']      >= 50 ? '#16a34a' : '#ca8a04';
      var pfColor  = mt['Profit Factor'] >= 1  ? '#16a34a' : '#dc2626';
      tr.innerHTML =
        '<td><strong style="color:' + PALETTE[i % PALETTE.length] + '">● </strong>' +
        '<span style="color:#6b7280;font-size:0.8em;font-family:monospace">#' + (s.rank || i+1) + '</span> ' +
        '<strong>' + s.class + '</strong></td>' +
        '<td>' + s.coin + '</td>' +
        '<td>' + s.timeframe + '</td>' +
        '<td style="color:' + retColor + '">' + (mt['Total Return'] >= 0 ? '+' : '') + mt['Total Return'].toFixed(1) + '%</td>' +
        '<td style="color:' + shColor  + '">' + mt['Sharpe Ratio'].toFixed(2) + '</td>' +
        '<td style="color:' + shColor  + '">' + (mt['Sortino Ratio'] || 0).toFixed(2) + '</td>' +
        '<td style="color:#dc2626">'   + Math.abs(mt['Max Drawdown %']).toFixed(1) + '%</td>' +
        '<td style="color:' + wrColor + '">' + mt['Win Rate'].toFixed(1) + '%</td>' +
        '<td>' + mt['Total Trades'] + '</td>' +
        '<td style="font-family:monospace;color:#94a3b8">' + (s.leverage || '—') + 'x</td>' +
        '<td style="color:' + pfColor + '">' + (mt['Profit Factor'] || 0).toFixed(2) + '</td>';
      tr.addEventListener('click', function () {
        document.querySelectorAll('#mc-rank-tbody tr').forEach(function(r){ r.classList.remove('row-active'); });
        tr.classList.add('row-active');
        showMcDetail(s, i);
      });
      tbody.appendChild(tr);
    });

    document.getElementById('mc-results').scrollIntoView({behavior:'smooth', block:'start'});
  }

  // ── Detail panel — mirrors showStrategyDetail ─────────────────────

  document.getElementById('mc-close-detail').addEventListener('click', function () {
    document.getElementById('mc-detail-panel').style.display = 'none';
    document.querySelectorAll('#mc-rank-tbody tr').forEach(function(r){ r.classList.remove('row-active'); });
  });

  function showMcDetail(s, colorIdx) {
    var panel = document.getElementById('mc-detail-panel');
    panel.style.display = '';
    _mcActiveIdx = colorIdx;

    document.getElementById('mc-detail-title').textContent = s.class;
    document.getElementById('mc-detail-meta').textContent  =
      s.desc + '  |  ' + s.coin + ' ' + s.timeframe + '  |  Initial: $' + s.initial_balance.toLocaleString();

    // Reset sub-tabs
    panel.querySelectorAll('.tab-btn[data-mctab]').forEach(function(b){ b.classList.remove('active'); });
    panel.querySelectorAll('[id^="stab-mc-"]').forEach(function(c){ c.classList.remove('active'); });
    panel.querySelector('[data-mctab="mc-metrics"]').classList.add('active');
    document.getElementById('stab-mc-metrics').classList.add('active');

    panel.querySelectorAll('.tab-btn[data-mctab]').forEach(function(btn) {
      btn.onclick = function () {
        panel.querySelectorAll('.tab-btn[data-mctab]').forEach(function(b){ b.classList.remove('active'); });
        panel.querySelectorAll('[id^="stab-mc-"]').forEach(function(c){ c.classList.remove('active'); });
        btn.classList.add('active');
        document.getElementById('stab-' + btn.dataset.mctab).classList.add('active');
        if (btn.dataset.mctab === 'mc-equity')   renderMcDetailEquity(s, colorIdx);
        if (btn.dataset.mctab === 'mc-price')    renderMcDetailPrice(s, colorIdx);
        if (btn.dataset.mctab === 'mc-periodic') renderMcDetailPeriodic(s);
        if (btn.dataset.mctab === 'mc-trades')   renderMcDetailTrades(s);
      };
    });

    renderMcDetailMetrics(s);
    panel.scrollIntoView({behavior:'smooth', block:'start'});
  }

  function renderMcDetailMetrics(s) {
    var grid = document.getElementById('mc-metrics-grid');
    var mt   = s.metrics;
    var fmt  = s.fmt_metrics || {};
    var blocks = [
      {icon:'💰', title:'Account', items:[
        ['Initial Balance', fmt['Initial Balance'] || '—'],
        ['Final Balance',   fmt['Final Balance']   || '—'],
        ['Net Profit',      fmt['Net Profit']      || '—'],
        ['Total Fees',      fmt['Total Fees']      || '—'],
        ['Leverage',        (s.leverage || '—') + 'x'],
      ]},
      {icon:'⚡', title:'Edge & Efficiency', items:[
        ['Total Return',    (mt['Total Return']  >= 0 ? '+' : '') + mt['Total Return'].toFixed(2)  + '%'],
        ['Annual Return',   (mt['Annual Return'] >= 0 ? '+' : '') + (mt['Annual Return']||0).toFixed(2) + '%'],
        ['Sharpe Ratio',    mt['Sharpe Ratio'].toFixed(2)],
        ['Sortino Ratio',   (mt['Sortino Ratio']||0).toFixed(2)],
        ['Calmar Ratio',    (mt['Calmar Ratio']||0).toFixed(2)],
        ['Profit Factor',   (mt['Profit Factor']||0).toFixed(2)],
        ['Expectancy',      fmt['Expectancy'] || '—'],
        ['Max Drawdown',    Math.abs(mt['Max Drawdown %']).toFixed(2) + '%'],
      ]},
      {icon:'📊', title:'Trade Statistics', items:[
        ['Total Trades',    mt['Total Trades']],
        ['Win Rate',        mt['Win Rate'].toFixed(1) + '%'],
        ['Avg Win',         fmt['Avg Win']    || '—'],
        ['Avg Loss',        fmt['Avg Loss']   || '—'],
        ['Best Trade',      fmt['Best Trade'] || '—'],
        ['Worst Trade',     fmt['Worst Trade']|| '—'],
        ['Avg Duration',    fmt['Avg Duration (days)'] || '—'],
      ]},
    ];
    grid.innerHTML = '';
    blocks.forEach(function(block) {
      var sec = document.createElement('section');
      sec.className = 'card'; sec.style.marginTop = '0';
      var rows = block.items.map(function(item){
        return '<div class="metric-row"><span class="ml">' + item[0] + '</span><span class="mv">' + item[1] + '</span></div>';
      }).join('');
      sec.innerHTML = '<div class="card-header"><span class="icon">' + block.icon + '</span><h2>' + block.title + '</h2></div>' +
                      '<div class="metric-list">' + rows + '</div>';
      grid.appendChild(sec);
    });
  }

  function renderMcDetailEquity(s, colorIdx) {
    Plotly.newPlot('chart-mc-detail-equity', [{
      x:s.equity_times, y:s.equity_cumret, name:s.class,
      type:'scatter', mode:'lines',
      line:{color:PALETTE[colorIdx % PALETTE.length], width:2},
      fill:'tozeroy', fillcolor:'rgba(59,130,246,.06)'
    }], {
      template:'plotly_white', hovermode:'x unified',
      yaxis:{title:'Cumulative Return', tickformat:'.1%'},
      xaxis:{title:'Date'}, margin:{t:20,b:50,l:70,r:20}
    }, {responsive:true});
  }

  function renderMcDetailPrice(s, colorIdx) {
    var trips  = s.round_trips || [];
    var longs  = trips.filter(function(t){ return t.side === 'LONG'; });
    var shorts = trips.filter(function(t){ return t.side === 'SHORT'; });
    Plotly.newPlot('chart-mc-detail-price', [
      {x:s.equity_times, y:s.equity_prices, name:s.coin + ' Close', type:'scatter', mode:'lines',
       line:{color:'#94a3b8', width:1.5}},
      {x:longs.map(function(t){return t.entry_time;}), y:longs.map(function(t){return t.entry_price;}),
       name:'Long Entry', mode:'markers', marker:{color:'#16a34a',size:12,symbol:'triangle-up',line:{color:'#fff',width:1}}},
      {x:shorts.map(function(t){return t.entry_time;}), y:shorts.map(function(t){return t.entry_price;}),
       name:'Short Entry', mode:'markers', marker:{color:'#dc2626',size:12,symbol:'triangle-down',line:{color:'#fff',width:1}}},
      {x:longs.map(function(t){return t.exit_time;}), y:longs.map(function(t){return t.exit_price;}),
       name:'Exit Long', mode:'markers', marker:{color:'#16a34a',size:11,symbol:'x',line:{color:'#16a34a',width:2}}},
      {x:shorts.map(function(t){return t.exit_time;}), y:shorts.map(function(t){return t.exit_price;}),
       name:'Exit Short', mode:'markers', marker:{color:'#dc2626',size:11,symbol:'x',line:{color:'#dc2626',width:2}}}
    ], {
      template:'plotly_white', hovermode:'x unified',
      yaxis:{title:'Price (USD)', tickprefix:'$'},
      xaxis:{title:'Date'},
      legend:{orientation:'h', y:1.14, font:{size:11}},
      margin:{t:20,b:50,l:80,r:20}
    }, {responsive:true});
  }

  function renderMcDetailPeriodic(s) {
    var p = s.periodic;
    if (!p || !p.monthly || !p.monthly.labels.length) {
      document.getElementById('chart-mc-monthly').innerHTML =
        '<p style="text-align:center;padding-top:80px;color:#64748b">No data.</p>';
      return;
    }
    var layout = {template:'plotly_white', margin:{t:10,b:40,l:50,r:10}, yaxis:{title:'Return (%)'}};
    Plotly.newPlot('chart-mc-monthly', [{
      x:p.monthly.labels, y:p.monthly.values, type:'bar',
      marker:{color:p.monthly.values.map(function(v){return v>=0?'#16a34a':'#dc2626';})}
    }], layout, {responsive:true});
    if (p.yearly && p.yearly.labels.length) {
      Plotly.newPlot('chart-mc-yearly', [{
        x:p.yearly.labels, y:p.yearly.values, type:'bar',
        marker:{color:p.yearly.values.map(function(v){return v>=0?'#16a34a':'#dc2626';})}
      }], layout, {responsive:true});
    }
  }

  function renderMcDetailTrades(s) {
    var tbody = document.getElementById('mc-detail-trades-tbody');
    tbody.innerHTML = '';
    var trips = s.round_trips || [];
    if (!trips.length) {
      tbody.innerHTML = '<tr><td colspan="16" style="text-align:center;color:#64748b;padding:20px">No completed round-trip trades.</td></tr>';
      return;
    }
    trips.forEach(function(t) {
      var tr     = document.createElement('tr');
      var pc     = t.net_profit >= 0 ? '#16a34a' : '#dc2626';
      var badge  = t.net_profit >= 0 ? '<span class="badge-win">WIN</span>' : '<span class="badge-loss">LOSS</span>';
      var roeCol = (t.roe_pct  || 0) >= 0 ? '#16a34a' : '#dc2626';
      var mktCol = (t.mkt_pct  || 0) >= 0 ? '#16a34a' : '#dc2626';
      var reason = t.reason || '—';
      var reasonColor = reason === 'TP' ? '#16a34a' : reason === 'SL' ? '#dc2626' : '#64748b';
      var grossPnl = t.gross_pnl || 0;
      tr.innerHTML =
        '<td style="font-size:0.8rem">' + t.entry_time + '</td>' +
        '<td style="font-size:0.8rem">' + t.exit_time  + '</td>' +
        '<td><span class="strat-side-' + t.side.toLowerCase() + '">' + t.side + '</span></td>' +
        '<td style="font-family:monospace;color:#94a3b8">' + (t.qty != null ? t.qty.toLocaleString(undefined, {maximumFractionDigits:4}) : '—') + '</td>' +
        '<td>$' + t.entry_price.toLocaleString() + '</td>' +
        '<td>$' + t.exit_price.toLocaleString()  + '</td>' +
        '<td style="color:' + (grossPnl>=0?'#16a34a':'#dc2626') + ';opacity:0.8">' + (grossPnl>=0?'+$':'-$') + Math.abs(grossPnl).toLocaleString() + '</td>' +
        '<td style="color:#64748b">-$' + (t.total_fees||0).toLocaleString() + '</td>' +
        '<td style="color:#f59e0b;font-size:0.8rem">-$' + (t.slippage_usd||0).toLocaleString(undefined,{maximumFractionDigits:4}) + '</td>' +
        '<td style="color:' + pc + ';font-weight:bold">' + badge + ' ' + (t.net_profit>=0?'+$':'-$') + Math.abs(t.net_profit).toLocaleString() + '</td>' +
        '<td style="color:' + mktCol + '">' + ((t.mkt_pct||0)>=0?'+':'') + (t.mkt_pct||0).toFixed(2) + '%</td>' +
        '<td>' + (t.duration_days||0) + 'd</td>' +
        '<td style="font-family:monospace;color:#94a3b8">' + (t.leverage||'—') + 'x</td>' +
        '<td style="color:' + roeCol + ';font-weight:bold">' + ((t.roe_pct||0)>=0?'+':'') + (t.roe_pct||0).toFixed(1) + '%</td>' +
        '<td><span style="color:' + reasonColor + ';font-weight:700;font-size:0.8rem">' + reason + '</span></td>' +
        '<td style="font-family:monospace">$' + (t.balance_after||0).toLocaleString() + '</td>';
      tbody.appendChild(tr);
    });
  }

  function renderDeepResults(data, container) {
    var checks  = data.checks || [];
    var score   = data.score   || 0;
    var maxSc   = data.max_score || 100;
    var verdict = data.verdict  || '—';
    var pct     = data.pct      || 0;

    var verdictColor = verdict === 'APPROVED' ? '#16a34a' : '#dc2626';
    var scoreColor   = pct >= 70 ? '#16a34a' : pct >= 50 ? '#d97706' : '#dc2626';

    var html = '<div class="rb-deep-result">' +
      '<div class="rb-dr-header">' +
        '<span class="rb-dr-verdict" style="color:' + verdictColor + '">' + verdict + '</span>' +
        '<span class="rb-dr-score" style="color:' + scoreColor + '">' + score + ' / ' + maxSc.toFixed(0) + ' pts &nbsp;(' + pct.toFixed(1) + '%)</span>' +
      '</div>';

    var deepCodes = ['T0-01','T1-08','T1-09','T1-10','T2-01','T2-02','T2-03','T2-05','T3-01','T3-02','T3-05','CR-01','CR-02','CR-03'];
    var deepChecks = checks.filter(function(c){ return deepCodes.indexOf(c.code) !== -1; });

    if (deepChecks.length) {
      deepChecks.forEach(function(c) {
        var icon = c.passed ? '✅' : '❌';
        var cls  = c.passed ? 'rb-pass' : 'rb-fail';
        html += '<div class="rb-check-row ' + cls + '">' +
          '<span class="rb-check-code">' + c.code + '</span>' +
          '<span class="rb-check-icon">' + icon + '</span>' +
          '<span class="rb-check-label" style="flex:1.5">' + (c.details || '') + '</span>' +
          '<span class="rb-check-pts">+' + (c.score || 0).toFixed(0) + 'pt</span>' +
        '</div>';
      });
    }

    html += '</div>';
    container.innerHTML = html;
  }

});
