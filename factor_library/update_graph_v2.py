"""
update_graph_v2.py — Option 3 Graph Restructure

Changes made:
  1. Trim concept hubs to top 5 only (ATR, EMA, RSI, Order_Flow, Bollinger_Bands)
  2. Remove dead concept links from all Connections blocks
  3. Inject #validated / #queued / #in_progress / #rejected tags into frontmatter
     so graph color groups can highlight pipeline status
  4. Rewrite .obsidian/graph.json with the 3-layer color scheme

Run with Obsidian CLOSED:
    python update_graph_v2.py
Then reopen Obsidian and open Graph View.
"""

import os
import re
import json
import yaml

VAULT_ROOT = os.path.dirname(os.path.abspath(__file__))
CONCEPTS_DIR = os.path.join(VAULT_ROOT, "_Concepts")
OBSIDIAN_DIR = os.path.join(VAULT_ROOT, ".obsidian")

# Only these 5 concept hubs survive — the genuine cross-category connectors
KEEP_CONCEPTS = {"ATR", "EMA", "RSI", "Order_Flow", "Bollinger_Bands"}

# Status → tag name (no spaces, lowercase)
STATUS_TAG_MAP = {
    "VALIDATED":   "validated",
    "IN_PROGRESS": "in_progress",
    "QUEUED":      "queued",
    "REJECTED":    "rejected",
    "IMPLEMENTED": "implemented",
}

# Graph color scheme (RGB decimal = R*65536 + G*256 + B)
# Priority order: first match wins in Obsidian
GRAPH_JSON = {
    "collapse-filter": True,
    "search": "",
    "showTags": False,
    "showAttachments": False,
    "hideUnresolved": False,
    "showOrphans": True,
    "collapse-color-groups": False,
    "colorGroups": [
        # Layer 1 — Pipeline status (highest priority, overrides category color)
        {"query": "tag:#validated",   "color": {"a": 1, "rgb": 16776960}},   # Bright Yellow
        {"query": "tag:#in_progress", "color": {"a": 1, "rgb": 16750848}},   # Amber

        # Layer 2 — Structural nodes
        {"query": "path:_Concepts",   "color": {"a": 1, "rgb": 16041008}},   # Gold
        {"query": "file:_Index",      "color": {"a": 1, "rgb": 16777215}},   # White
        {"query": "file:README",      "color": {"a": 1, "rgb": 16777215}},   # White

        # Layer 3 — Category clusters
        {"query": "path:Trend_Momentum",    "color": {"a": 1, "rgb": 51283}},    # Green
        {"query": "path:Mean_Reversion",    "color": {"a": 1, "rgb": 2718207}},  # Blue
        {"query": "path:Volatility_Breakout","color": {"a": 1, "rgb": 16739584}},# Orange
        {"query": "path:Funding_Rate_Arb",  "color": {"a": 1, "rgb": 11141375}}, # Purple
        {"query": "path:Cross_Sectional",   "color": {"a": 1, "rgb": 48340}},    # Cyan
        {"query": "path:Sentiment_OnChain", "color": {"a": 1, "rgb": 15277667}}, # Pink
        {"query": "path:HFT",               "color": {"a": 1, "rgb": 16717636}}, # Red
        {"query": "path:Market_Making",     "color": {"a": 1, "rgb": 16717636}}, # Red
    ],
    "collapse-display": True,
    "showArrow": False,
    "textFadeMultiplier": 0,
    "nodeSizeMultiplier": 1.5,
    "lineSizeMultiplier": 1,
    "collapse-forces": True,
    "centerStrength": 0.518713248970312,
    "repelStrength": 10,
    "linkStrength": 1,
    "linkDistance": 180,
    "scale": 0.9,
    "close": False,
}


# ── helpers ──────────────────────────────────────────────────────────────────

def parse_frontmatter(text):
    """Return (fm_dict, body_text, has_fm). fm_dict is {} if no frontmatter."""
    m = re.match(r"^---\s*\n(.*?)\n---\s*\n(.*)", text, re.DOTALL)
    if not m:
        return {}, text, False
    try:
        fm = yaml.safe_load(m.group(1)) or {}
    except Exception:
        fm = {}
    return fm, m.group(2), True


def serialise_frontmatter(fm):
    return "---\n" + yaml.dump(fm, default_flow_style=False, allow_unicode=True) + "---\n"


