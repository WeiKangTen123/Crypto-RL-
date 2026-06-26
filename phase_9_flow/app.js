/* app.js — loads live counts from scan_results.json (if served via Flask)
   and falls back gracefully to the hardcoded HTML values. */

const SCAN_URL  = '/api/scan_summary';   // Flask endpoint (Phase 6)
const FINETUNE_URL = '/.gemini/skills/crypto-strategy-tuner/data/scan_results.json';

/* ── Attempt to load live data ────────────────────────────────────── */
async function loadLiveData() {
  try {
    // Try relative path (works when opened via Flask)
    const res = await fetch(FINETUNE_URL, { cache: 'no-store' });
    if (!res.ok) throw new Error('no data');
    const data = await res.json();
    applyData(data);
  } catch {
    // Silently keep hardcoded HTML values — no network errors shown
  }
}

function applyData(d) {
  const set = (id, val) => {
    const el = document.getElementById(id);
    if (el && val !== undefined) el.textContent = val;
  };

  set('cnt-good',      d.GOOD     ?? d.good);
  set('cnt-mediocre',  d.MEDIOCRE ?? d.mediocre);
  set('cnt-bad',       d.BAD      ?? d.bad);
  set('cnt-total',     d.total);
  set('grade-good',    d.GOOD     ?? d.good);
  set('grade-mediocre',d.MEDIOCRE ?? d.mediocre);
  set('grade-bad',     d.BAD      ?? d.bad);

  if (d.scanned_at) {
    const ts = d.scanned_at.slice(0, 16).replace('T', ' ');
    set('scan-time', `Last scan: ${ts}`);
  }
}

/* ── Hover tooltips on intake nodes ──────────────────────────────── */
const TIPS = {
  'tip-web':   'Pro model required for web search. Flash model falls back to queue-only mode.',
  'tip-queue': 'QUEUED cards are processed in order of interest: High first. Cards with NEED: lines in Data Engineer Request are BLOCKED.',
  'tip-data':  'known_data_gaps.md lists partial gaps — NOT unusable pairs. All 5 coins usable across all 5 TFs. 30m exists but unused.',
};

function initTooltips() {
  const tooltip = document.createElement('div');
  tooltip.style.cssText = `
    position: fixed; z-index: 9999; max-width: 260px;
    background: #0f1623; border: 1px solid #2d4060;
    border-radius: 7px; padding: 8px 12px;
    font-size: 11px; color: #94a3b8; line-height: 1.5;
    pointer-events: none; opacity: 0;
    transition: opacity 0.15s; box-shadow: 0 4px 20px rgba(0,0,0,.5);
  `;
  document.body.appendChild(tooltip);

  document.querySelectorAll('[data-tip]').forEach(el => {
    el.style.cursor = 'default';
    el.addEventListener('mouseenter', e => {
      const key = el.dataset.tip;
      if (!TIPS[key]) return;
      tooltip.textContent = TIPS[key];
      tooltip.style.opacity = '1';
    });
    el.addEventListener('mousemove', e => {
      tooltip.style.left = (e.clientX + 14) + 'px';
      tooltip.style.top  = (e.clientY + 14) + 'px';
    });
    el.addEventListener('mouseleave', () => {
      tooltip.style.opacity = '0';
    });
  });
}

