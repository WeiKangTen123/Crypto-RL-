import os, sys
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', 'core'))

import optuna
import joblib
import numpy as np
import scipy.stats as stats
import plotly.graph_objects as go
import plotly.io as pio
from datetime import datetime

_PROJECT_ROOT  = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
_DASHBOARD_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'validation_dashboard')


class StudyAnalyzer:
    def __init__(self, pickle_result: str):
        self.pickle_result = pickle_result
        self.study = joblib.load(
            os.path.join(_PROJECT_ROOT, 'train_results', pickle_result, 'study.pkl'))
        self.best_trial = self.study.best_trial
        os.makedirs(_DASHBOARD_DIR, exist_ok=True)

    # ── helpers ────────────────────────────────────────────────────────────────
    @staticmethod
    def _ci(data, confidence=0.95):
        a = np.array(data, dtype=float)
        n = len(a)
        m = float(np.mean(a))
        if n < 2 or float(np.std(a)) == 0:
            return m, 0.0
        se = stats.sem(a)
        h  = float(se * stats.t.ppf((1 + confidence) / 2., n - 1))
        return m, h

    @staticmethod
    def _badge(label, value, color):
        return f"""
        <div class="badge" style="background:{color}20;border:1.5px solid {color};color:{color}">
            <span class="badge-label">{label}</span>
            <span class="badge-value">{value}</span>
        </div>"""

    # ── main ───────────────────────────────────────────────────────────────────
    def analyze(self):
        sharpe_drl  = np.array(self.best_trial.user_attrs['sharpe_list_bot'],  dtype=float)
        sharpe_hodl = np.array(self.best_trial.user_attrs['sharpe_list_ewq'],  dtype=float)
        n_splits    = len(sharpe_drl)
        mean_drl    = float(np.mean(sharpe_drl))
        mean_hodl   = float(np.mean(sharpe_hodl))
        edge        = mean_drl - mean_hodl
        n_trials    = len(self.study.trials)
        best_value  = float(self.study.best_value)
        ci_drl      = self._ci(sharpe_drl)
        ci_hodl     = self._ci(sharpe_hodl)

        if float(np.std(sharpe_drl)) > 0 and float(np.std(sharpe_hodl)) > 0:
            tt    = stats.ttest_ind(sharpe_drl, sharpe_hodl, equal_var=True)
            pval  = round(float(tt.pvalue), 4)
            tstat = round(float(tt.statistic), 4)
            sig   = pval < 0.05
        else:
            pval, tstat, sig = 'n/a', 'n/a', False

        zero_drl = float(np.std(sharpe_drl)) == 0 and mean_drl == 0

        print(f"Best Trial : #{self.best_trial.number}")
        print(f"Sharpe DRL : {np.round(sharpe_drl,  4)}")
        print(f"Sharpe HODL: {np.round(sharpe_hodl, 4)}")
        print(f"Edge       : {round(edge, 4)}")
        print(f"p-value    : {pval}")

        # ── figures ────────────────────────────────────────────────────────────
        splits = [f"Split {i+1}" for i in range(n_splits)]

        # 1. Sharpe per split
        win_count = int(np.sum(sharpe_drl > sharpe_hodl))
        fig_sharpe = go.Figure()
        fig_sharpe.add_trace(go.Bar(
            x=splits, y=list(sharpe_drl),
            name='DRL Bot', marker_color='#3182ce',
            text=[f'{v:.3f}' for v in sharpe_drl], textposition='outside'))
        fig_sharpe.add_trace(go.Bar(
            x=splits, y=list(sharpe_hodl),
            name='Buy & Hold', marker_color='#e53e3e',
            text=[f'{v:.3f}' for v in sharpe_hodl], textposition='outside'))
        fig_sharpe.add_hline(y=0, line_dash='dash', line_color='gray', line_width=1)
        fig_sharpe.update_layout(
            barmode='group', template='plotly_white',
            yaxis_title='Sharpe Ratio', xaxis_title='CPCV Split',
            legend=dict(orientation='h', y=1.12),
            margin=dict(t=20, b=40))

        # 2. Optimization history
        fig_opt = optuna.visualization.plot_optimization_history(self.study)
        fig_opt.update_layout(template='plotly_white', margin=dict(t=20, b=40))

        # 3. Param importance
        completed_trials = [t for t in self.study.trials if t.state == optuna.trial.TrialState.COMPLETE]
        if len(completed_trials) > 1:
            fig_imp = optuna.visualization.plot_param_importances(self.study)
        else:
            fig_imp = go.Figure()
            fig_imp.add_annotation(text="Parameter importance requires > 1 completed trial", showarrow=False, font=dict(size=16))
        fig_imp.update_layout(template='plotly_white', margin=dict(t=20, b=40))

        # 4. Parallel coords
        fig_par = optuna.visualization.plot_parallel_coordinate(self.study)
        fig_par.update_layout(template='plotly_white', margin=dict(t=20, b=40))

        # 5. CI comparison
        fig_ci = go.Figure()
        for label, m, h, color in [
            ('DRL Bot',    ci_drl[0],  ci_drl[1],  '#3182ce'),
            ('Buy & Hold', ci_hodl[0], ci_hodl[1], '#e53e3e'),
        ]:
            fig_ci.add_trace(go.Scatter(
                x=[label], y=[m],
                error_y=dict(type='data', array=[h], visible=True, color=color),
                mode='markers',
                marker=dict(size=18, color=color, symbol='circle'),
                name=label))
        fig_ci.add_hline(y=0, line_dash='dot', line_color='gray')
        fig_ci.update_layout(
            template='plotly_white',
            yaxis_title='Mean Sharpe ± 95% CI',
            margin=dict(t=20, b=40))

        # ── HTML ───────────────────────────────────────────────────────────────
        def embed(fig, first=False):
            return pio.to_html(fig, full_html=False,
                               include_plotlyjs='cdn' if first else False)

        edge_color  = '#276749' if edge > 0 else '#c53030'
        sig_color   = '#276749' if sig else '#c05621'
        warn_block  = f"""
        <div class="alert alert-warn">
            ⚠️ <strong>All DRL Sharpe values are zero.</strong>
            The agent is not trading — it is holding cash every step.
            This means the reward signal was too small to learn from.
            <strong>Suggested fix:</strong> increase <code>norm_reward</code>
            (currently {self.best_trial.params.get('norm_reward', 'n/a')}) or
            review the environment's reward scaling.
        </div>""" if zero_drl else ""

        best_params_rows = ''.join(
            f'<tr><td>{k}</td><td><strong>{round(v,6) if isinstance(v,float) else v}</strong></td></tr>'
            for k, v in self.best_trial.params.items())

        html = f"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>CPCV Validation Dashboard</title>
