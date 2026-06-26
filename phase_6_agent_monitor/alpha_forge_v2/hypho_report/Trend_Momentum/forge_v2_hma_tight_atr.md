## Core Hypothesis — WHY should this strategy have an edge?

Hull Moving Average (HMA = WMA(2×WMA(n/2) - WMA(n), √n)) is a mathematically near-zero-lag moving average. By differencing two WMAs of different periods and then smoothing the result, HMA reduces lag to near-zero while maintaining smooth output. HMA crossovers therefore signal trend changes earlier than any standard EMA/SMA crossover. Paired with ATR expansion filter (confirms volatility is expanding as the trend initiates) and tight ATR exits (asymmetric TP/SL forcing only conviction trades to hold), this composition targets high-quality early trend entries.

**Signal ID 124** | ETH/4h | Entry: hma_cross (NEW INDICATOR) | Filter: atr_expansion | Exit: tight_atr
