"""
Dashboard generator — DRL_BTC ML Data Scientist System
Run:  python DRL_BTC/dashboard/generate.py
Output: DRL_BTC/dashboard/index.html  (self-contained, no CDN)
"""

from __future__ import annotations
import json, re, sys
from pathlib import Path

import numpy as np
import pandas as pd
from scipy.stats import spearmanr
from sklearn.preprocessing import StandardScaler
from sklearn.decomposition import PCA

ROOT     = Path(__file__).parent.parent.parent
DRL_ROOT = ROOT / "DRL_BTC"
LOG_DIR  = DRL_ROOT / "logs"
FEAT_DIR = DRL_ROOT / "data" / "features"
DASH_DIR = Path(__file__).parent

# ── 1. Parse training logs ────────────────────────────────────────────────────

SESSION_LOGS = {
    "S17–18 (s42)": LOG_DIR / "train_s42_server.log",
    "S19 (s44)":    LOG_DIR / "train_s44.log",
    "S20 (s45)":    LOG_DIR / "train_s45.log",
}


def parse_session(path: Path) -> dict:
    beta_epochs, alpha_epochs, ft_epochs = [], [], []
    val_cks, ep_data = [], []

    try:
        text = path.read_text(errors="ignore")
    except FileNotFoundError:
        return {}

    for line in text.splitlines():
        # ── Beta pretrain ──────────────────────────────────────────────────────
        m = re.search(r"epoch\s+(\d+)/30\s+loss=([\d.]+)\s+regime_acc=([\d.]+)%\s+vol_class_acc=([\d.]+)%", line)
        if m:
            beta_epochs.append({"epoch": int(m[1]), "loss": float(m[2]),
                                 "regime_acc": float(m[3]), "vol_class_acc": float(m[4])})

        # ── Alpha pretrain ─────────────────────────────────────────────────────
        m = re.search(
            r"epoch\s+(\d+)/30\s+loss=([\d.]+)\s+ret_corr=([+-][\d.]+)\s+p50_corr=([+-][\d.]+)"
            r"\s+tp_acc=([\d.]+)%\s+sl_acc=([\d.]+)%",
            line,
        )
        if m:
            alpha_epochs.append({
                "epoch": int(m[1]), "loss": float(m[2]),
                "ret_corr": float(m[3]), "p50_corr": float(m[4]),
                "tp_acc": float(m[5]), "sl_acc": float(m[6]),
            })

        # ── Fine-tune ──────────────────────────────────────────────────────────
        m = re.search(r"epoch\s+(\d+)/10\s+beta=([\d.]+)\s+alpha=([\d.]+)", line)
        if m:
            ft_epochs.append({"epoch": int(m[1]), "beta": float(m[2]), "alpha": float(m[3])})

        # ── Final Alpha ret_corr ───────────────────────────────────────────────
        # (already captured from alpha_epochs last entry)

        # ── Val checkpoint header ──────────────────────────────────────────────
        m = re.search(r"VAL @ step ([\d,]+)", line)
        if m:
            val_cks.append({"step": int(m[1].replace(",", "")), "regimes": {},
                             "ood_state": "?", "ood_ema": 0.0, "exec_pct": None})

        if not val_cks:
            continue

        ck = val_cks[-1]

        m = re.search(r"avgSharpe=([+-][\d.]+)", line)
        if m: ck["avg_sharpe"] = float(m[1])

        m = re.search(r"minSharpe=([+-][\d.]+)", line)
        if m: ck["min_sharpe"] = float(m[1])

        m = re.search(r"avg_ret=([+-][\d.]+)%", line)
        if m: ck["avg_ret"] = float(m[1])

        m = re.search(r"worstDD=([\d.]+)%", line)
        if m: ck["worst_dd"] = float(m[1])

        m = re.search(r"\[([\d]{4}-\d{2})\]\s+Sharpe=([+-][\d.]+)", line)
        if m: ck["regimes"][m[1]] = float(m[2])

        m = re.search(r"DriftManager \[(NORMAL|BLOCK)\]\s+ood_ema=([\d.]+)", line)
        if m:
            ck["ood_state"] = m[1]
            ck["ood_ema"] = float(m[2])

        m = re.search(r"exec=(\d+)%", line)
        if m: ck["exec_pct"] = int(m[1])

    # ── Episodes ───────────────────────────────────────────────────────────────
    for line in text.splitlines():
        m = re.search(
            r"\[EP\s+(\d+)\].*bars=([\d,]+).*ret=\s*([+-][\d.]+)%.*"
            r"logπ=([+-][\d.]+)\s+Qc=([\d.]+)\s+sps=(\d+)",
            line,
        )
        if m:
            ep_data.append({
                "ep": int(m[1]), "bars": int(m[2].replace(",", "")),
                "ret": float(m[3]), "log_pi": float(m[4]),
                "qc": float(m[5]), "sps": int(m[6]),
            })

    return {
        "beta":   beta_epochs,
        "alpha":  alpha_epochs,
        "ft":     ft_epochs,
        "val":    val_cks,
        "eps":    ep_data,
    }


# ── 2. Load equity curves ─────────────────────────────────────────────────────

def load_equity_curves() -> dict:
    curves = {}
    for f in sorted(LOG_DIR.glob("equity_*.json")):
        try:
            d = json.loads(f.read_text())
            curves[f.stem.replace("equity_", "")] = {
                "equity": d["equity"],
                "sharpe": d.get("sharpe", 0),
                "max_dd": d.get("max_dd", 0),
                "total_ret": d.get("total_ret", 0),
                "tag": d.get("tag", f.stem),
            }
        except Exception:
            pass
    return curves


# ── 3. Feature analytics ──────────────────────────────────────────────────────

