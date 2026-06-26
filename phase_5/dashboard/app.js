'use strict';

document.addEventListener('DOMContentLoaded', function () {
  const D = window.PBO_DATA;
  if (!D) {
    document.body.innerHTML = '<p style="padding:40px;color:red">pbo_data.js not found — run pbo.py first.</p>';
    return;
  }

  const colors = ['#3182ce', '#e53e3e', '#38a169', '#805ad5', '#d69e2e'];

  // ── Header metadata ───────────────────────────────────────────────────────
  document.getElementById('h-generated').textContent = '🕒 ' + D.metadata.generated;
  document.getElementById('h-results-count').textContent = '📁 ' + D.metadata.results_processed + ' Results Processed';

  // ── AI Executive Summary ──────────────────────────────────────────────────
  if (D.results.length > 0 && D.results[0].interpretation) {
    const ai = D.results[0].interpretation;
    const summaryCard = document.getElementById('exec-summary-card');
    if (summaryCard) {
        summaryCard.style.display = 'block';
        
        const parseBold = str => str.replace(/\*\*(.*?)\*\*/g, '<strong>$1</strong>');
        
        document.getElementById('ai-pbo').innerHTML = '<strong>1. PBO Score: </strong> ' + parseBold(ai.pbo_eval);
        document.getElementById('ai-logits').innerHTML = '<strong>2. Logits Hump: </strong> ' + parseBold(ai.logits_eval);
        document.getElementById('ai-robust').innerHTML = '<strong>3. Robustness Verdict: </strong> ' + parseBold(ai.robust_eval);
        document.getElementById('ai-regime').innerHTML = '<strong>4. Regime Attribution: </strong> ' + parseBold(ai.regime_eval);
        document.getElementById('ai-verdict').innerHTML = parseBold(ai.verdict);
    }
  }

  // ── PBO Cards ─────────────────────────────────────────────────────────────
  const summaryContainer = document.getElementById('pbo-summary');
  const robustContainer = document.getElementById('robust-container');
  const regimeContainer = document.getElementById('regime-container');

  D.results.forEach((res, idx) => {
    const accent = colors[idx % colors.length];

    // 1. PBO Card
    const card = document.createElement('div');
    card.className = 'pbo-card';
    let pboColor = '#16a34a'; 
    if (res.pbo > 40) pboColor = '#dc2626';
    else if (res.pbo > 15) pboColor = '#ca8a04';
    
    card.innerHTML = `
      <div class="model-name">${res.name}</div>
      <div class="pbo-value" style="color: ${pboColor}">${res.pbo.toFixed(1)}%</div>
      <div class="pbo-label">Prob. of Backtest Overfitting</div>
    `;
    summaryContainer.appendChild(card);

    // 2. Robustness Card
    if (res.robustness) {
        const rob = res.robustness;
        const robCard = document.createElement('div');
        robCard.className = 'pbo-card';
        robCard.style.borderLeft = `5px solid ${accent}`;
        
        let statusText = rob.no_outlier_mean_ret > 0 ? '✅ ROBUST' : '⚠️ FRAGILE';
        let statusColor = rob.no_outlier_mean_ret > 0 ? '#16a34a' : '#dc2626';

        robCard.innerHTML = `
          <div class="model-name">${res.name} ${statusText}</div>
          <div style="display:flex; flex-direction:column; gap:8px; margin-top:15px;">
            <div style="display:flex; justify-content:space-between;">
                <span style="color:#64748b; font-size:0.75rem; font-weight:700;">ORIGINAL MEAN RET:</span>
                <span style="font-weight:800;">${rob.original_mean_ret.toFixed(4)}%</span>
            </div>
            <div style="display:flex; justify-content:space-between;">
                <span style="color:#64748b; font-size:0.75rem; font-weight:700;">WITHOUT TOP 5%:</span>
                <span style="font-weight:800; color:${statusColor};">${rob.no_outlier_mean_ret.toFixed(4)}%</span>
            </div>
            <div style="display:flex; justify-content:space-between; margin-top:10px; padding-top:10px; border-top:1px dashed #e2e8f0;">
                <span style="color:#64748b; font-size:0.75rem; font-weight:700;">OUTLIER IMPACT:</span>
                <span style="font-weight:800;">${rob.outlier_impact_ratio.toFixed(2)}x</span>
            </div>
          </div>
        `;
        robustContainer.appendChild(robCard);

        // 3. Regime Card
        const reg = rob.regimes;
        const regCard = document.createElement('div');
        regCard.className = 'pbo-card';
        regCard.style.borderLeft = `5px solid ${accent}`;

        regCard.innerHTML = `
          <div class="model-name">${res.name} Attribution</div>
          <div style="display:flex; flex-direction:column; gap:12px; margin-top:15px;">
            <div style="border-bottom: 1px solid #f1f5f9; padding-bottom: 10px;">
                <div style="display:flex; justify-content:space-between;">
                    <span style="color:#64748b; font-size:0.7rem; font-weight:700;">HIGH VOLATILITY:</span>
                    <span style="font-weight:800; color:${reg.high_vol_mean >=0 ? '#16a34a':'#dc2626'}">${reg.high_vol_mean.toFixed(4)}%</span>
                </div>
                <div style="display:flex; justify-content:space-between; margin-top:4px;">
                    <span style="color:#64748b; font-size:0.7rem; font-weight:700;">LOW VOLATILITY:</span>
                    <span style="font-weight:800; color:${reg.low_vol_mean >=0 ? '#16a34a':'#dc2626'}">${reg.low_vol_mean.toFixed(4)}%</span>
                </div>
            </div>
            <div>
                <div style="display:flex; justify-content:space-between;">
                    <span style="color:#64748b; font-size:0.7rem; font-weight:700;">BULL (POS BARS):</span>
                    <span style="font-weight:800; color:#16a34a">${reg.positive_regime_mean.toFixed(4)}%</span>
                </div>
                <div style="display:flex; justify-content:space-between; margin-top:4px;">
                    <span style="color:#64748b; font-size:0.7rem; font-weight:700;">BEAR (NEG BARS):</span>
                    <span style="font-weight:800; color:#dc2626">${Math.abs(reg.negative_regime_mean).toFixed(4)}%</span>
                </div>
            </div>
          </div>
        `;
        regimeContainer.appendChild(regCard);
    }
  });

  // ── Logits Chart ──────────────────────────────────────────────────────────
  const traces = D.results.map((res, idx) => {
    return {
      x: res.logits,
      name: res.name,
      type: 'histogram',
      histnorm: 'probability density',
      opacity: 0.6,
      nbinsx: 30,
      marker: { color: colors[idx % colors.length] },
      autobinx: true
    };
  });

  // Add a vertical line at 0
  const layout = {
    template: 'plotly_white',
    hovermode: 'x unified',
    xaxis: { 
      title: 'Logits (Relative OOS Rank)',
      zeroline: false
    },
    yaxis: { title: 'Probability Density' },
    barmode: 'overlay',
    legend: { orientation: 'h', y: 1.12 },
    margin: { t: 40, b: 60, l: 60, r: 20 },
    shapes: [{
      type: 'line',
      x0: 0,
      y0: 0,
      x1: 0,
      yref: 'paper',
      y1: 1,
      line: {
        color: 'red',
        width: 3,
        dash: 'dashdot'
      }
    }]
  };

  Plotly.newPlot('chart-logits', traces, layout);
});
