# Unified Crypto-RL Control & Review System

This document outlines the architecture for transforming the individual project phases into a cohesive, automated system managed by a central controller and a unified dashboard.

## 1. System Architecture

### A. Central Controller (`main.py`)
A Python-based CLI application that serves as the "brain" of the project.
- **Execution Engine:** Uses `subprocess` to execute Python scripts for each phase.
- **State Tracking:** Maintains a `pipeline_state.json` file to track the status of each phase (Pending, Running, Completed, Failed).
- **Progress Reporting:** Implements `tqdm` for terminal-based progress bars, particularly for Phase 0 (Data Download).
- **Automation Logic:** Optional "Auto-Run" mode where finishing one phase successfully triggers the next.

### B. Master Dashboard (`index.html`)
A root-level web interface providing a single point of entry for all visualizations.
- **Navigation Sidebar:** Quick links to switch between:
    - **Global Overview:** High-level metrics (Sharpe, PBO, latest run date).
    - **Phase 0:** Data quality and distribution report.
    - **Phase 2:** Hyperparameter optimization & Validation results.
    - **Phase 4:** Backtest performance & Equity curves.
    - **Phase 5:** PBO & Overfitting analysis.
- **Dynamic Content:** Uses `<iframe>` or AJAX to load phase-specific dashboards without refreshing the page.

## 2. Integration Features

### Progress Tracking (Phase 0)
- Modify `dl_trainval_data.py` to output machine-readable progress (e.g., `PROGRESS: 45%`).
- `main.py` captures this output and renders a smooth progress bar.

### Auto-Update Mechanism
- **Standardized Export:** Each phase script will export a `data.js` or `data.json` to a standardized location.
- **Registry System:** `pipeline_state.json` will store the paths to the most recent `best_trial` and `result_folder`, allowing dashboards to always show the freshest data.

### Unified Navigation
- Standardizing the CSS across all dashboards for a professional, "software product" feel.
- A shared header component that displays the current model being reviewed and its overall status.

## 3. Implementation Roadmap

1. **Step 1: The Registry:** Create `pipeline_state.json` and a utility script to update it.
2. **Step 2: The Master UI:** Build the root `index.html` with a sidebar and frame layout.
3. **Step 3: The Controller:** Build `main.py` to trigger Phase 0 with a progress bar.
4. **Step 4: Script Linking:** Update Phase 1, 2, 4, and 5 scripts to register their completion and update the Master UI data paths.

---
**Goal:** Transform "Running scripts and checking folders" into "One command to run, one page to review."
