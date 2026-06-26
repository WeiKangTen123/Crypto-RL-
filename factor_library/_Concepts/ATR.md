---
name: ATR
type: concept
tags: [concept, indicator]
---

# ATR

Average True Range — volatility measure used in stop-loss sizing and breakout filters.

---
## Used By
```dataview
LIST
FROM "factor_library"
WHERE contains(file.outlinks, this.file.link)
```
