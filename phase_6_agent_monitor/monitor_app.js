'use strict';

// HTML-escape helper — prevents XSS and broken rendering from log content
function esc(str) {
    return String(str)
        .replace(/&/g, '&amp;')
        .replace(/</g, '&lt;')
        .replace(/>/g, '&gt;');
}

let _activeDossierId = null; // Track open agent for real-time infographic sync

// Preferred starting model per agent (to detect fallback)
const PREFERRED_MODELS = {
    fullstack:  'gemini-2.5-flash',
    data:       'gemini-3.1-flash-lite-preview',
    researcher: 'gemini-3.1-pro-preview',
    developer:  'gemini-2.5-flash',
    qa:         'gemini-2.5-flash-lite',
    tuner:      'gemini-2.5-flash',
};

// ─────────────────────────────────────────────
//  MAIN POLL
// ─────────────────────────────────────────────
let _activeStageIndex = null;

async function updateTelemetry() {
    try {
        const response = await fetch('/api/agent_telemetry');
        if (!response.ok) {
            throw new Error(`Server Error: ${response.status} ${response.statusText}`);
        }
        const data = await response.json();
        window.latestTelemetry = data;

        // 1. System metrics
        if (data.system) {
            document.getElementById('disk-val').textContent = data.system.disk_free_gb || '--';
            document.getElementById('pid-val').textContent = data.system.active_python_processes || '--';
            document.getElementById('system-time').textContent = `LAST_SYNC: ${data.system.last_update || '??'}`;
        }

        // 1b. ALPHA_FORGE_V2 Pipeline
        if (data.pipeline_stats) {
            for (let i=0; i<=5; i++) {
                const el = document.getElementById(`val-stage-${i}`);
                if (el) {
                    const val = data.pipeline_stats[`stage${i}`] || 0;
                    el.textContent = val;
                    el.className = 'stage-val' + (val === 0 ? ' val-zero' : val > 20 ? ' val-high' : '');
                }
                // Agent dot — update live status
                const dotEl = document.getElementById(`stage-dot-${i}`);
                if (dotEl && STAGE_AGENT[i]) {
                    const agentHb = (data.heartbeats || {})[STAGE_AGENT[i].key] || {};
                    const st = agentHb.status || 'OFFLINE';
                    const act = agentHb.action || 'Idle';
                    const isWorking = act !== 'Idle' && act !== 'N/A' && act.includes('[');
                    
                    let dotClass = 'dot-offline';
                    if (st === 'ONLINE' || st === 'ACTIVE') {
                        dotClass = isWorking ? 'dot-active' : 'dot-idle';
                    } else if (st === 'STANDBY') {
                        dotClass = 'dot-idle';
                    }
                    
                    dotEl.className = 'stage-agent-dot ' + dotClass;
                    dotEl.title = `${STAGE_AGENT[i].key}: ${st} (${act})`;
                }
                // Bottleneck — flag stages 1-7 above threshold
                if (i > 0) {
                    const stageEl = document.getElementById(`stage-${i}`);
                    const val = data.pipeline_stats[`stage${i}`] || 0;
                    if (stageEl) {
                        const isJam = val > STAGE_BOTTLENECK_THRESHOLD;
                        stageEl.classList.toggle('stage-bottleneck', isJam);
                        let warnEl = stageEl.querySelector('.bottleneck-warn');
                        if (isJam && !warnEl) {
                            warnEl = document.createElement('div');
                            warnEl.className = 'bottleneck-warn';
                            warnEl.textContent = '⚠ JAM';
                            stageEl.appendChild(warnEl);
                        } else if (!isJam && warnEl) {
                            warnEl.remove();
                        }
                    }
                }
            }
            // Stage-0 sub-label: built/pending
            const sub0 = document.getElementById('stage-0-sub');
            if (sub0) {
                const built    = data.pipeline_stats.stage0_built    || 0;
                const rejected = data.pipeline_stats.stage0_rejected || 0;
                const pending  = data.pipeline_stats.stage0_pending  || 0;
                sub0.textContent = `${built} Impl · ${rejected} Rejected · ${pending} Pending`;
            }
            // Update Graveyard count — BAD/ERROR strategies + QA failures + dead letters
            const gvEl = document.getElementById('val-stage-graveyard');
            if (gvEl) {
                const gvCount = data.pipeline_stats.graveyard || 0;
                gvEl.textContent = gvCount;
                gvEl.className = 'stage-val' + (gvCount === 0 ? ' val-zero' : ' text-danger');
            }
            // Conversion funnel
            updatePipelineFunnel(data.pipeline_stats);

            // Refresh open stage modal if active
            if (_activeStageIndex !== null) {
                refreshStageModal(_activeStageIndex);
            }
        }

        // 2. Global health badge in header
        updateGlobalHealthBadge(data.health_summary || {});

        // 3. Agent cards
        const agents = [
            { id: 'fullstack',  key: 'crypto-fullstack' },
            { id: 'data',       key: 'crypto-data-engineer' },
            { id: 'researcher', key: 'alpha-researcher' },
            { id: 'developer',  key: 'alpha-developer' },
            { id: 'tuner',      key: 'crypto-strategy-tuner' },
            { id: 'qa',         key: 'crypto-qa-tester' }
        ];
        agents.forEach(agent => {
            try {
                const hb = data.heartbeats[agent.key] || { status: 'OFFLINE', action: 'N/A' };
                updateAgent(
                    agent.id,
                    data.logs[agent.id] || [],
                    hb,
                    data.error_counts || {},
                    data.health_summary || {},
                    (data.watcher_pids || {})[agent.id] || { pid: null, alive: false }
                );
                // Inbox badge
                const cnt = (data.inbox_counts || {})[agent.key] || 0;
                const ib = document.getElementById(`inbox-badge-${agent.id}`);
                if (ib) {
                    ib.textContent = `${cnt} MSG`;
                    ib.style.display = cnt > 0 ? 'inline-block' : 'none';
                }
                // Last-seen
                const lsEl = document.getElementById(`last-seen-${agent.id}`);
                if (lsEl && lsEl.textContent !== timeAgo(hb.ts)) {
                    lsEl.textContent = timeAgo(hb.ts);
                }

                // --- Live Dossier Sync ---
                if (_activeDossierId === agent.id) {
                    renderDossierProgress(agent.id, hb);
                    document.getElementById('modal-focus').textContent = hb.action || "Idle";
                    
                    const isWorking = hb.action && hb.action !== 'Idle' && hb.action !== 'N/A' && hb.action.includes('[');
                    const isOnline  = hb.status === "ONLINE" || hb.status === "ACTIVE";
                    
                    document.getElementById('modal-mode').textContent  = isOnline ? (isWorking ? "ACTIVE_DUTY" : "IDLE_READY") : "OFFLINE";
                    document.getElementById('modal-mode').style.background = isOnline ? (isWorking ? "#10b981" : "#f59e0b") : "#ef4444";
                }
            } catch (err) {
                console.error(`Error updating agent ${agent.id}:`, err);
            }
        });

        // 4. HIGH priority alert banner
        updateAlertBanner(data.inbox_messages || [], data.active_flags || []);

        // 5. Health Scout log
        const healthFeed = document.getElementById('health-feed');
        if (healthFeed && data.logs.health) {
            const newHealth = data.logs.health.map(line => {
                const cls = line.includes('[ERROR]') ? 'line-error' :
                            line.includes('[WARN]')  ? 'line-warn'  :
                            line.includes('[OK]')    ? 'line-ok'    : '';
                return `<div class="line ${cls}">${esc(line)}</div>`;
            }).join('');
            if (healthFeed.innerHTML !== newHealth) {
                const atBottom = healthFeed.scrollTop + healthFeed.clientHeight >= healthFeed.scrollHeight - 5;
                healthFeed.innerHTML = newHealth;
                if (atBottom) healthFeed.scrollTop = healthFeed.scrollHeight;
            }
        }

        // 6. Collaboration Ledger
        const collabFeed = document.getElementById('collab-feed');
        if (collabFeed && data.collab) {
            const newCollab = data.collab.map(line => {
                if (line.startsWith('##')) {
                    return `<div class="line collab-section">${esc(line)}</div>`;
                }
                if (line.startsWith('|---') || line.trim() === '---') return '';
                if (line.includes('|')) {
                    const cells = line.split('|').map(c => c.trim()).filter(c => c.length > 0);
                    const statusCls = (cells[3] || '').includes('COMPLETE') ? 'line-ok' :
                                      (cells[3] || '').includes('ISSUES')   ? 'line-warn' : '';
                    const notes = cells[4] ? ` <span style="opacity:0.6">${esc(cells[4])}</span>` : '';
                    return `<div class="line collab-entry ${statusCls}"><span class="highlight">${esc(cells[0] || '')}</span> | ${esc(cells[1] || '')} | ${esc(cells[2] || '')} | ${esc(cells[3] || '')}${notes}</div>`;
                }
                return line.trim() ? `<div class="line">${esc(line)}</div>` : '';
            }).join('');
            if (collabFeed.innerHTML !== newCollab) {
                const savedScroll = collabFeed.scrollTop;
                const atBottom = collabFeed.scrollTop + collabFeed.clientHeight >= collabFeed.scrollHeight - 20;
                const isEmpty = collabFeed.scrollHeight <= collabFeed.clientHeight;
                collabFeed.innerHTML = newCollab;
                requestAnimationFrame(() => {
                    if (isEmpty || atBottom) {
                        collabFeed.scrollTop = collabFeed.scrollHeight;
                    } else {
                        collabFeed.scrollTop = savedScroll;
                    }
                });
            }
        }

        // 7. Model Usage Monitor
        if (data.model_usage) {
            updateModelUsage(data.model_usage);
        }

        // 7b. Strategy Tuner Panel
        if (data.scan_results !== undefined) {
            updateTunerPanel(data.scan_results);
        }

        // 7c. Network modal (only redraws if open)
        updateNetworkModal();

        // 8. Activity Timeline
        if (data.timeline) {
            updateTimeline('fullstack',  data.timeline.fullstack  || []);
            updateTimeline('data',       data.timeline.data       || []);
            updateTimeline('researcher', data.timeline.researcher || []);
            updateTimeline('developer',  data.timeline.developer  || []);
            updateTimeline('qa',         data.timeline.qa         || []);
        }

        // 9. Cross-Agent Inbox (pending)
        const protocolFeed = document.getElementById('protocol-feed');
        if (protocolFeed) {
            const msgs = data.inbox_messages || [];
            const newProto = msgs.length === 0
                ? '<div class="line" style="opacity:0.5">No pending inbox messages</div>'
                : msgs.map(msg => renderInboxCard(msg, false)).join('');
            if (protocolFeed.innerHTML !== newProto) {
                const savedScroll = protocolFeed.scrollTop;
                protocolFeed.innerHTML = newProto;
                requestAnimationFrame(() => { protocolFeed.scrollTop = savedScroll; });
            }
        }

        // 10. System Changelog
        const syslogFeed = document.getElementById('syslog-feed');
        if (syslogFeed && data.system_changelog) {
            updateSystemChangelog(data.system_changelog);
        }

        // 11. QA Results log
        const qaFeed = document.getElementById('qa-feed');
        if (qaFeed && data.qa_results) {
            updateQAFeed(data.qa_results);
        }

        // 12. Inbox Archive (resolved)
        const archiveFeed = document.getElementById('archive-feed');
        if (archiveFeed) {
            const resolved = data.resolved_inbox || [];
            const newArchive = resolved.length === 0
                ? '<div class="line" style="opacity:0.5">No resolved messages yet</div>'
                : resolved.map(msg => renderInboxCard(msg, true)).join('');
            if (archiveFeed.innerHTML !== newArchive) {
                const savedScroll = archiveFeed.scrollTop;
                archiveFeed.innerHTML = newArchive;
                requestAnimationFrame(() => { archiveFeed.scrollTop = savedScroll; });
            }
        }

        window.latestTelemetry = data;

    } catch (e) {
        console.error("Telemetry Sync Error:", e);
    }
}

// ─────────────────────────────────────────────
//  FEATURE 3 — HIGH PRIORITY ALERT BANNER
// ─────────────────────────────────────────────
function updateAlertBanner(inboxMsgs, activeFlags) {
    const banner = document.getElementById('alert-banner');
    const highMsgs = inboxMsgs.filter(m => m.priority === 'HIGH');

    // Also surface STALE_CRITICAL / ANOMALY flags
    const critFlags = activeFlags.filter(f =>
        f.flag && (f.flag.includes('STALE_CRITICAL') || f.flag.includes('ANOMALY') || f.flag.includes('CRITICAL'))
    );

    const items = [
        ...highMsgs.map(m =>
            `<span class="alert-item"><span class="alert-prio">⚠ HIGH</span><span class="alert-topic">${esc(m.topic || '')}</span> <span class="alert-from">← ${esc(m.from || '')} → ${esc(m._to || '')}</span></span>`
        ),
        ...critFlags.map(f =>
            `<span class="alert-item"><span class="alert-prio">🚨 FLAG</span><span class="alert-topic">${esc(f.flag)}</span> <span class="alert-from">${esc(f.details || '').slice(0, 60)}</span></span>`
        )
    ];

    if (items.length > 0) {
        banner.innerHTML = '⚡ ALERT: ' + items.join('&ensp;|&ensp;');
        banner.style.display = 'block';
    } else {
        banner.style.display = 'none';
    }
}

