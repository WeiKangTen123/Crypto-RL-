# Signal Replay — Usage Guide
> preview of the future backtest

Run your strategy on **your own infra** and POST your signals to our API — we replay exactly what you sent and score it, and **we never run your code**. Mint a key below, integrate (the Claude Code prompt wires it up for you), and every submission becomes a scored run in **your** table. This is the model that will replace strategy-upload backtests.

---

## Signal API Endpoint

What a provider integrates against. They pull market data / timestamps from us, and POST a signal when their model fires. We stamp `as_of` on receipt.

```
POST https://btest.abcz-tr.com/api/v1/signals
```

> `as_of` is stamped server-side on receipt — providers can't back-date a signal or claim latency they didn't have.

### Signal Contract

| Field      | Type          | Meaning                                                              |
|------------|---------------|----------------------------------------------------------------------|
| `ts`       | int (ns) req  | decision time (their bar)                                            |
| `symbol`   | string req    | e.g. BTCUSDT                                                         |
| `target`   | float [-1,1] req | desired position: +1 long … -1 short, 0 flat                     |
| `strength` | float         | conviction — **sizes the bet** (higher = bigger, relative to your own calls) |
| `margin`   | float ($)     | optional sizing scheme → runs your scheme alongside ours            |
| `leverage` | float         | optional — with margin → notional = margin × leverage               |
| `notional` | float ($)     | optional — explicit Run B notional (instead of margin × leverage)   |
| `horizon`  | int (ns)      | optional intended hold                                               |
| `reason`   | string        | optional free text                                                   |
| `as_of`    | int (ns)      | server-stamped — ignored if sent                                     |

### Example

```bash
# provider POSTs its signal series (one submission → one scored run)
curl -X POST https://btest.abcz-tr.com/api/v1/signals \
  -H "Authorization: Bearer sk_sig_..." \
  -H "Content-Type: application/json" \
  -d '{
    "symbol": "BTCUSDT", "resolution": "1d",
    "signals": [
      {"ts": 1700000000000000000, "target": 1.0},
      {"ts": 1701000000000000000, "target": 0.0}
    ]
  }'
```

We replay the submitted series through the same deterministic engine (fills, fees, slippage, funding) — the score reflects OUR execution, not theirs. One submission → one run in the table below.

---

## Sizing — Want to Set Your Own Leverage?

Every run is graded on **our standard sizing (Run A)** — that's the **grade of record**, so results stay comparable across providers. If you also want **your own leverage / margin** measured, tag every signal with a sizing scheme and we'll **additionally** replay it as **Run B** and report the gap between the two.

### Run A — Standard Sizing (ALWAYS)

```json
// just direction + conviction — we size it
"signals": [
  {"ts": ..., "target": 1.0, "strength": 0.8},
  {"ts": ..., "target": -0.5, "strength": 0.3}
]
```

### Run B — Your Own Leverage (OPTIONAL)

```json
// add margin + leverage to EVERY signal
"signals": [
  {"ts": ..., "target": 1.0, "margin": 500,  "leverage": 5},
  {"ts": ..., "target": 1.0, "margin": 1000, "leverage": 3}
]
```

One cross-margin book, ≤95% of equity per position. `strength` (optional) scales the bet — higher conviction → bigger bet, relative to your own calls.

`margin` (USD) × `leverage` = your notional — or send an explicit `notional`.  
We replay your scheme alongside Run A; the **A↔B gap is what your sizing is worth**.  
Miss the scheme on any signal → Run B is skipped. (`target` still sets direction; your scheme sets size.)

The grade of record stays Run A either way — we never let a provider flatter the headline grade with their own sizing. Run B is shown as a side-by-side comparison in each run's report.

---

## Multiple Coins & Custom Backtest Period

Two more knobs on a submission: run a **multi-coin book**, and pin the **backtest window** instead of letting it default to wherever your signals fall.

### Multiple Coins → One Portfolio

```json
// tag each signal with its own symbol
"signals": [
  {"ts": ..., "symbol": "BTCUSDT",  "target": 1.0},
  {"ts": ..., "symbol": "ETHUSDT",  "target": -0.5},
  {"ts": ..., "symbol": "SOLUSDT",  "target": 1.0}
]
```

All coins run in **one cross-margin book** (gross exposure capped at 3×) → one equity curve, one grade for the basket. The top-level `symbol` becomes an optional fallback. Coins we have no price data for are **skipped** and listed as uncovered.

### Custom Period (Optional)

```json
// pin the window; omit → your signal span
{
  "resolution": "1d",
  "start": "2023-01-01",
  "end":   "2025-01-01",
  "signals": [ ... ]
}
```

We replay over exactly `[start, end]` (clipped to available data). Time with no active signal is **flat**; signals outside are ignored. Handy to grade **every provider on the same window**. Omit both → first-signal … last-signal.

---

## Integrate with Claude Code

Hand this to your Claude Code — it has the endpoint, auth, signal contract and the rules, so it wires up submission correctly the first time. (Swap in your own provider key.)

```
You are integrating with the SIGNAL STRIVE signal-replay API to submit trading signals for evaluation.

WHAT THIS IS
  I run my own strategy on my own infra. When my model decides a position, I POST a signal.
  The platform stamps `as_of` on receipt, replays my submitted signals through its deterministic
  engine (its fills, fees, slippage, funding) and scores the result. It never runs my code.

ENDPOINT
  POST https://btest.abcz-tr.com/api/v1/signals
  Headers:
    Authorization: Bearer <MY_PROVIDER_KEY>   # starts with sk_sig_
    Content-Type: application/json

REQUEST BODY (one submission = one scored run — send my full signal series)
  {
    "symbol": "BTCUSDT",        // OPTIONAL fallback; omit and tag each signal for multi-coin
    "resolution": "1d",         // 1m | 5m | 15m | 1h | 1d
    "start": "2023-01-01",      // OPTIONAL custom window (YYYY-MM-DD); omit → my signal span
```
