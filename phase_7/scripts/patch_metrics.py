"""
Patch utility: recompute MDD and financial metrics for all existing raw result files.

Fixes applied:
  - MDD recomputed from equity_curve (correct peak-to-trough)
  - Win/loss now classified by NET pnl (gross_pnl - exit_fee - entry_fee), matching metrics.py
  - Hedge-mode pairing: long and short entry fees tracked independently so each EXIT
    pairs with its own side's accumulated entry fees (same logic as metrics.py)
  - gross_profit / gross_loss based on gross_pnl of exits (correct for profit factor)
  - total_fees: sum of ALL trade fees (entry + exit, both sides)
  - total_slippage: sum of slippage_usd across all trade records (was missing)
  - win_rate stored as "X.XX%" string

All values recomputed from stored equity_curve and trades_detail fields.
"""
import json
import os

RAW_DIR = "phase_7/data/raw_results"


def patch_file(path):
    with open(path) as f:
        d = json.load(f)

    changed = False

    # ── 1. Recompute MDD from equity_curve ──────────────────────────────────
    equity  = d.get("equity_curve", [])
    initial = float(d.get("initial_balance", 1000.0))
    if equity:
        peak   = initial
        max_dd = 0.0
        for v in equity:
            if v > peak:
                peak = v
            dd = (peak - v) / peak * 100.0
            if dd > max_dd:
                max_dd = dd
        correct_mdd = round(max_dd, 2)
    else:
        correct_mdd = 0.0

    if d.get("mdd") != correct_mdd:
        d["mdd"] = correct_mdd
        changed = True

    # ── 2. Recompute financial metrics from trades_detail ───────────────────
    # Mirrors metrics.py logic exactly:
    #   - gross_profit / gross_loss from EXIT gross_pnl (before fees)
    #   - win/loss by NET = exit_pnl - entry_fees (fully after fee & slippage)
    #   - hedge mode: long and short entry fees tracked independently
    trades = d.get("trades_detail", [])

    long_entry_fees  = 0.0
    short_entry_fees = 0.0
    wins = losses    = 0
    gross_profit = gross_loss = total_fees = total_slippage = 0.0

    for t in trades:
        total_fees     += float(t.get("fee", 0))
        total_slippage += float(t.get("slippage_usd", 0))
        ttype = t.get("type", "")

        if ttype in ("BUY", "BUY_ADD"):
            long_entry_fees += float(t.get("fee", 0))

        elif ttype in ("SELL", "SELL_ADD"):
            short_entry_fees += float(t.get("fee", 0))

        elif ttype == "EXIT_LONG":
            g = float(t.get("gross_pnl", 0))
            if g > 0:   gross_profit += g
            elif g < 0: gross_loss   += abs(g)
            # Net = exit pnl (already has exit fee deducted) minus accumulated entry fees
            net = float(t.get("pnl", 0)) - long_entry_fees
            if net > 0:   wins   += 1
            elif net < 0: losses += 1
            long_entry_fees = 0.0

        elif ttype == "EXIT_SHORT":
            g = float(t.get("gross_pnl", 0))
            if g > 0:   gross_profit += g
            elif g < 0: gross_loss   += abs(g)
            net = float(t.get("pnl", 0)) - short_entry_fees
            if net > 0:   wins   += 1
            elif net < 0: losses += 1
            short_entry_fees = 0.0

    total_rt     = wins + losses
    win_rate_pct = round(wins / total_rt * 100, 2) if total_rt > 0 else 0.0
    win_rate_str = f"{win_rate_pct:.2f}%"

    gross_profit_r   = round(gross_profit, 2)
    gross_loss_r     = round(gross_loss, 2)
    total_fees_r     = round(total_fees, 2)
    total_slippage_r = round(total_slippage, 4)

    if d.get("gross_profit")     != gross_profit_r:   d["gross_profit"]     = gross_profit_r;   changed = True
    if d.get("gross_loss")       != gross_loss_r:     d["gross_loss"]       = gross_loss_r;     changed = True
    if d.get("total_fees")       != total_fees_r:     d["total_fees"]       = total_fees_r;     changed = True
    if d.get("total_slippage")   != total_slippage_r: d["total_slippage"]   = total_slippage_r; changed = True
    if d.get("winning_trades")   != wins:             d["winning_trades"]   = wins;             changed = True
    if d.get("losing_trades")    != losses:           d["losing_trades"]    = losses;           changed = True
    if str(d.get("win_rate", "")) != win_rate_str:    d["win_rate"]         = win_rate_str;     changed = True

    if changed:
        with open(path, "w") as f:
            json.dump(d, f, indent=4)

    return changed


def main():
    files = sorted(os.listdir(RAW_DIR))
    total = len(files)
    patched = 0
    for i, fname in enumerate(files, 1):
        if not fname.endswith(".json"):
            continue
        path = os.path.join(RAW_DIR, fname)
        if patch_file(path):
            patched += 1
        if i % 100 == 0 or i == total:
            print(f"  {i}/{total} processed, {patched} patched so far...")
    print(f"Done. {patched}/{total} files updated.")


if __name__ == "__main__":
    os.chdir(os.path.join(os.path.dirname(__file__), "..", ".."))
    main()