// ─────────────────────────────────────────────
//  FEATURE 2 & 4 & 7 — AGENT CARD BADGES
// ─────────────────────────────────────────────
function updateGlobalHealthBadge(summary) {
    const el = document.getElementById('health-badge-global');
    if (!el) return;
    const { errors = 0, warns = 0, oks = 0 } = summary;
    if (errors > 0) {
        el.textContent = `${errors}E ${warns}W`;
        el.className = 'health-badge-global hbg-err';
    } else if (warns > 0) {
        el.textContent = `${warns}W ${oks}OK`;
        el.className = 'health-badge-global hbg-warn';
    } else {
        el.textContent = `${oks} OK`;
        el.className = 'health-badge-global hbg-ok';
    }
}

function updateAgent(id, logs, heartbeat, errorCounts, healthSummary, watcherPid = {}) {
    const body     = document.getElementById(`log-${id}`);
    const statusEl = document.getElementById(`status-${id}`);
    const card     = document.getElementById(`term-${id}`);

    if (!card || !statusEl || !body) return;

    if (!card.dataset.hasListener) {
        card.addEventListener('click', () => openDossier(id));
        card.dataset.hasListener = "true";
    }

    const status = heartbeat.status || 'OFFLINE';
    const action = heartbeat.action || 'Idle';
    const isWorking = action !== 'Idle' && action !== 'N/A' && action.includes('[');
    const badgeStatus = (status === 'ONLINE' && !isWorking) ? 'IDLE' : status;

    // Staleness check — if ONLINE but heartbeat ts > 120s old, flag as stale
    const hbAge = heartbeat.ts ? (Date.now() - new Date(heartbeat.ts).getTime()) / 1000 : 0;
    const isStale = (status === 'ONLINE' || status === 'STANDBY') && hbAge > 120;
    
    statusEl.textContent = isStale ? 'STALE' : status;
    statusEl.className = `agent-status status-${isStale ? 'stale' : badgeStatus.toLowerCase()}`;
    statusEl.style.cursor = 'pointer';
    statusEl.title = isStale
        ? `⚠ No heartbeat for ${Math.round(hbAge)}s — agent may be hung or crashed`
        : status === 'ONLINE' ? 'Click to STOP' : 'Click to go ACTIVE';

    // Status badge click = quick toggle (OFFLINE/STANDBY → active, ONLINE → offline)
    if (!statusEl.dataset.hasHandshake) {
        statusEl.addEventListener('click', (e) => {
            e.stopPropagation();
            const s = statusEl.textContent.trim();
            if (s === 'ONLINE') setAgentMode(id, 'offline');
            else setAgentMode(id, 'active');
        });
        statusEl.dataset.hasHandshake = 'true';
    }

    // Control buttons + scheduler toggle — only re-render when status changes
    const ctrlsEl = document.getElementById(`controls-${id}`);
    if (ctrlsEl && (ctrlsEl.dataset.currentStatus !== status || !ctrlsEl.dataset.currentStatus)) {
        ctrlsEl.dataset.currentStatus = status;
        const s          = status.toUpperCase();
        const isOffline  = s === 'OFFLINE';
        const schedOn    = s === 'ONLINE';
        const nextLabel  = heartbeat.next_run_at ? heartbeat.next_run_at : '—';

        ctrlsEl.innerHTML =
            // Row 1 — mode buttons
            `<div class="ctrl-row" onclick="event.stopPropagation()">` +
                `<button class="ctrl-btn ctrl-active${s === 'ONLINE' ? ' is-current' : ''}" onclick="event.stopPropagation();setAgentMode('${id}','active')" title="Full autonomous — scheduled tasks + inbox">ACTIVE</button>` +
                `<button class="ctrl-btn ctrl-standby${s === 'STANDBY' ? ' is-current' : ''}" onclick="event.stopPropagation();setAgentMode('${id}','standby')" title="Inbox-only — no scheduled tasks">STANDBY</button>` +
                `<button class="ctrl-btn ctrl-stop${s === 'OFFLINE' ? ' is-current' : ''}" onclick="event.stopPropagation();setAgentMode('${id}','offline')" title="Kill agent process">STOP</button>` +
            `</div>` +
            // Row 2 — scheduler toggle
            `<div class="sched-row" onclick="event.stopPropagation()">` +
                `<span class="sched-label">SCHEDULER</span>` +
                `<label class="sched-toggle ${isOffline ? 'sched-disabled' : ''}" title="${isOffline ? 'Start agent first' : schedOn ? 'Scheduler ON — click to pause' : 'Scheduler OFF — click to resume'}" onclick="event.stopPropagation()">` +
                    `<input type="checkbox" ${schedOn ? 'checked' : ''} ${isOffline ? 'disabled' : ''}` +
                    ` onclick="event.stopPropagation();setAgentMode('${id}', this.checked ? 'active' : 'standby')">` +
                    `<span class="sched-pill"></span>` +
                `</label>` +
                `<span class="sched-status ${schedOn ? 'sched-on' : isOffline ? 'sched-off' : 'sched-paused'}">` +
                    `${schedOn ? 'ON' : isOffline ? 'N/A' : 'PAUSED'}` +
                `</span>` +
                `${schedOn ? `<span class="sched-next">next ${nextLabel}</span>` : ''}` +
            `</div>`;
    }

    // Keep next_run_at live — update sched-next without full re-render
    if (heartbeat.next_run_at) {
        const nextEl = ctrlsEl?.querySelector('.sched-next');
        if (nextEl) nextEl.textContent = `next ${heartbeat.next_run_at}`;
    }

    const actionEl = card.querySelector('.agent-action') || createActionEl(card);
    const lastAction = heartbeat.last_action && heartbeat.last_action !== action
        ? ` | last: ${heartbeat.last_action}` : '';
    const nextRun = heartbeat.next_run_at ? ` | next: ${heartbeat.next_run_at}` : '';
    const pidText = watcherPid.alive && watcherPid.pid
        ? ` | PID: ${watcherPid.pid}` : '';
    actionEl.textContent = action + lastAction + nextRun + pidText;

    if (status === "ONLINE" && heartbeat.action && heartbeat.action.toLowerCase() !== "idle") {
        card.classList.add('is-working');
    } else {
        card.classList.remove('is-working');
    }

    // Colour-coded by event type — infrastructure vs Gemini working output
    const newContent = logs.map(line => {
        const cls = /═══.*ONLINE/.test(line)                           ? 'log-online'  :
                    /═══.*OFFLINE/.test(line)                          ? 'log-offline' :
                    /✓ GEMINI DONE/.test(line)                         ? 'log-done'    :
                    /▶ GEMINI START/.test(line)                        ? 'log-start'   :
                    /⚠ Quota hit/.test(line)                           ? 'log-quota'   :
                    /📥 INBOX/.test(line)                               ? 'log-inbox'   :
                    /⏰ SCHEDULED/.test(line)                           ? 'log-sched'   :
                    /\[ERROR\]|Error executing/.test(line)              ? 'log-error'   :
                    /✗ /.test(line)                                     ? 'log-error'   :
                    /\| RESULT\b|\| VALIDATED\b/.test(line)            ? 'log-done'    :
                    /\| FIXING\b|\| REPAIRING\b|\| DEVELOPING\b/.test(line) ? 'log-start' :
                    /\| ESCALATING\b/.test(line)                       ? 'log-quota'   : 'log-gemini';
        return `<div class="line log-line ${cls}">${esc(line)}</div>`;
    }).join('');
    if (body.innerHTML !== newContent) {
        body.innerHTML = newContent;
        body.scrollTop = body.scrollHeight;
    }

    // ── Feature 4: Model badge ──
    const modelBadge = document.getElementById(`model-badge-${id}`);
    if (modelBadge) {
        const model = heartbeat.model || '--';
        modelBadge.textContent = model === '--' ? 'NO_MODEL' : model.replace('gemini-', 'g-');
        const preferred = PREFERRED_MODELS[id];
        if (model !== '--' && preferred && model !== preferred) {
            modelBadge.classList.add('fallback');
            modelBadge.title = `Fell back from ${preferred}`;
        } else {
            modelBadge.classList.remove('fallback');
            modelBadge.title = `Model: ${model}`;
        }
    }

    // ── Feature 2: Health badge (data agent gets real health; qa has its own score badge; others N/A) ──
    const healthBadge = document.getElementById(`health-badge-${id}`);
    if (healthBadge && id !== 'qa') {
        if (id === 'data') {
            const { errors = 0, warns = 0, oks = 0 } = healthSummary;
            if (errors > 0) {
                healthBadge.textContent = `${errors}E · ${warns}W`;
                healthBadge.className = 'badge badge-health has-error';
            } else if (warns > 0) {
                healthBadge.textContent = `${warns}W · ${oks}OK`;
                healthBadge.className = 'badge badge-health has-warn';
            } else {
                healthBadge.textContent = `${oks} OK`;
                healthBadge.className = 'badge badge-health';
            }
        } else {
            healthBadge.textContent = 'N/A';
            healthBadge.className = 'badge badge-health';
        }
    }

    // ── Agent Task Progress (1-2-3-4) ──
    if (id === 'developer' || id === 'researcher') {
        updateAgentProgress(id, heartbeat);
    }

    // ── Feature 7: Error count badge ──
    const errBadge = document.getElementById(`error-badge-${id}`);
    if (errBadge) {
        const cnt = errorCounts[id] || 0;
        errBadge.textContent = cnt > 0 ? `${cnt} ERR/1h` : '0 ERR';
        errBadge.className = cnt > 0 ? 'badge badge-error has-errors' : 'badge badge-error';
        errBadge.title = `${cnt} error(s) in the last hour`;
    }

    // ── Tuner scan badge ──
    if (id === 'tuner') {
        const scanBadge = document.getElementById('tuner-scan-badge');
        if (scanBadge && window.latestTelemetry?.scan_results?.total) {
            const sr = window.latestTelemetry.scan_results;
            scanBadge.textContent = `${sr.GOOD||0}G ${sr.MEDIOCRE||0}M ${sr.BAD||0}B`;
            scanBadge.className   = (sr.BAD||0) > 0 ? 'badge badge-tuner-scan has-bad'
                                  : (sr.MEDIOCRE||0) > 0 ? 'badge badge-tuner-scan has-med'
                                  : 'badge badge-tuner-scan';
        }
    }
}

function updateAgentProgress(id, heartbeat) {
    const container = document.getElementById(`progress-${id}`);
    if (!container) return;

    // Hide for developer (overview only) as requested — detail available in click tab
    if (id === 'developer') {
        container.style.display = 'none';
        return;
    }

    const status = heartbeat.status || 'OFFLINE';
    const action = heartbeat.action || 'Idle';
    const match = action.match(/\[(\d+)\/(\d+)\]/);

    if (!match && status !== 'WORKING') {
        container.style.display = 'none';
        return;
    }
    
    container.style.display = 'block';

    let currentStep = 0;
    let stepStatus = 'active'; 
    
    if (match) currentStep = parseInt(match[1]);
    if (action.includes('FAILED') || action.includes('✗')) stepStatus = 'fail';
    else if (action.includes('COMPLETE') || action.includes('✓')) stepStatus = 'done';

    // Define steps based on agent type
    const steps = id === 'developer' 
        ? [{ n: 1, label: 'INGEST' }, { n: 2, label: 'BUILD' }, { n: 3, label: 'SYNTAX' }, { n: 4, label: 'SMOKE' }]
        : [{ n: 1, label: 'SEARCH' }, { n: 2, label: 'EXTRACT' }, { n: 3, label: 'HYPHO' }, { n: 4, label: 'INDEX' }];

    container.innerHTML = `
        <span class="progress-label">${id.toUpperCase()} STEP ${currentStep || '?'}: ${esc(action.split(']')[1] || action)}</span>
        <div class="progress-stepper">
            ${steps.map(s => {
                let cls = '';
                if (s.n < currentStep) cls = 'step-done';
                else if (s.n === currentStep) {
                    if (stepStatus === 'fail') cls = 'step-fail';
                    else if (stepStatus === 'done') cls = 'step-done';
                    else cls = 'step-active';
                }
                return `<div class="step-node ${cls}" title="${s.label}">${s.n}</div>`;
            }).join('')}
        </div>
    `;
}

// ─────────────────────────────────────────────
//  MODEL USAGE MONITOR
// ─────────────────────────────────────────────
const MODEL_COLORS = {
    'gemini-3.1-pro-preview':        '#c084fc',  // purple  — heaviest (researcher)
    'gemini-2.5-flash':              '#60a5fa',  // blue    — balanced
    'gemini-3.1-flash-lite-preview': '#34d399',  // teal    — newer lite
    'gemini-2.5-flash-lite':         '#86efac',  // green   — lightest
};

