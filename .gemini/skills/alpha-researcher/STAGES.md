# ALPHA RESEARCHER: STAGE-SPECIFIC MISSIONS

## STAGE 1: WEB_SEARCH
- **Goal**: Discovery. **Model**: gemini-3.1-pro-preview
- **Instruction**: Use `google_web_search`. Search for novel alpha (TradingView, GitHub, arXiv). (Optional: Tier 3 API Mining).
- **Mandatory Output**: `[1/3] WEB_SEARCH: Hunting for novel Alpha (TradingView, GitHub, arXiv)...`

## STAGE 2: EXTRACT_ALPHA
- **Goal**: Professional Modeling & Validation. **Model**: gemini-2.5-flash
- **Instruction**: 
    1. Extract core math.
    2. Apply Institutional Guards (Poison/Library/Data).
    3. Create Professional Candidate Card in `factor_library/{CATEGORY}/`.
    4. **YAML frontmatter — mandatory coin and timeframe constraints**:
       - `coins:` — only `BTC`, `ETH`, `BNB`, `SOL`, `XRP`. No exceptions. If source uses another coin, adapt to closest supported one. Primary coin first.
       - `timeframes:` — only `5m`, `15m`, `1h`, `4h`, `1d`. No `30m`, `2h`, `8h` etc. Primary timeframe first, based on strategy's trading frequency.
    5. **Must include**: Strategy Play Style, Strategic Disadvantages, and Enhancement Recommendations.
- **Mandatory Output**: `[2/3] EXTRACT_ALPHA: Modeling math & drafting professional Candidate Card (coins: {list}, tf: {list})...`

## STAGE 3: HYPHO_REPORT_&_INDEX_SYNC
- **Goal**: Categorized Dashboard Visibility, Obsidian Sync, and Handoff. **Model**: gemini-2.5-flash
- **Condition**: Skip this stage entirely if Stage 2 did not produce a novel Candidate Card.
- **Instruction**: 
    1. Generate a formal professional hypothesis report in `phase_6_agent_monitor/alpha_forge_v2/hypho_report/{CATEGORY}/`.
    2. Sync Obsidian Ledger. Handoff to Developer via inbox.
- **Mandatory Output**: `[3/3] HYPHO_REPORT_&_INDEX_SYNC: Generated report, synced ledger, handed off to Developer...`
