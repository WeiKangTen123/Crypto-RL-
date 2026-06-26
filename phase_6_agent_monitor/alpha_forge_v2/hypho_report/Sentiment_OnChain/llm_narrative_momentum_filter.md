## Strategy Name
LLM-Driven Narrative Momentum Filter

## Category
Sentiment / On-Chain

## Core Hypothesis — WHY should this strategy have an edge?
As institutional-grade trading agents dominate the market, rapid shifts in market narratives—fueled by social media activity, regulatory announcements, and governance proposals—often precede price movements. By using Large Language Models (LLMs) to perform real-time sentiment analysis on high-velocity data sources (like Farcaster and institutional-grade news feeds), this factor can quantify "Narrative Speed." When the sentiment score exceeds a threshold, it acts as a momentum filter to amplify existing trend-following signals, effectively front-running narrative-driven inflows.

## Entry Signal — exact condition that triggers a buy
1. **Indicator:** Narrative Sentiment Score (NSS).
2. **Requirement:** NSS increases by > 15% within a 1-hour window (suggesting a viral narrative).
3. **Trigger:** Combined with a positive slope in the 1H VWAP.

## Exit Signal — exact condition that triggers a sell or position close
1. **Take-Profit:** NSS plateaus or drops by > 10% from the peak (narrative saturation).
2. **Stop Loss:** Price falls below the 1H VWAP.

## Key Indicators / Data Required
- Real-time LLM-processed sentiment stream (e.g., from X, Farcaster, or news API).
- High-velocity price data.
- 1H VWAP.

## Timeframe Compatibility (scalp / swing / position)
- **Primary:** Scalp/Day Trade.

## Theoretical Risk — what market conditions break this strategy?
1. **Narrative Fakeouts:** Rapid sentiment spikes without actual volume backing.
2. **LLM Latency:** If sentiment processing is too slow, the price move may already be priced in by competing agents.

## Source — URL or reference
Derived from 2026 QuantAgent protocols.

## Interest Rating — [High]
High — Essential for identifying "hot" regimes in the current AI-driven quant landscape.

---
## Connections

**Category:** [[Sentiment_OnChain/_Index]]

**Indicators:** [[_Concepts/Sentiment]]