function updateModelUsage(rows) {
    const tbody   = document.getElementById('model-usage-body');
    const summary = document.getElementById('model-usage-summary');
    if (!tbody) return;

    if (!rows || rows.length === 0) {
        tbody.innerHTML = '<tr><td colspan="8" style="opacity:0.5;text-align:center">No runs yet — bring agents online</td></tr>';
        if (summary) summary.textContent = '0 models';
        return;
    }

    if (summary) {
        const totalCalls = rows.reduce((s, r) => s + r.calls, 0);
        summary.textContent = `${rows.length} models · ${totalCalls} total calls`;
    }

    const totalCalls2 = rows.reduce((s, r) => s + r.calls, 0);

    tbody.innerHTML = rows.map(r => {
        const color      = MODEL_COLORS[r.model] || '#9ca3af';
        const shortModel = r.model.replace('gemini-', 'g-');
        const avgFmt     = r.avg_secs > 0 ? `${r.avg_secs}s` : '--';
        const totalFmt   = r.completed > 0 ? `${Math.round(r.avg_secs * r.completed / 60)}m` : '--';
        const quotaCls   = r.quota_hits > 0 ? 'mu-quota-hit' : '';
        const agentLabel = r.agent ? `@${r.agent}` : '--';
        const barPct     = totalCalls2 > 0 ? Math.round(r.calls / totalCalls2 * 100) : 0;

        return `<tr>
            <td><span class="mu-model-name" style="color:${color}">${esc(shortModel)}</span>
                <div class="mu-bar-wrap"><div class="mu-bar" style="width:${barPct}%;background:${color}22;border-color:${color}55"></div></div>
            </td>
            <td class="mu-num">${r.calls}</td>
            <td class="mu-num">${r.completed}</td>
            <td class="mu-num">${avgFmt}</td>
            <td class="mu-num">${totalFmt}</td>
            <td class="mu-num ${quotaCls}">${r.quota_hits > 0 ? '⚠ ' + r.quota_hits : '0'}</td>
            <td class="mu-ts">${esc(r.last_used || '--')}</td>
            <td class="mu-agent">${esc(agentLabel)}</td>
        </tr>`;
    }).join('');
}

// ─────────────────────────────────────────────
//  BACKTEST QUICK-RUN MODAL
// ─────────────────────────────────────────────
function openBtModal(sid, strat, coin, tf) {
    document.getElementById('bt-modal-title').textContent = `▶ ${strat} | ${coin} | ${tf}`;
    document.getElementById('bt-modal').dataset.sid  = sid;
    document.getElementById('bt-modal').dataset.coin = coin;
    document.getElementById('bt-modal').dataset.tf   = tf;
    document.getElementById('bt-results').innerHTML  = '';
    document.getElementById('bt-run-btn').disabled   = false;
    document.getElementById('bt-run-btn').textContent = '▶ RUN BACKTEST';
    document.getElementById('bt-modal').style.display = 'block';
}

function closeBtModal() {
    document.getElementById('bt-modal').style.display = 'none';
}

async function runLeaderboardBacktest() {
    const modal   = document.getElementById('bt-modal');
    const sid     = modal.dataset.sid;
    const results = document.getElementById('bt-results');
    const btn     = document.getElementById('bt-run-btn');
    const from    = document.getElementById('bt-date-from').value;
    const to      = document.getElementById('bt-date-to').value;

    btn.disabled    = true;
    btn.textContent = '⏳ Running...';
    results.innerHTML = '<div class="bt-loading">Running backtest — this may take 10–30s...</div>';

    try {
        const r = await fetch('/api/strategy_backtest', {
            method:  'POST',
            headers: { 'Content-Type': 'application/json' },
            body:    JSON.stringify({ strategy_ids: [sid], date_from: from, date_to: to })
        });
        const data = await r.json();

        if (data.error) {
            results.innerHTML = `<div class="bt-error">Error: ${esc(data.error)}</div>`;
        } else if (!data.results || data.results.length === 0) {
            results.innerHTML = `<div class="bt-error">No results returned — strategy may require a working venv.</div>`;
        } else {
            const res    = data.results[0];
            const m      = res.metrics || {};
            const sharpe = parseFloat(m['Sharpe Ratio'])  || 0;
            const ret    = parseFloat(m['Total Return'])   || 0;
            const dd     = parseFloat(m['Max Drawdown %']) || 0;
            const wr     = parseFloat(m['Win Rate'])       || 0;
            const trades = parseInt(m['Total Trades'])     || 0;
            // PF may be "∞" string — handle safely
            const pfRaw  = m['Profit Factor'];
            const pfIsInf = pfRaw === '∞' || parseFloat(pfRaw) >= 99;
            const pf     = pfIsInf ? 99 : (parseFloat(pfRaw) || 0);
            const pfDisp = pfIsInf ? '∞' : pf.toFixed(2);

            const sharpeC = sharpe >= 1.0 ? 'bt-good' : sharpe >= 0.3 ? 'bt-warn' : 'bt-bad';
            const retC    = ret    >= 100  ? 'bt-good' : ret    >= 0   ? 'bt-warn' : 'bt-bad';
            const ddC     = dd     <  20   ? 'bt-good' : dd     <  50  ? 'bt-warn' : 'bt-bad';
            const wrC     = wr     >= 55   ? 'bt-good' : wr     >= 40  ? 'bt-warn' : 'bt-bad';
            const trC     = trades >= 100  ? 'bt-good' : trades >= 30  ? 'bt-warn' : 'bt-bad';
            const pfC     = pf     >= 1.5  ? 'bt-good' : pf     >= 1.0 ? 'bt-warn' : 'bt-bad';

            results.innerHTML = `
                <div class="bt-metrics-grid">
                    <div class="bt-metric"><span class="bt-label">SHARPE</span>
                        <span class="bt-val ${sharpeC}">${sharpe.toFixed(2)}</span></div>
                    <div class="bt-metric"><span class="bt-label">RETURN</span>
                        <span class="bt-val ${retC}">${ret.toFixed(1)}%</span></div>
                    <div class="bt-metric"><span class="bt-label">MAX DD</span>
                        <span class="bt-val ${ddC}">${dd.toFixed(1)}%</span></div>
                    <div class="bt-metric"><span class="bt-label">WIN RATE</span>
                        <span class="bt-val ${wrC}">${wr.toFixed(1)}%</span></div>
                    <div class="bt-metric"><span class="bt-label">TRADES</span>
                        <span class="bt-val ${trC}">${trades}</span></div>
                    <div class="bt-metric"><span class="bt-label">PROFIT FACTOR</span>
                        <span class="bt-val ${pfC}">${pfDisp}</span></div>
                </div>
                <div class="bt-period">Period: ${esc(from)} → ${esc(to)} · ${esc(res.class || sid)} <span style="opacity:0.5">#${esc(sid)}</span></div>`;
        }
    } catch (e) {
        results.innerHTML = `<div class="bt-error">Request failed: ${esc(String(e))}</div>`;
    }

    btn.disabled    = false;
    btn.textContent = '▶ RUN AGAIN';
}

window.addEventListener('click', e => {
    if (e.target === document.getElementById('bt-modal')) closeBtModal();
});

// ─────────────────────────────────────────────
//  FEATURE 5 — ACTIVITY TIMELINE
// ─────────────────────────────────────────────
function updateTimeline(id, events) {
    const track = document.getElementById(`lane-${id}`);
    if (!track) return;
    track.innerHTML = '';
    events.forEach(evt => {
        const dot = document.createElement('div');
        dot.className = `tl-dot tl-${evt.type}`;
        dot.style.left = `${Math.min(Math.max(evt.pct, 0.5), 99.5)}%`;
        dot.title = `${evt.ts} — ${evt.msg}`;
        track.appendChild(dot);
    });
    if (events.length === 0) {
        track.innerHTML = '<span style="font-size:0.55rem;opacity:0.3;padding-left:8px">no events</span>';
    }
}

// ─────────────────────────────────────────────
//  FEATURE 6 — INBOX CARD RENDERER (pending + archive)
// ─────────────────────────────────────────────
function renderInboxCard(msg, isResolved) {
    const prioCls = msg.priority === 'HIGH'   ? 'inbox-high' :
                    msg.priority === 'MEDIUM' ? 'inbox-med'  : 'inbox-low';
    const resolvedCls = isResolved ? ' inbox-resolved' : '';
    const activeCls = !isResolved && msg._status === 'PROCESSING' ? ' inbox-processing' : '';

    // Graceful fallback for non-standard message formats
    const sender = msg.from || (msg._file ? msg._file.split('_from_')[1]?.split('_')[0] || 'system' : 'system');
    const topic  = msg.topic   || msg.summary?.slice(0, 60) || '(no topic)';
    const body   = msg.message || msg.summary  || msg.recommendation || '(no message body)';

    const statusLabel = !isResolved ? `<span class="inbox-status">${esc(msg._status || 'PENDING')}</span>` : '';
    const resolvedAt  = isResolved && msg._resolved_at
        ? `<div class="inbox-resolved-at">✓ resolved ${esc(msg._resolved_at.slice(0, 16).replace('T', ' '))}</div>`
        : '';

    return `<div class="inbox-msg ${prioCls}${resolvedCls}${activeCls}">` +
        `<div class="inbox-header">` +
            `<span class="inbox-route">${esc(sender)} → ${esc(msg._to || '?')}</span>` +
            statusLabel +
            `<span class="inbox-prio">${esc(msg.priority || 'LOW')}</span>` +
        `</div>` +
        `<div class="inbox-topic">${esc(topic)}</div>` +
        `<div class="inbox-body">${esc(body)}</div>` +
        resolvedAt +
    `</div>`;
}

// ─────────────────────────────────────────────
//  COLLAPSIBLE SECTIONS
// ─────────────────────────────────────────────
function toggleSection(id) {
    const body   = document.getElementById(`body-${id}`);
    const toggle = document.getElementById(`toggle-${id}`);
    if (!body) return;
    const collapsed = body.classList.toggle('collapsed');
    if (toggle) toggle.textContent = collapsed ? '▶' : '▼';
}