/* ── Stage click expand ───────────────────────────────────────────── */
const STAGE_DETAIL = {
  '1/8': 'Extract from card YAML: coins (primary = first listed), timeframes (primary = first listed), Minimum history. Check for NEED: lines in Data Engineer Request — BLOCKED if present.',
  '2/8': 'Pre-build checklist: run "grep \\"^def \\" library.py" to see 43 available functions. Skim 1–2 similar strategies. Write strategy.py with SIGNAL_PARAMS frozenset, OPTIMIZATION_RANGES dict, inline regime masks (NO check_regime() method). super().__init__() auto-assigns all kwargs via setattr.',
  '3/8': 'Run Python AST check: python -c "import ast; ast.parse(open(\'file.py\').read())". Fix all syntax errors and broken imports before proceeding.',
  '4/8': 'Signal Sanity: call generate_signals() on 1 month of data, print (signal==1).sum() and (signal==-1).sum(). If BOTH are 0 → impossible condition (fix before engine). Verify manage_trade returns only: SL, TP, TS, EXIT, REVERSE, HOLD, SKIP, ADD.',
  '5/8': '① Baseline backtest (default params, primary coin/TF, date_from by TF). ② Register in settings.py NOW with defaults. ③ Run finetune.py --strategy_id {id}. ④ Final backtest with Optuna best params. ⑤ Cross-asset (same TF, other coins from card). ⑥ Write dev report with finetuned metrics.',
  '6/8': 'Walk-Forward Optimization: 4 sliding windows across the date range. Tests stability of the OPTIMIZED strategy (Optuna best from Stage 5). Fail = AUTOPSY. WFO does NOT run Optuna — it only tests stability.',
  '7/8': 'Probability of Backtest Overfitting. Threshold: PBO < 0.40. Uses CPCV (Combinatorial Purged Cross-Validation). Fail = AUTOPSY + card REJECTED.',
  '8/8': 'Verify settings.py has Optuna best params from Stage 5 (do NOT overwrite). Sync metrics to Obsidian via sync_backtest_to_obsidian.py. Append Implementation Metadata Block to Candidate Card. Notify @crypto-strategy-tuner.',
};

function initStageExpand() {
  document.querySelectorAll('.stage').forEach(el => {
    el.title = 'Click for detail';
    el.style.cursor = 'pointer';
    el.addEventListener('click', () => {
      const num = el.querySelector('.stage__num')?.textContent;
      if (!num || !STAGE_DETAIL[num]) return;

      // toggle inline detail
      let detail = el.querySelector('.stage__detail');
      if (detail) {
        detail.remove();
        el.style.maxWidth = '130px';
        return;
      }
      detail = document.createElement('div');
      detail.className = 'stage__detail';
      detail.style.cssText = `
        font-size: 10px; color: #64748b; margin-top: 6px;
        border-top: 1px solid rgba(99,102,241,.2); padding-top: 6px;
        line-height: 1.5;
      `;
      detail.textContent = STAGE_DETAIL[num];
      el.appendChild(detail);
      el.style.maxWidth = '280px';
    });
  });
}

/* ── Grade counter animate-in ─────────────────────────────────────── */
function animateCounters() {
  document.querySelectorAll('.grade__count, .counter__n').forEach(el => {
    const target = parseInt(el.textContent, 10);
    if (isNaN(target) || target < 2) return;
    let current = 0;
    const step = Math.ceil(target / 30);
    const timer = setInterval(() => {
      current = Math.min(current + step, target);
      el.textContent = current;
      if (current >= target) clearInterval(timer);
    }, 25);
  });
}

/* ── Tab navigation ───────────────────────────────────────────────── */
function initTabs() {
  const btns   = document.querySelectorAll('.tab-btn');
  const panels = document.querySelectorAll('.tab-panel');

  btns.forEach(btn => {
    btn.addEventListener('click', () => {
      btns.forEach(b   => b.classList.remove('tab-btn--active'));
      panels.forEach(p => p.classList.remove('tab-panel--active'));
      btn.classList.add('tab-btn--active');
      const panel = document.getElementById('tab-' + btn.dataset.tab);
      if (panel) panel.classList.add('tab-panel--active');
      // scroll canvas back to top on tab switch
      window.scrollTo({ top: document.querySelector('.tab-nav').offsetTop - 4, behavior: 'smooth' });
    });
  });
}

/* ── Init ─────────────────────────────────────────────────────────── */
document.addEventListener('DOMContentLoaded', () => {
  loadLiveData();
  initTooltips();
  initStageExpand();
  initTabs();
  setTimeout(animateCounters, 200);
});
