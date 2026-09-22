"""
BC Risk Pretrainer — Session 7.

Generates oracle risk labels from a composite-rule simulation on training data,
then trains the actor's 4D output to produce sensible risk params from day 1.

Label generation (per entry bar of a simulated trade):
  pos_size : regime-scaled sizing  0.05 + 0.20 × max(0, regime_score)
  sl_atr   : vol-adaptive stop     BC_SL_ATR_DEFAULT − vol_z × 0.5 (clamped)
  tp_atr   : trend-adaptive target BC_TP_ATR_DEFAULT + adx × 2.0   (clamped)
  trail_on : 1.0 if adx_1h > 0.5 (trending regime), 0.0 otherwise

Loss per batch:
  MSE on pos_size, sl_atr, tp_atr  (decoded via linear remap from tanh output)
  BCE on trail_on                   (sigmoid with gain=3 applied to tanh output)

After pretraining the actor starts with:
  - regime-appropriate sizing (5-25%)
  - ATR-based stop distances (0.5-3×ATR)
  - trend-adaptive profit targets (1-6×ATR)
  - trailing stop enabled in trending regimes
"""

from __future__ import annotations

import logging
import numpy as np
import pandas as pd
import torch
import torch.nn as nn
import torch.nn.functional as F
from torch.utils.data import DataLoader, TensorDataset

from DRL_BTC.config import (
    SEQ_LEN, TRAIN_END, ENTRY_THRESHOLD,
    POS_SIZE_MIN, POS_SIZE_MAX,
    SL_ATR_MULT_MIN, SL_ATR_MULT_MAX,
    TP_ATR_MULT_MIN, TP_ATR_MULT_MAX,
    ATR_FEATURE, ATR_SCALE,
    BC_PRETRAIN_EPOCHS, BC_PRETRAIN_LR, BC_PRETRAIN_BATCH,
    BC_SL_ATR_DEFAULT, BC_TP_ATR_DEFAULT,
    INITIAL_CAPITAL,
)
from DRL_BTC.env.btc_env import N_PORTFOLIO_FEATS


# ── label generation ──────────────────────────────────────────────────────────

def generate_risk_labels(features: pd.DataFrame, close: pd.Series) -> pd.DataFrame:
    """
    Simulate composite-rule entries over the training window and produce
    oracle labels for all 4 action dimensions (entry bar only).

    Returns a DataFrame with columns:
      bar_idx, hold_bars, entry_px, position, atr_frac,
      pos_size, sl_atr, tp_atr, trail
    """
    mask     = features.index <= TRAIN_END
    feats    = features.loc[mask]
    cl       = close.loc[mask]
    cols     = list(feats.columns)

    macro_idx  = cols.index("macro_score")  if "macro_score"  in cols else None
    swing_idx  = cols.index("swing_score")  if "swing_score"  in cols else None
    regime_idx = cols.index("regime_score") if "regime_score" in cols else None
    atr_idx    = cols.index(ATR_FEATURE)    if ATR_FEATURE    in cols else None
    vol_z_idx  = cols.index("vol_z_1h")     if "vol_z_1h"    in cols else None
    adx_idx    = cols.index("adx_1h")       if "adx_1h"      in cols else None

    feats_np = feats.values.astype(np.float32)
    close_np = cl.values.astype(np.float64)

    in_position = False
    position    = 0.0
    entry_px    = 0.0
    entry_atr   = 0.0
    hold_bars   = 0

    records = []

    for i in range(SEQ_LEN, len(feats_np)):
        row    = feats_np[i]
        cur_px = close_np[i]

        raw_atr  = float(row[atr_idx]) if atr_idx is not None else 0.10
        atr_frac = max(raw_atr * ATR_SCALE, 0.001)

        regime = float(row[regime_idx]) if regime_idx is not None else 0.5
        vol_z  = float(row[vol_z_idx])  if vol_z_idx  is not None else 0.0
        adx    = float(row[adx_idx])    if adx_idx    is not None else 0.0

        macro    = float(row[macro_idx])  if macro_idx  is not None else 0.0
        swing    = float(row[swing_idx])  if swing_idx  is not None else 0.0
        combined = 0.65 * macro + 0.35 * swing
        if   combined >  ENTRY_THRESHOLD and regime > 0.0: new_dir =  1.0
        elif combined < -ENTRY_THRESHOLD and regime > 0.0: new_dir = -1.0
        else:                                               new_dir =  0.0

        # Oracle risk labels
        pos_size_lbl = float(np.clip(
            POS_SIZE_MIN + (POS_SIZE_MAX - POS_SIZE_MIN) * max(0.0, regime),
            POS_SIZE_MIN, POS_SIZE_MAX
        ))
        sl_atr_lbl = float(np.clip(
            BC_SL_ATR_DEFAULT - vol_z * 0.5, SL_ATR_MULT_MIN, SL_ATR_MULT_MAX
        ))
        tp_atr_lbl = float(np.clip(
            BC_TP_ATR_DEFAULT + adx * 2.0, TP_ATR_MULT_MIN, TP_ATR_MULT_MAX
        ))
        trail_lbl = 1.0 if adx > 0.5 else 0.0

        if not in_position:
            if new_dir != 0.0:
                in_position = True
                position    = new_dir
                entry_px    = cur_px
                entry_atr   = atr_frac
                hold_bars   = 0
                # Label only the entry bar — this is when the actor acts
                records.append({
                    "bar_idx":   i,
                    "hold_bars": 0,
                    "entry_px":  entry_px,
                    "position":  position,
                    "atr_frac":  atr_frac,
                    "pos_size":  pos_size_lbl,
                    "sl_atr":    sl_atr_lbl,
                    "tp_atr":    tp_atr_lbl,
                    "trail":     trail_lbl,
                })
        else:
            hold_bars += 1
            pnl_pct   = (cur_px / entry_px - 1.0) * position

            sl_hit  = pnl_pct < -BC_SL_ATR_DEFAULT * entry_atr
            tp_hit  = pnl_pct >  BC_TP_ATR_DEFAULT * entry_atr
            dir_rev = (new_dir == 0.0) or (new_dir != 0.0 and new_dir != position)
            timeout = hold_bars >= 72

            if sl_hit or tp_hit or dir_rev or timeout:
                in_position = False
                position    = 0.0

    return pd.DataFrame(records)