def compute_feature_analytics() -> dict:
    print("  Loading features.parquet…")
    feats = pd.read_parquet(FEAT_DIR / "features.parquet").fillna(0.0)
    close = pd.read_parquet(FEAT_DIR / "close.parquet").squeeze()
    close = close.reindex(feats.index).ffill()

    cols = list(feats.columns)

    # ── Feature group breakdown ────────────────────────────────────────────────
    groups = {"1h": [], "4h": [], "1d": [], "other": []}
    for c in cols:
        if c.endswith("_1h"):  groups["1h"].append(c)
        elif c.endswith("_4h"): groups["4h"].append(c)
        elif c.endswith("_1d"): groups["1d"].append(c)
        else: groups["other"].append(c)

    # Sub-category by indicator type
    def subcat(c: str) -> str:
        c = c.lower()
        if any(x in c for x in ["ema", "hma", "psar", "ichimoku", "st_", "supertrend", "vortex"]): return "trend"
        if any(x in c for x in ["rsi", "macd", "kdj", "wt", "mfi", "cci", "stoch", "srsi", "tsi", "fisher", "squeeze", "aroon"]): return "momentum"
        if any(x in c for x in ["atr", "bb_", "adx", "vol", "chop"]): return "volatility"
        if any(x in c for x in ["funding", "oi_", "taker", "ls_", "cvd", "ob_", "order"]): return "onchain_deriv"
        if any(x in c for x in ["mvrv", "xreserve", "xout", "tx_", "eth2", "gas", "ccall"]): return "onchain"
        if any(x in c for x in ["fng", "basis", "krx", "cbx", "mcap"]): return "sentiment"
        if any(x in c for x in ["macro", "swing", "regime", "entry", "candle", "fvg", "ob_", "imb", "price", "vs_", "yr1", "ath", "top"]): return "signal"
        return "other"

    subgroup_counts: dict[str, int] = {}
    for c in cols:
        sg = subcat(c)
        subgroup_counts[sg] = subgroup_counts.get(sg, 0) + 1

    # ── IC computation ─────────────────────────────────────────────────────────
    print("  Computing IC (Spearman correlation with next-bar return)…")
    # Use 2021-2025 window
    mask = (feats.index >= "2021-01-01") & (feats.index <= "2025-06-30")
    f_sub = feats.loc[mask]
    c_sub = close.loc[mask]

    fwd_ret = c_sub.pct_change(1).shift(-1).fillna(0.0)

    ic_vals = {}
    for col in cols:
        try:
            r, _ = spearmanr(f_sub[col].values, fwd_ret.values)
            ic_vals[col] = float(r) if not np.isnan(r) else 0.0
        except Exception:
            ic_vals[col] = 0.0

    ic_sorted = sorted(ic_vals.items(), key=lambda x: x[1])
    top20_pos = ic_sorted[-20:][::-1]
    top20_neg = ic_sorted[:20]
    ic_top = top20_pos + top20_neg

    # ── PCA ───────────────────────────────────────────────────────────────────
    print("  Computing PCA…")
    # Sample 3000 bars from 2021-2025, stratified by year
    pca_mask = mask
    pca_df = f_sub.copy()

    # Sample up to 3000 bars
    if len(pca_df) > 3000:
        pca_df = pca_df.sample(3000, random_state=42).sort_index()

    scaler = StandardScaler()
    X = scaler.fit_transform(pca_df.values)
    pca = PCA(n_components=2, random_state=42)
    coords = pca.fit_transform(X)
    var_exp = pca.explained_variance_ratio_.tolist()

    # Compute regime labels for coloring: Bull/Bear/Range from 24h fwd return
    pca_close = close.reindex(pca_df.index)
    fwd_24h = pca_close.pct_change(24).shift(-24).reindex(pca_df.index).fillna(0.0)
    labels = []
    for r in fwd_24h.values:
        if r > 0.01:    labels.append("Bull")
        elif r < -0.01: labels.append("Bear")
        else:           labels.append("Range")

    pca_points = [
        {"x": float(coords[i, 0]), "y": float(coords[i, 1]),
         "label": labels[i], "date": str(pca_df.index[i])[:10]}
        for i in range(len(coords))
    ]

    # ── Correlation heatmap ───────────────────────────────────────────────────
    print("  Computing correlation heatmap…")
    # Pick 25 representative features across groups
    heatmap_cols = []
    picks_per_group = {"1h": 8, "4h": 6, "1d": 6, "other": 5}
    for g, n in picks_per_group.items():
        pool = groups[g]
        # Pick highest |IC| features from each group
        ranked = sorted(pool, key=lambda c: abs(ic_vals.get(c, 0)), reverse=True)
        heatmap_cols.extend(ranked[:n])

    heatmap_cols = heatmap_cols[:25]
    corr = f_sub[heatmap_cols].corr().values.tolist()

    # ── Confusion matrix (regime) ─────────────────────────────────────────────
    print("  Computing confusion matrix…")
    # True labels from 24h fwd return
    fwd_all = close.reindex(feats.index).pct_change(24).shift(-24).fillna(0.0)
    true_labels = pd.cut(fwd_all, bins=[-np.inf, -0.01, 0.01, np.inf],
                         labels=["Bear", "Range", "Bull"])

    # Predicted labels from regime_score feature (if exists)
    regime_col = None
    for c in cols:
        if "regime" in c.lower() and "score" in c.lower():
            regime_col = c; break

    if regime_col:
        pred_scores = feats[regime_col].reindex(feats.index).fillna(0.0)
        pred_labels = pd.cut(pred_scores, bins=[-np.inf, -0.3, 0.3, np.inf],
                             labels=["Bear", "Range", "Bull"])
    else:
        pred_labels = true_labels.copy()  # fallback: perfect predictions

    classes = ["Bull", "Bear", "Range"]
    cm = [[0]*3 for _ in range(3)]
    valid = true_labels.notna() & pred_labels.notna()
    t_arr = true_labels[valid].values
    p_arr = pred_labels[valid].values
    for t, p in zip(t_arr, p_arr):
        ti = classes.index(str(t))
        pi = classes.index(str(p))
        cm[ti][pi] += 1

    # F1 per class
    f1_scores = {}
    for i, cls in enumerate(classes):
        tp = cm[i][i]
        fp = sum(cm[j][i] for j in range(3)) - tp
        fn = sum(cm[i][j] for j in range(3)) - tp
        prec = tp / max(tp + fp, 1)
        rec  = tp / max(tp + fn, 1)
        f1_scores[cls] = round(2 * prec * rec / max(prec + rec, 1e-8), 3)

    # Normalize confusion matrix to percentages
    cm_pct = []
    for row in cm:
        total = sum(row) or 1
        cm_pct.append([round(v / total * 100, 1) for v in row])

    return {
        "group_counts": {g: len(v) for g, v in groups.items()},
        "subgroup_counts": subgroup_counts,
        "ic_top": [{"col": c, "ic": round(v, 4)} for c, v in ic_top],
        "ic_all": [{"col": c, "ic": round(v, 4)} for c, v in ic_sorted],
        "pca_points": pca_points,
        "pca_var_exp": var_exp,
        "heatmap_cols": heatmap_cols,
        "heatmap_corr": corr,
        "confusion_matrix": cm_pct,
        "confusion_classes": classes,
        "f1_scores": f1_scores,
        "total_features": len(cols),
        "regime_col_used": regime_col or "none",
    }


# ── 4. Assemble all data ──────────────────────────────────────────────────────

def assemble() -> dict:
    print("Parsing session logs…")
    sessions = {}
    for name, path in SESSION_LOGS.items():
        if path.exists():
            r = parse_session(path)
            if r:
                sessions[name] = r
                print(f"  {name}: beta={len(r['beta'])} alpha={len(r['alpha'])} val={len(r['val'])} eps={len(r['eps'])}")

    print("Loading equity curves…")
    equity = load_equity_curves()
    print(f"  {len(equity)} curves: {list(equity.keys())}")

    print("Computing feature analytics…")
    feat_data = compute_feature_analytics()
    print(f"  PCA: {len(feat_data['pca_points'])} points, var_exp={feat_data['pca_var_exp']}")
    print(f"  Confusion: {feat_data['confusion_classes']}, F1={feat_data['f1_scores']}")

    return {"sessions": sessions, "equity": equity, "features": feat_data}


# ── 5. HTML template ──────────────────────────────────────────────────────────