// ─────────────────────────────────────────────
//  DOSSIER MODAL
// ─────────────────────────────────────────────
function openDossier(agentId) {
    if (!window.latestTelemetry) return;
    _activeDossierId = agentId;
    const modal    = document.getElementById('agent-modal');
    const agentKey = agentId === 'fullstack'  ? 'crypto-fullstack'     :
                     agentId === 'data'       ? 'crypto-data-engineer' :
                     agentId === 'researcher' ? 'alpha-researcher'     :
                     agentId === 'developer'  ? 'alpha-developer'      :
                     agentId === 'tuner'      ? 'crypto-strategy-tuner' :
                                                'crypto-qa-tester';
    const hb   = window.latestTelemetry.heartbeats[agentKey] || { status: 'OFFLINE', action: 'N/A' };
    const logs = window.latestTelemetry.logs[agentId] || [];

    document.getElementById('modal-agent-name').textContent = `@${agentKey.toUpperCase()}_DOSSIER`;
    document.getElementById('modal-focus').textContent  = hb.action || "Idle";
    document.getElementById('modal-mode').textContent   = hb.status === "ONLINE" ? "ACTIVE_DUTY" : "OFFLINE";
    document.getElementById('modal-mode').style.background = hb.status === "ONLINE" ? "#10b981" : "#ef4444";

    const inboxCounts = (window.latestTelemetry.inbox_counts || {});
    const inboxCount  = inboxCounts[agentKey] || 0;
    const inboxEl     = document.getElementById('modal-inbox-list');
    inboxEl.innerHTML = inboxCount > 0
        ? `<li>${inboxCount} message(s) pending</li>`
        : '<li>No pending messages</li>';

    const errorCount = (window.latestTelemetry.error_counts || {})[agentId] || 0;
    const modelInfo  = hb.model ? `Model: ${hb.model}` : (hb.next_run_at ? `Next: ${hb.next_run_at}` : 'None');
    document.getElementById('modal-tools-list').textContent =
        modelInfo + (errorCount > 0 ? ` · ${errorCount} err/1h` : '');

    // ── LIVE TASK EVOLUTION (Infographic) ──
    renderDossierProgress(agentId, hb);

    const logEl = document.getElementById('modal-extended-log');
    logEl.innerHTML = logs.map(l => {
        const isMilestone = /\[\d+\/\d+\]/.test(l);
        const milestoneIcon = isMilestone ? '<span class="milestone-bullet">⬢</span> ' : '';
        
        const cls = isMilestone                        ? 'log-milestone' :
                    /═══.*ONLINE/.test(l)              ? 'log-online'  :
                    /═══.*OFFLINE/.test(l)             ? 'log-offline' :
                    /✓ GEMINI DONE/.test(l)            ? 'log-done'    :
                    /▶ GEMINI START/.test(l)           ? 'log-start'   :
                    /⚠ Quota hit/.test(l)              ? 'log-quota'   :
                    /📥 INBOX/.test(l)                  ? 'log-inbox'   :
                    /\[ERROR\]|Error executing/.test(l) ? 'log-error'   : 'log-gemini';
        return `<div class="line log-line ${cls}">${milestoneIcon}${esc(l)}</div>`;
    }).join('');

    // Changes log for this agent
    const changesEl = document.getElementById('modal-changes-log');
    if (changesEl) {
        const changesLines = ((window.latestTelemetry.changes_logs || {})[agentId] || []);
        changesEl.innerHTML = changesLines.length === 0
            ? '<div class="line" style="opacity:0.4">No changes logged yet</div>'
            : changesLines.map(l => {
                const action = l.match(/\]\s+(MODIFIED|FIXED|CREATED|DELETED|REPAIRED|REVERTED|TESTED|REGISTERED|OPTIMIZED|PATCHED)/)?.[1] || '';
                const cls = action === 'FIXED'    ? 'cl-fixed'    :
                            action === 'CREATED'  ? 'cl-created'  :
                            action === 'DELETED'  ? 'cl-deleted'  :
                            action === 'REVERTED' ? 'cl-reverted' :
                            action === 'TESTED'   ? 'cl-tested'   :
                            action === 'REGISTERED' || action === 'OPTIMIZED' ? 'cl-registered' :
                            'cl-modified';
                return `<div class="line ${cls}">${esc(l)}</div>`;
            }).join('');
    }

    // Session log (Reasoning & Background Output) — renders session_memory.md Markdown
    const sessionEl = document.getElementById('modal-session-log');
    if (sessionEl) {
        const sessionLines = ((window.latestTelemetry.session_logs || {})[agentId] || []);
        if (sessionLines.length === 0) {
            sessionEl.innerHTML = '<div class="line" style="opacity:0.4">No session background data</div>';
        } else {
            sessionEl.innerHTML = sessionLines.map(l => {
                const s = esc(l);
                // --- divider
                if (/^---+\s*$/.test(l.trim()))
                    return '<hr style="border:none;border-top:1px solid #334155;margin:6px 0">';
                // ## heading
                if (/^\s*##\s/.test(l))
                    return `<div style="color:#67e8f9;font-weight:700;margin-top:8px;font-size:0.72rem">${s.replace(/^#+\s*/, '')}</div>`;
                // # heading
                if (/^\s*#\s/.test(l))
                    return `<div style="color:#7dd3fc;font-weight:700;margin-top:6px;font-size:0.7rem;opacity:0.6">${s.replace(/^#+\s*/, '')}</div>`;
                // empty line
                if (l.trim() === '' || l.trim() === '_No sessions recorded yet._')
                    return '<div style="height:4px"></div>';
                // inline Markdown: **bold**, _italic_, `code`
                const rendered = s
                    .replace(/\*\*(.+?)\*\*/g, '<strong style="color:#e2e8f0">$1</strong>')
                    .replace(/_(.+?)_/g, '<em style="color:#94a3b8">$1</em>')
                    .replace(/`(.+?)`/g, '<code style="background:#1e293b;padding:0 3px;border-radius:2px;color:#7dd3fc">$1</code>');
                return `<div class="line" style="color:#94a3b8;overflow-wrap:break-word;word-break:break-word">${rendered}</div>`;
            }).join('');
        }
    }

    modal.style.display = 'block';
}

function renderDossierProgress(id, heartbeat) {
    const container = document.getElementById('modal-progress-container');
    const stepper   = document.getElementById('modal-task-stepper');
    if (!container || !stepper) return;

    // Show for core agents, hide for utility agents unless working
    const isCore = ['developer', 'researcher', 'tuner'].includes(id);
    const action = heartbeat.action || 'Idle';
    const isWorking = action !== 'Idle' && action !== 'N/A';

    if (!isCore && !isWorking) {
        container.style.display = 'none';
        return;
    }

    container.style.display = 'block';
    
    // Support both [X/Y] and "Stage X" formats
    const matchXY    = action.match(/\[(\d+)\/(\d+)\]/);
    const matchStage = action.match(/Stage\s+(\d+)/i);
    
    let currentStep = 0;
    let stepStatus = 'active'; 
    
    if (matchXY) {
        currentStep = parseInt(matchXY[1]);
    } else if (matchStage) {
        currentStep = parseInt(matchStage[1]);
    } else if (isWorking) {
        // Default to step 1 if working but haven't received a stage marker yet
        currentStep = 1;
    }

    if (action.includes('FAILED') || action.includes('✗')) stepStatus = 'fail';
    else if (action.includes('COMPLETE') || action.includes('✓')) stepStatus = 'done';

    // Agent-specific step labels
    const isDense = id === 'developer';
    const steps = id === 'developer'
        ? [
            {n:1,l:'INGEST'},     {n:2,l:'BUILD'},      {n:3,l:'SYNTAX'},    {n:4,l:'SMOKE'},
            {n:5,l:'DEV_REPORT'}, {n:6,l:'WFO_EVO'},    {n:7,l:'PBO_AUDIT'}, {n:8,l:'MANIFEST'}
          ]
        : id === 'researcher'
        ? [{n:1,l:'WEB_SEARCH'},{n:2,l:'EXTRACT_ALPHA'},{n:3,l:'HYPHO_REPORT'},{n:4,l:'INDEX_SYNC'}]
        : id === 'qa'
        ? [{n:1,l:'GROUP_1'},{n:2,l:'GROUP_2'},{n:3,l:'GROUP_3'},{n:4,l:'GROUP_5'},{n:5,l:'FINALIZE'}]
        : id === 'tuner'
        ? [{n:1,l:'AUDIT'},{n:2,l:'WORK_CYCLE'},{n:3,l:'REPORTING'},{n:4,l:'MANIFEST'}]
        : [{n:1,l:'INITIALIZE'},{n:2,l:'WORK_CYCLE'},{n:3,l:'VALIDATE'},{n:4,l:'FINALIZE'}];

    // Calculate progress line width
    let progressRatio = 0;
    const total = steps.length;
    if (currentStep > 1) {
        progressRatio = (currentStep - 1) / (total - 1);
    } else if (currentStep === 1 && stepStatus === 'done') {
        progressRatio = 1 / (total - 1);
    }
    
    const lineColor = stepStatus === 'fail' ? 'var(--danger)' : 'var(--success)';

    stepper.innerHTML = `
        <div class="infographic-stepper ${isDense ? 'stepper-dense' : ''}">
            <div class="stepper-progress-line" style="width: calc(${progressRatio} * (100% - ${isDense ? 60 : 80}px)); background: ${lineColor};"></div>
            ${steps.map(s => {
                let cls = '';
                let prompt = '';
                if (s.n < currentStep) {
                    cls = 'done';
                    prompt = 'Verified';
                } else if (s.n === currentStep) {
                    cls = stepStatus;
                    prompt = stepStatus === 'fail' ? 'Fault' : 
                             stepStatus === 'done' ? 'Success' : 
                             esc(action.replace(/\[\d+\/\d+\]\s*/, '')).slice(0, 20);
                } else {
                    prompt = 'Waiting';
                }
                return `
                    <div class="info-step ${cls}">
                        <div class="info-circle">${s.n}</div>
                        <div class="info-label">${s.l}</div>
                        <div class="info-prompt">${prompt}</div>
                    </div>
                `;
            }).join('')}
        </div>
    `;
}

function closeModal() {
    _activeDossierId = null;
    document.getElementById('agent-modal').style.display = 'none';
}

// ─────────────────────────────────────────────
//  AGENT NETWORK MODAL
// ─────────────────────────────────────────────
const NET_AGENTS = [
    { id: 'data',       key: 'crypto-data-engineer',    label: 'data' },
    { id: 'tuner',      key: 'crypto-strategy-tuner',   label: 'tuner' },
    { id: 'researcher', key: 'alpha-researcher',        label: 'researcher' },
    { id: 'developer',  key: 'alpha-developer',         label: 'developer' },
    { id: 'fullstack',  key: 'crypto-fullstack',        label: 'fullstack' },
    { id: 'qa',         key: 'crypto-qa-tester',        label: 'qa' },
];

// Arrow id → [from-agent, to-agent] for inbox-driven highlighting
const NET_ARROW_MAP = {
    'arr-data-fullstack':  ['data',       'fullstack'],
    'arr-data-researcher': ['data',       'researcher'],
    'arr-researcher-dev':  ['researcher', 'developer'],
    'arr-dev-tuner':       ['developer',  'tuner'],
    'arr-tuner-fullstack': ['tuner',      'fullstack'],
    'arr-qa-fullstack':    ['qa',         'fullstack'],
    'arr-qa-data':         ['qa',         'data'],
    'arr-qa-tuner':        ['qa',         'tuner'],
    'arr-tuner-researcher':['tuner',      'researcher'],
    'arr-researcher-data': ['researcher', 'data'],
};

function openNetworkModal() {
    document.getElementById('network-modal').style.display = 'flex';
    updateNetworkModal();
}

function closeNetworkModal() {
    document.getElementById('network-modal').style.display = 'none';
}

function updateNetworkModal() {
    if (document.getElementById('network-modal').style.display === 'none') return;
    const tel = window.latestTelemetry;
    if (!tel) return;

    const hbs   = tel.heartbeats   || {};
    const inbox = tel.inbox_counts || {};

    // ── Update agent boxes ──
    NET_AGENTS.forEach(({ id, key, label }) => {
        const hb     = hbs[key] || {};
        const status = (hb.status || 'OFFLINE').toUpperCase();
        const action = hb.action  || '—';
        const next   = hb.next_run_at || '';

        const box       = document.getElementById(`net-box-${id}`);
        const statusEl  = document.getElementById(`net-status-${id}`);
        const actionEl  = document.getElementById(`net-action-${id}`);

        if (box) {
            box.classList.remove('online', 'standby', 'offline');
            box.classList.add(status === 'ONLINE' ? 'online' : status === 'STANDBY' ? 'standby' : 'offline');
        }
        if (statusEl) {
            statusEl.textContent = status;
            statusEl.classList.remove('online', 'standby');
            if (status === 'ONLINE')   statusEl.classList.add('online');
            if (status === 'STANDBY')  statusEl.classList.add('standby');
        }
        if (actionEl) {
            const shortAction = action.length > 22 ? action.slice(0, 22) + '…' : action;
            actionEl.textContent = shortAction;
        }
    });

    // ── Animate arrows based on pending inbox messages ──
    Object.entries(NET_ARROW_MAP).forEach(([arrId, [fromId, toId]]) => {
        const el = document.getElementById(arrId);
        if (!el) return;
        const fromKey = NET_AGENTS.find(a => a.id === fromId)?.key || '';
        // Arrow lights up if source agent has sent messages (inbox_counts for destination)
        const toKey   = NET_AGENTS.find(a => a.id === toId)?.key   || '';
        const pending = (inbox[toKey] || 0) > 0;
        el.classList.remove('active', 'high');
        if (pending) el.classList.add('active');
    });

    // ── Update summary table ──
    const tbody = document.getElementById('net-summary-body');
    if (!tbody) return;
    tbody.innerHTML = NET_AGENTS.map(({ id, key, label }) => {
        const hb      = hbs[key]   || {};
        const cnt     = inbox[key] || 0;
        const status  = (hb.status || 'OFFLINE').toUpperCase();
        const action  = hb.action  || '—';
        const next    = hb.next_run_at || '—';
        const color   = status === 'ONLINE' ? '#10b981' : status === 'STANDBY' ? '#f59e0b' : '#4b5563';
        return `<tr>
            <td>${label}</td>
            <td style="color:${color};font-weight:700">${status}</td>
            <td style="max-width:110px;overflow:hidden;text-overflow:ellipsis;white-space:nowrap" title="${esc(action)}">${esc(action)}</td>
            <td>${esc(next)}</td>
            <td style="color:${cnt>0?'#f59e0b':'#4b5563'};font-weight:700">${cnt > 0 ? `${cnt} pending` : '0'}</td>
        </tr>`;
    }).join('');
}

// ─────────────────────────────────────────────
//  UTILITY
// ─────────────────────────────────────────────
function createActionEl(parent) {
    const el = document.createElement('div');
    el.className = 'agent-action';
    el.style.cssText = 'font-size:0.6rem;color:#60a5fa;padding:2px 10px;font-style:italic;';
    parent.querySelector('.term-header').after(el);
    return el;
}

async function setAgentMode(agentId, mode) {
    try {
        const r = await fetch('/api/agent_mode', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ agent_id: agentId, mode })
        });
        const result = await r.json();
        console.log(result.message || result.error);

        // Optimistic visual update — don't wait for heartbeat to confirm
        // (heartbeat lags by up to 30s after mode change)
        const newStatus = mode === 'active' ? 'ONLINE' : mode === 'standby' ? 'STANDBY' : 'OFFLINE';

        // 1. Main status badge on the card header
        const statusEl = document.getElementById(`status-${agentId}`);
        if (statusEl) {
            statusEl.textContent = newStatus;
            statusEl.className = `agent-status status-${newStatus.toLowerCase()}`;
        }

        const ctrlsEl = document.getElementById(`controls-${agentId}`);
        if (ctrlsEl) {
            // 2. ACTIVE / STANDBY / STOP button is-current highlight
            ctrlsEl.querySelectorAll('.ctrl-btn').forEach(btn => btn.classList.remove('is-current'));
            const targetClass = mode === 'active' ? '.ctrl-active' : mode === 'standby' ? '.ctrl-standby' : '.ctrl-stop';
            const targetBtn = ctrlsEl.querySelector(targetClass);
            if (targetBtn) targetBtn.classList.add('is-current');

            // 3. Scheduler checkbox
            const cb = ctrlsEl.querySelector('input[type="checkbox"]');
            if (cb) cb.checked = (mode === 'active');

            // 4. Scheduler pill colour
            const pill = ctrlsEl.querySelector('.sched-pill');
            if (pill) {
                if (mode === 'active') {
                    pill.style.background = 'rgba(16,185,129,0.35)';
                    pill.style.borderColor = 'var(--success)';
                } else {
                    pill.style.background = '';
                    pill.style.borderColor = '';
                }
            }

            // 5. Scheduler ON / PAUSED / N/A label
            const statusSpan = ctrlsEl.querySelector('.sched-status');
            if (statusSpan) {
                if (mode === 'active') {
                    statusSpan.className = 'sched-status sched-on';
                    statusSpan.textContent = 'ON';
                } else if (mode === 'standby') {
                    statusSpan.className = 'sched-status sched-paused';
                    statusSpan.textContent = 'PAUSED';
                } else {
                    statusSpan.className = 'sched-status sched-off';
                    statusSpan.textContent = 'N/A';
                }
            }

            // Lock currentStatus so the next telemetry poll won't re-render
            // back to the old state before the heartbeat catches up
            ctrlsEl.dataset.currentStatus = newStatus;
        }

        // Scroll to and flash the agent card
        const card = document.getElementById(`term-${agentId}`);
        if (card) {
            card.scrollIntoView({ behavior: 'smooth', block: 'center' });
            card.classList.remove('card-flash');
            void card.offsetWidth;
            card.classList.add('card-flash');
            setTimeout(() => card.classList.remove('card-flash'), 950);
        }

        // Delay telemetry refresh — agent watcher needs ~2s to write its first heartbeat
        // Immediate fetch would return old status and flip the toggle back
        setTimeout(updateTelemetry, 2500);
    } catch (e) { console.error('setAgentMode failed', e); }
}

