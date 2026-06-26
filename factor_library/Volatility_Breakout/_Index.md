# 💥 Volatility Breakout
#tag/category/volatility

Strategies that exploit sudden expansions in market range. These are designed to capture the "explosion" from low-volatility periods.

## 🗄️ Available Factors & Strategies
```dataview
TABLE interest, status, sharpe
FROM "Volatility_Breakout"
WHERE file.name != "_Index"
SORT interest DESC
```

---
[[README|⬅ Back to Main Vault]]