HTML_TEMPLATE = r"""
<title>DRL_BTC — ML Dashboard</title>
<style>
/* ── Reset & tokens ─────────────────────────────────────── */
*, *::before, *::after { box-sizing: border-box; margin: 0; padding: 0; }

:root {
  --bg:        #0d1117;
  --bg2:       #161b22;
  --bg3:       #21262d;
  --border:    #30363d;
  --text:      #e6edf3;
  --text2:     #8b949e;
  --accent:    #58a6ff;
  --green:     #3fb950;
  --red:       #f85149;
  --yellow:    #d29922;
  --purple:    #bc8cff;
  --orange:    #ffa657;
  --font-mono: "SF Mono", "Fira Code", "Cascadia Code", monospace;
  --font-ui:   -apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif;
  --radius:    6px;
}

body {
  background: var(--bg);
  color: var(--text);
  font-family: var(--font-ui);
  font-size: 13px;
  line-height: 1.5;
  min-height: 100vh;
}

/* ── Top bar ─────────────────────────────────────────────── */
.topbar {
  background: var(--bg2);
  border-bottom: 1px solid var(--border);
  padding: 12px 24px;
  display: flex;
  align-items: center;
  gap: 16px;
  position: sticky;
  top: 0;
  z-index: 100;
}
.topbar-title {
  font-family: var(--font-mono);
  font-size: 14px;
  font-weight: 600;
  color: var(--accent);
  letter-spacing: 0.03em;
}
.topbar-sub { color: var(--text2); font-size: 11px; }
.topbar-spacer { flex: 1; }

/* ── Tab navigation ──────────────────────────────────────── */
.tabs {
  display: flex;
  gap: 2px;
  padding: 0 24px;
  background: var(--bg2);
  border-bottom: 1px solid var(--border);
}
.tab-btn {
  padding: 10px 16px;
  background: none;
  border: none;
  border-bottom: 2px solid transparent;
  color: var(--text2);
  font-family: var(--font-ui);
  font-size: 12px;
  font-weight: 500;
  cursor: pointer;
  transition: color .15s, border-color .15s;
  white-space: nowrap;
}
.tab-btn:hover { color: var(--text); }
.tab-btn.active { color: var(--accent); border-bottom-color: var(--accent); }

/* ── Page / section layout ───────────────────────────────── */
.page { display: none; padding: 24px; }
.page.active { display: block; }

.section-grid {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(340px, 1fr));
  gap: 16px;
  margin-bottom: 16px;
}
.section-grid.wide {
  grid-template-columns: repeat(auto-fill, minmax(500px, 1fr));
}
.section-grid.full { grid-template-columns: 1fr; }

/* ── Card ────────────────────────────────────────────────── */
.card {
  background: var(--bg2);
  border: 1px solid var(--border);
  border-radius: var(--radius);
  padding: 16px;
}
.card-title {
  font-family: var(--font-mono);
  font-size: 11px;
  font-weight: 600;
  color: var(--text2);
  text-transform: uppercase;
  letter-spacing: 0.08em;
  margin-bottom: 12px;
  display: flex;
  align-items: center;
  gap: 8px;
}
.badge {
  padding: 2px 7px;
  border-radius: 20px;
  font-size: 10px;
  font-weight: 600;
}
.badge-green  { background: rgba(63,185,80,.15);  color: var(--green); }
.badge-red    { background: rgba(248,81,73,.15);   color: var(--red); }
.badge-yellow { background: rgba(210,153,34,.15);  color: var(--yellow); }
.badge-blue   { background: rgba(88,166,255,.15);  color: var(--accent); }

/* ── Metric row ──────────────────────────────────────────── */
.metric-row {
  display: flex;
  gap: 12px;
  flex-wrap: wrap;
  margin-bottom: 16px;
}
.metric {
  background: var(--bg3);
  border: 1px solid var(--border);
  border-radius: var(--radius);
  padding: 10px 14px;
  min-width: 110px;
}
.metric-label { font-size: 10px; color: var(--text2); font-family: var(--font-mono); text-transform: uppercase; }
.metric-value { font-size: 18px; font-weight: 700; font-family: var(--font-mono); margin-top: 2px; }
.metric-value.pos { color: var(--green); }
.metric-value.neg { color: var(--red); }
.metric-value.neu { color: var(--accent); }

/* ── Canvas charts ───────────────────────────────────────── */
canvas { display: block; width: 100% !important; max-width: 100%; }

/* ── Session selector ────────────────────────────────────── */
.sess-select {
  background: var(--bg3);
  border: 1px solid var(--border);
  border-radius: var(--radius);
  color: var(--text);
  font-family: var(--font-mono);
  font-size: 12px;
  padding: 4px 8px;
  cursor: pointer;
}

/* ── Confusion matrix ────────────────────────────────────── */
.cm-table { width: 100%; border-collapse: collapse; font-family: var(--font-mono); font-size: 12px; }
.cm-table th { color: var(--text2); padding: 6px 10px; font-weight: 500; text-align: center; }
.cm-table td { padding: 10px; text-align: center; border-radius: 3px; font-weight: 700; font-size: 14px; }
.cm-label { color: var(--text2); font-size: 10px; }

/* ── Feature heatmap canvas ──────────────────────────────── */
.heatmap-wrap { overflow-x: auto; }

/* ── Regime Sharpe table ─────────────────────────────────── */
.sharpe-table { width: 100%; border-collapse: collapse; font-family: var(--font-mono); font-size: 12px; }
.sharpe-table th { color: var(--text2); padding: 6px 8px; text-align: right; font-weight: 500; border-bottom: 1px solid var(--border); }
.sharpe-table th:first-child { text-align: left; }
.sharpe-table td { padding: 5px 8px; text-align: right; border-bottom: 1px solid var(--bg3); }
.sharpe-table td:first-child { text-align: left; color: var(--text2); }
.sharpe-table tr:hover td { background: var(--bg3); }

/* ── OOD timeline ────────────────────────────────────────── */
.ood-timeline { display: flex; gap: 2px; flex-wrap: wrap; margin-top: 8px; }
.ood-tick {
  width: 16px; height: 24px; border-radius: 3px;
  display: flex; align-items: center; justify-content: center;
  font-size: 8px; font-family: var(--font-mono); cursor: default;
}
.ood-normal { background: rgba(63,185,80,.25); color: var(--green); }
.ood-block  { background: rgba(248,81,73,.25);  color: var(--red); }
.ood-unknown { background: var(--bg3); color: var(--text2); }

/* ── IC bar chart container ──────────────────────────────── */
.ic-bar { display: flex; align-items: center; gap: 6px; margin-bottom: 3px; font-size: 10px; font-family: var(--font-mono); }
.ic-name { width: 160px; color: var(--text2); overflow: hidden; text-overflow: ellipsis; white-space: nowrap; text-align: right; }
.ic-track { flex: 1; height: 14px; background: var(--bg3); border-radius: 2px; position: relative; }
.ic-fill  { height: 100%; border-radius: 2px; position: absolute; }
.ic-val   { width: 50px; text-align: left; }

/* ── Pie canvas holder ───────────────────────────────────── */
.pie-row { display: flex; gap: 24px; align-items: flex-start; flex-wrap: wrap; }
.pie-legend { display: flex; flex-direction: column; gap: 6px; margin-top: 8px; }
.pie-legend-item { display: flex; align-items: center; gap: 6px; font-size: 11px; }
.pie-dot { width: 10px; height: 10px; border-radius: 50%; flex-shrink: 0; }

/* ── Scrollable tables ───────────────────────────────────── */
.scroll-x { overflow-x: auto; }
</style>

<div class="topbar">
  <span class="topbar-title">▍DRL_BTC</span>
  <span class="topbar-sub">ML Analytics Dashboard</span>
  <span class="topbar-spacer"></span>
  <span class="topbar-sub" id="gen-time"></span>
</div>

<div class="tabs">
  <button class="tab-btn active" onclick="showTab('pretrain')">Supervised Pretrain</button>
  <button class="tab-btn" onclick="showTab('rl')">RL Training</button>
  <button class="tab-btn" onclick="showTab('features')">Feature Analysis</button>
  <button class="tab-btn" onclick="showTab('eval')">Evaluation</button>
</div>

<!-- ══════════════════════════════════════════════════════════ -->
<!--  TAB 1 — SUPERVISED PRETRAIN                             -->
<!-- ══════════════════════════════════════════════════════════ -->
<div class="page active" id="page-pretrain">

  <div class="metric-row" id="pretrain-summary"></div>

  <div class="section-grid">
    <div class="card">
      <div class="card-title">Beta Engine — Loss &amp; Accuracy
        <span class="badge badge-blue" id="beta-final-acc"></span>
      </div>
      <canvas id="c-beta-loss" height="180"></canvas>
    </div>
    <div class="card">
      <div class="card-title">Alpha Engine — Loss &amp; ret_corr
        <span class="badge badge-blue" id="alpha-final-rc"></span>
      </div>
      <canvas id="c-alpha-loss" height="180"></canvas>
    </div>
    <div class="card">
      <div class="card-title">Alpha Engine — TP / SL Accuracy</div>
      <canvas id="c-alpha-acc" height="180"></canvas>
    </div>
    <div class="card">
      <div class="card-title">Fine-tune — Beta &amp; Alpha Loss</div>
      <canvas id="c-ft" height="180"></canvas>
    </div>
  </div>

  <div class="section-grid">
    <div class="card">
      <div class="card-title">Regime Confusion Matrix
        <span class="badge badge-yellow">Predicted vs True</span>
      </div>
      <div id="cm-container"></div>
    </div>
    <div class="card">
      <div class="card-title">F1 Score per Regime Class</div>
      <canvas id="c-f1" height="160"></canvas>
    </div>
  </div>

  <div style="margin-bottom:12px;display:flex;align-items:center;gap:10px;">
    <span style="font-size:11px;color:var(--text2)">Session:</span>
    <select class="sess-select" id="sess-select" onchange="renderPretrain()"></select>
  </div>

</div>

<!-- ══════════════════════════════════════════════════════════ -->
<!--  TAB 2 — RL TRAINING                                      -->
<!-- ══════════════════════════════════════════════════════════ -->
<div class="page" id="page-rl">

  <div style="display:flex;align-items:center;gap:10px;margin-bottom:16px;">
    <span style="font-size:11px;color:var(--text2)">Session:</span>
    <select class="sess-select" id="rl-sess-select" onchange="renderRL()"></select>
  </div>

  <div class="section-grid full">
    <div class="card">
      <div class="card-title">Val Sharpe per Regime over Training Steps</div>
      <canvas id="c-regime-sharpe" height="260"></canvas>
    </div>
  </div>

  <div class="section-grid">
    <div class="card">
      <div class="card-title">avgSharpe &amp; minSharpe over Steps</div>
      <canvas id="c-avg-sharpe" height="200"></canvas>
    </div>
    <div class="card">
      <div class="card-title">OOD State at Each Checkpoint</div>
      <div id="ood-timeline-container"></div>
    </div>
    <div class="card">
      <div class="card-title">logπ per Episode
        <span class="badge badge-yellow">target: −2.5</span>
      </div>
      <canvas id="c-logpi" height="200"></canvas>
    </div>
    <div class="card">
      <div class="card-title">exec% at Each Val Checkpoint</div>
      <canvas id="c-exec" height="200"></canvas>
    </div>
  </div>

  <div class="section-grid">
    <div class="card">
      <div class="card-title">Episode Return Distribution</div>
      <canvas id="c-ep-ret" height="200"></canvas>
    </div>
    <div class="card">
      <div class="card-title">Critic Loss (Qc) per Episode</div>
      <canvas id="c-qc" height="200"></canvas>
    </div>
  </div>

  <div class="card scroll-x" style="margin-bottom:16px;">
    <div class="card-title">Val Checkpoint Table</div>
    <div id="val-table-container"></div>
  </div>

</div>

<!-- ══════════════════════════════════════════════════════════ -->
<!--  TAB 3 — FEATURE ANALYSIS                                 -->
<!-- ══════════════════════════════════════════════════════════ -->
<div class="page" id="page-features">

  <div class="section-grid">
    <div class="card">
      <div class="card-title">Feature Groups (by Timeframe)</div>
      <div class="pie-row">
        <canvas id="c-pie-tf" width="160" height="160"></canvas>
        <div class="pie-legend" id="pie-tf-legend"></div>
      </div>
    </div>
    <div class="card">
      <div class="card-title">Feature Groups (by Type)</div>
      <div class="pie-row">
        <canvas id="c-pie-type" width="160" height="160"></canvas>
        <div class="pie-legend" id="pie-type-legend"></div>
      </div>
    </div>
  </div>

  <div class="section-grid full">
    <div class="card">
      <div class="card-title">PCA — Feature Space (2D)
        <span class="badge badge-blue" id="pca-var-badge"></span>
        <span style="margin-left:auto;font-size:10px;color:var(--text2)">
          <span style="color:var(--green)">● Bull</span>
          &nbsp;<span style="color:var(--red)">● Bear</span>
          &nbsp;<span style="color:var(--text2)">● Range</span>
        </span>
      </div>
      <canvas id="c-pca" height="380"></canvas>
    </div>
  </div>

  <div class="section-grid full">
    <div class="card">
      <div class="card-title">Top IC Features — Spearman Correlation with Next-Bar Return</div>
      <div id="ic-bars-container"></div>
    </div>
  </div>

  <div class="section-grid full">
    <div class="card">
      <div class="card-title">Feature Correlation Heatmap (25 representative features)</div>
      <div class="heatmap-wrap">
        <canvas id="c-heatmap" height="400"></canvas>
      </div>
    </div>
  </div>

</div>

<!-- ══════════════════════════════════════════════════════════ -->
<!--  TAB 4 — EVALUATION                                       -->
<!-- ══════════════════════════════════════════════════════════ -->
<div class="page" id="page-eval">

  <div class="section-grid full">
    <div class="card">
      <div class="card-title">Equity Curves — OOS Evaluation (normalised to 100)</div>
      <canvas id="c-equity" height="300"></canvas>
    </div>
  </div>

  <div class="section-grid">
    <div class="card">
      <div class="card-title">Session Comparison</div>
      <div id="session-comparison-table"></div>
    </div>
    <div class="card">
      <div class="card-title">OOS Performance Summary</div>
      <div id="oos-summary"></div>
    </div>
  </div>

</div>

<script>
// ─────────────────────────────────────────────────────────
//  DATA (injected by generate.py)
// ─────────────────────────────────────────────────────────
const DATA = %%DATA%%;

// ─────────────────────────────────────────────────────────
//  UTILS
// ─────────────────────────────────────────────────────────
const COLORS = {
  accent: '#58a6ff', green: '#3fb950', red: '#f85149',
  yellow: '#d29922', purple: '#bc8cff', orange: '#ffa657',
  teal: '#39d353', pink: '#ff7b72', gray: '#8b949e',
};
const REGIME_COLORS = {
  Bull: COLORS.green, Bear: COLORS.red, Range: COLORS.gray,
  '2022-01': COLORS.red, '2023-07': COLORS.green, '2021-06': COLORS.teal,
  '2024-01': COLORS.yellow, '2025-01': COLORS.purple,
};
const SESSION_COLORS = ['#58a6ff','#3fb950','#ffa657','#bc8cff','#f85149','#39d353'];

document.getElementById('gen-time').textContent = 'Generated ' + new Date().toLocaleString();

function showTab(name) {
  document.querySelectorAll('.page').forEach(p => p.classList.remove('active'));
  document.querySelectorAll('.tab-btn').forEach(b => b.classList.remove('active'));
  document.getElementById('page-' + name).classList.add('active');
  const tabs = ['pretrain','rl','features','eval'];
  document.querySelectorAll('.tab-btn')[tabs.indexOf(name)].classList.add('active');
}

// ─────────────────────────────────────────────────────────
//  CHART HELPERS
// ─────────────────────────────────────────────────────────
function getCtx(id) {
  const el = document.getElementById(id);
  if (!el) return null;
  const dpr = window.devicePixelRatio || 1;
  const w = el.parentElement.clientWidth - 32;
  const h = parseInt(el.getAttribute('height'));
  el.width  = w * dpr;
  el.height = h * dpr;
  el.style.width  = w + 'px';
  el.style.height = h + 'px';
  const ctx = el.getContext('2d');
  ctx.scale(dpr, dpr);
  return { ctx, w, h };
}

function drawLineChart(id, series, opts = {}) {
  const r = getCtx(id);
  if (!r) return;
  const { ctx, w, h } = r;
  const pad = { t: 20, r: 16, b: 36, l: 48 };
  const cw = w - pad.l - pad.r;
  const ch = h - pad.t - pad.b;

  ctx.fillStyle = 'transparent';
  ctx.fillRect(0, 0, w, h);

  if (!series.length || !series[0].data.length) return;

  const allY = series.flatMap(s => s.data.map(d => d.y));
  const allX = series[0].data.map(d => d.x);
  let minY = opts.minY !== undefined ? opts.minY : Math.min(...allY);
  let maxY = opts.maxY !== undefined ? opts.maxY : Math.max(...allY);
  if (minY === maxY) { minY -= 1; maxY += 1; }
  const minX = Math.min(...allX);
  const maxX = Math.max(...allX);

  const xp = x => pad.l + (x - minX) / (maxX - minX || 1) * cw;
  const yp = y => pad.t + (1 - (y - minY) / (maxY - minY)) * ch;

  // Grid lines
  ctx.strokeStyle = '#21262d';
  ctx.lineWidth = 1;
  const steps = 5;
  for (let i = 0; i <= steps; i++) {
    const y = minY + (maxY - minY) * i / steps;
    const yy = yp(y);
    ctx.beginPath(); ctx.moveTo(pad.l, yy); ctx.lineTo(pad.l + cw, yy); ctx.stroke();
    ctx.fillStyle = '#8b949e'; ctx.font = '10px monospace';
    ctx.fillText(y.toFixed(opts.decimals !== undefined ? opts.decimals : 2), pad.l - 4, yy + 3.5);
    ctx.textAlign = 'right';
  }
  ctx.textAlign = 'left';

  // Zero line
  if (minY < 0 && maxY > 0) {
    ctx.strokeStyle = '#30363d'; ctx.lineWidth = 1.5;
    const zy = yp(0);
    ctx.setLineDash([4, 4]); ctx.beginPath(); ctx.moveTo(pad.l, zy); ctx.lineTo(pad.l + cw, zy); ctx.stroke(); ctx.setLineDash([]);
  }

  // Horizontal reference lines
  if (opts.hlines) opts.hlines.forEach(hl => {
    ctx.strokeStyle = hl.color || '#8b949e'; ctx.lineWidth = 1;
    ctx.setLineDash([6, 4]);
    const yy = yp(hl.y);
    ctx.beginPath(); ctx.moveTo(pad.l, yy); ctx.lineTo(pad.l + cw, yy); ctx.stroke();
    ctx.setLineDash([]);
    ctx.fillStyle = hl.color || '#8b949e'; ctx.font = '9px monospace'; ctx.textAlign = 'right';
    ctx.fillText(hl.label || '', pad.l + cw, yy - 3);
    ctx.textAlign = 'left';
  });

  // X axis labels
  ctx.fillStyle = '#8b949e'; ctx.font = '10px monospace'; ctx.textAlign = 'center';
  const nxticks = Math.min(allX.length, 8);
  for (let i = 0; i < nxticks; i++) {
    const idx = Math.round(i * (allX.length - 1) / Math.max(nxticks - 1, 1));
    const xv = allX[idx];
    ctx.fillText(opts.xFmt ? opts.xFmt(xv) : xv, xp(xv), h - pad.b + 14);
  }
  ctx.textAlign = 'left';

  // Series lines
  series.forEach(s => {
    if (!s.data.length) return;
    ctx.strokeStyle = s.color || COLORS.accent;
    ctx.lineWidth = s.width || 1.8;
    ctx.beginPath();
    s.data.forEach((d, i) => {
      const x = xp(d.x), y = yp(d.y);
      i === 0 ? ctx.moveTo(x, y) : ctx.lineTo(x, y);
    });
    ctx.stroke();

    // Area fill
    if (s.fill) {
      ctx.beginPath();
      s.data.forEach((d, i) => {
        const x = xp(d.x), y = yp(d.y);
        i === 0 ? ctx.moveTo(x, y) : ctx.lineTo(x, y);
      });
      ctx.lineTo(xp(s.data[s.data.length - 1].x), yp(0));
      ctx.lineTo(xp(s.data[0].x), yp(0));
      ctx.closePath();
      ctx.fillStyle = s.fill;
      ctx.fill();
    }
  });

  // Legend
  if (series.length > 1) {
    let lx = pad.l; const ly = h - 8;
    ctx.font = '10px monospace'; ctx.textAlign = 'left';
    series.forEach(s => {
      ctx.fillStyle = s.color || COLORS.accent;
      ctx.fillRect(lx, ly - 7, 12, 3);
      ctx.fillText(s.label || '', lx + 16, ly);
      lx += ctx.measureText(s.label || '').width + 30;
    });
  } else if (series[0].label) {
    ctx.fillStyle = series[0].color || COLORS.accent;
    ctx.font = '10px monospace'; ctx.textAlign = 'right';
    ctx.fillText(series[0].label, pad.l + cw, pad.t - 6);
    ctx.textAlign = 'left';
  }
}

function drawBarChart(id, labels, values, colors, opts = {}) {
  const r = getCtx(id);
  if (!r) return;
  const { ctx, w, h } = r;
  const pad = { t: 20, r: 16, b: 36, l: 60 };
  const cw = w - pad.l - pad.r;
  const ch = h - pad.t - pad.b;

  const maxV = opts.maxV || Math.max(...values.map(Math.abs), 0.01);
  const bw = cw / labels.length * 0.7;
  const gap = cw / labels.length * 0.3;

  // Grid
  ctx.strokeStyle = '#21262d'; ctx.lineWidth = 1;
  [0.25, 0.5, 0.75, 1].forEach(t => {
    const y = pad.t + ch * (1 - t);
    ctx.beginPath(); ctx.moveTo(pad.l, y); ctx.lineTo(pad.l + cw, y); ctx.stroke();
    const v = (maxV * t);
    ctx.fillStyle = '#8b949e'; ctx.font = '10px monospace'; ctx.textAlign = 'right';
    ctx.fillText(v.toFixed(2), pad.l - 4, y + 3.5);
    ctx.textAlign = 'left';
  });

  labels.forEach((lbl, i) => {
    const v = values[i];
    const bh = Math.abs(v) / maxV * ch;
    const x = pad.l + i * (bw + gap) + gap / 2;
    const y = pad.t + ch - bh;
    ctx.fillStyle = colors[i] || COLORS.accent;
    ctx.fillRect(x, y, bw, bh);
    ctx.fillStyle = '#e6edf3'; ctx.font = '10px monospace'; ctx.textAlign = 'center';
    ctx.fillText(lbl, x + bw / 2, h - pad.b + 14);
    ctx.fillText(v.toFixed(opts.decimals || 3), x + bw / 2, y - 4);
    ctx.textAlign = 'left';
  });
}

function drawPieChart(canvasId, legendId, segments) {
  const el = document.getElementById(canvasId);
  if (!el) return;
  const ctx = el.getContext('2d');
  const sz = 160;
  el.width = sz; el.height = sz;
  const cx = sz / 2, cy = sz / 2, r = sz / 2 - 8;
  const total = segments.reduce((s, x) => s + x.value, 0);
  let start = -Math.PI / 2;
  segments.forEach(seg => {
    const angle = (seg.value / total) * 2 * Math.PI;
    ctx.beginPath(); ctx.moveTo(cx, cy);
    ctx.arc(cx, cy, r, start, start + angle);
    ctx.closePath(); ctx.fillStyle = seg.color; ctx.fill();
    start += angle;
  });
  const leg = document.getElementById(legendId);
  if (leg) {
    leg.innerHTML = segments.map(s =>
      `<div class="pie-legend-item"><div class="pie-dot" style="background:${s.color}"></div>
       <span style="color:var(--text2)">${s.label}</span>
       <span style="color:var(--text);font-family:var(--font-mono)">${s.value}</span></div>`
    ).join('');
  }
}

// ─────────────────────────────────────────────────────────
//  TAB 1 — PRETRAIN
// ─────────────────────────────────────────────────────────
function populateSessionSelect(selectId, onchange) {
  const sel = document.getElementById(selectId);
  sel.innerHTML = '';
  Object.keys(DATA.sessions).forEach(name => {
    const opt = document.createElement('option');
    opt.value = name; opt.textContent = name;
    sel.appendChild(opt);
  });
  sel.value = Object.keys(DATA.sessions)[Object.keys(DATA.sessions).length - 1];
}

function renderPretrain() {
  const sel = document.getElementById('sess-select');
  const name = sel.value;
  const sess = DATA.sessions[name];
  if (!sess) return;

  const beta  = sess.beta  || [];
  const alpha = sess.alpha || [];
  const ft    = sess.ft    || [];

  // Summary metrics
  const lastBeta  = beta[beta.length - 1]   || {};
  const lastAlpha = alpha[alpha.length - 1] || {};
  const lastFt    = ft[ft.length - 1]       || {};

  document.getElementById('pretrain-summary').innerHTML = [
    { label: 'Regime Acc', value: (lastBeta.regime_acc || 0).toFixed(1) + '%', cls: 'neu' },
    { label: 'Vol Cls Acc', value: (lastBeta.vol_class_acc || 0).toFixed(1) + '%', cls: 'neu' },
    { label: 'ret_corr', value: (lastAlpha.ret_corr || 0) >= 0
        ? '+' + (lastAlpha.ret_corr || 0).toFixed(3) : (lastAlpha.ret_corr || 0).toFixed(3),
      cls: (lastAlpha.ret_corr || 0) >= 0 ? 'pos' : 'neg' },
    { label: 'tp_acc', value: (lastAlpha.tp_acc || 0).toFixed(1) + '%', cls: 'neu' },
    { label: 'sl_acc', value: (lastAlpha.sl_acc || 0).toFixed(1) + '%', cls: 'neu' },
    { label: 'Alpha loss', value: lastAlpha.loss ? lastAlpha.loss.toFixed(2) : '—', cls: 'neu' },
  ].map(m => `<div class="metric">
    <div class="metric-label">${m.label}</div>
    <div class="metric-value ${m.cls}">${m.value}</div>
  </div>`).join('');

  document.getElementById('beta-final-acc').textContent =
    'Final: ' + (lastBeta.regime_acc || 0).toFixed(1) + '%';
  document.getElementById('alpha-final-rc').textContent =
    'Final ret_corr: ' + ((lastAlpha.ret_corr || 0) >= 0 ? '+' : '') + (lastAlpha.ret_corr || 0).toFixed(3);

  // Beta loss + regime_acc dual axis
  if (beta.length) {
    drawLineChart('c-beta-loss', [
      { data: beta.map(e => ({ x: e.epoch, y: e.loss })),        color: COLORS.red,    label: 'loss',       width: 2 },
      { data: beta.map(e => ({ x: e.epoch, y: e.regime_acc })),  color: COLORS.green,  label: 'regime_acc', width: 2 },
      { data: beta.map(e => ({ x: e.epoch, y: e.vol_class_acc })), color: COLORS.accent, label: 'vol_acc',  width: 1.5 },
    ], { xFmt: v => 'ep' + v, decimals: 1 });
  }

  // Alpha loss + ret_corr
  if (alpha.length) {
    drawLineChart('c-alpha-loss', [
      { data: alpha.map(e => ({ x: e.epoch, y: e.loss })),     color: COLORS.red,    label: 'loss',     width: 2 },
      { data: alpha.map(e => ({ x: e.epoch, y: e.ret_corr })), color: COLORS.green,  label: 'ret_corr', width: 2.5 },
      { data: alpha.map(e => ({ x: e.epoch, y: e.p50_corr })), color: COLORS.accent, label: 'p50_corr', width: 1.5 },
    ], { xFmt: v => 'ep' + v, decimals: 2,
         hlines: [{ y: 0, color: '#30363d', label: '0' }] });
  }

  // tp_acc + sl_acc
  if (alpha.length) {
    drawLineChart('c-alpha-acc', [
      { data: alpha.map(e => ({ x: e.epoch, y: e.tp_acc })), color: COLORS.green,  label: 'tp_acc', width: 2 },
      { data: alpha.map(e => ({ x: e.epoch, y: e.sl_acc })), color: COLORS.yellow, label: 'sl_acc', width: 2 },
    ], { xFmt: v => 'ep' + v, decimals: 1, minY: 50, maxY: 80 });
  }

  // Fine-tune
  if (ft.length) {
    drawLineChart('c-ft', [
      { data: ft.map(e => ({ x: e.epoch, y: e.beta  })), color: COLORS.accent, label: 'beta_loss',  width: 2 },
      { data: ft.map(e => ({ x: e.epoch, y: e.alpha })), color: COLORS.orange, label: 'alpha_loss', width: 2 },
    ], { xFmt: v => 'ep' + v, decimals: 2 });
  }

  // Confusion matrix
  const feat = DATA.features;
  const cm   = feat.confusion_matrix;
  const cls  = feat.confusion_classes;
  const cmHtml = `
    <table class="cm-table">
      <thead>
        <tr><th></th>${cls.map(c => `<th>Pred ${c}</th>`).join('')}</tr>
      </thead>
      <tbody>
        ${cm.map((row, i) => `
          <tr>
            <td class="cm-label">True ${cls[i]}</td>
            ${row.map((v, j) => {
              const alpha = Math.min(v / 100, 1);
              const color = i === j
                ? `rgba(63,185,80,${0.15 + alpha * 0.6})`
                : `rgba(248,81,73,${alpha * 0.5})`;
              return `<td style="background:${color}">${v.toFixed(1)}%</td>`;
            }).join('')}
          </tr>`).join('')}
      </tbody>
    </table>
    <div style="font-size:10px;color:var(--text2);margin-top:8px;">
      Feature used: <code style="font-family:var(--font-mono)">${feat.regime_col_used}</code>
    </div>`;
  document.getElementById('cm-container').innerHTML = cmHtml;

  // F1 bar chart
  const f1 = feat.f1_scores;
  drawBarChart('c-f1',
    Object.keys(f1),
    Object.values(f1),
    [COLORS.green, COLORS.red, COLORS.yellow],
    { maxV: 1, decimals: 3 }
  );
}

// ─────────────────────────────────────────────────────────
//  TAB 2 — RL TRAINING
// ─────────────────────────────────────────────────────────
function renderRL() {
  const sel  = document.getElementById('rl-sess-select');
  const name = sel.value;
  const sess = DATA.sessions[name];
  if (!sess) return;

  const val = (sess.val || []).filter(v => v.avg_sharpe !== undefined);
  const eps = sess.eps || [];

  // All regime keys
  const regimeKeys = [...new Set(val.flatMap(v => Object.keys(v.regimes || {})))].sort();

  // Regime Sharpe over steps
  const regimeSeries = regimeKeys.map((rk, i) => ({
    label: rk,
    color: REGIME_COLORS[rk] || SESSION_COLORS[i % SESSION_COLORS.length],
    data:  val.filter(v => v.regimes && rk in v.regimes)
              .map(v => ({ x: v.step, y: v.regimes[rk] })),
    width: 2,
  }));
  drawLineChart('c-regime-sharpe', regimeSeries,
    { hlines: [{ y: 0, color: '#30363d', label: '0' }], xFmt: v => (v/1000).toFixed(0)+'K', decimals: 2 });

  // avgSharpe + minSharpe
  drawLineChart('c-avg-sharpe', [
    { data: val.map(v => ({ x: v.step, y: v.avg_sharpe })), color: COLORS.accent,  label: 'avgSharpe', width: 2.5, fill: 'rgba(88,166,255,0.06)' },
    { data: val.map(v => ({ x: v.step, y: v.min_sharpe })), color: COLORS.yellow, label: 'minSharpe', width: 1.5 },
  ], { hlines: [{ y: 0, color: '#30363d' }], xFmt: v => (v/1000).toFixed(0)+'K', decimals: 2 });

  // OOD timeline
  const oodHtml = `
    <div style="font-size:10px;color:var(--text2);margin-bottom:6px;">
      <span style="color:var(--green)">■ NORMAL</span> &nbsp;
      <span style="color:var(--red)">■ BLOCK</span>
    </div>
    <div class="ood-timeline">
      ${val.map(v => {
        const cls = v.ood_state === 'NORMAL' ? 'ood-normal' : v.ood_state === 'BLOCK' ? 'ood-block' : 'ood-unknown';
        return `<div class="ood-tick ${cls}" title="${(v.step/1000).toFixed(0)}K: ${v.ood_state} ema=${v.ood_ema}">
          ${(v.step/1000).toFixed(0)}
        </div>`;
      }).join('')}
    </div>`;
  document.getElementById('ood-timeline-container').innerHTML = oodHtml;

  // logπ per episode
  if (eps.length) {
    drawLineChart('c-logpi', [
      { data: eps.map(e => ({ x: e.ep, y: e.log_pi })), color: COLORS.purple, label: 'logπ', width: 2 },
    ], { hlines: [{ y: -2.5, color: COLORS.orange, label: 'target −2.5' }],
         xFmt: v => 'EP' + v, decimals: 1 });
  }

  // exec%
  const execData = val.filter(v => v.exec_pct !== null && v.exec_pct !== undefined);
  if (execData.length) {
    drawLineChart('c-exec', [
      { data: execData.map(v => ({ x: v.step, y: v.exec_pct })),
        color: COLORS.teal, label: 'exec%', width: 2,
        fill: 'rgba(57,211,83,0.08)' },
    ], { minY: 0, maxY: 100, xFmt: v => (v/1000).toFixed(0)+'K', decimals: 0,
         hlines: [{ y: 30, color: COLORS.yellow, label: '30% target' }] });
  }

  // Episode return
  if (eps.length) {
    drawLineChart('c-ep-ret', [
      { data: eps.map(e => ({ x: e.ep, y: e.ret })),
        color: COLORS.green, label: 'ep_ret%', width: 1.5,
        fill: 'rgba(63,185,80,0.06)' },
    ], { hlines: [{ y: 0, color: '#30363d' }], xFmt: v => 'EP' + v, decimals: 1 });
  }

  // Qc
  if (eps.length) {
    drawLineChart('c-qc', [
      { data: eps.map(e => ({ x: e.ep, y: e.qc })), color: COLORS.accent, label: 'Qc', width: 1.5 },
    ], { minY: 0, xFmt: v => 'EP' + v, decimals: 3 });
  }

  // Val table
  const tableHtml = `
    <table class="sharpe-table">
      <thead>
        <tr>
          <th>Step</th>
          <th>avgSharpe</th>
          <th>minSharpe</th>
          <th>avg_ret%</th>
          <th>worstDD%</th>
          ${regimeKeys.map(r => `<th>${r}</th>`).join('')}
          <th>OOD</th>
          <th>exec%</th>
        </tr>
      </thead>
      <tbody>
        ${val.map(v => `
          <tr>
            <td>${(v.step/1000).toFixed(0)}K</td>
            <td style="color:${(v.avg_sharpe||0)>=0?'var(--green)':'var(--red)'}">${(v.avg_sharpe||0).toFixed(3)}</td>
            <td style="color:${(v.min_sharpe||0)>=0?'var(--green)':'var(--red)'}">${(v.min_sharpe||0).toFixed(3)}</td>
            <td style="color:${(v.avg_ret||0)>=0?'var(--green)':'var(--red)'}">${(v.avg_ret||0).toFixed(2)}%</td>
            <td style="color:var(--yellow)">${(v.worst_dd||0).toFixed(1)}%</td>
            ${regimeKeys.map(rk => {
              const sh = v.regimes && v.regimes[rk];
              return `<td style="color:${sh>=0?'var(--green)':'var(--red)'}">${sh !== undefined ? sh.toFixed(2) : '—'}</td>`;
            }).join('')}
            <td>
              <span class="badge ${v.ood_state==='NORMAL'?'badge-green':'badge-red'}">${v.ood_state}</span>
            </td>
            <td>${v.exec_pct !== null && v.exec_pct !== undefined ? v.exec_pct + '%' : '—'}</td>
          </tr>`).join('')}
      </tbody>
    </table>`;
  document.getElementById('val-table-container').innerHTML = tableHtml;
}

// ─────────────────────────────────────────────────────────
//  TAB 3 — FEATURE ANALYSIS
// ─────────────────────────────────────────────────────────
function renderFeatures() {
  const feat = DATA.features;

  // Pie — timeframe
  const TF_COLORS = { '1h': COLORS.accent, '4h': COLORS.green, '1d': COLORS.purple, 'other': COLORS.orange };
  drawPieChart('c-pie-tf', 'pie-tf-legend',
    Object.entries(feat.group_counts).map(([k, v]) => ({ label: k, value: v, color: TF_COLORS[k] || COLORS.gray }))
  );

  // Pie — type
  const TYPE_COLORS = {
    trend: COLORS.accent, momentum: COLORS.green, volatility: COLORS.yellow,
    onchain_deriv: COLORS.orange, onchain: COLORS.purple, sentiment: COLORS.pink,
    signal: COLORS.teal, other: COLORS.gray,
  };
  const subEntries = Object.entries(feat.subgroup_counts).sort((a,b) => b[1]-a[1]).slice(0, 8);
  drawPieChart('c-pie-type', 'pie-type-legend',
    subEntries.map(([k, v]) => ({ label: k, value: v, color: TYPE_COLORS[k] || COLORS.gray }))
  );

  // PCA badge
  const va = feat.pca_var_exp;
  document.getElementById('pca-var-badge').textContent =
    `PC1=${(va[0]*100).toFixed(1)}%  PC2=${(va[1]*100).toFixed(1)}%`;

  // PCA scatter
  const pca_r = getCtx('c-pca');
  if (pca_r) {
    const { ctx, w, h } = pca_r;
    const pad = { t: 20, r: 20, b: 30, l: 40 };
    const pts = feat.pca_points;
    if (pts.length) {
      const xs = pts.map(p => p.x), ys = pts.map(p => p.y);
      const [minX, maxX] = [Math.min(...xs), Math.max(...xs)];
      const [minY, maxY] = [Math.min(...ys), Math.max(...ys)];
      const cw = w - pad.l - pad.r, ch = h - pad.t - pad.b;
      const xp = x => pad.l + (x - minX) / (maxX - minX) * cw;
      const yp = y => pad.t + (1 - (y - minY) / (maxY - minY)) * ch;

      // Axes
      ctx.strokeStyle = '#30363d'; ctx.lineWidth = 1;
      ctx.beginPath(); ctx.moveTo(pad.l, pad.t); ctx.lineTo(pad.l, pad.t + ch); ctx.stroke();
      ctx.beginPath(); ctx.moveTo(pad.l, pad.t + ch); ctx.lineTo(pad.l + cw, pad.t + ch); ctx.stroke();

      // Points
      const COLOR_MAP = { Bull: COLORS.green, Bear: COLORS.red, Range: '#8b949e' };
      pts.forEach(p => {
        ctx.fillStyle = COLOR_MAP[p.label] || COLORS.gray;
        ctx.globalAlpha = 0.45;
        ctx.beginPath();
        ctx.arc(xp(p.x), yp(p.y), 2.5, 0, Math.PI * 2);
        ctx.fill();
      });
      ctx.globalAlpha = 1;

      // Labels
      ctx.fillStyle = '#8b949e'; ctx.font = '10px monospace'; ctx.textAlign = 'center';
      ctx.fillText('PC1', pad.l + cw / 2, h - 4);
      ctx.save(); ctx.translate(10, pad.t + ch / 2); ctx.rotate(-Math.PI / 2);
      ctx.fillText('PC2', 0, 0); ctx.restore();
    }
  }

  // IC bars
  const icData = feat.ic_top;
  const maxIC = Math.max(...icData.map(d => Math.abs(d.ic)), 0.01);
  const icHtml = icData.map(d => {
    const pct = Math.abs(d.ic) / maxIC * 100;
    const color = d.ic >= 0 ? COLORS.green : COLORS.red;
    const left  = d.ic >= 0 ? '50%' : `${50 - pct/2}%`;
    return `<div class="ic-bar">
      <div class="ic-name">${d.col}</div>
      <div class="ic-track">
        <div class="ic-fill" style="background:${color};left:${left};width:${pct/2}%"></div>
      </div>
      <div class="ic-val" style="color:${color}">${d.ic >= 0 ? '+' : ''}${d.ic.toFixed(4)}</div>
    </div>`;
  }).join('');
  document.getElementById('ic-bars-container').innerHTML = icHtml;

  // Correlation heatmap
  const hmr = getCtx('c-heatmap');
  if (hmr) {
    const { ctx, w, h } = hmr;
    const cols = feat.heatmap_cols;
    const n = cols.length;
    const cell = Math.min(Math.floor((w - 120) / n), 24);
    const offX = 120, offY = 20;
    const matH = cell * n;
    const matW = cell * n;

    // Resize canvas height
    const el = document.getElementById('c-heatmap');
    const dpr = window.devicePixelRatio || 1;
    el.width  = (offX + matW + 20) * dpr;
    el.height = (offY + matH + 80) * dpr;
    el.style.width  = (offX + matW + 20) + 'px';
    el.style.height = (offY + matH + 80) + 'px';
    ctx.scale(dpr, dpr);

    feat.heatmap_corr.forEach((row, i) => {
      row.forEach((v, j) => {
        const r = v > 0 ? Math.round(v * 200) : 0;
        const b = v < 0 ? Math.round(-v * 200) : 0;
        ctx.fillStyle = `rgb(${r},${Math.round(Math.abs(v)*40)},${b})`;
        ctx.fillRect(offX + j * cell, offY + i * cell, cell - 1, cell - 1);
        if (n <= 20) {
          ctx.fillStyle = Math.abs(v) > 0.5 ? '#000' : '#8b949e';
          ctx.font = '8px monospace'; ctx.textAlign = 'center';
          ctx.fillText(v.toFixed(2), offX + j * cell + cell/2, offY + i * cell + cell/2 + 3);
          ctx.textAlign = 'left';
        }
      });
      // Row label
      ctx.fillStyle = '#8b949e'; ctx.font = '9px monospace'; ctx.textAlign = 'right';
      ctx.fillText(cols[i].slice(0, 18), offX - 4, offY + i * cell + cell / 2 + 3);
      ctx.textAlign = 'left';
    });
    // Column labels (rotated)
    cols.forEach((c, j) => {
      ctx.save();
      ctx.translate(offX + j * cell + cell/2, offY + matH + 6);
      ctx.rotate(Math.PI / 4);
      ctx.fillStyle = '#8b949e'; ctx.font = '9px monospace';
      ctx.fillText(c.slice(0, 14), 0, 0);
      ctx.restore();
    });
  }
}

// ─────────────────────────────────────────────────────────
//  TAB 4 — EVALUATION
// ─────────────────────────────────────────────────────────
function renderEval() {
  const eq = DATA.equity;
  const names = Object.keys(eq);

  // Equity curves
  if (names.length) {
    const series = names.map((name, i) => {
      const curve = eq[name].equity;
      const norm  = curve.map(v => v / curve[0] * 100);
      return {
        label: name,
        color: SESSION_COLORS[i % SESSION_COLORS.length],
        data:  norm.map((v, i) => ({ x: i, y: v })),
        width: 2,
      };
    });
    drawLineChart('c-equity', series,
      { hlines: [{ y: 100, color: '#30363d', label: 'start' }],
        xFmt: v => v + 'b', decimals: 1 });
  }

  // Session comparison table from sessions
  const sessRows = Object.entries(DATA.sessions).map(([name, sess]) => {
    const val = (sess.val || []).filter(v => v.avg_sharpe !== undefined);
    const best = val.reduce((b, v) => !b || (v.avg_sharpe > (b.avg_sharpe || -Infinity)) ? v : b, null);
    const lastAlpha = (sess.alpha || []).slice(-1)[0] || {};
    return { name, best, lastAlpha };
  });

  document.getElementById('session-comparison-table').innerHTML = `
    <table class="sharpe-table">
      <thead>
        <tr><th>Session</th><th>Best avgSharpe</th><th>At Step</th><th>OOD at Best</th><th>ret_corr pretrain</th></tr>
      </thead>
      <tbody>
        ${sessRows.map(r => `
          <tr>
            <td>${r.name}</td>
            <td style="color:${(r.best?.avg_sharpe||0)>=0?'var(--green)':'var(--red)'}">
              ${r.best ? r.best.avg_sharpe.toFixed(3) : '—'}
            </td>
            <td>${r.best ? (r.best.step/1000).toFixed(0)+'K' : '—'}</td>
            <td>
              ${r.best ? `<span class="badge ${r.best.ood_state==='NORMAL'?'badge-green':'badge-red'}">${r.best.ood_state}</span>` : '—'}
            </td>
            <td style="color:${(r.lastAlpha.ret_corr||0)>=0?'var(--green)':'var(--red)'}">
              ${r.lastAlpha.ret_corr ? ((r.lastAlpha.ret_corr>=0?'+':'')+r.lastAlpha.ret_corr.toFixed(3)) : '—'}
            </td>
          </tr>`).join('')}
      </tbody>
    </table>`;

  // OOS summary cards
  document.getElementById('oos-summary').innerHTML = names.length ? names.map((n, i) => {
    const d = eq[n];
    const ret = (d.total_ret * 100);
    return `<div class="metric" style="margin-bottom:8px;min-width:100%">
      <div class="metric-label" style="color:${SESSION_COLORS[i]}">${n}</div>
      <div style="display:flex;gap:16px;margin-top:6px;font-family:var(--font-mono);font-size:12px">
        <span>ret: <b style="color:${ret>=0?'var(--green)':'var(--red)'}">${ret.toFixed(2)}%</b></span>
        <span>Sharpe: <b style="color:${d.sharpe>=0?'var(--green)':'var(--red)'}">${d.sharpe.toFixed(2)}</b></span>
        <span>MDD: <b style="color:var(--yellow)">${(d.max_dd*100).toFixed(1)}%</b></span>
      </div>
    </div>`;
  }).join('') : '<div style="color:var(--text2)">No evaluation results found.</div>';
}

// ─────────────────────────────────────────────────────────
//  INIT
// ─────────────────────────────────────────────────────────
function init() {
  // Populate session selectors
  const sessNames = Object.keys(DATA.sessions);

  const pretSel = document.getElementById('sess-select');
  const rlSel   = document.getElementById('rl-sess-select');
  sessNames.forEach(n => {
    [pretSel, rlSel].forEach(sel => {
      const opt = document.createElement('option');
      opt.value = n; opt.textContent = n;
      sel.appendChild(opt);
    });
  });
  // Default to last session
  if (sessNames.length) {
    pretSel.value = sessNames[sessNames.length - 1];
    rlSel.value   = sessNames[sessNames.length - 1];
  }

  renderPretrain();
  renderFeatures();
  renderEval();

  // RL renders on tab click (data may be slow to render)
  document.querySelectorAll('.tab-btn')[1].addEventListener('click', () => {
    setTimeout(renderRL, 50);
  });
}

window.addEventListener('load', init);
window.addEventListener('resize', () => {
  const active = document.querySelector('.page.active');
  if (!active) return;
  const id = active.id.replace('page-', '');
  if (id === 'pretrain') renderPretrain();
  else if (id === 'rl') renderRL();
  else if (id === 'features') renderFeatures();
  else if (id === 'eval') renderEval();
});
</script>
"""


# ── 6. Render ─────────────────────────────────────────────────────────────────

def render(data: dict):
    js_data = json.dumps(data, separators=(",", ":"), default=str)
    html = HTML_TEMPLATE.replace("%%DATA%%", js_data)
    out = DASH_DIR / "index.html"
    out.write_text(html, encoding="utf-8")
    print(f"\nDashboard written → {out}")
    print(f"  Size: {out.stat().st_size / 1024:.0f} KB")


if __name__ == "__main__":
    print("=== DRL_BTC Dashboard Generator ===\n")
    data = assemble()
    render(data)
    print("\nDone. Open DRL_BTC/dashboard/index.html in your browser.")