async function forceOnline(agentId) { await setAgentMode(agentId, 'active'); }
async function setOffline(agentId)  { await setAgentMode(agentId, 'offline'); }

async function triggerManual(action) {
    try {
        const r = await fetch('/api/trigger_agent_action', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ action: action })
        });
        const result = await r.json();
        if (result.message) { console.log(result.message); updateTelemetry(); }
    } catch (e) { console.error("Failed to trigger agent action", e); }
}

window.onclick = function(event) {
    const modal = document.getElementById('agent-modal');
    if (event.target === modal) closeModal();
};

// ─────────────────────────────────────────────
//  SYSTEM CHANGELOG
// ─────────────────────────────────────────────
function updateSystemChangelog(lines) {
    const feed = document.getElementById('syslog-feed');
    if (!feed) return;

    // Filter to only table rows (start with |), skip headers and separators
    const rows = lines.filter(l => l.startsWith('|') && !l.includes('---') && !l.toLowerCase().includes('timestamp'));

    const newHtml = rows.length === 0
        ? '<div class="line" style="opacity:0.4;padding:6px">No changes logged yet — agents will write here when they modify files</div>'
        : rows.map(line => {
            const cells = line.split('|').map(c => c.trim()).filter(c => c);
            if (cells.length < 4) return '';
            const [ts, agent, file, what, why] = cells;
            return `<div class="syslog-row">
                <span class="syslog-ts"  title="${esc(ts||'')}">${esc(ts || '')}</span>
                <span class="syslog-agent" title="${esc(agent||'')}">${esc(agent || '')}</span>
                <span class="syslog-file"  title="${esc(file||'')}">${esc(file || '')}</span>
                <span class="syslog-what"  title="${esc(what||'')}">${esc(what || '')}</span>
                <span class="syslog-why"   title="${esc(why||'')}">${esc(why || '')}</span>
            </div>`;
        }).join('');

    if (feed.innerHTML !== newHtml) {
        const savedScroll = feed.parentElement?.scrollTop || 0;
        feed.innerHTML = newHtml;
        if (feed.parentElement) feed.parentElement.scrollTop = savedScroll;
    }
}

// ─────────────────────────────────────────────
//  QA AGENT SPECIFICS
// ─────────────────────────────────────────────
function updateQAFeed(lines) {
    const feed = document.getElementById('qa-feed');
    if (!feed) return;

    // Parse summary line for score badge
    let passed = 0, failed = 0, warned = 0;
    for (const line of lines) {
        const m = line.match(/QA SUMMARY:\s*(\d+)\s*PASS\s*·\s*(\d+)\s*FAIL\s*·\s*(\d+)\s*WARN/);
        if (m) { passed = +m[1]; failed = +m[2]; warned = +m[3]; }
    }
    const scoreBadge = document.getElementById('qa-score-badge');
    if (scoreBadge && (passed + failed + warned > 0)) {
        scoreBadge.textContent = `${passed}P ${failed}F ${warned}W`;
        scoreBadge.className = failed > 0 ? 'badge badge-qa-score qa-fail'
                             : warned > 0 ? 'badge badge-qa-score qa-warn'
                             :              'badge badge-qa-score qa-pass';
    }

    // Render log lines with colour
    const newHtml = lines.length === 0
        ? '<div class="line" style="opacity:0.5">No QA runs yet — bring QA agent online</div>'
        : lines.map(line => {
            const cls = line.includes('[FAIL]') ? 'line-error' :
                        line.includes('[WARN]') ? 'line-warn'  :
                        line.includes('[PASS]') ? 'line-ok'    :
                        line.includes('SUMMARY') ? 'collab-section' : '';
            return `<div class="line ${cls}">${esc(line)}</div>`;
        }).join('');

    if (feed.innerHTML !== newHtml) {
        const atBottom = feed.scrollTop + feed.clientHeight >= feed.scrollHeight - 5;
        feed.innerHTML = newHtml;
        if (atBottom) feed.scrollTop = feed.scrollHeight;
    }
}

// ─────────────────────────────────────────────
//  STRATEGY TUNER PANEL
// ─────────────────────────────────────────────
const _tunerSelected = new Set();  // persists across re-renders

function _updateQueueBtn() {
    const btn      = document.getElementById('tuner-queue-btn');
    const countEl  = document.getElementById('tuner-sel-count');
    const n        = _tunerSelected.size;
    if (btn)     { btn.disabled = n === 0; }
    if (countEl) { countEl.textContent = `(${n})`; }
}

function tunerToggleAll(headerCb) {
    document.querySelectorAll('.tuner-cb').forEach(cb => {
        cb.checked = headerCb.checked;
        const sid = cb.dataset.sid;
        if (headerCb.checked) _tunerSelected.add(sid);
        else                  _tunerSelected.delete(sid);
        cb.closest('tr').classList.toggle('tuner-row-selected', headerCb.checked);
    });
    _updateQueueBtn();
}

function tunerToggleRow(cb) {
    const sid = cb.dataset.sid;
    if (cb.checked) _tunerSelected.add(sid);
    else            _tunerSelected.delete(sid);
    cb.closest('tr').classList.toggle('tuner-row-selected', cb.checked);
    // Sync header checkbox
    const all     = document.querySelectorAll('.tuner-cb');
    const checked = document.querySelectorAll('.tuner-cb:checked');
    const headerCb = document.getElementById('tuner-select-all');
    if (headerCb) {
        headerCb.indeterminate = checked.length > 0 && checked.length < all.length;
        headerCb.checked       = checked.length === all.length && all.length > 0;
    }
    _updateQueueBtn();
}

function updateTunerPanel(scan) {
    const tbody   = document.getElementById('tuner-body');
    const summary = document.getElementById('tuner-summary');
    if (!tbody) return;

    if (!scan || !scan.results || scan.results.length === 0) {
        tbody.innerHTML = '<tr><td colspan="12" style="opacity:0.5;text-align:center">No scan data — click RUN SCAN or set tuner to ACTIVE</td></tr>';
        if (summary) summary.textContent = 'no scan yet';
        return;
    }

    const ts           = scan.scanned_at ? scan.scanned_at.slice(0, 16).replace('T', ' ') : '';
    const forceFlag    = scan._force_rescan_pending;
    const classifiedOk = scan.classified === true;
    const forceBtn     = document.getElementById('tuner-force-rescan-btn');
    if (forceBtn) {
        forceBtn.classList.toggle('rescan-pending', !!forceFlag);
        forceBtn.title = forceFlag ? 'Force rescan is queued — will run on next agent wake-up' : 'Force a fresh scan even if results already exist';
    }
    if (summary) {
        const classTag = classifiedOk ? '' : ' · ⏳ awaiting classification';
        const forceTag = forceFlag    ? ' · 🔄 rescan queued' : '';
        summary.textContent = `${scan.GOOD||0} GOOD · ${scan.MEDIOCRE||0} MEDIOCRE · ${scan.BAD||0} BAD · scanned ${ts}${classTag}${forceTag}`;
    }

    // Show ALL strategies sorted by ID ascending
    const visible = scan.results;
    if (visible.length === 0) {
        tbody.innerHTML = '<tr><td colspan="12" style="opacity:0.5;text-align:center">No scan data.</td></tr>';
        return;
    }

    tbody.innerHTML = visible
        .sort((a, b) => parseInt(a.id) - parseInt(b.id))
        .map(r => {
            const sid        = String(r.id);
            const isSelected = _tunerSelected.has(sid);
            const canSelect  = r.grade !== 'ERROR' && r.grade !== 'PENDING';
            const gradeCls   = r.grade === 'GOOD'    ? 'tuner-good'
                             : r.grade === 'BAD'     ? 'tuner-bad'
                             : r.grade === 'ERROR'   ? 'tuner-error'
                             : r.grade === 'PENDING' ? 'tuner-pending'
                             : 'tuner-med';
            const sharpeStr  = r.sharpe != null ? r.sharpe.toFixed(2) : 'N/A';
            const returnStr  = r.total_return != null ? `${r.total_return}%` : 'N/A';
            const ddStr      = r.max_drawdown != null ? `${r.max_drawdown}%` : 'N/A';
            const tradesStr  = r.total_trades != null ? String(r.total_trades) : 'N/A';
            const pfVal      = r.profit_factor != null ? parseFloat(r.profit_factor) : null;
            const pfStr      = pfVal == null ? 'N/A' : pfVal >= 99 ? '∞' : pfVal.toFixed(2);
            const reason     = r.grade_reason ? esc(r.grade_reason) : '<span style="opacity:0.35">—</span>';
            const cbHtml     = canSelect
                ? `<input type="checkbox" class="tuner-cb" data-sid="${sid}"
                          ${isSelected ? 'checked' : ''}
                          onclick="event.stopPropagation();tunerToggleRow(this)">`
                : `<span style="opacity:0.2">—</span>`;
            return `<tr class="${isSelected ? 'tuner-row-selected' : ''}"
                        onclick="if(event.target.type!=='checkbox'&&event.target.tagName!=='BUTTON'){const cb=this.querySelector('.tuner-cb');if(cb){cb.checked=!cb.checked;tunerToggleRow(cb);}}">
                <td>${cbHtml}</td>
                <td class="mu-num">${esc(sid)}</td>
                <td>${esc(r.class)}</td>
                <td>${esc(r.coin||'?')}</td>
                <td>${esc(r.tf||'?')}</td>
                <td class="${r.sharpe==null ? '' : r.sharpe>=1.0 ? 'bt-good' : r.sharpe>=0.3 ? 'bt-warn' : 'bt-bad'}">${sharpeStr}</td>
                <td class="${r.total_return==null ? '' : r.total_return>=100 ? 'bt-good' : r.total_return>=0 ? 'bt-warn' : 'bt-bad'}">${returnStr}</td>
                <td class="${r.max_drawdown==null ? '' : r.max_drawdown<20 ? 'bt-good' : r.max_drawdown<50 ? 'bt-warn' : 'bt-bad'}">${ddStr}</td>
                <td class="${r.total_trades==null ? '' : r.total_trades>=100 ? 'bt-good' : r.total_trades>=30 ? 'bt-warn' : 'bt-bad'}">${tradesStr}</td>
                <td class="${pfVal==null ? '' : pfVal>=1.5 ? 'bt-good' : pfVal>=1.0 ? 'bt-warn' : 'bt-bad'}">${pfStr}</td>
                <td><span class="tuner-grade ${gradeCls}">${r.grade}</span></td>
                <td class="tuner-reason">${reason}</td>
            </tr>`;
        }).join('');
    _updateQueueBtn();
}

