'use strict';

document.addEventListener('DOMContentLoaded', function () {
  const navItems = document.querySelectorAll('.nav-item');
  const viewTitle = document.getElementById('view-title');
  const systemStatus = document.getElementById('system-status');
  const overviewView = document.getElementById('overview-view');
  const infoView = document.getElementById('info-view');
  const infoTitle = document.getElementById('info-title');
  const infoText = document.getElementById('info-text');
  const dashboardFrame = document.getElementById('dashboard-frame');
  const phaseGrid = document.getElementById('phase-grid');

  let pipelineState = null;
  let lastStateStr = "";
  let availableResults = [];

  function switchView(viewName) {
    overviewView.style.display = 'none';
    infoView.style.display = 'none';
    dashboardFrame.style.display = 'none';

    if (viewName === 'overview') {
      overviewView.style.display = 'block';
    } else if (viewName === 'info') {
      infoView.style.display = 'block';
    } else if (viewName === 'dashboard') {
      dashboardFrame.style.display = 'block';
    }
  }

  async function fetchState() {
    try {
      const response = await fetch('/check_updates');
      const data = await response.json();
      const stateStr = JSON.stringify(data);

      // Only re-render if something actually changed OR if it's the first load
      if (stateStr !== lastStateStr) {
          // Guard: Don't re-render if the user is actively using a dropdown
          if (document.activeElement && document.activeElement.tagName === 'SELECT') {
              return; 
          }

          pipelineState = data;
          lastStateStr = stateStr;
          await fetchResults();
          renderOverview();
          updateNavStatus();
          updateSystemStatus();
      }
    } catch (err) {
      console.error('Error fetching state:', err);
    }
  }

  async function fetchResults() {
    try {
        const response = await fetch('/list_results');
        availableResults = await response.json();
    } catch (err) {
        console.error('Error fetching results list:', err);
    }
  }

  async function fetchAgentData() {
    try {
      const response = await fetch('/api/agent_console');
      const data = await response.json();
      
      const heartbeatsEl = document.getElementById('agent-heartbeats');
      const historyEl = document.getElementById('agent-history');
      const healthEl = document.getElementById('system-health-log');
      const syncEl = document.getElementById('last-agent-sync');

      if (!heartbeatsEl || !historyEl || !healthEl) return;

      // 1. Render Heartbeats
      heartbeatsEl.innerHTML = Object.entries(data.statuses).map(([name, s]) => {
        const statusClass = `agent-${s.status.toLowerCase()}`;
        return `
          <div class="agent-status-row">
            <span class="agent-name">${name.replace('crypto-', '')}</span>
            <span class="agent-badge ${statusClass}">${s.status}</span>
          </div>
          <div style="font-size: 0.6rem; color: var(--gray); margin-bottom: 8px;">
            ${s.detail || s.action || ''}
          </div>
        `;
      }).join('');

      // 2. Render History
      historyEl.innerHTML = data.history.map(line => {
        return `<div class="history-item">${line}</div>`;
      }).join('');

      // 3. Render Health
      healthEl.textContent = data.health;

      syncEl.textContent = `Last sync: ${new Date().toLocaleTimeString()}`;
    } catch (err) {
      console.error('Error fetching agent data:', err);
    }
  }

  function updateSystemStatus() {
    const running = Object.values(pipelineState.phases).some(p => p.status === 'running');
    systemStatus.textContent = running ? '🟡 System Running...' : '🟢 System Standby';
    systemStatus.style.color = running ? '#fbbf24' : '#22c55e';
  }

  function renderOverview() {
    if (!pipelineState) return;
    phaseGrid.innerHTML = '';
    
    let currentGroup = '';

    Object.entries(pipelineState.phases).forEach(([key, info]) => {
      // Logic for grouping
      const group = key.startsWith('phase_0') ? 'Phase 0: Data Acquisition' : 
                    key.startsWith('phase_1') ? 'Phase 1: Optimization' :
                    key.startsWith('phase_2') ? 'Phase 2: Validation' :
                    key.startsWith('phase_4') ? 'Phase 4: Backtesting' :
                    key.startsWith('phase_5') ? 'Phase 5: Risk Analysis' : 'General';
      
      if (group !== currentGroup) {
        const header = document.createElement('div');
        header.className = 'phase-group-header';
        header.textContent = group;
        phaseGrid.appendChild(header);
        currentGroup = group;
      }

      const card = document.createElement('div');
      card.className = 'phase-card';
      
      const isRunning = info.status === 'running';
      const cleanKey = key.replace('phase_0_', '').replace('_', ' ');
      
      let metaHtml = '';
      if (info.metadata) {
        metaHtml = `
          <div class="meta-box" style="margin-top: 10px; font-size: 0.7rem; color: #94a3b8; background: #0f172a; padding: 8px; border-radius: 4px; border: 1px solid #334155;">
            <div><strong>Tickers:</strong> ${info.metadata.tickers.join(', ')}</div>
            <div><strong>Period:</strong> ${info.metadata.start_date.split(' ')[0]} → ${info.metadata.end_date.split(' ')[0]}</div>
            <div><strong>Candles:</strong> ${info.metadata.candles} (${info.metadata.timeframe})</div>
          </div>
        `;
      }

      // Add Result Selection for applicable phases
      let resultSelectorHtml = '';
      const phasesWithSelection = ['phase_2', 'phase_4', 'phase_5'];
      if (phasesWithSelection.includes(key)) {
        const options = availableResults.map(r => `<option value="${r}">${r}</option>`).join('');
        resultSelectorHtml = `
          <div style="margin-top: 15px;">
            <label style="font-size: 0.7rem; color: var(--gray); display: block; margin-bottom: 5px;">SELECT RESULT DIRECTORY:</label>
            <select id="select-${key}" style="width: 100%; background: #0f172a; color: #f8fafc; border: 1px solid #334155; border-radius: 4px; padding: 6px; font-size: 0.75rem; outline: none;">
              ${options || '<option disabled>No results found in train_results/</option>'}
            </select>
          </div>
        `;
      }
      
      card.innerHTML = `
        <h3 style="text-transform: capitalize;">${cleanKey}</h3>
        <p style="flex: 1;">${info.description}</p>
        ${metaHtml}
        ${resultSelectorHtml}
        <div class="status-row" style="margin-top: 15px;">
          <span class="status-badge status-${info.status}">${info.status}</span>
          <span style="font-size: 0.75rem; color: #64748b;">
            ${info.last_run ? info.last_run : 'Never run'}
          </span>
        </div>
        <div class="controls">
          <button class="btn btn-run" onclick="runPhase('${key}')" ${isRunning ? 'disabled' : ''}>
            ${isRunning ? 'Running...' : 'Run'}
          </button>
          <button class="btn btn-stop" onclick="stopPhase('${key}')" ${!isRunning ? 'disabled' : ''}>
            Stop
          </button>
        </div>
      `;
      phaseGrid.appendChild(card);
    });
  }

  window.runPhase = async function(phase) {
    const selector = document.getElementById(`select-${phase}`);
    const folder = selector ? selector.value : null;

    if (selector && !folder) {
        alert("Please select a result directory first.");
        return;
    }

    try {
      const response = await fetch(`/run/${phase}`, { 
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ folder: folder })
      });
      const result = await response.json();
      if (result.error) alert(result.error);
      fetchState();
    } catch (err) {
      alert('Failed to start phase');
    }
  };

  window.stopPhase = async function(phase) {
    if (!confirm(`Are you sure you want to stop ${phase}?`)) return;
    try {
      const response = await fetch(`/stop/${phase}`, { method: 'POST' });
      const result = await response.json();
      if (result.error) alert(result.error);
      fetchState();
    } catch (err) {
      alert('Failed to stop phase');
    }
  };

  function updateNavStatus() {
    if (!pipelineState) return;
    navItems.forEach(item => {
      const view = item.dataset.view;
      if (!view) return;
      
      const relatedPhases = Object.entries(pipelineState.phases).filter(([k, v]) => k.startsWith(view));
      if (relatedPhases.length > 0) {
        item.classList.remove('completed', 'failed', 'running');
        const anyRunning = relatedPhases.some(([k, v]) => v.status === 'running');
        const allCompleted = relatedPhases.every(([k, v]) => v.status === 'completed');
        
        if (anyRunning) item.classList.add('running');
        else if (allCompleted) item.classList.add('completed');
      }
    });
  }

  navItems.forEach(item => {
    item.addEventListener('click', () => {
      navItems.forEach(i => i.classList.remove('active'));
      item.classList.add('active');
      viewTitle.textContent = item.querySelector('span').textContent;
      localStorage.setItem('activeView', item.dataset.view);

      const view = item.dataset.view;
      const path = item.dataset.path;

      if (view === 'overview') {
        switchView('overview');
        fetchState();
      } else if (view === 'phase_6') {
        switchView('dashboard');
        dashboardFrame.src = '/agent_monitor';
      } else if (view === 'phase_2' || view === 'phase_4' || view === 'phase_5' || view === 'phase_7' || view === 'phase_9' || view === 'phase_10' || view === 'phase_11' || view === 'phase_12') {
        // If clicking from sidebar, show the dashboard frame but don't auto-run
        switchView('dashboard');
        dashboardFrame.src = path;
      } else if (view === 'phase_0') {
        switchView('info');
        infoTitle.textContent = "Data Management & Acquisition";
        
        let html = `
          <div id="data-preview-container" style="background: var(--card); padding: 20px; border-radius: 12px; border: 1px solid var(--border); margin-bottom: 30px; display: none;">
            <h4 id="preview-title" style="color: var(--blue); margin-bottom: 10px;">Dataset Preview</h4>
            <div id="preview-plot" style="width: 100%; height: 350px; background: #0f172a; border-radius: 8px;"></div>
          </div>

          <h3 style="margin-bottom: 16px; font-size: 1rem; color: var(--gray); text-transform: uppercase; letter-spacing: 1px;">Processed "Ready-to-Use" Datasets</h3>
          <div id="processed-grid" style="display: grid; grid-template-columns: repeat(auto-fill, minmax(280px, 1fr)); gap: 16px; text-align: left; margin-bottom: 40px;">
            Loading processed folders...
          </div>

          <h3 style="margin-bottom: 16px; font-size: 1rem; color: var(--gray); text-transform: uppercase; letter-spacing: 1px;">Raw Data Source Review</h3>
          <div id="dataset-grid" style="display: grid; grid-template-columns: repeat(auto-fill, minmax(200px, 1fr)); gap: 16px; text-align: left;">
            Loading parquet stats...
          </div>
        `;
        infoText.innerHTML = html;

        window.previewDataset = function(params, element) {
          // Highlight
          document.querySelectorAll('.data-card').forEach(c => c.classList.remove('selected'));
          element.classList.add('selected');

          const container = document.getElementById('data-preview-container');
          container.style.display = 'block';
          
          const plotDiv = document.getElementById('preview-plot');
          Plotly.purge(plotDiv);
          
          const query = new URLSearchParams(params).toString();
          fetch(`/data_preview?${query}`)
            .then(res => res.json())
            .then(data => {
              if (data.error) {
                alert(data.error);
                return;
              }
              
              document.getElementById('preview-title').textContent = data.title;
              
              const trace = {
                x: data.times,
                y: data.prices,
                type: 'scatter',
                mode: 'lines',
                name: 'Close Price',
                line: { color: '#3b82f6', width: 2 }
              };
              
              const layout = {
                paper_bgcolor: 'rgba(0,0,0,0)',
                plot_bgcolor: 'rgba(0,0,0,0)',
                font: { color: '#94a3b8', size: 10 },
                margin: { l: 40, r: 20, t: 20, b: 40 },
                xaxis: { gridcolor: '#1e293b', zeroline: false },
                yaxis: { gridcolor: '#1e293b', zeroline: false },
                hovermode: 'x unified'
              };
              
              Plotly.newPlot(plotDiv, [trace], layout, { responsive: true, displayModeBar: false });
              container.scrollIntoView({ behavior: 'smooth', block: 'start' });
            });
        };

        // Fetch Processed Datasets
        fetch('/processed').then(res => res.json()).then(data => {
          const grid = document.getElementById('processed-grid');
          let gridHtml = '';
          
          const allProcessed = [
            ...data.trainval.map(d => ({ ...d, type: 'Train/Val' })),
            ...data.trade.map(d => ({ ...d, type: 'Trade' }))
          ];

          if (allProcessed.length === 0) {
            gridHtml = '<div style="color: var(--gray); font-style: italic;">No processed datasets found. Run Phase 0 scripts to generate them.</div>';
          } else {
            allProcessed.forEach(item => {
              const meta = item.metadata;
              const isTrade = item.type === 'Trade';
              gridHtml += `
                <div class="data-card" 
                     onclick="previewDataset({type: 'processed', folder: '${item.folder}', trade: ${isTrade}}, this)"
                     style="background: #1e293b; padding: 16px; border-radius: 8px; border: 1px solid ${isTrade ? '#10b981' : '#3b82f6'}; position: relative; cursor: pointer; transition: all 0.2s;">
                  <span style="position: absolute; top: 12px; right: 12px; font-size: 0.6rem; padding: 2px 6px; border-radius: 4px; background: ${isTrade ? '#064e3b' : '#1e3a8a'}; color: ${isTrade ? '#34d399' : '#60a5fa'}; font-weight: bold; border: 1px solid ${isTrade ? '#34d399' : '#60a5fa'};">
                    ${item.type}
                  </span>
                  <div style="color: #f8fafc; font-weight: 700; font-size: 0.9rem; margin-bottom: 8px; overflow: hidden; text-overflow: ellipsis; white-space: nowrap;" title="${item.folder}">
                    ${item.folder}
                  </div>
                  <div style="font-size: 0.75rem; color: #94a3b8; margin-bottom: 4px;">Tickers: <b>${meta.tickers.join(', ')}</b></div>
                  <div style="font-size: 0.75rem; color: #94a3b8; margin-bottom: 4px;">Range: <b>${meta.start_date.split(' ')[0]} to ${meta.end_date.split(' ')[0]}</b></div>
                  <div style="font-size: 0.75rem; color: #94a3b8; margin-bottom: 4px;">Candles: <b>${meta.candles}</b> (${meta.timeframe})</div>
                  <div style="font-size: 0.7rem; color: #64748b; margin-top: 10px; border-top: 1px solid #334155; padding-top: 8px;">
                    <details onclick="event.stopPropagation()">
                      <summary style="cursor: pointer; color: #3b82f6;">View ${meta.features.length} Indicators</summary>
                      <div style="margin-top: 8px; display: flex; flex-wrap: wrap; gap: 4px;">
                        ${meta.features.map(f => `<span style="background: #0f172a; padding: 2px 5px; border-radius: 3px; font-size: 0.6rem; border: 1px solid #334155;">${f}</span>`).join('')}
                      </div>
                    </details>
                  </div>
                </div>
              `;
            });
          }
          grid.innerHTML = gridHtml;
        });
        
        fetch('/datasets').then(res => res.json()).then(data => {
          const grid = document.getElementById('dataset-grid');
          let gridHtml = '';
          Object.entries(data).forEach(([coin, files]) => {
            files.forEach(f => {
              gridHtml += `
                <div class="data-card" 
                     onclick="previewDataset({type: 'raw', coin: '${coin}', tf: '${f.timeframe}'}, this)"
                     style="background: #1e293b; padding: 16px; border-radius: 8px; border: 1px solid #334155; cursor: pointer; transition: all 0.2s;">
                  <div style="color: #3b82f6; font-weight: 800; font-size: 1.1rem; margin-bottom: 4px;">${coin}</div>
                  <div style="font-size: 0.8rem; color: #94a3b8;">Timeframe: <b>${f.timeframe}</b></div>
                  <div style="font-size: 0.8rem; color: #94a3b8;">Size: ${f.size}</div>
                  <div style="font-size: 0.7rem; color: #64748b; margin-top: 8px; border-top: 1px solid #334155; padding-top: 8px;">
                    <details onclick="event.stopPropagation()">
                      <summary style="cursor: pointer; color: #94a3b8; font-size: 0.65rem;">Raw Columns</summary>
                      <div style="font-size: 0.6rem; color: #64748b; margin-top: 4px;">
                        OHLCV, Volume, Quote Vol, Trades, Taker Vol
                      </div>
                    </details>
                  </div>
                  <div style="font-size: 0.6rem; color: #475569; margin-top: 4px;">Modified: ${f.last_modified}</div>
                </div>
              `;
            });
          });
          grid.innerHTML = gridHtml;
        });
      } else {
        switchView('info');
        infoTitle.textContent = `${view.toUpperCase()} Tools`;
        infoText.textContent = `Control script execution for ${view} from the Pipeline Overview.`;
      }
    });
  });

  const savedView = localStorage.getItem('activeView');
  if (savedView) {
    const savedItem = document.querySelector(`[data-view="${savedView}"]`);
    if (savedItem) savedItem.click();
  }

  fetchState();
  fetchAgentData();
  setInterval(fetchState, 2000);
  setInterval(fetchAgentData, 5000);
});