# ── observation builder ───────────────────────────────────────────────────────

def _build_obs(
    feats_np: np.ndarray,
    close_np: np.ndarray,
    bar_idx:  int,
    position: float,
    pos_size: float,
    hold_bars: int,
    entry_px:  float,
    entry_atr: float,
) -> np.ndarray:
    """Build (SEQ_LEN, n_market + N_PORTFOLIO_FEATS) observation for BC training."""
    raw    = feats_np[bar_idx - SEQ_LEN: bar_idx].copy()
    cur_px = close_np[bar_idx]

    sl_price_oracle = entry_px * (1.0 - position * BC_SL_ATR_DEFAULT * entry_atr)
    sl_dist = 0.0
    if cur_px > 0:
        sl_dist = float(np.clip(
            (cur_px - sl_price_oracle) / cur_px * position, -0.2, 1.0
        ))

    unrealised = float(np.clip(
        (cur_px / (entry_px + 1e-8) - 1.0) * position, -1.0, 1.0
    ))

    port = np.array([
        position,
        pos_size,
        sl_dist,
        float(min(hold_bars, 48)) / 48.0,
        0.0,
        0.0,
        unrealised,
        1.0,
    ], dtype=np.float32)

    obs = np.concatenate([raw, np.tile(port, (SEQ_LEN, 1))], axis=1).astype(np.float32)
    return np.nan_to_num(obs, nan=0.0, posinf=1.0, neginf=-1.0)


# ── pretraining entry point ───────────────────────────────────────────────────