async function queueSelectedFinetunes() {
    if (_tunerSelected.size === 0) return;

    const btn = document.getElementById('tuner-queue-btn');
    btn.disabled    = true;
    btn.textContent = `⏳ Queuing ${_tunerSelected.size}...`;

    const ids     = [..._tunerSelected];
    const results = [];

    for (const sid of ids) {
        try {
            const r = await fetch('/api/trigger_finetune', {
                method:  'POST',
                headers: { 'Content-Type': 'application/json' },
                body:    JSON.stringify({ strategy_id: sid, n_trials: 30,
                                          date_from: '2023-01-01', date_to: '2024-01-01' })
            });
            const d = await r.json();
            results.push({ sid, ok: !d.error, msg: d.message || d.error });
        } catch (e) {
            results.push({ sid, ok: false, msg: String(e) });
        }
    }

    const ok  = results.filter(r => r.ok).length;
    const bad = results.filter(r => !r.ok).length;

    // Show brief toast-style result
    const summary = document.getElementById('tuner-summary');
    if (summary) {
        const prev = summary.textContent;
        summary.textContent = `✓ ${ok} queued${bad > 0 ? ` · ${bad} failed` : ''} — tuner will process on next wake-up`;
        summary.style.color = ok > 0 ? 'var(--success)' : 'var(--danger)';
        setTimeout(() => { summary.style.color = ''; summary.textContent = prev; }, 5000);
    }

    // Clear selection
    _tunerSelected.clear();
    document.getElementById('tuner-select-all').checked = false;
    _updateQueueBtn();
    btn.textContent = `Queue Selected`;

    updateTelemetry();
}

async function triggerTunerScan() {
    const btn = document.getElementById('tuner-scan-btn');
    btn.disabled    = true;
    btn.textContent = '⏳ Triggering...';
    try {
        const r = await fetch('/api/run_tuner_scan', {
            method:  'POST',
            headers: { 'Content-Type': 'application/json' }
        });
        const d = await r.json();
        console.log(d.message || d.error);
        btn.textContent = d.error ? '✗ Error' : '✓ Scan triggered';
        setTimeout(() => { btn.disabled = false; btn.textContent = '⟳ RUN SCAN'; }, 4000);
        updateTelemetry();
    } catch (e) {
        btn.disabled = false;
        btn.textContent = '⟳ RUN SCAN';
        console.error(e);
    }
}

async function triggerGradePending() {
    const btn = document.getElementById('tuner-grade-pending-btn');
    btn.disabled    = true;
    btn.textContent = '⏳ Checking...';
    try {
        const r = await fetch('/api/grade_pending', {
            method: 'POST', headers: { 'Content-Type': 'application/json' }
        });
        const d = await r.json();
        if (d.error) {
            btn.textContent = '✗ Error';
        } else if (d.pending_count === 0) {
            btn.textContent = '✓ None pending';
        } else {
            btn.textContent = `✓ Grading ${d.pending_count}`;
        }
        console.log(d.message || d.error);
        setTimeout(() => { btn.disabled = false; btn.textContent = '✦ GRADE PENDING'; }, 5000);
        setTimeout(updateTelemetry, 2500);
    } catch (e) {
        btn.disabled = false;
        btn.textContent = '✦ GRADE PENDING';
        console.error(e);
    }
}

async function triggerScanNew() {
    const btn = document.getElementById('tuner-scan-new-btn');
    btn.disabled    = true;
    btn.textContent = '⏳ Checking...';
    try {
        const r = await fetch('/api/scan_new_strategies', {
            method: 'POST', headers: { 'Content-Type': 'application/json' }
        });
        const d = await r.json();
        if (d.error) {
            btn.textContent = '✗ Error';
        } else if (d.new_count === 0) {
            btn.textContent = '✓ Up to date';
        } else {
            btn.textContent = `✓ Scanning ${d.new_count} new`;
        }
        console.log(d.message || d.error);
        setTimeout(() => { btn.disabled = false; btn.textContent = '⊕ SCAN NEW'; }, 5000);
        setTimeout(updateTelemetry, 3000);
    } catch (e) {
        btn.disabled = false;
        btn.textContent = '⊕ SCAN NEW';
        console.error(e);
    }
}

async function triggerForceRescan() {
    const btn = document.getElementById('tuner-force-rescan-btn');
    btn.disabled    = true;
    btn.textContent = '⏳ Flagging...';
    try {
        const r = await fetch('/api/trigger_tuner_rescan', {
            method: 'POST', headers: { 'Content-Type': 'application/json' }
        });
        const d = await r.json();
        console.log(d.message || d.error);
        btn.textContent = '✓ Rescan queued';
        btn.classList.add('rescan-pending');
        setTimeout(() => {
            btn.disabled = false;
            btn.textContent = '↺ FORCE RESCAN';
        }, 3000);
        updateTelemetry();
    } catch (e) {
        btn.disabled = false;
        btn.textContent = '↺ FORCE RESCAN';
        console.error(e);
    }
}

// Fine-tune modal
function openFtModal(sid, stratName) {
    document.getElementById('ft-modal-title').textContent = `⚡ FINE-TUNE — ${stratName} (ID: ${sid})`;
    document.getElementById('ft-modal').dataset.sid = sid;
    document.getElementById('ft-result').innerHTML   = '';
    document.getElementById('ft-confirm-btn').disabled    = false;
    document.getElementById('ft-confirm-btn').textContent = '⚡ QUEUE FINE-TUNE';
    document.getElementById('ft-modal').style.display = 'block';
}

function closeFtModal() {
    document.getElementById('ft-modal').style.display = 'none';
}

async function confirmFinetune() {
    const modal  = document.getElementById('ft-modal');
    const sid    = modal.dataset.sid;
    const trials = document.getElementById('ft-trials').value;
    const from   = document.getElementById('ft-date-from').value;
    const to     = document.getElementById('ft-date-to').value;
    const btn    = document.getElementById('ft-confirm-btn');
    const result = document.getElementById('ft-result');

    btn.disabled    = true;
    btn.textContent = '⏳ Queuing...';

    try {
        const r = await fetch('/api/trigger_finetune', {
            method:  'POST',
            headers: { 'Content-Type': 'application/json' },
            body:    JSON.stringify({ strategy_id: sid, n_trials: parseInt(trials), date_from: from, date_to: to })
        });
        const d = await r.json();
        if (d.error) {
            result.innerHTML = `<div class="bt-error">${esc(d.error)}</div>`;
            btn.disabled = false;
            btn.textContent = '⚡ QUEUE FINE-TUNE';
        } else {
            result.innerHTML = `<div style="color:var(--success);padding:12px">✓ ${esc(d.message)}<br><span style="opacity:0.6;font-size:0.65rem">The tuner agent will process this on its next wake-up. Check the tuner terminal card for progress.</span></div>`;
            btn.textContent = '✓ Queued';
            updateTelemetry();
        }
    } catch (e) {
        result.innerHTML = `<div class="bt-error">Request failed: ${esc(String(e))}</div>`;
        btn.disabled = false;
        btn.textContent = '⚡ QUEUE FINE-TUNE';
    }
}

window.addEventListener('click', e => {
    if (e.target === document.getElementById('ft-modal')) closeFtModal();
});

// ─────────────────────────────────────────────
//  FAILURE VAULT
// ─────────────────────────────────────────────
async function openFailureModal() {
    const modal = document.getElementById('failure-modal');
    const tbody = document.getElementById('failure-body');
    tbody.innerHTML = '<tr><td colspan="5" style="text-align:center; padding: 20px;">Scanning archives...</td></tr>';
    modal.style.display = 'block';

    try {
        const r = await fetch('/api/failure_report');
        const failures = await r.json();

        if (failures.length === 0) {
            tbody.innerHTML = '<tr><td colspan="5" style="text-align:center; padding: 20px; opacity:0.5;">No failures recorded in recent history. System is healthy.</td></tr>';
        } else {
            tbody.innerHTML = failures.map(f => {
                let rowStyle = 'border-bottom: 1px solid #1f2937;';
                let typeColor = 'var(--warn)';
                let typeLabel = f.type;
                let clickAction = '';

                if (f.type === 'SYSTEM_ERROR') {
                    typeColor = 'var(--danger)';
                } else if (f.type === 'AUTOPSY') {
                    typeColor = '#94a3b8'; // Muted grey for historical autopsy
                    typeLabel = '⚰️ AUTOPSY';
                    rowStyle += 'cursor:pointer;';
                    clickAction = `onclick="openCardViewer('${esc(f.file)}')" onmouseover="this.style.background='rgba(255,255,255,0.05)'" onmouseout="this.style.background=''"`
                }

                return `
                    <tr style="${rowStyle}" ${clickAction}>
                        <td style="padding: 8px; opacity: 0.6;">${esc(f.ts.slice(0, 16).replace('T', ' '))}</td>
                        <td style="padding: 8px;"><span style="color: ${typeColor}">${esc(typeLabel)}</span></td>
                        <td style="padding: 8px; font-weight: bold;">${esc(f.name)} ${f.id !== 'N/A' ? `(ID ${f.id})` : ''}</td>
                        <td style="padding: 8px; font-size: 0.6rem; color: var(--highlight);">${esc(f.stage)}</td>
                        <td style="padding: 8px; font-style: italic; opacity: 0.8; font-size: 0.65rem;">${esc(f.reason)}</td>
                    </tr>
                `;
            }).join('');
        }
    } catch (e) {
        tbody.innerHTML = `<tr><td colspan="5" style="text-align:center; padding: 20px; color: var(--danger);">Failed to load failure report: ${esc(e)}</td></tr>`;
    }
}

function closeFailureModal() {
    document.getElementById('failure-modal').style.display = 'none';
}

// ─────────────────────────────────────────────
//  PIPELINE STAGE DOSSIER
// ─────────────────────────────────────────────
const STAGE_METADATA = {
    0: {
        title: "00 RAW_IDEA",
        desc: "All raw Alpha concepts in factor_library/, grouped by category. Click any idea to read its full Candidate Card.",
        listTitle: "ALPHA_CARD_VAULT",
        action: { label: "HUNT_ALPHA", func: "triggerManual('RESEARCH')" }
    },
    1: {
        title: "01 HYPOTHESIS",
        desc: "Hypothesis reports written by @alpha-researcher. Each report models a factor mathematically, documents edge rationale, and links to the source idea card. Reports live in alpha_forge_v2/hypho_report/.",
        listTitle: "HYPHO_REPORT_VAULT"
    },
    2: {
        title: "02 DEVELOPMENT",
        desc: "Development & initial backtest reports written by @alpha-developer. Each strategy produces exactly one report covering implementation details, factor logic, and preliminary backtest results. Reports live in alpha_forge_v2/dev_report/.",
        listTitle: "DEV_REPORT_VAULT"
    },
    3: {
        title: "03 BACKTEST",
        desc: "Performance and stability reports generated by @strategy-tuner. Includes Optuna optimization results, parameter sensitivity analysis, and cross-asset robustness checks. Reports live in alpha_forge_v2/backtest_report/.",
        listTitle: "BACKTEST_REPORT_VAULT",
        action: { label: "RUN_SCAN", func: "triggerTunerScan()" }
    },
    4: {
        title: "04 PAPER_READY",
        desc: "Elite strategies with formal Market Fit Memos. The Tuner evaluates recent regime fit and portfolio correlation before deployment. Reports live in alpha_forge_v2/elite_report/.",
        listTitle: "ELITE_REPORT_VAULT"
    },
    5: {
        title: "05 PAPER_TRADE",
        desc: "Live Paper Trading. Strategies executing trades on real-time data with zero capital risk.",
        listTitle: "ACTIVE_PAPER_SCRIPTS"
    }
};

// Which agent owns each pipeline stage
const STAGE_AGENT = {
    0: { key: 'alpha-researcher',      short: 'researcher' },
    1: { key: 'alpha-researcher',      short: 'researcher' },
    2: { key: 'alpha-developer',       short: 'developer'  },
    3: { key: 'crypto-strategy-tuner', short: 'tuner'      },
    4: { key: 'crypto-strategy-tuner', short: 'tuner'      },
    5: { key: 'crypto-fullstack',      short: 'fullstack'  },
};
const STAGE_BOTTLENECK_THRESHOLD = 50;

function initPipelineAgentBadges() {
    for (let i = 0; i <= 5; i++) {
        if (!STAGE_AGENT[i]) continue;
        const el = document.getElementById(`stage-${i}`);
        if (!el || el.querySelector('.stage-agent-badge')) continue;
        const badge = document.createElement('div');
        badge.className = 'stage-agent-badge';
        badge.id = `stage-ab-${i}`;
        badge.innerHTML = `<span class="stage-agent-dot dot-offline" id="stage-dot-${i}"></span><span class="stage-agent-name">${STAGE_AGENT[i].short}</span>`;
        el.appendChild(badge);
    }
}

function openStageModal(index) {
    _activeStageIndex = index;
    refreshStageModal(index);
    document.getElementById('stage-modal').style.display = 'block';
}

