---
name: Order_Flow
type: concept
tags: [concept, indicator]
---

# Order Flow

Order Flow / CVD — cumulative delta and taker buy/sell imbalance for directional bias.

---
## Used By
```dataview
LIST
FROM "factor_library"
WHERE contains(file.outlinks, this.file.link)
```