def pretrain_actor(
    actor,
    features: pd.DataFrame,
    close:    pd.Series,
    device:   torch.device,
    log:      logging.Logger,
) -> None:
    """
    Pretrain the actor in-place using BC risk labels (Session 7 — 4D).

    Trains all 4 action dims to start near sensible defaults:
      [0] pos_size  → regime-scaled (5-25%)
      [1] sl_atr    → vol-adaptive (0.5-3.0×ATR)
      [2] tp_atr    → trend-adaptive (1.0-6.0×ATR)
      [3] trail_on  → True in trending regime (ADX > 0.5)

    Only entry bars are labeled (the actor only acts at entry in trade-level replay).
    """
    log.info("─── STAGE 1: BC Risk Pretraining ─────────────────────────────────────────")

    log.info("  Generating oracle risk labels from composite-rule simulation…")
    label_df = generate_risk_labels(features, close)
    if len(label_df) < BC_PRETRAIN_BATCH * 4:
        log.warning("  Fewer than 4 batches of labels — skipping BC pretrain.")
        return

    log.info(
        f"  {len(label_df):,} entry bars labeled  "
        f"(long={(label_df['position']>0).mean():.1%}  "
        f"short={(label_df['position']<0).mean():.1%})"
    )

    mask     = features.index <= TRAIN_END
    feats_np = features.loc[mask].values.astype(np.float32)
    close_np = close.loc[mask].values.astype(np.float64)

    log.info("  Building observation tensors…")
    obs_list    = []
    target_list = []

    for _, row in label_df.iterrows():
        bar_idx = int(row["bar_idx"])
        if bar_idx < SEQ_LEN:
            continue
        obs = _build_obs(
            feats_np, close_np,
            bar_idx   = bar_idx,
            position  = float(row["position"]),
            pos_size  = float(row["pos_size"]),
            hold_bars = int(row["hold_bars"]),
            entry_px  = float(row["entry_px"]),
            entry_atr = float(row["atr_frac"]),
        )
        target = np.array([
            float(row["pos_size"]),
            float(row["sl_atr"]),
            float(row["tp_atr"]),
            float(row["trail"]),
        ], dtype=np.float32)
        obs_list.append(obs)
        target_list.append(target)

    if not obs_list:
        log.warning("  No valid BC observations — skipping pretrain.")
        return

    obs_t    = torch.tensor(np.array(obs_list),    dtype=torch.float32)
    target_t = torch.tensor(np.array(target_list), dtype=torch.float32)

    dataset    = TensorDataset(obs_t, target_t)
    dataloader = DataLoader(dataset, batch_size=BC_PRETRAIN_BATCH, shuffle=True, drop_last=True)

    actor_mod = getattr(actor, "_orig_mod", actor)
    optimizer  = torch.optim.Adam(actor_mod.parameters(), lr=BC_PRETRAIN_LR)
    actor_mod.train()

    log.info(
        f"  {BC_PRETRAIN_EPOCHS} epochs × {len(dataloader)} batches  "
        f"(batch={BC_PRETRAIN_BATCH}  lr={BC_PRETRAIN_LR})"
    )

    for epoch in range(BC_PRETRAIN_EPOCHS):
        epoch_loss = 0.0
        n_batches  = 0

        for batch_obs, batch_tgt in dataloader:
            batch_obs = batch_obs.to(device)
            batch_tgt = batch_tgt.to(device)

            _, _, mean_tanh = actor_mod(batch_obs)   # (B, 4) in [-1, 1]

            # Decode continuous dims via linear remap
            pos_size_pred = POS_SIZE_MIN    + (POS_SIZE_MAX    - POS_SIZE_MIN)    * (mean_tanh[:, 0] + 1.0) / 2.0
            sl_atr_pred   = SL_ATR_MULT_MIN + (SL_ATR_MULT_MAX - SL_ATR_MULT_MIN) * (mean_tanh[:, 1] + 1.0) / 2.0
            tp_atr_pred   = TP_ATR_MULT_MIN + (TP_ATR_MULT_MAX - TP_ATR_MULT_MIN) * (mean_tanh[:, 2] + 1.0) / 2.0

            # Logit for binary dim (gain=3 matches env's sigmoid(×3) decode)
            trail_logit = mean_tanh[:, 3] * 3.0

            loss = (
                F.mse_loss(pos_size_pred, batch_tgt[:, 0]) +
                F.mse_loss(sl_atr_pred,   batch_tgt[:, 1]) +
                F.mse_loss(tp_atr_pred,   batch_tgt[:, 2]) +
                F.binary_cross_entropy_with_logits(trail_logit, batch_tgt[:, 3])
            )

            optimizer.zero_grad()
            loss.backward()
            nn.utils.clip_grad_norm_(actor_mod.parameters(), 1.0)
            optimizer.step()

            epoch_loss += loss.item()
            n_batches  += 1

        if (epoch + 1) % 5 == 0 or epoch == 0:
            log.info(
                f"  epoch {epoch+1:>3}/{BC_PRETRAIN_EPOCHS}  "
                f"loss={epoch_loss/max(n_batches,1):.4f}"
            )

    actor_mod.train()   # ensure training mode for SAC LSTM backward
    log.info("  BC Risk Pretraining complete.")
    log.info("")