function closeStageModal() {
    _activeStageIndex = null;
    document.getElementById('stage-modal').style.display = 'none';
    // Reset sig so next open always does a fresh render with categories collapsed
    const itemsEl = document.getElementById('modal-stage-items');
    if (itemsEl) delete itemsEl.dataset.renderSig;
}

function refreshStageModal(index) {
    const meta = STAGE_METADATA[index];
    if (!meta) return;

    document.getElementById('modal-stage-title').textContent     = meta.title;
    document.getElementById('modal-stage-desc').textContent      = meta.desc;
    document.getElementById('modal-stage-list-title').textContent = meta.listTitle;

    const itemsEl = document.getElementById('modal-stage-items');
    const tel = window.latestTelemetry;
    const ps  = tel?.pipeline_stats || {};

    // Compute a fingerprint — skip full re-render if data hasn't changed.
    // This prevents the scroll position from resetting on every 5-second poll.
    const sig = index === 0
        ? `0:${ps.stage0}:${ps.stage0_built}`
        : `${index}:${ps[`stage${index}`]}:${(ps[`stage${index}_items`] || []).length}`;
    if (itemsEl.dataset.renderSig === sig) {
        // Data unchanged — titles already updated above, nothing else to do
        const actionBox = document.getElementById('modal-stage-action-box');
        const actions   = document.getElementById('modal-stage-actions');
        if (meta.action) {
            actionBox.style.display = 'block';
            actions.innerHTML = `<button class="btn-cyber" onclick="${meta.action.func};closeStageModal()">${meta.action.label}</button>`;
        } else {
            actionBox.style.display = 'none';
        }
        return;
    }
    itemsEl.dataset.renderSig = sig;

    if (index === 0 && tel && tel.pipeline_stats) {
        renderStage0(tel.pipeline_stats, itemsEl);
    } else if (tel && tel.pipeline_stats) {
        const items = tel.pipeline_stats[`stage${index}_items`] || [];
        const count = tel.pipeline_stats[`stage${index}`] || 0;

        const ST = {
            DRAFT:       { dot: '#4b5563', pill: 'rgba(75,85,99,0.18)',      text: '#6b7280' },
            QUEUED:      { dot: '#4b5563', pill: 'rgba(75,85,99,0.18)',      text: '#6b7280' },
            PENDING:     { dot: '#4b5563', pill: 'rgba(75,85,99,0.18)',      text: '#6b7280' },
            IN_PROGRESS: { dot: '#3b82f6', pill: 'rgba(59,130,246,0.18)',    text: '#60a5fa' },
            COMPLETE:    { dot: '#10b981', pill: 'rgba(16,185,129,0.18)',    text: '#34d399' },
            IMPLEMENTED: { dot: '#10b981', pill: 'rgba(16,185,129,0.18)',    text: '#34d399' },
            SCANNED:     { dot: '#10b981', pill: 'rgba(16,185,129,0.18)',    text: '#34d399' },
            VALIDATED:   { dot: '#f59e0b', pill: 'rgba(245,158,11,0.18)',    text: '#fbbf24' },
            PAPER_READY: { dot: '#f59e0b', pill: 'rgba(245,158,11,0.18)',    text: '#fbbf24' },
            ACTIVE:      { dot: '#f59e0b', pill: 'rgba(245,158,11,0.18)',    text: '#fbbf24' },
            LIVE:        { dot: '#f59e0b', pill: 'rgba(245,158,11,0.18)',    text: '#fbbf24' },
            REJECTED:    { dot: '#ef4444', pill: 'rgba(239,68,68,0.18)',     text: '#f87171' },
        };
        const st = s => ST[s] || ST.DRAFT;
        const INACTIVE = new Set(['DRAFT', 'QUEUED', 'PENDING']);
        const doneCount = items.filter(it => typeof it === 'object' && !INACTIVE.has(it.status || 'DRAFT')).length;
        const donePct   = count > 0 ? Math.round(doneCount / count * 100) : 0;

        const byCat = {};
        items.forEach(it => {
            const cat = (typeof it === 'object' && it !== null && it.category) ? it.category : 'Uncategorized';
            (byCat[cat] = byCat[cat] || []).push(it);
        });
        const catCount = Object.keys(byCat).filter(c => !c.startsWith('_')).length;

        let reportHtml = `
        <div style="display:flex;align-items:center;gap:14px;padding:0 2px 12px;border-bottom:1px solid #1f2937;margin-bottom:14px">
            <span style="font-size:0.68rem;color:#6b7280">${count} reports · ${catCount} ${catCount === 1 ? 'category' : 'categories'}</span>
            <div style="flex:1;height:4px;background:#1f2937;border-radius:2px;overflow:hidden">
                <div style="width:${donePct}%;height:100%;background:linear-gradient(90deg,#10b981,#34d399);transition:width .6s ease"></div>
            </div>
            <span style="font-size:0.68rem;font-weight:700;color:#10b981;white-space:nowrap">${doneCount} active</span>
        </div>
        <div style="max-height:460px;overflow-y:auto;padding-right:2px">`;

        if (items.length === 0) {
            reportHtml += '<div style="opacity:0.4;font-size:0.7rem;padding:12px">No active items in this stage</div>';
        } else {
            Object.entries(byCat).filter(([cat]) => !cat.startsWith('_')).sort(([a],[b]) => a.localeCompare(b)).forEach(([cat, catItems]) => {
                const catDone  = catItems.filter(it => typeof it === 'object' && !INACTIVE.has(it.status || 'DRAFT')).length;
                const catPct   = catItems.length > 0 ? Math.round(catDone / catItems.length * 100) : 0;
                const catLabel = cat.replace(/_/g, ' ');

                reportHtml += `
                <div style="margin-bottom:12px">
                    <div style="display:flex;align-items:center;gap:10px;padding:6px 10px;
                                background:rgba(15,23,42,0.9);border-left:3px solid #3b82f6;
                                border-radius:0 4px 0 0;cursor:pointer;user-select:none"
                         onclick="const g=this.nextElementSibling;g.style.display=g.style.display==='none'?'grid':'none'">
                        <span style="font-size:0.7rem;font-weight:700;color:#e2e8f0;letter-spacing:0.05em;flex:1">${esc(catLabel)}</span>
                        <div style="width:80px;height:3px;background:#1f2937;border-radius:2px;overflow:hidden">
                            <div style="width:${catPct}%;height:100%;background:#10b981;border-radius:2px"></div>
                        </div>
                        <span style="font-size:0.58rem;color:#4b5563;white-space:nowrap">${catDone}/${catItems.length}</span>
                        <span style="font-size:0.6rem;color:#374151">▼</span>
                    </div>
                    <div style="display:none;grid-template-columns:1fr 1fr;gap:3px 6px;
                                padding:6px 8px 8px 14px;background:rgba(9,14,24,0.5);border-left:3px solid #1f2937;border-radius:0 0 4px 0">
                    ${catItems.map(it => {
                        if (typeof it !== 'object' || it === null) {
                            return `<div style="display:flex;align-items:center;gap:6px;padding:4px 6px">
                                <span style="width:5px;height:5px;border-radius:50%;background:#4b5563;flex-shrink:0"></span>
                                <span style="font-size:0.66rem;color:#93c5fd">${esc(String(it))}</span>
                            </div>`;
                        }
                        const s     = st(it.status || 'DRAFT');
                        const label = (it.name || '').replace(/^\d{8}_/,'').replace(/[-_]/g,' ');
                        const hasMetrics = it.sharpe || it.total_return;
                        const metricsHtml = hasMetrics
                            ? `<span style="font-size:0.5rem;color:#6b7280;font-family:monospace;white-space:nowrap;flex-shrink:0">SR:${parseFloat(it.sharpe||0).toFixed(2)} R:${it.total_return||'—'}%</span>`
                            : '';
                        return `<div style="display:flex;align-items:center;gap:6px;padding:4px 6px;border-radius:4px;
                                            cursor:pointer;transition:background .15s"
                                     onmouseover="this.style.background='rgba(59,130,246,0.07)'"
                                     onmouseout="this.style.background=''"
                                     onclick="openCardViewer('${esc(it.file)}')">
                            <span style="width:5px;height:5px;border-radius:50%;background:${s.dot};flex-shrink:0"></span>
                            <span style="font-size:0.66rem;color:#93c5fd;white-space:nowrap;overflow:hidden;text-overflow:ellipsis;max-width:140px"
                                  title="${esc(it.name || '')}">${esc(label)}</span>
                            <span style="font-size:0.52rem;color:${s.text};background:${s.pill};
                                         padding:1px 5px;border-radius:3px;white-space:nowrap;flex-shrink:0;margin-left:auto">${esc(it.status || 'DRAFT')}</span>
                            ${metricsHtml}
                        </div>`;
                    }).join('')}
                    </div>
                </div>`;
            });
        }
        reportHtml += '</div>';
        itemsEl.innerHTML = reportHtml;
    }

    const actionBox = document.getElementById('modal-stage-action-box');
    const actions   = document.getElementById('modal-stage-actions');
    if (meta.action) {
        actionBox.style.display = 'block';
        actions.innerHTML = `<button class="btn-cyber" onclick="${meta.action.func};closeStageModal()">${meta.action.label}</button>`;
    } else {
        actionBox.style.display = 'none';
    }
}

// ── Stage 0 ALPHA_RAW_IDEA renderer — grouped by category ────────────────────
const S0_STATUS_COLOR = {
    'QUEUED':      '#4b5563',
    'PENDING':     '#4b5563',
    'IN_PROGRESS': '#3b82f6',
    'IMPLEMENTED': '#10b981',
    'VALIDATED':   '#f59e0b',
    'LIVE':        '#f59e0b',
    'ACTIVE':      '#f59e0b',
    'COMPLETE':    '#10b981',
    'REJECTED':    '#ef4444',
};

function renderStage0(stats, itemsEl) {
    const built = stats.stage0_built   || 0;
    const total = stats.stage0         || 0;
    const cards = stats.stage0_items   || [];

    const byCat = {};
    cards.forEach(it => {
        const cat = it.category || 'Uncategorized';
        (byCat[cat] = byCat[cat] || []).push(it);
    });

    // Colour per status
    const ST = {
        QUEUED:      { dot: '#4b5563', pill: 'rgba(75,85,99,0.18)',      text: '#6b7280' },
        PENDING:     { dot: '#4b5563', pill: 'rgba(75,85,99,0.18)',      text: '#6b7280' },
        IN_PROGRESS: { dot: '#3b82f6', pill: 'rgba(59,130,246,0.18)',    text: '#60a5fa' },
        IMPLEMENTED: { dot: '#10b981', pill: 'rgba(16,185,129,0.18)',    text: '#34d399' },
        VALIDATED:   { dot: '#f59e0b', pill: 'rgba(245,158,11,0.18)',    text: '#fbbf24' },
        COMPLETE:    { dot: '#10b981', pill: 'rgba(16,185,129,0.18)',    text: '#34d399' },
        REJECTED:    { dot: '#ef4444', pill: 'rgba(239,68,68,0.18)',     text: '#f87171' },
    };
    const st = s => ST[s] || ST.QUEUED;

    const rejected    = stats.stage0_rejected || 0;
    const visibleCats = Object.entries(byCat).filter(([c]) => !c.startsWith('_'));
    const catCount    = visibleCats.length;
    const processedPct  = total > 0 ? Math.round((built + rejected) / total * 100) : 0;
    const builtPct      = total > 0 ? Math.round(built   / total * 100) : 0;
    const rejectedPct   = total > 0 ? Math.round(rejected / total * 100) : 0;

    let html = `
    <div style="display:flex;align-items:center;gap:14px;padding:0 2px 12px;border-bottom:1px solid #1f2937;margin-bottom:14px">
        <span style="font-size:0.68rem;color:#6b7280">${total} ideas · ${catCount} categories</span>
        <div style="flex:1;height:4px;background:#1f2937;border-radius:2px;overflow:hidden;display:flex">
            <div style="width:${builtPct}%;height:100%;background:linear-gradient(90deg,#10b981,#34d399);transition:width .6s ease"></div>
            <div style="width:${rejectedPct}%;height:100%;background:#ef4444;transition:width .6s ease"></div>
        </div>
        <span style="font-size:0.68rem;font-weight:700;white-space:nowrap">
            <span style="color:#10b981">${built} implemented</span>
            <span style="color:#6b7280"> · </span>
            <span style="color:#f87171">${rejected} rejected</span>
            <span style="color:#6b7280"> · </span>
            <span style="color:#9ca3af">${processedPct}%</span>
        </span>
    </div>
    <div style="max-height:460px;overflow-y:auto;padding-right:2px">`;

    Object.entries(byCat).filter(([cat]) => !cat.startsWith('_')).sort(([a],[b]) => a.localeCompare(b)).forEach(([cat, items]) => {
        const catBuilt  = items.filter(it => it.status === 'IMPLEMENTED').length;
        const catPct    = items.length > 0 ? Math.round(catBuilt / items.length * 100) : 0;
        const catLabel  = cat.replace(/_/g, ' ');

        html += `
        <div style="margin-bottom:12px">
            <div style="display:flex;align-items:center;gap:10px;padding:6px 10px;
                        background:rgba(15,23,42,0.9);border-left:3px solid #3b82f6;
                        border-radius:0 4px 0 0;cursor:pointer;user-select:none"
                 onclick="const g=this.nextElementSibling;g.style.display=g.style.display==='none'?'grid':'none'">
                <span style="font-size:0.7rem;font-weight:700;color:#e2e8f0;letter-spacing:0.05em;flex:1">${esc(catLabel)}</span>
                <div style="width:80px;height:3px;background:#1f2937;border-radius:2px;overflow:hidden">
                    <div style="width:${catPct}%;height:100%;background:#10b981;border-radius:2px"></div>
                </div>
                <span style="font-size:0.58rem;color:#4b5563;white-space:nowrap">${catBuilt}/${items.length}</span>
                <span style="font-size:0.6rem;color:#374151">▼</span>
            </div>
            <div style="display:none;grid-template-columns:1fr 1fr;gap:3px 6px;
                        padding:6px 8px 8px 14px;background:rgba(9,14,24,0.5);border-left:3px solid #1f2937;border-radius:0 0 4px 0">
            ${items.map(it => {
                const s = st(it.status);
                const label = it.name.replace(/^\d{8}_/,'').replace(/[-_]/g,' ');
                return `<div style="display:flex;align-items:center;gap:6px;padding:4px 6px;border-radius:4px;
                                    cursor:pointer;transition:background .15s"
                             onmouseover="this.style.background='rgba(59,130,246,0.07)'"
                             onmouseout="this.style.background=''"
                             onclick="openCardViewer('${esc(it.file)}')">
                    <span style="width:5px;height:5px;border-radius:50%;background:${s.dot};flex-shrink:0"></span>
                    <span style="font-size:0.66rem;color:#93c5fd;white-space:nowrap;overflow:hidden;text-overflow:ellipsis;max-width:140px"
                          title="${esc(it.name)}">${esc(label)}</span>
                    <span style="font-size:0.52rem;color:${s.text};background:${s.pill};
                                 padding:1px 5px;border-radius:3px;white-space:nowrap;flex-shrink:0;margin-left:auto">${esc(it.status)}</span>
                </div>`;
            }).join('')}
            </div>
        </div>`;
    });

    html += '</div>';
    itemsEl.innerHTML = html;
}