def ensure_tag(fm, tag):
    tags = fm.get("tags", [])
    if isinstance(tags, str):
        tags = [tags]
    elif tags is None:
        tags = []
    else:
        tags = list(tags)
    if tag not in tags:
        tags.append(tag)
    fm["tags"] = tags


# ── step 1: trim concept hubs ─────────────────────────────────────────────

def trim_concept_hubs():
    removed = []
    for fname in os.listdir(CONCEPTS_DIR):
        slug = fname.replace(".md", "")
        if slug not in KEEP_CONCEPTS:
            path = os.path.join(CONCEPTS_DIR, fname)
            os.remove(path)
            removed.append(slug)
    print(f"  Removed {len(removed)} low-value concept hubs: {', '.join(sorted(removed))}")


# ── step 2: update all factor files ──────────────────────────────────────

def clean_dead_concept_links(connections_block):
    """Remove [[_Concepts/X]] links for deleted hubs from the Indicators line."""
    lines = connections_block.split("\n")
    new_lines = []
    for line in lines:
        if line.startswith("**Indicators:**"):
            # Extract all concept links, keep only KEEP_CONCEPTS ones
            kept = re.findall(r'\[\[_Concepts/([^\]]+)\]\]', line)
            kept = [s for s in kept if s in KEEP_CONCEPTS]
            if kept:
                new_lines.append("**Indicators:** " + " · ".join(f"[[_Concepts/{s}]]" for s in kept))
            # If no kept indicators, drop the whole line
        else:
            new_lines.append(line)
    return "\n".join(new_lines)


def update_factor_file(abs_path):
    with open(abs_path, "r", encoding="utf-8") as fh:
        raw = fh.read()

    fm, body, has_fm = parse_frontmatter(raw)
    changed = False

    # Inject status tag
    status = str(fm.get("status", "")).strip().upper()
    tag = STATUS_TAG_MAP.get(status)
    if tag:
        before = list(fm.get("tags", []))
        ensure_tag(fm, tag)
        if fm.get("tags") != before:
            changed = True

    # Clean dead concept links in Connections block
    if "## Connections" in body:
        conn_start = body.index("## Connections")
        pre = body[:conn_start]
        conn_block = body[conn_start:]
        new_block = clean_dead_concept_links(conn_block)
        if new_block != conn_block:
            body = pre + new_block
            changed = True

    if not changed:
        return False

    if has_fm:
        new_text = serialise_frontmatter(fm) + body
    else:
        # File had no frontmatter — prepend a minimal one with just the tag
        if tag:
            minimal_fm = {"tags": [tag]}
            new_text = serialise_frontmatter(minimal_fm) + raw
        else:
            return False

    with open(abs_path, "w", encoding="utf-8") as fh:
        fh.write(new_text)
    return True


def update_all_factors():
    updated = 0
    skipped = 0
    for root, dirs, files in os.walk(VAULT_ROOT):
        dirs[:] = [d for d in dirs if not d.startswith(".") and d != "_Concepts" and d != "templates"]
        for fname in files:
            if not fname.endswith(".md"):
                continue
            if fname in ("README.md",) or fname.startswith("_"):
                continue
            abs_path = os.path.join(root, fname)
            if update_factor_file(abs_path):
                updated += 1
            else:
                skipped += 1
    print(f"  Updated {updated} factor files ({skipped} unchanged)")


# ── step 3: write graph.json ──────────────────────────────────────────────

def write_graph_json():
    path = os.path.join(OBSIDIAN_DIR, "graph.json")
    with open(path, "w", encoding="utf-8") as fh:
        json.dump(GRAPH_JSON, fh, indent=2)
    print(f"  Wrote graph.json with {len(GRAPH_JSON['colorGroups'])} color groups")


# ── main ──────────────────────────────────────────────────────────────────

def main():
    print("=" * 55)
    print("  Graph Restructure v2 — Option 3 Hybrid")
    print("=" * 55)
    print("\n1. Trimming concept hubs to top 5...")
    trim_concept_hubs()
    print("\n2. Injecting status tags + cleaning dead links...")
    update_all_factors()
    print("\n3. Writing graph.json color scheme...")
    write_graph_json()
    print("\n" + "=" * 55)
    print("  Done.")
    print("  → Reopen Obsidian and press Cmd+Shift+G (Graph View)")
    print("  → VALIDATED strategies glow yellow")
    print("  → IN_PROGRESS glow amber")
    print("  → Each category has its own color")
    print("  → Gold nodes = ATR / EMA / RSI / Order_Flow / Bollinger")
    print("=" * 55)


if __name__ == "__main__":
    main()
