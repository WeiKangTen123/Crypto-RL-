---
name: Bollinger_Bands
type: concept
tags: [concept, indicator]
---

# Bollinger Bands

Bollinger Bands / BBW — volatility envelope; squeeze = low vol, expansion = breakout.

---
## Used By
```dataview
LIST
FROM "factor_library"
WHERE contains(file.outlinks, this.file.link)
```
