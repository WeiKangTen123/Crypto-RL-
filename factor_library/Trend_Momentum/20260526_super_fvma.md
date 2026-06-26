---name: super-fvma-triple-confirmation
strategy_id: SUPER_FVMA_BTC_4H
type: long-term
timeframes: 4h, 1d
coins: BTC, ETH, BNB, SOL, XRP
source: Pineify / TradingView
interest: High
status: VALIDATED
sharpe: 1.69
win_rate: 33.33
total_return: 51.32
max_drawdown: 13.01
---

# Super FVMA Triple Confirmation

## Concept
Combines Supertrend for direction, Fair Value Moving Average (FVMA) for trend strength/confirmation, and Zero Lag MACD for precise entry timing. This "Triple Confirmation" system aims to capture strong momentum moves while filtering out noise.

## Entry Conditions
- Price > FVMA
- Supertrend is green (bullish)
- Zero Lag MACD crosses above zero (bullish momentum)
- All conditions must be met for a Long entry.

## Exit Conditions
- Take profit: ATR-based trailing stop or Supertrend flip to red.
- Stop loss: Recent swing low or 1.5 * ATR below entry.

## Key Indicators
- Supertrend (10, 3.0)
- Fair Value Moving Average (FVMA) - period 20
- Zero Lag MACD (12, 26, 9)

## Expected Edge
Capturing the meat of a trend by requiring three independent signals to align. Supertrend provides the macro bias, FVMA ensures price is holding value above average, and Zero Lag MACD prevents entering too late into an exhausted trend.

## Data Requirements
- Columns needed: Close, High, Low
- Minimum timeframe: 4h
- Minimum history: 2 years

## Implementation Notes
- Zero Lag MACD needs a custom implementation (typically `EMA(EMA(price)) - EMA(EMA(EMA(price)))` logic).
- FVMA might be implemented as a volume-weighted or price-action adjusted MA if standard FVMA is proprietary; otherwise, a smoothed hull or adaptive MA can substitute.


## Rejection Notes
Failed WFO validation. Sharpe > 0.5 only in 2/4 windows. MaxDD > 30% in window 2. Strategy discarded.


## 📈 Performance Summary
*Automatically updated by backtest engine.*

| Metric | Value |
| --- | --- |
| Sharpe Ratio | 1.69 |
| Win Rate | 33.33% |
| Total Return | 51.32% |
| Max Drawdown | 13.01% |


## Performance Summary
*Auto-updated by sync_backtest_to_obsidian.py when strategy_id matches.*

| Metric | Value |
| --- | --- |
| Sharpe Ratio | 1.69 |
| Win Rate | 33.33% |
| Total Return | 51.32% |
| Max Drawdown | 13.01% |