# 💰 Funding & Basis Arb
#tag/category/arbitrage

Strategies utilizing derivatives market data (Funding Rates, Basis, Open Interest) to exploit imbalances between spot and perp markets.

## 🗄️ Available Factors & Strategies
```dataview
TABLE interest, status, sharpe
FROM "Funding_Rate_Arb"
WHERE file.name != "_Index"
SORT interest DESC
```

---
[[README|⬅ Back to Main Vault]]
