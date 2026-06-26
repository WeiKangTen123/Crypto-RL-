# Alpha Researcher Pipeline

This document covers your job scope: **discover → extract factor → create Candidate Card → hand off**.
The build, optimization, and validation steps are owned by `@alpha-developer`.

## Phase 0 — Strategy Discovery (Web Research)
Use your web search capability to find 1–2 new strategy ideas each session. Search in tier order — stop when you have enough ideas.

**If `google_web_search` fails or returns nothing → skip Phase 0 entirely, go to Phase 1 (queue check). Do NOT block.**

### Tier 1 — Strategy-ready (search first)
| Source | What to Search |
| :--- | :--- |
| TradingView | "best crypto strategy Pine Script 2026", "BTC momentum strategy published scripts" |
| GitHub: `freqtrade/freqtrade-strategies` | Browse recent commits and strategy README |
| GitHub: `jesse-ai/strategies` | Browse full strategy list |
| Quantpedia.com | Search "crypto" or "bitcoin" in their strategy database |
| SSRN (ssrn.com) | "cryptocurrency trading strategy", "bitcoin momentum alpha" |

### Tier 2 — Concepts to implement
| Source | What to Search |
| :--- | :--- |
| arXiv q-fin | "cryptocurrency momentum", "bitcoin trading signal" |
| Reddit r/algotrading | "crypto backtest results" (sort: Top / Month) |
| Binance Research (research.binance.com) | Browse all reports |
| Glassnode blog | On-chain indicator strategies (MVRV, SOPR, exchange flows) |
| CryptoQuant | Taker flow, fund flow, miner data strategy ideas |

### Tier 3 — Broad inspiration (last resort)
| Source | What to Search |
| :--- | :--- |
| X/Twitter | @CryptoCred, @KoroushAK, @CredibleCrypto — search `#cryptostrategy #algotrading` |
| QuantConnect forums | Search "crypto" — community strategy discussions |

### Priority Factor Types (gaps in current library)
Focus discovery on these — data already available in `dataset/`:

```
HIGH PRIORITY:
  1. Funding rate mean reversion   — uses taker_buy_base_vol (already in parquets)
  2. Multi-TF divergence           — RSI/MACD signal on 1h confirmed on 4h + 1d
  3. Volume-profile anchored VWAP  — institutional entry/exit logic
  4. Fear & Greed + RSI combo      — sentiment filter on top of technical signal

MEDIUM PRIORITY:
  5. BTC dominance regime filter   — macro signal for alt coin positioning
  6. Fibonacci retracement + volume confirmation
  7. Basis trade / spot-perp spread mean reversion
```

## Phase 1 — Pick from Queue
Open `factor_library/` and check for any Candidate Cards with `status: QUEUED` that haven't yet been handed off to `@alpha-developer`. Prioritise `interest: High`.

## Phase 2 — Feasibility Check

### Data Universe (definitive — do not deviate)

**Supported coins (5 only)**: `BTC`, `ETH`, `BNB`, `SOL`, `XRP`
No other coins have data. If a strategy from a paper uses DOGE, AVAX, LINK, etc. — adapt it to the most correlated supported coin.

**Available timeframes**: `5m`, `15m`, `1h`, `4h`, `1d`
`30m` exists but is unused — avoid it. `1m` is excluded. `2h`, `8h`, `12h` do not exist.

**Note on `known_data_gaps.md`**: This file logs *partial* gaps (missing days) within existing datasets. It does NOT mean a coin/tf pair is unusable. All 5 coins have usable data across all 5 timeframes above.

### Available columns (no request needed)
All crypto parquets at `dataset/{COIN}/{TF}/spot_ohlcv.parquet` contain:
`Open`, `High`, `Low`, `Close`, `Volume`, `taker_buy_base_vol`, `num_trades`

Funding rate: `dataset/{COIN}/4h/funding_rate.parquet` — column `funding_rate` — all 5 coins, 4h only.

CVD is derivable: `CVD ≈ 2 × taker_buy_base_vol − Volume` (cumulative sum).

### Decision
- **QUEUED** — all required columns exist in the parquets above → proceed to Phase 3.
- **BLOCKED** — strategy needs data NOT listed above (e.g., Open Interest, liquidation events, order book depth, long/short ratio). Fill in the `Data Engineer Request` block in the Candidate Card and send a `DATA_REQUEST` inbox message to `@crypto-data-engineer`. Mark the card `BLOCKED` until confirmed.

### Category decision (file the card correctly)
| Strategy mechanism | Folder |
|---|---|
| Uses `funding_rate` column literally | `Funding_Rate_Arb/` |
| Price returning to mean (RSI, BB, VWAP, Z-score, Keltner) | `Mean_Reversion/` |
| Directional momentum (EMA, MACD, Supertrend, ADX, Ichimoku) | `Trend_Momentum/` |
| Volatility compression → expansion (BB squeeze, Donchian, ATR) | `Volatility_Breakout/` |
| Multi-asset ranking / lead-lag / macro cross-asset | `Cross_Sectional/` |
| On-chain metrics (MVRV, NVT, flows, miner data) | `Sentiment_OnChain/` |

## Phase 3 — Factor Extraction & Candidate Card
1. Extract the pure mathematical logic from the discovered idea.
2. If the math is novel, code it as an isolated function in `strategy_backtest/library.py` (e.g., `def calc_funding_divergence(df): ...`). Do NOT write a full `BaseStrategy` class — that belongs to `@alpha-developer`.
3. Create a Candidate Card in `factor_library/{FactorClass}/` using `factor_library/templates/Factor_Card_Template.md` as the canonical template.
   - Populate `factor_class`, `directional_bias`, `optimal_regime` accurately.
   - Include 2–3 `Recommended Logic Switches` so `@alpha-developer` can build in flexibility.
   - Set `status: QUEUED`.

## Phase 4 — Handoff

**To `@alpha-developer`:**
- Topic: `NEW_FACTOR_DISCOVERED`
- Include: path to Candidate Card, function name in `library.py` (if applicable), any data caveats.

**To `@crypto-data-engineer` (only if `Data Engineer Request` block is filled):**
- Topic: `DATA_REQUEST`
- Include: the exact `NEED:` lines from the card's `Data Engineer Request` block.
- Mark the Candidate Card `status: BLOCKED` until `DATA_VALIDATION_DONE` is received.

After handoff to developer, update the Candidate Card `status` to `HANDED_OFF`.
