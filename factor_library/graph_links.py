"""
graph_links.py
Injects Obsidian [[wiki-links]] into every factor .md file and creates
concept hub notes, so the Graph View builds a rich connected network.

Run once from the factor_library root:
    python graph_links.py
"""

import os
import re
import yaml

VAULT_ROOT = os.path.dirname(os.path.abspath(__file__))
CONCEPTS_DIR = os.path.join(VAULT_ROOT, "_Concepts")

CATEGORY_MAP = {
    "Trend_Momentum":    "Trend_Momentum/_Index",
    "Volatility_Breakout": "Volatility_Breakout/_Index",
    "Mean_Reversion":    "Mean_Reversion/_Index",
    "Funding_Rate_Arb":  "Funding_Rate_Arb/_Index",
    "Cross_Sectional":   "Cross_Sectional/_Index",
    "Sentiment_OnChain": "Sentiment_OnChain/_Index",
    "HFT":               "HFT/_Index",
    "Market_Making":     "Market_Making/_Index",
    "Basis_Arb":         "Basis_Arb/_Index",
    "Cross_Exchange_Arb":"Cross_Exchange_Arb/_Index",
}

# indicator keyword → concept note slug
INDICATOR_PATTERNS = {
    r"\bATR\b":                     "ATR",
    r"\bAverage True Range\b":      "ATR",
    r"\bEMA\b":                     "EMA",
    r"\bExponential Moving Average\b": "EMA",
    r"\bSMA\b":                     "SMA",
    r"\bSimple Moving Average\b":   "SMA",
    r"\bMACD\b":                    "MACD",
    r"\bRSI\b":                     "RSI",
    r"\bRelative Strength Index\b": "RSI",
    r"\bADX\b":                     "ADX",
    r"\bDMI\b":                     "ADX",
    r"\bDirectional Movement\b":    "ADX",
    r"\bBollinger Band\b":          "Bollinger_Bands",
    r"\bBBW\b":                     "Bollinger_Bands",
    r"\bKeltner Channel\b":         "Keltner_Channel",
    r"\bDonchian\b":                "Donchian_Channel",
    r"\bVWAP\b":                    "VWAP",
    r"\bIchimoku\b":                "Ichimoku",
    r"\bSuperTrend\b":              "SuperTrend",
    r"\bsuper_trend\b":             "SuperTrend",
    r"\bStochastic\b":              "Stochastic",
    r"\bKDJ\b":                     "Stochastic",
    r"\bFunding Rate\b":            "Funding_Rate",
    r"\bfunding_rate\b":            "Funding_Rate",
    r"\bOrder Flow\b":              "Order_Flow",
    r"\bCVD\b":                     "Order_Flow",
    r"\bnum_trades\b":              "Trade_Intensity",
    r"\bTrade Intensity\b":         "Trade_Intensity",
    r"\bFair Value Gap\b":          "FVG",
    r"\bFVG\b":                     "FVG",
    r"\bOn.Chain\b":                "On_Chain",
    r"\bMVRV\b":                    "On_Chain",
    r"\bFibonacci\b":               "Fibonacci",
    r"\bfib\b":                     "Fibonacci",
    r"\bZero.Lag\b":                "Zero_Lag_EMA",
    r"\bZLEMA\b":                   "Zero_Lag_EMA",
    r"\bT3\b":                      "T3_Moving_Average",
}

CONCEPT_DESCRIPTIONS = {
    "ATR":              "Average True Range — volatility measure used in stop-loss sizing and breakout filters.",
    "EMA":              "Exponential Moving Average — trend direction and dynamic support/resistance.",
    "SMA":              "Simple Moving Average — baseline trend and signal smoothing.",
    "MACD":             "Moving Average Convergence Divergence — momentum and trend-change detection.",
    "RSI":              "Relative Strength Index — overbought/oversold oscillator.",
    "ADX":              "Average Directional Index / DMI — trend strength filter. ADX > 25 = trending market.",
    "Bollinger_Bands":  "Bollinger Bands / BBW — volatility envelope; squeeze = low vol, expansion = breakout.",
    "Keltner_Channel":  "Keltner Channel — ATR-based envelope; used with Bollinger for squeeze detection.",
    "Donchian_Channel": "Donchian Channel — N-bar price range; basis of the classic Turtle Trader system.",
    "VWAP":             "Volume Weighted Average Price — institutional benchmark and intraday mean-reversion anchor.",
    "Ichimoku":         "Ichimoku Cloud — all-in-one trend, momentum, and support/resistance system.",
    "SuperTrend":       "SuperTrend — ATR-based trailing stop-and-reverse trend indicator.",
    "Stochastic":       "Stochastic / KDJ — momentum oscillator measuring close position within recent range.",
    "Funding_Rate":     "Funding Rate — perp funding arbitrage signal; extreme rates signal over-leveraged positioning.",
    "Order_Flow":       "Order Flow / CVD — cumulative delta and taker buy/sell imbalance for directional bias.",
    "Trade_Intensity":  "Trade Intensity (num_trades) — transaction frequency filter separating institutional from retail moves.",
    "FVG":              "Fair Value Gap (FVG) — ICT imbalance zone; unfilled gap between candles acts as magnet.",
    "On_Chain":         "On-Chain Analytics — MVRV, NVT, exchange flows as macro regime signals.",
    "Fibonacci":        "Fibonacci Retracement/Extension — harmonic price levels for entries and targets.",
    "Zero_Lag_EMA":     "Zero-Lag EMA (ZLEMA) — EMA variant that removes lag by compensating for the delay.",
    "T3_Moving_Average":"T3 Moving Average — smooth, low-lag MA using a cascade of EMAs.",
}


