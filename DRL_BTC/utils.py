"""Shared utilities — device selection, seeding, metrics."""

from __future__ import annotations

import random
import numpy as np
import torch


def select_device() -> torch.device:
    if torch.cuda.is_available():
        return torch.device("cuda")
    if torch.backends.mps.is_available():
        return torch.device("mps")
    return torch.device("cpu")


def set_seed(seed: int) -> None:
    random.seed(seed)
    np.random.seed(seed)
    torch.manual_seed(seed)
    if torch.backends.mps.is_available():
        torch.mps.manual_seed(seed)
    if torch.cuda.is_available():
        torch.cuda.manual_seed_all(seed)


def compute_metrics(equity_curve: list | np.ndarray) -> dict:
    """
    Standard trading metrics from an equity curve (list of equity values).
    Returns dict with keys: total_ret, cagr, max_dd, sharpe, calmar, n_bars.
    """
    eq = np.asarray(equity_curve, dtype=np.float64)
    n  = len(eq) - 1  # number of bars (steps)

    total_ret = (eq[-1] / eq[0] - 1.0) * 100.0

    peak   = np.maximum.accumulate(eq)
    dd_arr = (peak - eq) / (peak + 1e-10)
    max_dd = float(dd_arr.max()) * 100.0

    n_years = n / (365.0 * 24.0)
    cagr    = ((eq[-1] / eq[0]) ** (1.0 / max(n_years, 1e-6)) - 1.0) * 100.0

    # Sharpe: annualise hourly returns (√(365×24) ≈ 93.6)
    hourly_rets = np.diff(eq) / (eq[:-1] + 1e-10)
    sharpe = float(hourly_rets.mean() / (hourly_rets.std() + 1e-10)) * (365 * 24) ** 0.5

    # Calmar: CAGR / max_dd (undefined when max_dd is 0 → inf, cap at 99)
    calmar = float(cagr / max_dd) if max_dd > 0.01 else 99.0

    return {
        "total_ret": float(total_ret),
        "cagr":      float(cagr),
        "max_dd":    float(max_dd),
        "sharpe":    float(sharpe),
        "calmar":    float(calmar),
        "n_bars":    int(n),
    }