// ─────────────────────────────────────────────
//  UTILITY — RELATIVE TIME
// ─────────────────────────────────────────────
function timeAgo(ts) {
    if (!ts) return 'never';
    const secs = Math.floor((Date.now() - new Date(ts).getTime()) / 1000);
    if (secs < 5)     return 'just now';
    if (secs < 60)    return `${secs}s ago`;
    if (secs < 3600)  return `${Math.floor(secs / 60)}m ago`;
    if (secs < 86400) return `${Math.floor(secs / 3600)}h ago`;
    return `${Math.floor(secs / 86400)}d ago`;
}

// ─────────────────────────────────────────────
//  PIPELINE FUNNEL
// ─────────────────────────────────────────────
function updatePipelineFunnel(stats) {
    const el = document.getElementById('pipeline-funnel');
    if (!el) return;
    const vals   = [0,1,2,3,4,5].map(i => stats[`stage${i}`] || 0);
    const labels = ['RAW_IDEA','HYPOTHESIS','DEVELOP','BACKTEST','PAPER_READY','LIVE'];
    const cls    = ['fn-node','fn-node','fn-built','fn-built','fn-elite','fn-elite'];
    let html = '';
    vals.forEach((val, i) => {
        if (i > 0) {
            const pct = vals[i-1] > 0 ? Math.round(val / vals[i-1] * 100) : 0;
            html += `<span class="fn-arrow">→</span><span class="fn-pct">${pct}%</span><span class="fn-arrow">→</span>`;
        }
        html += `<span class="${cls[i]}">${labels[i]}&nbsp;<strong>${val}</strong></span>`;
    });
    el.innerHTML = html;
}

// ─────────────────────────────────────────────
//  GLOBAL SEARCH
// ─────────────────────────────────────────────
function handleGlobalSearch(value) {
    const dropdown = document.getElementById('search-dropdown');
    if (!dropdown) return;
    if (!value || value.length < 2) { dropdown.style.display = 'none'; return; }
    const q = value.toLowerCase();
    const tel = window.latestTelemetry;
    const results = [];

    ((tel?.pipeline_stats?.stage0_items) || [])
        .filter(c => c.name.toLowerCase().includes(q)).slice(0, 6)
        .forEach(c => results.push({ type: 'IDEA', label: c.name, sub: c.status,
                                     action: `openCardViewer('${esc(c.file)}')` }));

    dropdown.innerHTML = results.length === 0
        ? '<div class="sr-empty">No results</div>'
        : results.map(r =>
            `<div class="sr-item"${r.action ? ` onclick="${r.action};closeSearch()"` : ''}>` +
                `<span class="sr-type">${esc(r.type)}</span>` +
                `<span class="sr-label">${esc(r.label)}</span>` +
                `<span class="sr-sub">${esc(r.sub || '')}</span>` +
            `</div>`
          ).join('');
    dropdown.style.display = 'block';
}

function closeSearch() {
    const el = document.getElementById('search-dropdown');
    if (el) el.style.display = 'none';
}

// ─────────────────────────────────────────────
//  INBOX PREVIEW PANEL
// ─────────────────────────────────────────────
function toggleInboxPreview(agentId, agentKey) {
    const panel = document.getElementById(`inbox-preview-${agentId}`);
    if (!panel) return;
    if (panel.style.display !== 'none') { panel.style.display = 'none'; return; }

    const msgs = ((window.latestTelemetry?.inbox_messages) || [])
        .filter(m => (m._to || m.to) === agentKey);

    panel.innerHTML = msgs.length === 0
        ? '<div class="ip-empty">No pending messages</div>'
        : msgs.map(m =>
            `<div class="ip-msg${m._status === 'PROCESSING' ? ' ip-processing' : ''}">` +
                `<div class="ip-row1">` +
                    `<span class="ip-topic">${esc(m.topic || '(no topic)')}</span>` +
                    `<span class="ip-status">${esc(m._status || 'PENDING')}</span>` +
                `</div>` +
                `<div class="ip-from">from ${esc(m.from || 'system')}</div>` +
                `<div class="ip-preview">${esc((m.message || m.summary || '').slice(0, 80))}</div>` +
            `</div>`
          ).join('');
    panel.style.display = 'block';
}

// ─────────────────────────────────────────────
//  FACTOR CARD VIEWER
// ─────────────────────────────────────────────
let _cvCurrentFile = null;

// Render inline markdown on an already-HTML-escaped string
function _cvInline(s) {
    return s
        .replace(/\*\*(.+?)\*\*/g, '<strong style="color:#e2e8f0">$1</strong>')
        .replace(/`([^`]+)`/g,     '<code style="background:#1e293b;padding:0 3px;border-radius:2px;color:#7dd3fc;font-size:0.88em">$1</code>')
        .replace(/\[\[(.+?)\]\]/g, '<span style="color:#818cf8">$1</span>');
}

const _CV_STATUS_COLOR = {
    QUEUED:'#374151', PENDING:'#374151', DRAFT:'#374151',
    IN_PROGRESS:'#3b82f6', IMPLEMENTED:'#10b981',
    VALIDATED:'#f59e0b', COMPLETE:'#10b981', REJECTED:'#ef4444'
};

// Badge class per frontmatter key
function _cvBadgeClass(key) {
    const k = key.toLowerCase();
    if (k === 'coins' || k === 'coin')      return 'cv-badge cv-badge-coin';
    if (k === 'timeframes' || k === 'tf')   return 'cv-badge cv-badge-tf';
    if (k === 'type')                       return 'cv-badge cv-badge-type';
    if (k === 'source')                     return 'cv-badge cv-badge-source';
    if (k === 'interest')                   return 'cv-badge cv-badge-interest';
    return 'cv-badge';
}

async function openCardViewer(file) {
    _cvCurrentFile = file;
    const modal      = document.getElementById('card-viewer-modal');
    const titleEl    = document.getElementById('cv-title');
    const statusEl   = document.getElementById('cv-status');
    const fmEl       = document.getElementById('cv-fm-badges');
    const contentEl  = document.getElementById('cv-content');
    const dispatchBtn= document.getElementById('cv-dispatch-btn');
    if (!modal) return;

    const name = file.split('/').pop().replace('.md','').replace(/[-_]/g,' ');
    if (titleEl)     titleEl.textContent = name.toUpperCase();
    if (statusEl)    { statusEl.textContent = 'LOADING'; statusEl.style.background = '#374151'; }
    if (fmEl)        fmEl.innerHTML = '';
    if (contentEl)   contentEl.innerHTML = '<div style="opacity:0.4;padding:12px">Loading...</div>';
    if (dispatchBtn) dispatchBtn.style.display = 'none';
    modal.style.display = 'flex';

    try {
        const r = await fetch(`/api/read_card?file=${encodeURIComponent(file)}`);
        const d = await r.json();
        if (d.error) {
            if (contentEl) contentEl.innerHTML = `<div style="color:var(--danger);padding:12px">Error: ${esc(d.error)}</div>`;
            return;
        }

        // Status badge
        if (statusEl) {
            statusEl.textContent = d.status || '—';
            statusEl.style.background = _CV_STATUS_COLOR[d.status] || '#374151';
        }

        // Frontmatter badges — skip status/name/tags (shown elsewhere)
        if (fmEl && d.frontmatter) {
            const SKIP = new Set(['status','name','tags']);
            fmEl.innerHTML = Object.entries(d.frontmatter)
                .filter(([k]) => !SKIP.has(k.toLowerCase()))
                .map(([k, v]) => {
                    // coins: split by comma → one badge each
                    if (k.toLowerCase() === 'coins') {
                        return String(v).split(',').map(c =>
                            `<span class="cv-badge cv-badge-coin">${esc(c.trim())}</span>`
                        ).join('');
                    }
                    return `<span class="${_cvBadgeClass(k)}">${esc(k)}: ${esc(String(v))}</span>`;
                }).join('');
        }

        // Body — render markdown
        if (contentEl) {
            contentEl.innerHTML = (d.body || []).map(line => {
                const s = esc(line);
                if (/^---+$/.test(line.trim()))
                    return '<hr style="border:none;border-top:1px solid #1f2937;margin:10px 0">';
                if (/^###\s/.test(line))
                    return `<div class="cv-h3">${_cvInline(s.replace(/^###\s/,''))}</div>`;
                if (/^##\s/.test(line))
                    return `<div class="cv-h2">${_cvInline(s.replace(/^##\s/,''))}</div>`;
                if (/^#\s/.test(line))
                    return `<div class="cv-h1">${_cvInline(s.replace(/^#\s/,''))}</div>`;
                if (/^\s*\d+\.\s/.test(line))
                    return `<div class="cv-li">• ${_cvInline(s.replace(/^\s*\d+\.\s/,''))}</div>`;
                if (/^\s*[-*]\s/.test(line))
                    return `<div class="cv-li">• ${_cvInline(s.replace(/^\s*[-*]\s/,''))}</div>`;
                if (line.trim() === '')
                    return '<div style="height:5px"></div>';
                return `<div style="line-height:1.6">${_cvInline(s)}</div>`;
            }).join('');
        }

        // Show dispatch button for unprocessed cards
        if (dispatchBtn && ['QUEUED','PENDING','DRAFT'].includes(d.status))
            dispatchBtn.style.display = 'inline-block';

    } catch (e) {
        if (contentEl) contentEl.innerHTML = `<div style="color:var(--danger);padding:12px">Failed: ${esc(String(e))}</div>`;
    }
}

function openFactorCard(file, name) { openCardViewer(file); }

function closeCardViewer() {
    _cvCurrentFile = null;
    const modal = document.getElementById('card-viewer-modal');
    if (modal) modal.style.display = 'none';
}

async function dispatchToResearcher() {
    if (!_cvCurrentFile) return;
    const btn = document.getElementById('cv-dispatch-btn');
    if (btn) { btn.disabled = true; btn.textContent = '⏳ Dispatching...'; }
    try {
        const r = await fetch('/api/dispatch_to_researcher', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ file: _cvCurrentFile })
        });
        const d = await r.json();
        if (btn) {
            btn.textContent = d.error ? '✗ Failed' : '✓ Dispatched';
            setTimeout(() => { btn.disabled = false; btn.textContent = '⚡ DISPATCH TO RESEARCHER'; }, 3000);
        }
        if (!d.error) updateTelemetry();
    } catch (e) {
        if (btn) { btn.disabled = false; btn.textContent = '⚡ DISPATCH TO RESEARCHER'; }
        console.error('dispatchToResearcher failed', e);
    }
}

// ── BOOTSTRAP ────────────────────────────────────────────────────────────────
document.addEventListener('DOMContentLoaded', () => {
    initPipelineAgentBadges();
    updateTelemetry();
    setInterval(updateTelemetry, 5000);
});
