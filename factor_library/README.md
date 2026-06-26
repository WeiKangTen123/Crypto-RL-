# 🏛️ The Alpha Vault (Factor Library)

Welcome to the central knowledge hub of the Crypto-RL Alpha Pipeline. This vault uses **Obsidian** and the **Dataview community plugin** to automatically track and categorize quant concepts.

---

## 🗺️ Map of Content (Categories)
Click a category to explore its specific factors and strategies.

- [[Trend_Momentum/_Index|📈 Trend & Momentum]]
- [[Mean_Reversion/_Index|📉 Mean Reversion]]
- [[Volatility_Breakout/_Index|💥 Volatility Breakout]]
- [[Funding_Rate_Arb/_Index|💰 Funding & Basis Arb]]
- [[Cross_Sectional/_Index|📊 Cross-Sectional & Stat-Arb]]
- [[Sentiment_OnChain/_Index|🧠 Sentiment & On-Chain]]

---

## 🚧 Pipeline Dashboard
*The tables below are powered by the Dataview plugin. Ensure it is installed in Obsidian.*

### 🔍 Active Research (QUEUED)
```dataview
TABLE type as "Type", factor_class as "Class", interest as "Interest"
FROM ""
WHERE status = "QUEUED"
SORT interest DESC
```

### 🧪 Implementing (IN_PROGRESS)
```dataview
TABLE type as "Type", factor_class as "Class"
FROM ""
WHERE status = "IN_PROGRESS"
```

### 🏆 The Elite Vault (VALIDATED)
*Strategies that passed 4-Window WFO and are ready for Paper Trading.*
```dataview
TABLE type as "Type", factor_class as "Class", sharpe as "Sharpe"
FROM ""
WHERE status = "VALIDATED"
SORT sharpe DESC
```

### ❌ Rejection Graveyard
```dataview
LIST
FROM ""
WHERE status = "REJECTED"
```

---

## 🛠️ Infrastructure
- **Factor Library**: [[strategy_backtest/library.py]]
- **Strategy Settings**: [[strategy_backtest/settings.py]]
- **Templates**: [[templates/Factor_Card_Template|Factor Card Template]]
- **Automation**: Use `python strategy_backtest/run_backtest.py --strategy all --save results/technical_backtest.csv` to automatically update these notes with the latest performance metrics. Ensure your Markdown card has a matching `strategy_id` in its YAML frontmatter.
- **Global Wisdom**: [[.gemini/shared/GLOBAL_LTM.md]]

---
*Last updated: 2026-06-09 by GEMINI_CLI*
