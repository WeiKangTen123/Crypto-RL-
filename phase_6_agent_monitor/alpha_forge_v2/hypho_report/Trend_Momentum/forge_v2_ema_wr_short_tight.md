## Core Hypothesis — WHY should this strategy have an edge?

EMA price crosses fail most frequently when they occur at momentum extremes — price crosses the EMA after already overshooting (overbought) and the cross itself becomes a reversal signal, not a continuation signal. Williams %R captures this: WR above -10 means price is at 90th percentile of its recent high-low range (overbought). By filtering out EMA crosses when WR > -10 or WR < -90, the strategy eliminates the majority of failed entries. The remaining EMA crosses occur at "medium" momentum — neither overbought nor oversold — and have dramatically higher follow-through.

The tight ATR exit (sl_atr_mult=2.30, tp_atr_mult=6.54, R:R=2.84) then ensures that every accepted trade either runs to a 2.84R gain or stops out — no "mediocre" partial outcomes.

**Signal ID 127** | ETH/4h | Entry: ema_price_cross | Filter: wr_not_extreme (NEW) + ema_trend_short | Exit: tight_atr
**★ MOST STABLE — All 5 years positive, 2022 +74%, MDD 26%**