def parse_frontmatter(text):
    """Return (frontmatter_dict, body_text). frontmatter_dict is {} if none."""
    match = re.match(r"^---\s*\n(.*?)\n---\s*\n(.*)", text, re.DOTALL)
    if not match:
        return {}, text
    try:
        fm = yaml.safe_load(match.group(1)) or {}
    except Exception:
        fm = {}
    return fm, match.group(2)


def detect_indicators(text):
    found = set()
    for pattern, slug in INDICATOR_PATTERNS.items():
        if re.search(pattern, text, re.IGNORECASE):
            found.add(slug)
    return sorted(found)


def build_connections_block(category, indicators, related_factors):
    lines = ["\n---\n## Connections\n"]

    if category in CATEGORY_MAP:
        lines.append(f"**Category:** [[{CATEGORY_MAP[category]}]]\n")

    if indicators:
        indicator_links = " · ".join(f"[[_Concepts/{i}]]" for i in indicators)
        lines.append(f"**Indicators:** {indicator_links}\n")

    if related_factors:
        factor_links = " · ".join(f"[[{f}]]" for f in related_factors[:8])
        lines.append(f"**Related Factors:** {factor_links}\n")

    return "\n".join(lines)


def connections_already_injected(text):
    return "## Connections" in text


def get_all_factors():
    """Return list of (rel_path, category, abs_path) for every non-index factor."""
    factors = []
    for root, dirs, files in os.walk(VAULT_ROOT):
        dirs[:] = [d for d in dirs if not d.startswith(".") and d != "_Concepts" and d != "templates"]
        category = os.path.basename(root)
        for f in files:
            if f.endswith(".md") and f not in ("README.md",) and not f.startswith("_"):
                abs_path = os.path.join(root, f)
                rel_path = os.path.relpath(abs_path, VAULT_ROOT).replace("\\", "/")
                # strip .md for wiki-link
                rel_link = rel_path[:-3]
                factors.append((rel_link, category, abs_path))
    return factors


def build_related_index(all_factors):
    """Build a map: abs_path → set of related factor rel_links (shared coins/type)."""
    meta = {}
    for rel_link, category, abs_path in all_factors:
        with open(abs_path, "r", encoding="utf-8") as fh:
            text = fh.read()
        fm, _ = parse_frontmatter(text)
        coins = set(re.split(r"[\s,\[\]]+", str(fm.get("coins", ""))))
        ftype = str(fm.get("type", ""))
        meta[abs_path] = {"coins": coins, "type": ftype, "rel_link": rel_link, "category": category}

    related = {}
    for path, info in meta.items():
        others = []
        for other_path, other_info in meta.items():
            if other_path == path:
                continue
            shared_coins = info["coins"] & other_info["coins"] - {"", "None"}
            same_type = info["type"] and info["type"] == other_info["type"]
            same_cat = info["category"] == other_info["category"]
            score = len(shared_coins) * 2 + (1 if same_type else 0) + (1 if same_cat else 0)
            if score >= 3:
                others.append((score, other_info["rel_link"]))
        others.sort(reverse=True)
        related[path] = [r for _, r in others[:6]]

    return related


def create_concept_notes():
    os.makedirs(CONCEPTS_DIR, exist_ok=True)
    created = 0
    for slug, description in CONCEPT_DESCRIPTIONS.items():
        note_path = os.path.join(CONCEPTS_DIR, f"{slug}.md")
        if not os.path.exists(note_path):
            content = f"""---
name: {slug}
type: concept
tags: [concept, indicator]
---

# {slug.replace("_", " ")}

{description}

---
## Used By
```dataview
LIST
FROM "factor_library"
WHERE contains(file.outlinks, this.file.link)
```
"""
            with open(note_path, "w", encoding="utf-8") as fh:
                fh.write(content)
            created += 1
    print(f"  Created {created} concept hub notes in _Concepts/")


def inject_links():
    all_factors = get_all_factors()
    related_index = build_related_index(all_factors)

    updated = 0
    skipped = 0

    for rel_link, category, abs_path in all_factors:
        with open(abs_path, "r", encoding="utf-8") as fh:
            text = fh.read()

        if connections_already_injected(text):
            skipped += 1
            continue

        indicators = detect_indicators(text)
        related = related_index.get(abs_path, [])
        block = build_connections_block(category, indicators, related)

        with open(abs_path, "a", encoding="utf-8") as fh:
            fh.write(block)

        updated += 1

    print(f"  Injected links into {updated} files ({skipped} already had connections)")


def main():
    print("Building Obsidian Graph Links...")
    print("1. Creating concept hub notes...")
    create_concept_notes()
    print("2. Injecting [[wiki-links]] into factor files...")
    inject_links()
    print("\nDone. Open Obsidian → Graph View to see your network.")
    print("Tip: In Graph View, use Groups to color by #tag/category/momentum etc.")


if __name__ == "__main__":
    main()
