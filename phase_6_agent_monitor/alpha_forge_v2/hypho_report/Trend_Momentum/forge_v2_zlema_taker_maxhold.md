## Core Hypothesis — WHY should this strategy have an edge?

Zero-Lag EMA crossovers fire 2-3 bars earlier than standard EMA crossovers because ZLEMA applies a lag-compensation term (2×EMA(n/2) - EMA(n)) before smoothing. Earlier entries capture a better average price relative to the trend's duration. The taker buy confirmation filter then requires institutional-grade order flow agreement before executing — taker buyers pay the spread aggressively, signalling urgency and conviction. The combination of earlier trend detection (ZLEMA) + flow validation (taker) creates a high-conviction entry that standard EMA strategies cannot replicate. Max hold exit prevents the common failure mode of over-staying after trend maturity.

**Signal ID 117** | ETH/4h | Entry: zlema_cross | Filter: taker_confirm | Exit: max_hold
