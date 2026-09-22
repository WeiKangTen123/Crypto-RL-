# Signal Strive — Submission Results

**Last updated:** 2026-07-12  
**Window:** 2021-01-01 → 2026-05-31  
**Capital (Run B base):** $1,000,000  
**Total submissions:** 55 runs (12 original + 23 + 19 WorldQuant Alpha batch + #241, with #238-240 resubmitted post-fix)

**2026-07-12 update:** #238-240 resubmitted after the `portfolio_engine.py` gross-exposure-cap fix (see "known issue" note below) — their local trade counts didn't change (already under the 3x cap even before the fix), so Signal Strive grades are materially unchanged (still all F). Added #241 FractalVarianceRatio (10-coin, same WorldQuant batch family) — also F (score 25.5, -31.0% Run A / -13.4% Run B). Old run_ids for #238-240 (`sr_338b70067c`, `sr_0e09e47578`, `sr_d1fbd076f1`) were replaced in `runs.json` with the post-fix resubmissions rather than kept as duplicates.

---

## WorldQuant Alpha Batch (#222–#240, 19 strats) — Leaderboard (Run A Score, descending)

All 19 are `MultiCoinBaseStrategy` portfolio strategies (5–10 coins, 4h) submitted in one signal series each (all coins tagged by symbol in a single cross-margin book). Every submission scored both Run A (platform sizing) and Run B (our own `risk_per_trade`/`leverage` from `STRATEGY_LIBRARY`) in one call.

| Rank | Strat | Strategy | A Grade | A Score | A Return | A MDD | B Grade | B Return | run_id |
|------|-------|----------|---------|---------|----------|-------|---------|----------|--------|
| 1 | **#233** | MinDecayChains | F | **41.7** | +77.1% | 28.2% | **D** | +8.5% | sr_0185aa627a |
| 2 | #229 | VwapDecayNegation | F | 33.5 | +67.6% | 61.0% | F | +53.3% | sr_1bd77028d2 |
| 3 | #234 | VWAPSignedPower | F | 27.9 | +20.7% | 38.0% | F | +29.8% | sr_12eebe4a44 |
| 4 | #222 | VolCloseAntiMom | F | 25.5 | -29.3% | 65.7% | F | -9.5% | sr_ecf1976e22 |
| 5 | #224 | CloseOpenRatioMom | F | 24.5 | -38.3% | 54.4% | F | -42.1% | sr_a313cb006b |
| 6 | #230 | ComplexVolRankMomentum | F | 23.8 | -58.5% | 69.5% | F | -27.2% | sr_2ab32d4a63 |
| 7 | #235 | DeltaDecayFade | F | 23.6 | -59.0% | 76.4% | F | +4.9% | sr_b111efadcf |
| 8 | #237 | ExtremeNestedDecay | F | 23.3 | -72.0% | 76.5% | F | -51.8% | sr_e15e24fe5c |
| 9 | #239 | TripleTsRank | F | 23.0 | -62.1% | 72.7% | F | -34.2% | sr_0e09e47578 |
| 10 | #240 | MarketStressIndex | F | 23.0 | -42.7% | 71.3% | F | +7.2% | sr_d1fbd076f1 |
| 11 | #225 | OhlcGapRatio | F | 22.7 | -69.6% | 82.3% | F | -37.7% | sr_214b3d4c86 |
| 12 | #236 | RankDecayCascade | F | 22.0 | -81.0% | 87.0% | F | -5.5% | sr_27ed9a2eab |
| 13 | #226 | ReturnVolRatio | F | 21.5 | -62.7% | 70.1% | F | -51.0% | sr_41f815cda4 |
| 14 | #231 | RollingQuantileRegression | F | 21.2 | -17.3% | 73.3% | F | +47.4% | sr_e07779f8c4 |
| 15 | #238 | CorrelationMatrixGate | F | 21.2 | -93.5% | 95.7% | F | -80.1% | sr_338b70067c |
| 16 | #232 | ComplexVolumeScalar | F | 21.0 | -94.3% | 96.1% | F | -42.5% | sr_2d47ff82b6 |
| 17 | #227 | DecayLinearMomentum | F | 20.9 | -90.6% | 91.5% | F | -29.5% | sr_b5b3e65668 |
| 18 | #223 | OpenCloseRatioRank | F | 20.7 | -22.6% | 62.8% | F | +11.1% | sr_d4f3968a20 |
| 19 | #228 | DoubleDecayMin | F | 17.1 | +4.0% | 61.2% | F | -35.6% | sr_10ce03cf83 |

**Takeaways:**
- **All 19 scored F on Run A** — this batch is WorldQuant "Alpha 101" style factor formulas ported directly to crypto 4h bars; none clear the Sharpe > 0.7 edge-dimension threshold.
- **#233 MinDecayChains is the standout** — only D-grade Run B in the batch (score 41.7/A, 8.5% return with a much better MDD profile than the rest), and the only one with a controlled 28.2% max drawdown.
- **Most of the batch has severe drawdowns (60-96% MDD)** — several (#227, #232, #238) breach 90% MDD, consistent with raw factor signals having no stop-loss/risk discipline beyond the shared `risk_per_trade=0.05, leverage=3` config.
- **Run B (our sizing) sometimes flips sign vs Run A** — e.g. #231 RollingQuantileRegression: -17.3% (A) → +47.4% (B), #223: -22.6% (A) → +11.1% (B) — our lower-leverage, wider-book sizing dampens some of the volatility that hurts these factors under the platform's standard sizing.
- Submission tooling: `Signal_Replay/submit_batch.py` (payload construction, dry-run mode) + `Signal_Replay/finalize_runs.py` (batch driver, writes compact records into `runs.json`) — reusable for future strategy ID ranges.

**Known issue — multi-coin fill inflation (unresolved, not a payload bug):** These 19 runs show 2.3–24x more Run A fills than local trades (e.g. #232: 9,069 local trades → 23,477 platform fills), vs. the prior 35-run batch's ~1:1 ratio (see `mapping_result/strat_mapping.md`). The difference: the old batch submitted one symbol per run; this batch submits 5–10 symbols in one shared cross-margin book per run (per `usage.MD`'s "Multiple Coins → One Portfolio" — capped at 3× gross exposure / 95% equity per position). Four controlled live tests (dropping-event fix, margin/leverage cut, adding `strength`) each changed exactly one payload field and produced **byte-identical** Run A results (`n_fills`, `total_return`, `max_drawdown` all unchanged) — proving Run A's replay is a pure function of `(ts, symbol, target)` only; sizing/conviction fields never touch it. Fill count scales with how many coins are held simultaneously over the window, not with anything tunable in the submission. The only method with confirmed ~1:1 behavior is per-coin (single-symbol) submissions — not attempted here since it would mean ~150+ runs instead of 19 and grades per-coin edge instead of portfolio edge. Decision: accepted as-is; revisit with per-coin submissions if this batch's grades matter more precisely later.

---

## All-Time Leaderboard (Run A Score, descending)

| Rank | Strat | Strategy | Coin/TF | A Grade | A Score | A Return | A MDD | A Sharpe | B Grade | B Return | run_id |
|------|-------|----------|---------|---------|---------|----------|-------|----------|---------|----------|--------|
| 1 | **#14** | MACDKDJStrategy | ETH/4h | **C** | **62.1** | +39.5% | 7.4% | 0.326 | **C** | +11.0% | sr_d43dd58bfb |
| 2 | **#184** | DiamondTriangleBreakout | BTC/4h | D | 51.3 | +383.7% | 26.8% | 0.256 | **C** | +227.8% | sr_4b207ddc96 |
| 3 | **#56** | SupertrendPro | ETH/4h | D | 45.6 | +123.9% | 34.9% | 0.370 | D | +146.1% | sr_01702ae7cc |
| 4 | **#35** | VWAPATRReversion | BNB/4h | D | 54.9 | +138.3% | 35.8% | 0.383 | N/A | — | sr_54413c9624 |
| 5 | **#36** | VWAPATRReversion | SOL/4h | D | 52.7 | +411.7% | 32.5% | 0.390 | N/A | — | sr_5f2b10ca1e |
| 6 | #178 | ForgeStrategy | XRP/1d | D | 48.1 | +299.3% | 80.7% | 0.717 | N/A | — | sr_5f4b650d2c |
| 7 | #168 | ForgeStrategy | ETH/1d | D | 45.9 | +199.0% | 65.2% | 0.676 | N/A | — | sr_3a33a3808d |
| 8 | #193 | HurstRegimeAdaptive | ETH/4h | D | 44.6 | +87.4% | 37.0% | 0.295 | D | +121.2% | sr_2bb29885a3 |
| 9 | #182 | SupertrendEmaFilter | BTC/4h | D | 45.7 | +50.2% | 22.0% | 0.242 | D | +31.1% | sr_80f9337079 |
| 10 | #172 | ForgeStrategy | SOL/4h | D | 42.1 | +984.0% | 58.4% | 0.467 | N/A | — | sr_89b7ca864b |
| 11 | #38 | FVGMitigationReversal | BTC/4h | D | 42.1 | +281.2% | 46.3% | 0.381 | N/A | — | sr_f4781d5f46 |
| 12 | #66 | ZeroLagTrendSpeed | SOL/4h | F | 41.3 | +477.9% | 59.0% | 0.348 | N/A | — | sr_26e6c6f017 |
| 13 | #41 | DMIADXStrategy | XRP/4h | F | 41.1 | +17.2% | 14.3% | 0.151 | N/A | — | sr_8fb98359b0 |
| 14 | #25 | SuperFVMAStrategy | SOL/4h | F | 38.7 | +602.1% | 53.2% | 0.395 | N/A | — | sr_30177abf38 |
| 15 | #189 | PriceMomentumAccel | ETH/1h | F | 35.8 | +58.7% | 45.3% | 0.208 | F | +34.1% | sr_9a43001b17 |
| 16 | #167 | ForgeStrategy | ETH/4h | F | 35.6 | +129.8% | 42.4% | 0.245 | N/A | — | sr_ed738242fa |
| 17 | #116 | ForgeStrategy bb_breakout | ETH/4h | F | 33.2 | +34.7% | 25.2% | 0.142 | F | +11.8% | sr_89b11ed3f5 |
| 18 | #113 | ForgeStrategy bb_breakout | ETH/4h | F | 33.1 | +49.0% | 34.6% | 0.175 | F | +15.9% | sr_d04fcb053b |
| 19 | #31 | LiquiditySweepReversal | ETH/4h | F | 33.9 | +178.0% | 64.4% | 0.256 | F | +125.2% | sr_a2129faa2e |
| 20 | #177 | ForgeStrategy | XRP/4h | F | 30.6 | +60.0% | 53.1% | 0.170 | N/A | — | sr_386c3dd6f2 |
| 21 | #139 | DumpReversalPeakTrail | BTC/4h | F | 30.4 | +115.2% | 51.8% | 0.219 | N/A | — | sr_e796c3c9eb |
| 22 | #122 | ForgeStrategy ema_price_cross | ETH/4h | F | 28.4 | -21.1% | 41.3% | -0.090 | F | -18.3% | sr_a72faa2bf4 |
| 23 | #119 | ForgeStrategy hma_cross | ETH/4h | F | 26.5 | +7.8% | 47.7% | 0.047 | F | +11.4% | sr_c94f4ed815 |
| 24 | #20 | SupertrendProStrategy | BTC/4h | F | 29.0 | +28.5% | 37.1% | 0.129 | N/A | — | sr_4aa6654fca |
| 25 | #50 | EMACrossoverStrategy | SOL/4h | F | 29.0 | +776.5% | 78.3% | 0.365 | N/A | — | sr_1eabc71680 |
| 26 | #84 | RWAMomentumStrategy | ETH/4h | F | 26.7 | +16.2% | 54.7% | 0.096 | D | +58.4% | sr_e7007358f5 |
| 27 | #62 | SupertrendPro | BNB/4h | F | 25.4 | +14.8% | 57.9% | 0.093 | F | +22.6% | sr_f0fe315d5a |
| 28 | #115 | ForgeStrategy hma_cross | ETH/4h | F | 25.2 | +25.1% | 68.8% | 0.120 | F | +19.7% | sr_d0dc25c8cc |
| 29 | #72 | MeanReversionFundingRate | SOL/4h | F | 22.1 | +0.2% | 28.5% | 0.029 | F | +2.8% | sr_2ee8fa6842 |
| 30 | #24 | SuperFVMAStrategy | BNB/4h | F | 21.8 | +24.2% | 70.0% | 0.116 | N/A | — | sr_c1e79a2bb5 |
| 31 | #176 | ForgeStrategy | XRP/1h | F | 21.7 | -84.6% | 97.5% | -0.288 | F | -34.3% | sr_f2c51f316a |
| 32 | #73 | MeanReversionFundingRate | XRP/4h | F | 20.4 | -2.6% | 49.1% | 0.038 | F | -4.1% | sr_46093ddb1e |
| 33 | #148 | ForgeStrategy ema_cross | ADA/1h | F | 20.5 | -92.0% | 93.9% | -0.388 | F | -90.1% | sr_e2227a0496 |
| 34 | #57 | SupertrendPro | SOL/4h | F | 22.3 | -56.1% | 69.6% | -0.088 | F | -42.8% | sr_a8005a677e |
| 35 | #123 | ForgeStrategy | ETH/4h | F | 19.5 | -22.3% | 60.6% | 0.013 | F | +18.4% | sr_06ebf48dae |

> **N/A for Run B** = first 15 new strats submitted with an older script that had a RunB parsing bug (reads `report_b` instead of `sizing.run_b`). Summary stats unavailable.

---

## New Batch (23 strats) — Scorecard Detail

| Strat | Strategy | Edge | Robustness | Consistency | Cost & Cap | Overall |
|-------|----------|------|-----------|-------------|------------|---------|
| #14 | MACDKDJStrategy | F (33.9) | **B (81.2)** | **B (77.7)** | **C (71.8)** | **C 62.1** |
| #35 | VWAPATRReversion BNB | F (32.2) | D (46.8) | **B (72.7)** | **A (86.8)** | D 54.9 |
| #36 | VWAPATRReversion SOL | F (32.8) | F (38.5) | **B (76.8)** | **B (81.1)** | D 52.7 |
| #178 | ForgeStrategy XRP/1d | **C (61.4)** | F (28.9) | C (61.7) | F (35.3) | D 48.1 |
| #168 | ForgeStrategy ETH/1d | D (54.5) | F (27.4) | C (64.1) | F (35.5) | D 45.9 |
| #182 | SupertrendEmaFilter | F (25.3) | C (59.2) | C (64.5) | D (45.7) | D 45.7 |
| #172 | ForgeStrategy SOL/4h | F (39.1) | F (30.6) | C (64.5) | F (39.1) | D 42.1 |
| #38 | FVGMitigationReversal | F (34.5) | F (36.5) | C (61.5) | D (43.2) | D 42.1 |
| #66 | ZeroLagTrendSpeed | F (38.5) | F (35.8) | C (62.0) | F (32.3) | F 41.3 |
| #41 | DMIADXStrategy | F (15.5) | D (54.2) | C (62.0) | D (48.6) | F 41.1 |
| #25 | SuperFVMAStrategy SOL | F (36.3) | F (30.6) | C (58.3) | F (33.6) | F 38.7 |
| #167 | ForgeStrategy ETH/4h | F (23.2) | F (34.6) | D (57.3) | F (36.9) | F 35.6 |
| #31 | LiquiditySweepReversal | F (23.2) | F (29.7) | C (60.2) | F (31.7) | F 33.9 |
| #177 | ForgeStrategy XRP/4h | F (14.7) | F (27.3) | C (60.1) | F (33.3) | F 30.6 |
| #139 | DumpReversalPeakTrail | F (24.5) | F (21.8) | D (54.8) | F (27.3) | F 30.4 |
| #20 | SupertrendProStrategy BTC | F (12.0) | F (34.8) | C (61.1) | F (19.5) | F 29.0 |
| #50 | EMACrossoverStrategy | F (26.2) | F (17.8) | D (57.5) | F (19.8) | F 29.0 |
| #84 | RWAMomentumStrategy | F (10.9) | F (29.8) | D (53.8) | F (23.0) | F 26.7 |
| #72 | MeanReversionFundingRate SOL | F (4.0) | F (38.3) | D (55.7) | F (0.0) | F 22.1 |
| #24 | SuperFVMAStrategy BNB | F (10.6) | F (13.2) | D (54.3) | F (19.6) | F 21.8 |
| #176 | ForgeStrategy XRP/1h | F (2.3) | F (0.0) | D (52.6) | D (51.6) | F 21.7 |
| #73 | MeanReversionFundingRate XRP | F (4.3) | F (14.5) | C (58.6) | F (18.0) | F 20.4 |
| #123 | ForgeStrategy ETH/4h (alt) | F (3.6) | F (7.0) | D (55.8) | F (26.7) | F 19.5 |

---

## Original Batch (12 strats) — Leaderboard

| Rank | Strat | Strategy | Coin/TF | A Grade | A Score | A Return | A MDD | B Grade | B Score | run_id |
|------|-------|----------|---------|---------|---------|----------|-------|---------|---------|--------|
| 1 | **#184** | DiamondTriangleBreakout | BTC/4h | D | 51.3 | +383.7% | 26.8% | **C** | **60.1** | sr_4b207ddc96 |
| 2 | **#56** | SupertrendPro | ETH/4h | D | 45.6 | +123.9% | 34.9% | D | 50.4 | sr_01702ae7cc |
| 3 | **#193** | HurstRegimeAdaptive | ETH/4h | D | 44.6 | +87.4% | 37.0% | D | 46.2 | sr_2bb29885a3 |
| 4 | #189 | PriceMomentumAccel | ETH/1h | F | 35.8 | +58.7% | 45.3% | F | 34.1 | sr_9a43001b17 |
| 5 | #116 | ForgeStrategy bb_breakout | ETH/4h | F | 33.2 | +34.7% | 25.2% | F | 30.4 | sr_89b11ed3f5 |
| 6 | #113 | ForgeStrategy bb_breakout | ETH/4h | F | 33.1 | +49.0% | 34.6% | F | 29.5 | sr_d04fcb053b |
| 7 | #122 | ForgeStrategy ema_price_cross | ETH/4h | F | 28.4 | -21.1% | 41.3% | F | 29.2 | sr_a72faa2bf4 |
| 8 | #119 | ForgeStrategy hma_cross | ETH/4h | F | 26.5 | +7.8% | 47.7% | F | 29.7 | sr_c94f4ed815 |
| 9 | #62 | SupertrendPro | BNB/4h | F | 25.4 | +14.8% | 57.9% | F | 24.6 | sr_f0fe315d5a |
| 10 | #115 | ForgeStrategy hma_cross | ETH/4h | F | 25.2 | +25.1% | 68.8% | F | 27.5 | sr_d0dc25c8cc |
| 11 | #57 | SupertrendPro | SOL/4h | F | 22.3 | -56.1% | 69.6% | F | 23.8 | sr_a8005a677e |
| 12 | #148 | ForgeStrategy ema_cross | ADA/1h | F | 20.5 | -92.0% | 93.9% | F | 21.6 | sr_e2227a0496 |

**Skipped (no trades — need order-flow data not in OHLCV):**
- #117 entry=cvd_cross, #120 entry=fvg, #125 entry=imbalance_zone

---

## Original Batch — Scorecard Detail (Run A)

| Strat | Edge | Robustness | Consistency | Cost & Capacity | Overall |
|-------|------|-----------|-------------|-----------------|---------|
| #184 | D (43.8) | D (56.8) | C (63.2) | D (45.9) | **D 51.3** |
| #56  | F (33.0) | D (50.2) | C (64.5) | D (43.0) | D 45.6 |
| #193 | F (23.3) | F (31.5) | C (61.9) | **B (81.3)** | D 44.6 |
| #189 | F (26.7) | F (27.2) | C (59.9) | F (38.5) | F 35.8 |
| #116 | F (11.9) | F (38.0) | D (57.6) | F (40.2) | F 33.2 |
| #113 | F (15.4) | D (42.6) | D (56.4) | F (29.1) | F 33.1 |
| #122 | F (2.5) | F (21.9) | D (54.6) | D (55.7) | F 28.4 |
| #119 | F (8.6) | F (18.6) | D (55.4) | F (38.9) | F 26.5 |
| #62  | F (7.2) | F (15.7) | C (58.9) | F (35.7) | F 25.4 |
| #115 | F (10.6) | F (14.1) | D (55.6) | F (34.5) | F 25.2 |
| #57  | F (2.2) | F (4.6) | D (47.0) | D (54.8) | F 22.3 |
| #148 | F (1.3) | F (0.0) | D (43.2) | D (57.0) | F 20.5 |

---

## Key Takeaways

### New Batch Highlights

**#14 MACDKDJStrategy ETH/4h — Best New Submission (C/62.1)**
- Only C-grade in both Run A and Run B from the new batch
- Low drawdown (7.4%), decent Sharpe (0.326), only 74 fills — low cost drag
- Robustness B (81.2) and Consistency B (77.7) are exceptional; Edge still F because Sharpe < 0.7 threshold
- Run B also C (59.9) — platform's sizing doesn't hurt it

**#35 / #36 VWAPATRReversion (BNB/SOL) — Best Cost & Cap**
- Cost & Cap A (86.8) and B (81.1) respectively — very low fee drag
- Low trade counts (62–63 fills over 5 years) means low friction
- Grade D due to F-level edge, but cost efficiency is the best of all 35 strats

**Daily Timeframes Work Better on Edge**
- #178 ForgeStrategy XRP/1d: Edge C (61.4) — best edge score of any new strat
- #168 ForgeStrategy ETH/1d: Edge D (54.5) — also above average
- Daily TF → fewer fills → higher per-trade value → platform rewards it

**#182 SupertrendEmaFilter BTC/4h — Best Robustness (New Batch)**
- Robustness C (59.2), MDD only 22.0% — clean drawdown profile
- Also has RunB D (57.4), reasonable improvement

### Why Most Score F

1. **Edge dimension (weight 35%)** requires Sharpe > 0.7 for a passing score — most strats are 0.1–0.5
2. **Robustness** punishes MDD > 50% — many SOL/XRP strats breach this heavily
3. **Cost ratio too high** — high-frequency strategies (176 XRP/1h: 1975 fills) burn on fees + slippage + funding
4. **#72/#73 MeanReversionFundingRate** essentially flat on SS despite positive local backtest — funding rate signal doesn't translate to SS execution model

### Pattern Comparison: Original vs New Batch

| Metric | Original 12 | New 23 |
|--------|-------------|--------|
| Best grade | D (51.3) | C (62.1) |
| D-grade count | 3/12 | 8/23 |
| F-grade count | 9/12 | 15/23 |
| Avg A Score | 31.5 | 33.4 |
| Positive ROI count | 9/12 | 17/23 |

New batch is slightly better on average — more D-grades and a C-grade winner.

### Top 5 To Watch
1. **#14** — C grade both runs, low risk, ETH/4h, steady
2. **#184** — C grade RunB, BTC/4h, highest absolute ROI in original batch
3. **#35** — D grade, best cost efficiency (A), low drawdown candidate
4. **#178** — D grade, best edge score of new batch, XRP/1d
5. **#36** — D grade, SOL/4h, strong consistency B + cost B

---

## Price Mapping Analysis — Deep Analysis v3 (2026-07-08)

**Method:** Side + position-state fill classification  
**Coverage:** 33 strats (skipped #35, #36 — BNB/SOL VWAPATRReversion, 2020–2021 data only)  
**Capped at:** 2026-05-31

### Overall SS Fill Statistics

| Metric | Value |
|--------|-------|
| Total local entries submitted | 7,361 |
| Total local exits submitted | 7,354 |
| **Total SS fills (raw)** | **13,103** |
| **Total SS entry fills** | **6,657** (90.4% fill rate) |
| **Total SS exit fills** | **6,446** (87.7% fill rate) |
| Avg entry diff — side-based (NEW) | **3.422%** |
| Avg entry diff — sequential (OLD) | 8.552% |
| Avg exit diff — side-based | 11.705% |

> **Note on exit diff:** Exit diff is elevated (11.7% avg) because 5 high-lag strats with 50–322 bar delays are included. The exit fill rate is also lower than entry rate because SS hit the 1000-fill cap on strats with many trades (e.g. #176 XRP/1h only got 50.6% entry coverage — those excess trades have no corresponding exits to match).

---

### Root Cause Analysis

Two distinct root causes were identified for the elevated entry price diffs seen in prior analysis:

#### Root Cause 1 — Sequential Pairing Shift Bug (affects most strats)

The old approach assigned SS fills by index: `ss[0]=entry1, ss[1]=exit1, ss[2]=entry2, ...`. When SS skips any fill, all subsequent assignments shift — local entry N ends up compared to an exit fill or a wrong entry fill. This creates artificially large diffs (10–28%).

**Fix:** Side + position-state tracking correctly classifies each fill as entry/exit by inspecting the `side` field (`"buy"`/`"sell"`) and tracking running position state (None → long/short on entry, long/short → None on exit). `exit_reason` is always `""` for all fills and cannot be used.

**Impact — sequential → side-based:**
- #41 XRP/4h: 14.905% → 1.103%
- #50 SOL/4h: 11.659% → 1.736%
- #167 ETH/4h: 12.059% → 1.642%
- #172 SOL/4h: 15.728% → 1.708%
- #176 XRP/1h: 9.155% → 1.134%
- #189 ETH/1h: 15.957% → 1.739%
- #193 ETH/4h: 10.882% → 2.503%

#### Root Cause 2 — Genuine SS Fill Lag (5 strats)

SS has a 1000-fill cap per submission. Signals beyond the cap are queued, creating timestamp drift. Even with correct side-based matching, these fills happen 96–322 bars (16–53 days) after the signal. The price difference is real — SS filled at a completely different market price.

| Strat | Entry Diff | Avg Lag | Max Lag | Comment |
|-------|-----------|---------|---------|---------|
| #115 ForgeStrategy ETH/4h | 21.90% | 321.9 bars | 1145 bars | ~53 days avg lag |
| #122 ForgeStrategy ETH/4h | 15.89% | 245.6 bars | 1105 bars | ~41 days avg lag |
| #119 ForgeStrategy ETH/4h | 12.65% | 132.7 bars | 375 bars | ~22 days avg lag |
| #184 DiamondTriangleBreakout BTC/4h | 7.67% | 96.9 bars | 380 bars | ~16 days avg lag |
| #148 ForgeStrategy ADA/1h | 5.77% | 137.4 bars | 736 bars | ~5.7 days avg lag (1h bars) |

These 5 strats have **unreliable SS price comparisons** — the fills reflect SS's actual execution at delayed market prices, not the strategy's intended entry price.

---

### Per-Strategy Fill & Diff Summary

| Strat | Strategy | Coin/TF | SS Total | SS Entry | SS Exit | E Rate | X Rate | ΔE New | ΔE Old | Avg Lag | Group |
|-------|----------|---------|---------|---------|---------|--------|--------|--------|--------|---------|-------|
| #14 | MACDKDJStrategy | ETH/4h | 74 | 37 | 37 | 100.0% | 100.0% | 1.86% | 1.86% | 1.0 | ✅ low |
| #20 | SupertrendPro | BTC/4h | 760 | 380 | 380 | 101.6% | 101.6% | 1.94% | 1.94% | 1.0 | ✅ low |
| #24 | SuperFVMA | BNB/4h | 248 | 124 | 124 | 100.0% | 100.8% | 1.61% | 1.61% | 1.0 | ✅ low |
| #25 | SuperFVMA | SOL/4h | 204 | 102 | 102 | 100.0% | 100.0% | 2.33% | 2.33% | 1.0 | ✅ low |
| #31 | LiquiditySweepReversal | ETH/4h | 262 | 131 | 131 | 100.0% | 100.8% | 1.99% | 1.97% | 1.0 | ✅ low |
| #38 | FVGMitigationReversal | BTC/4h | 144 | 74 | 70 | 100.0% | 94.6% | 4.68% | 12.17% | 12.0 | ✅ low |
| #41 | DMIADXStrategy | XRP/4h | 70 | 36 | 34 | 102.9% | 97.1% | 1.10% | 14.91% | 1.5 | ✅ low |
| #50 | EMACrossover | SOL/4h | 394 | 199 | 195 | 100.5% | 99.0% | 1.74% | 11.66% | 1.2 | ✅ low |
| #56 | SupertrendPro | ETH/4h | 542 | 271 | 271 | 101.1% | 101.1% | 2.20% | 2.20% | 1.0 | ✅ low |
| #57 | SupertrendPro | SOL/4h | 1000 | 500 | 500 | 96.7% | 96.7% | 2.40% | 2.40% | 1.0 | ✅ low |
| #62 | SupertrendPro | BNB/4h | 875 | 438 | 437 | 101.2% | 100.9% | 1.64% | 1.64% | 1.0 | ✅ low |
| #66 | ZeroLagTrendSpeed | SOL/4h | 72 | 36 | 36 | 102.9% | 102.9% | 2.45% | 2.45% | 1.0 | ✅ low |
| #72 | MeanReversionFundingRate | SOL/4h | 98 | 49 | 49 | 100.0% | 100.0% | 1.54% | 1.54% | 1.0 | ✅ low |
| #73 | MeanReversionFundingRate | XRP/4h | 206 | 103 | 103 | 101.0% | 101.0% | 1.04% | 1.04% | 1.0 | ✅ low |
| #84 | RWAMomentum | ETH/4h | 105 | 53 | 52 | 101.9% | 100.0% | 2.24% | 2.42% | 1.0 | ✅ low |
| #113 | Forge bb_breakout | ETH/4h | 385 | 193 | 192 | 100.5% | 100.0% | 1.49% | 1.49% | 1.0 | ✅ low |
| #115 | Forge hma_cross | ETH/4h | 329 | 182 | 147 | 95.3% | 77.0% | **21.90%** | 23.96% | **321.9** | ⚠️ HIGH |
| #116 | Forge bb_breakout | ETH/4h | 457 | 229 | 228 | 101.3% | 100.9% | 1.62% | 1.62% | 1.0 | ✅ low |
| #119 | Forge hma_cross | ETH/4h | 297 | 161 | 136 | 98.8% | 84.0% | **12.65%** | 28.37% | **132.7** | ⚠️ HIGH |
| #122 | Forge ema_price_cross | ETH/4h | 206 | 109 | 97 | 96.5% | 85.8% | **15.89%** | 22.89% | **245.6** | ⚠️ HIGH |
| #123 | Forge | ETH/4h | 685 | 348 | 337 | 99.4% | 96.3% | 2.98% | 9.30% | 17.3 | ✅ low |
| #139 | DumpReversalPeakTrail | BTC/4h | 168 | 84 | 84 | 109.1% | 109.1% | 3.21% | 3.21% | 1.0 | ✅ low |
| #148 | Forge ema_cross | ADA/1h | 1000 | 513 | 487 | 70.6% | 67.0% | **5.77%** | 15.85% | **137.4** | ⚠️ HIGH |
| #167 | Forge | ETH/4h | 546 | 280 | 266 | 101.1% | 96.0% | 1.64% | 12.06% | 1.4 | ✅ low |
| #168 | Forge | ETH/1d | 122 | 61 | 61 | 100.0% | 101.7% | 3.08% | 3.13% | 1.0 | ✅ low |
| #172 | Forge | SOL/4h | 565 | 288 | 277 | 100.7% | 96.9% | 1.71% | 15.73% | 1.5 | ✅ low |
| #176 | Forge | XRP/1h | 1000 | 510 | 490 | 50.6% | 48.6% | 1.13% | 9.16% | 2.4 | ✅ low |
| #177 | Forge | XRP/4h | 919 | 460 | 459 | 100.9% | 100.7% | 1.41% | 2.25% | 1.0 | ✅ low |
| #178 | Forge | XRP/1d | 114 | 59 | 55 | 100.0% | 94.8% | 3.72% | 12.92% | 2.5 | ✅ low |
| #182 | SupertrendEmaFilter | BTC/4h | 156 | 78 | 78 | 100.0% | 100.0% | 2.84% | 2.84% | 1.0 | ✅ low |
| #184 | DiamondTriangleBreakout | BTC/4h | 476 | 245 | 231 | 98.8% | 93.5% | **7.67%** | 13.60% | **96.9** | ⚠️ HIGH |
| #189 | PriceMomentumAccel | ETH/1h | 477 | 248 | 229 | 101.6% | 93.9% | 1.74% | 15.96% | 7.5 | ✅ low |
| #193 | HurstRegimeAdaptive | ETH/4h | 147 | 76 | 71 | 102.7% | 95.9% | 2.50% | 10.88% | 2.1 | ✅ low |

**✅ low diff (< 5%):** 28 strats — entry price comparison is reliable  
**⚠️ HIGH diff (≥ 5%):** 5 strats — SS fill lag makes price comparison unreliable

---

### Takeaways

1. **Old sequential diffs (8.55% avg) were mostly measurement error** — correct side-based matching drops this to 3.42% across 33 strats.
2. **28/33 strats have reliable SS fills** — avg entry diff 1–4%, lag ≈ 1–17 bars. These are usable for live deployment confidence.
3. **5 strats have genuine SS lag** (#115, #119, #122, #148, #184) — SS hit its 1000-fill cap on these and queued signals weeks/months late. Their price comparison is not meaningful.
4. **Exit diffs are higher than entry diffs** for many strats even in the low-diff group (e.g. #41: exit diff 30.1% despite entry diff 1.1%). This is expected — exits depend on the position's in-fill state, and mismatches from fill-cap truncation affect exit coverage more than entries.
5. **#176 XRP/1h fill rate only 50.6%** — SS only received half the signals due to the 1000-fill cap on a 2000+ fill strategy. Low diff (1.13%) because only the early signals (before cap) were executed at near-correct prices.

---

## Settings Used Per Submission

| Strat | risk_per_trade | leverage | fee |
|-------|---------------|----------|-----|
| #56, #57, #62 | 0.10 | 10 | 0.0005 |
| #113–#122 (Forge) | 0.10 | 10 | 0.0004 |
| #148 (Forge ADA) | 0.05 | 5 | 0.0004 |
| #184 | 0.10 | 10 | 0.0005 |
| #189, #193 | 0.10 | 10 | 0.0005 |
| New batch (#14–#178) | per STRATEGY_LIBRARY | per strat | per strat |

*All runs use initial_balance=$1,000,000 for comparability with platform's $1M base.*