<style>
  :root {{
    --blue:   #2b6cb0; --blue-light: #ebf8ff;
    --green:  #276749; --green-light:#f0fff4;
    --red:    #c53030; --red-light:  #fff5f5;
    --yellow: #c05621; --yellow-light:#fffaf0;
    --gray:   #718096; --bg: #f7fafc; --card: #ffffff;
    --radius: 12px; --shadow: 0 2px 16px rgba(0,0,0,.08);
  }}
  * {{ box-sizing:border-box; margin:0; padding:0; }}
  body {{ font-family:-apple-system,BlinkMacSystemFont,'Segoe UI',sans-serif;
          background:var(--bg); color:#1a202c; line-height:1.6; }}

  /* ── header ── */
  header {{
    background: linear-gradient(135deg,#1a365d 0%,#2b6cb0 60%,#4299e1 100%);
    color:#fff; padding:36px 48px;
  }}
  header h1 {{ font-size:2rem; font-weight:800; letter-spacing:-.5px; }}
  header .sub {{ margin-top:6px; opacity:.8; font-size:.95rem; }}
  header .meta {{ margin-top:14px; display:flex; gap:24px; flex-wrap:wrap; }}
  header .meta span {{
    background:rgba(255,255,255,.15); border-radius:20px;
    padding:4px 14px; font-size:.85rem; }}

  /* ── layout ── */
  .container {{ max-width:1400px; margin:0 auto; padding:32px 24px; }}
  .grid-2 {{ display:grid; grid-template-columns:1fr 1fr; gap:24px; }}
  .grid-3 {{ display:grid; grid-template-columns:repeat(3,1fr); gap:16px; }}
  @media(max-width:900px){{
    .grid-2,.grid-3{{grid-template-columns:1fr;}}
  }}

  /* ── cards ── */
  .card {{
    background:var(--card); border-radius:var(--radius);
    box-shadow:var(--shadow); padding:28px; margin-bottom:0;
  }}
  .card-header {{
    display:flex; align-items:center; gap:10px;
    margin-bottom:16px; padding-bottom:12px;
    border-bottom:2px solid #e2e8f0;
  }}
  .card-header h2 {{ font-size:1.05rem; font-weight:700; color:#2d3748; }}
  .card-header .icon {{ font-size:1.3rem; }}
  .section-gap {{ display:flex; flex-direction:column; gap:24px; }}

  /* ── interp boxes ── */
  .interp {{
    background:#f7fafc; border-left:4px solid #4299e1;
    border-radius:0 8px 8px 0; padding:12px 16px;
    font-size:.88rem; color:#2d3748; margin-top:12px;
  }}
  .interp strong {{ color:#2b6cb0; }}

  /* ── alerts ── */
  .alert {{ border-radius:8px; padding:14px 18px; font-size:.9rem; margin-bottom:24px; }}
  .alert-warn {{ background:var(--yellow-light); border-left:5px solid #ed8936; color:#7b341e; }}
  .alert-good {{ background:var(--green-light);  border-left:5px solid #48bb78; color:#22543d; }}
  .alert-info {{ background:var(--blue-light);   border-left:5px solid #4299e1; color:#2c5282; }}

  /* ── stat badges ── */
  .badges {{ display:flex; gap:12px; flex-wrap:wrap; margin-bottom:20px; }}
  .badge {{
    border-radius:10px; padding:10px 18px; display:flex;
    flex-direction:column; align-items:center; min-width:110px;
  }}
  .badge-label {{ font-size:.75rem; font-weight:600; text-transform:uppercase;
                  letter-spacing:.5px; opacity:.75; }}
  .badge-value  {{ font-size:1.3rem; font-weight:800; margin-top:2px; }}

  /* ── table ── */
  table {{ width:100%; border-collapse:collapse; font-size:.9rem; }}
  th {{ background:#2b6cb0; color:#fff; padding:10px 14px; text-align:left; }}
  td {{ padding:9px 14px; border-bottom:1px solid #e2e8f0; }}
  tr:last-child td {{ border-bottom:none; }}
  tr:nth-child(even) td {{ background:#f7fafc; }}

  /* ── phase timeline ── */
  .timeline {{ display:flex; gap:0; margin-bottom:8px; }}
  .tl-step {{
    flex:1; text-align:center; padding:10px 4px;
    font-size:.8rem; font-weight:600; position:relative;
  }}
  .tl-step.active {{ background:#2b6cb0; color:#fff; border-radius:8px; }}
  .tl-step.done   {{ background:#e2e8f0; color:#718096; }}
  .tl-step.next   {{ background:#ebf8ff; color:#2b6cb0; border:1.5px dashed #4299e1; border-radius:8px; }}
</style>
</head>
<body>

<header>
  <h1>📊 CPCV Validation Dashboard</h1>
  <div class="sub">{self.pickle_result}</div>
  <div class="meta">
    <span>🗓 Generated: {datetime.now().strftime('%Y-%m-%d %H:%M')}</span>
    <span>🔁 Trials: {n_trials}</span>
    <span>📐 CPCV Splits: {n_splits}</span>
    <span>🏆 Best Trial: #{self.best_trial.number}</span>
    <span>⚡ Algorithm: PPO</span>
  </div>
</header>

<div class="container">

  <!-- Pipeline position -->
  <div class="card" style="margin-bottom:24px">
    <div class="card-header"><span class="icon">🗺</span><h2>Where You Are in the Pipeline</h2></div>
    <div class="timeline">
      <div class="tl-step done">Phase 0<br>Data</div>
      <div class="tl-step done">Phase 1<br>CPCV Optimise</div>
      <div class="tl-step active">Phase 2<br>✅ Validate</div>
      <div class="tl-step next">Phase 4<br>Backtest</div>
      <div class="tl-step next">Phase 5<br>PBO Analysis</div>
    </div>
    <div class="interp">
      <strong>Validation</strong> checks whether the best hyperparameters found by CPCV are statistically
      meaningful — not just a lucky fit to one time period. We compare the RL bot's Sharpe ratio against
      a simple buy-and-hold benchmark across all {n_splits} cross-validation splits.
    </div>
  </div>

  {warn_block}

  <!-- Key metrics -->
  <div class="card" style="margin-bottom:24px">
    <div class="card-header"><span class="icon">📌</span><h2>Key Metrics</h2></div>
    <div class="badges">
      {self._badge("Edge (DRL−HODL)", round(edge,4), edge_color)}
      {self._badge("Mean Sharpe DRL",  round(mean_drl,4),  "#3182ce")}
      {self._badge("Mean Sharpe HODL", round(mean_hodl,4), "#e53e3e")}
      {self._badge("Splits Won", f"{win_count}/{n_splits}", "#6b46c1")}
      {self._badge("p-value", pval, sig_color)}
      {self._badge("t-stat",  tstat, "#718096")}
    </div>
    <div class="interp">
      <strong>Edge</strong> = Mean Sharpe(DRL) − Mean Sharpe(Buy&Hold). Positive = bot outperforms on average. &nbsp;|&nbsp;
      <strong>p-value &lt; 0.05</strong> means the outperformance is statistically significant (not random). &nbsp;|&nbsp;
      <strong>Splits Won</strong> = number of the {n_splits} CPCV time windows where the bot beat buy-and-hold.
      {'⚠️ p-value is not applicable because Sharpe variance is zero.' if pval == 'n/a' else
       ('✅ Result is statistically significant.' if sig else '⚠️ Result is NOT statistically significant — may be due to chance.')}
    </div>
  </div>

  <!-- Sharpe comparison + CI -->
  <div class="grid-2" style="margin-bottom:24px">
    <div class="card">
      <div class="card-header"><span class="icon">📊</span><h2>Sharpe Ratio per CPCV Split</h2></div>
      {embed(fig_sharpe, first=True)}
      <div class="interp">
        Each pair of bars is one <strong>CPCV time window</strong>. Blue = DRL bot, Red = buy-and-hold.
        A good model should have <em>blue consistently higher than red</em> across most splits.
        If all blues are zero, the agent is not placing trades — reward normalisation needs adjustment.
        <br><br>
        <strong>What to look for:</strong> consistent outperformance across splits, not just one lucky window.
        Consistency across time is the whole point of CPCV.
      </div>
    </div>
    <div class="card">
      <div class="card-header"><span class="icon">🎯</span><h2>95% Confidence Interval Comparison</h2></div>
      {embed(fig_ci)}
      <div class="interp">
        The dot shows the <strong>mean Sharpe</strong>; the error bar spans the 95% confidence interval.
        If the two confidence intervals <em>do not overlap</em>, the difference is statistically meaningful.
        Overlapping intervals suggest the result could be random.
        <br><br>
        <strong>What to look for:</strong> DRL CI entirely above HODL CI, and both CIs above zero.
      </div>
    </div>
  </div>

  <!-- Optuna optimization history -->
  <div class="card section-gap" style="margin-bottom:24px">
    <div class="card-header"><span class="icon">📈</span><h2>Optuna Optimization History</h2></div>
    {embed(fig_opt)}
    <div class="interp">
      This chart shows how the <strong>objective value improved</strong> across {n_trials} Optuna trials.
      The objective is <code>mean Sharpe(DRL) − mean Sharpe(HODL)</code>.
      <br><br>
      <strong>Green dots</strong> = new best found. <strong>Blue dots</strong> = completed trials (not best).
      A rising best-value line means Optuna is learning which hyperparameters work.
      A flat line after many trials means the search has converged.
      <br><br>
      <strong>What to look for:</strong> an upward trend early on, then convergence. If the line never improves,
      the hyperparameter search space may need adjustment.
    </div>
  </div>

  <!-- Param importance + parallel -->
  <div class="grid-2" style="margin-bottom:24px">
    <div class="card">
      <div class="card-header"><span class="icon">🔍</span><h2>Hyperparameter Importance</h2></div>
      {embed(fig_imp)}
      <div class="interp">
        Computed using <strong>functional ANOVA</strong> — how much variance in the objective
        is explained by each hyperparameter.
        <br><br>
        <strong>High importance</strong> = tuning this parameter moves the needle significantly.
        <strong>Low importance</strong> = the model is robust to this parameter's value.
        <br><br>
        <strong>What to look for:</strong> focus future tuning effort on the top 2–3 parameters.
        If <code>learning_rate</code> or <code>batch_size</code> dominate, try a finer search grid for them.
      </div>
    </div>
    <div class="card">
      <div class="card-header"><span class="icon">🌐</span><h2>Hyperparameter Parallel Coordinates</h2></div>
      {embed(fig_par)}
      <div class="interp">
        Each <strong>line</strong> is one trial; colour indicates the objective value (brighter = higher = better).
        Vertical axes show hyperparameter values.
        <br><br>
        <strong>What to look for:</strong> bright lines that share a similar path indicate a
        <em>promising region</em> — e.g. most high-value trials may cluster at a specific learning rate.
        This tells you where to focus if you run more trials.
      </div>
    </div>
  </div>

  <!-- Best trial params table -->
  <div class="card" style="margin-bottom:24px">
    <div class="card-header"><span class="icon">🏆</span><h2>Best Trial — Hyperparameters</h2></div>
    <p style="font-size:.9rem;color:#718096;margin-bottom:14px">
      Trial #{self.best_trial.number} achieved the highest objective value of
      <strong style="color:{edge_color}">{round(best_value,6)}</strong>.
      These are the hyperparameters to use in the backtest.
    </p>
    <table>
      <thead><tr><th>Hyperparameter</th><th>Value</th></tr></thead>
      <tbody>{best_params_rows}</tbody>
    </table>
    <div class="interp" style="margin-top:14px">
      <strong>learning_rate</strong> — how fast the PPO agent updates its weights. Too high = unstable, too low = slow learning.<br>
      <strong>batch_size</strong> — number of experiences used per gradient update. Larger = more stable but slower.<br>
      <strong>gamma</strong> — discount factor for future rewards. Closer to 1 = agent values long-term gains more.<br>
      <strong>net_dimension</strong> — width of the neural network layers. Larger = more capacity but needs more data.<br>
      <strong>target_step</strong> — steps of environment interaction per training iteration.<br>
      <strong>break_step</strong> — total training steps before stopping each split's training.<br>
      <strong>norm_reward</strong> — scales the reward signal. Too small → agent sees near-zero reward → learns nothing.
    </div>
  </div>

  <!-- Next steps -->
  <div class="card">
    <div class="card-header"><span class="icon">➡️</span><h2>Next Steps</h2></div>
    <div class="alert alert-info">
      {"🔴 <strong>Action required before backtest:</strong> DRL Sharpe is all zero — the agent is not trading. "
       "Increase <code>norm_reward</code> in <code>config_main.py → ENV_PARAMS_CCXT</code> (try 2⁻⁵ instead of 2⁻¹⁰) "
       "and re-run <code>phase_1/optimize_cpcv.py</code>."
       if zero_drl else
       "✅ <strong>Results look valid.</strong> Proceed to <code>phase_4/backtest.py</code> to run the agent "
       "on the held-out test period (2024-07 → 2026-04) and measure real out-of-sample performance."}
    </div>
    <ol style="padding-left:20px;font-size:.93rem;line-height:2">
      {'<li><strong>Fix reward normalisation</strong> — update norm_reward in sample_hyperparams()</li><li><strong>Re-run</strong> phase_1/optimize_cpcv.py</li><li><strong>Re-run</strong> this validate step</li>'
       if zero_drl else
       '<li>Run <code>./venv/bin/python phase_4/backtest.py</code></li><li>Review the backtest chart and metrics in <code>plots_and_metrics/</code></li><li>Run <code>phase_5/pbo.py</code> for Probability of Backtest Overfitting analysis</li>'}
    </ol>
  </div>

</div>
</body>
</html>"""

        out_path = os.path.join(_DASHBOARD_DIR, 'dashboard.html')
        with open(out_path, 'w') as f:
            f.write(html)
        print(f"\n✅ Dashboard saved → {out_path}")
        print("Open it in your browser.\n")


if __name__ == "__main__":
    if len(sys.argv) > 1:
        pickle_result = sys.argv[1]
    else:
        pickle_result = input("Enter pickle result dir: ")
    
    StudyAnalyzer(pickle_result).analyze()
