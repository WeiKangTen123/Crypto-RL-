# Agent Long-Term Memory (LTM)
## Agent: @crypto-strategy-tuner

### Purpose
To store distilled insights, historical constraints, and lessons learned that must persist across sessions. Unlike logs, this file contains *wisdom*, not actions.

### Historical Insights & Constraints
- 2026-06-04 | Initialized LTM system.
- **2026-06-04**: Fine-tuning with auto-scaled trials (150 trials for 6 parameters) proved highly effective for sub-0.3 Sharpe strategies, achieving a nearly 5x improvement (0.27 -> 1.27) for TIPBreakoutStrategy.
- **2026-06-04**: Multiple fine-tuning attempts on strategies with consistently low or negative Sharpe ratios (e.g., IDs 66, 68, 72, 73, 74) did not result in significant parameter improvements or positive Sharpe ratios, suggesting a potential fundamental flaw in the strategy logic rather than sub-optimal parameters. Future efforts should prioritize addressing underlying strategy design for such cases.

- **2026-06-05**: Re-running fine-tuning on previously optimized, high-performing strategies (e.g., ID 10 at 1.27 Sharpe) yields diminishing or zero returns, indicating that they have likely reached their parameter bounds.
- **2026-06-08**: Continued pattern observed: fine-tuning strategies with deeply negative Sharpe ratios (e.g., IDs 83, 84, 87) rarely yields positive results, reinforcing the need for foundational logic review over parameter optimization for BAD strategies.
- **2026-06-08**: Fine-tuning can produce high Sharpe ratios (e.g., ID 60 reached 2.4) that are subsequently rejected by internal validation thresholds (e.g., insufficient trades or PF constraints), underscoring that raw Optuna Sharpe optimization requires strict WFO/trade count validation to prevent overfitting.
- **2026-06-08**: Strategy 74 fine-tuned again but Sharpe remained -0.53, further confirming that broken logic cannot be optimized.
- **2026-06-08**: Fine-tuning high-performing strategy ID 1 (MACDKDJStrategy, original Sharpe 1.24) yielded no improvement (best trial 1.22), further confirming that previously optimized or inherently strong strategies likely sit near their parameter bounds.
- **2026-06-08**: Proactive fine-tuning of Strategy 6 (MeanReversionVRSI, Sharpe -3.87) worsened the performance (best -11.35), reinforcing that BAD strategies with deeply negative Sharpe likely have fundamental logic issues.
- **2026-06-08**: Fine-tuning Strategy 47 (AroonRSIStrategy) resulted in no parameter improvement, further supporting the observation that poorly performing strategies require logical redesign rather than parameter optimization.
- **2026-06-08**: Fine-tuning effectively improves Sharpe ratios, even for strategies with initially negative performance (e.g., Strategy 95 improved from -1.65 to 1.27). `RWAMomentumStrategy` type appears to respond well to parameter optimization.