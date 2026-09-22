"""
Supervised pretraining of the SharedModel (TIA v3 / Session 10).

Three stages
────────────
  Stage 1 — BetaEngine
      CE(regime) + CE(vol_class) [NEW] + MSE(vol) + MSE(trend_confidence)
      + BCE(regime_stability) + BCE(transition_prob) [NEW]
      Encoder + BetaEngine updated.

  Stage 2 — AlphaEngine
      MSE(ret_pred) + Pinball(p10/p50/p90) + MSE(mfe/mae)
      + BCE(tp_prob) + BCE(sl_prob) + MSE(exp_vol) + 0.1×MSE(hold)
      + MSE(exp_variance) [NEW] + MSE(tail_risk) [NEW] + MSE(exp_max_dd) [NEW]
      Encoder + AlphaEngine updated.
      (alpha_confidence has no supervised label — RL calibrates it.)

  Stage 3 — Joint fine-tune
      All heads + DecisionFusionLayer together at 0.3× LR.
      (DecisionFusionLayer has no supervised gate labels — learns entirely via RL.)

After completion:
    shared_model.copy_encoder_to(agent.actor)
    del shared_model           # free GPU memory before RL
"""

from __future__ import annotations

import logging
import numpy as np
import torch
import torch.nn.functional as F

from DRL_BTC.config import (
    SEQ_LEN, TRAIN_END,
    SUPERVISED_PRETRAIN_LR, SUPERVISED_PRETRAIN_BATCH,
    BETA_PRETRAIN_EPOCHS, ALPHA_PRETRAIN_EPOCHS,
)
from DRL_BTC.env.btc_env import N_PORTFOLIO_FEATS
from DRL_BTC.models.shared_model import SharedModel
from DRL_BTC.training.label_generator import generate_beta_labels, generate_alpha_labels


# ── quantile (pinball) loss ───────────────────────────────────────────────────

def _pinball(pred: torch.Tensor, target: torch.Tensor, tau: float) -> torch.Tensor:
    """Pinball / quantile loss for a single quantile level tau ∈ (0, 1)."""
    err = target - pred
    return torch.where(err >= 0, tau * err, (tau - 1.0) * err).mean()


# ── observation builder ───────────────────────────────────────────────────────

def _build_obs_batch(
    feat_arr:    np.ndarray,   # (n_bars, n_market)  float32
    indices:     np.ndarray,   # integer bar positions
    n_portfolio: int,
    device:      torch.device,
) -> torch.Tensor:
    """
    Build a (len(indices), SEQ_LEN, n_market+n_portfolio) tensor.
    Portfolio features are zero — we have no env state during pretraining.
    """
    n_market = feat_arr.shape[1]
    n        = len(indices)
    out      = np.zeros((n, SEQ_LEN, n_market + n_portfolio), dtype=np.float32)
    for bi, idx in enumerate(indices):
        start  = max(0, idx - SEQ_LEN + 1)
        window = feat_arr[start: idx + 1]
        pad    = SEQ_LEN - len(window)
        if pad > 0:
            window = np.concatenate([np.tile(window[:1], (pad, 1)), window], axis=0)
        out[bi, :, :n_market] = window
    return torch.as_tensor(out, dtype=torch.float32, device=device)


# ── main pretrain function ────────────────────────────────────────────────────

def pretrain_shared_model(
    shared_model: SharedModel,
    features,             # pd.DataFrame
    close,                # pd.Series
    device:       torch.device,
    log:          logging.Logger,
) -> None:
    """
    In-place supervised pretraining of shared_model (TIA v3 / Session 10).
    After this call, shared_model.copy_encoder_to(actor) transfers
    the pretrained encoder + heads into the RL Actor.
    """
    import pandas as pd

    W = 60

    # ── filter to training window ─────────────────────────────────────────────
    train_mask  = features.index <= pd.Timestamp(TRAIN_END)
    feat_train  = features[train_mask]
    close_train = close[train_mask]
    n_train     = len(feat_train)
    feat_arr    = feat_train.values.astype(np.float32)

    log.info(f"  Training window: {n_train:,} bars  ({feat_train.index[0].date()} → {feat_train.index[-1].date()})")

    # ── generate labels ───────────────────────────────────────────────────────
    log.info("  Generating Beta labels (24h forward regime + stability)…")
    beta_df = generate_beta_labels(feat_train, close_train)
    log.info("  Generating Alpha labels (oracle trade simulation)…")
    alpha_df = generate_alpha_labels(feat_train, close_train)

    # ── Beta tensors ──────────────────────────────────────────────────────────
    beta_valid = beta_df[beta_df["valid"] & (beta_df.index < n_train - SEQ_LEN)]
    b_idx      = beta_valid.index.values
    b_reg      = torch.as_tensor(beta_valid["regime"].values,            dtype=torch.long,    device=device)
    b_vol      = torch.as_tensor(beta_valid["fwd_vol"].values,           dtype=torch.float32, device=device)
    b_trd      = torch.as_tensor(beta_valid["trend_str"].values,         dtype=torch.float32, device=device)
    b_stab     = torch.as_tensor(beta_valid["regime_stability"].values,  dtype=torch.float32, device=device)
    b_vol_class = torch.as_tensor(beta_valid["vol_class"].values,        dtype=torch.long,    device=device)  # TIA v3
    b_trans    = torch.as_tensor(beta_valid["transition_prob"].values,   dtype=torch.float32, device=device)  # TIA v3
    n_beta     = len(b_idx)
    dist       = {v: int((b_reg == v).sum()) for v in [0, 1, 2]}
    vc_dist    = {v: int((b_vol_class == v).sum()) for v in [0, 1, 2]}
    stab_rate  = float(b_stab.mean())
    log.info(f"  Beta  → {n_beta:,} bars  BULL={dist[0]:,}  BEAR={dist[1]:,}  RANGE={dist[2]:,}  stable={stab_rate:.1%}")
    log.info(f"          vol LOW={vc_dist[0]:,}  MED={vc_dist[1]:,}  HIGH={vc_dist[2]:,}  trans_rate={b_trans.mean():.1%}")

    # ── Alpha tensors ─────────────────────────────────────────────────────────
    valid_alpha = alpha_df[alpha_df.index < n_train - SEQ_LEN]
    a_idx   = valid_alpha.index.values
    a_ret   = torch.as_tensor(valid_alpha["trade_return"].values, dtype=torch.float32, device=device)
    a_mfe   = torch.as_tensor(valid_alpha["mfe"].values,          dtype=torch.float32, device=device)
    a_mae   = torch.as_tensor(valid_alpha["mae"].values,          dtype=torch.float32, device=device)
    a_tp    = torch.as_tensor(valid_alpha["tp_hit"].values,       dtype=torch.float32, device=device)
    a_sl    = torch.as_tensor(valid_alpha["sl_hit"].values,       dtype=torch.float32, device=device)
    a_vol   = torch.as_tensor(valid_alpha["exp_vol"].values,      dtype=torch.float32, device=device)
    a_hold  = torch.as_tensor(valid_alpha["hold_bars"].values,    dtype=torch.float32, device=device)
    a_var   = torch.as_tensor(valid_alpha["exp_variance"].values, dtype=torch.float32, device=device)  # TIA v3
    a_tail  = torch.as_tensor(valid_alpha["tail_risk"].values,    dtype=torch.float32, device=device)  # TIA v3
    a_maxdd = torch.as_tensor(valid_alpha["exp_max_dd"].values,   dtype=torch.float32, device=device)  # TIA v3
    n_alpha = len(a_idx)
    log.info(f"  Alpha → {n_alpha:,} entry bars  "
             f"TP={a_tp.mean():.1%}  SL={a_sl.mean():.1%}  "
             f"win={(a_ret>0).float().mean():.1%}  avg_hold={a_hold.mean():.0f}b")
    log.info(f"          avg_var={a_var.mean():.5f}  avg_tail={a_tail.mean():.4f}  avg_maxdd={a_maxdd.mean():.4f}")

    shared_model.to(device)
    B = SUPERVISED_PRETRAIN_BATCH

    # ── STAGE 1: BetaEngine ──────────────────────────────────────────────────
    log.info("")
    log.info(f"  ┌─ STAGE 1: BetaEngine  ({BETA_PRETRAIN_EPOCHS} epochs) " + "─" * 26)
    beta_opt = torch.optim.Adam(
        list(shared_model.encoder.parameters()) + list(shared_model.beta.parameters()),
        lr=SUPERVISED_PRETRAIN_LR,
    )
    for ep in range(1, BETA_PRETRAIN_EPOCHS + 1):
        perm    = np.random.permutation(n_beta)
        ep_loss = 0.0; nb = 0
        for s in range(0, n_beta, B):
            ib  = perm[s: s + B]
            obs = _build_obs_batch(feat_arr, b_idx[ib], N_PORTFOLIO_FEATS, device)
            shared_model.train()
            z   = shared_model.encoder(obs)
            bo  = shared_model.beta(z)
            loss = (F.cross_entropy(bo["regime_logits"],     b_reg[ib])
                  + 0.3 * F.cross_entropy(bo["vol_class_logits"], b_vol_class[ib])   # TIA v3
                  + 0.5 * F.mse_loss(bo["vol_pred"],          b_vol[ib])
                  + 0.5 * F.mse_loss(bo["trend_confidence"],  b_trd[ib])
                  + 0.5 * F.binary_cross_entropy(
                        bo["regime_stability"].clamp(1e-6, 1-1e-6), b_stab[ib])
                  + 0.3 * F.binary_cross_entropy(                                    # TIA v3
                        bo["transition_prob"].clamp(1e-6, 1-1e-6), b_trans[ib]))
            beta_opt.zero_grad(); loss.backward()
            torch.nn.utils.clip_grad_norm_(shared_model.parameters(), 1.0)
            beta_opt.step()
            ep_loss += loss.item(); nb += 1
        if ep == 1 or ep % 5 == 0:
            samp_b = np.random.choice(n_beta, min(2000, n_beta), replace=False)
            obs_b  = _build_obs_batch(feat_arr, b_idx[samp_b], N_PORTFOLIO_FEATS, device)
            shared_model.eval()
            with torch.no_grad():
                z_b   = shared_model.encoder(obs_b)
                bo_ev = shared_model.beta(z_b)
                reg_acc = (bo_ev["regime_logits"].argmax(-1) == b_reg[samp_b]).float().mean().item()
                vc_acc  = (bo_ev["vol_class_logits"].argmax(-1) == b_vol_class[samp_b]).float().mean().item()
            log.info(f"  │  epoch {ep:>3}/{BETA_PRETRAIN_EPOCHS}  loss={ep_loss/nb:.4f}"
                     f"  regime_acc={reg_acc:.1%}  vol_class_acc={vc_acc:.1%}")
    log.info(f"  └" + "─" * (W - 2))

    # ── STAGE 2: AlphaEngine ────────────────────────────────────────────────
    log.info("")
    log.info(f"  ┌─ STAGE 2: AlphaEngine  ({ALPHA_PRETRAIN_EPOCHS} epochs) " + "─" * 24)
    alpha_opt = torch.optim.Adam(
        list(shared_model.encoder.parameters()) + list(shared_model.alpha.parameters()),
        lr=SUPERVISED_PRETRAIN_LR,
    )
    for ep in range(1, ALPHA_PRETRAIN_EPOCHS + 1):
        perm    = np.random.permutation(n_alpha)
        ep_loss = 0.0; nb = 0
        for s in range(0, n_alpha, B):
            ib  = perm[s: s + B]
            obs = _build_obs_batch(feat_arr, a_idx[ib], N_PORTFOLIO_FEATS, device)
            shared_model.train()
            z   = shared_model.encoder(obs)
            ao  = shared_model.alpha(z)
            loss = (
                # Mean return prediction
                F.mse_loss(ao["ret_pred"], a_ret[ib])
                # Quantile predictions (pinball loss for distribution learning)
                + _pinball(ao["ret_p10"], a_ret[ib], 0.10)
                + _pinball(ao["ret_p50"], a_ret[ib], 0.50)
                + _pinball(ao["ret_p90"], a_ret[ib], 0.90)
                # Excursion predictions
                + F.mse_loss(ao["mfe_pred"], a_mfe[ib])
                + F.mse_loss(ao["mae_pred"], a_mae[ib])
                # Probability predictions
                + F.binary_cross_entropy(ao["tp_prob"].clamp(1e-6, 1-1e-6), a_tp[ib])
                + F.binary_cross_entropy(ao["sl_prob"].clamp(1e-6, 1-1e-6), a_sl[ib])
                # Expected volatility
                + F.mse_loss(ao["exp_vol"], a_vol[ib])
                # Hold time (lower weight — noisier label)
                + 0.1 * F.mse_loss(ao["hold_pred"], a_hold[ib])
                # TIA v3: intraperiod risk predictions
                + F.mse_loss(ao["exp_variance"], a_var[ib])
                + F.mse_loss(ao["tail_risk"],    a_tail[ib])
                + F.mse_loss(ao["exp_max_dd"],   a_maxdd[ib])
                # alpha_confidence: no supervised label; RL calibrates it
            )
            alpha_opt.zero_grad(); loss.backward()
            torch.nn.utils.clip_grad_norm_(shared_model.parameters(), 1.0)
            alpha_opt.step()
            ep_loss += loss.item(); nb += 1

        if ep == 1 or ep % 5 == 0:
            samp = np.random.choice(n_alpha, min(2000, n_alpha), replace=False)
            obs  = _build_obs_batch(feat_arr, a_idx[samp], N_PORTFOLIO_FEATS, device)
            shared_model.eval()
            with torch.no_grad():
                z  = shared_model.encoder(obs)
                ao = shared_model.alpha(z)
                r_corr = float(np.corrcoef(
                    ao["ret_pred"].cpu().numpy(), a_ret[samp].cpu().numpy())[0, 1])
                tp_acc = float(((ao["tp_prob"] > 0.5).float() == a_tp[samp]).float().mean())
                sl_acc = float(((ao["sl_prob"] > 0.5).float() == a_sl[samp]).float().mean())
                p50_corr = float(np.corrcoef(
                    ao["ret_p50"].cpu().numpy(), a_ret[samp].cpu().numpy())[0, 1])
                var_mse  = F.mse_loss(ao["exp_variance"], a_var[samp]).item()
                tail_mse = F.mse_loss(ao["tail_risk"],    a_tail[samp]).item()
            log.info(f"  │  epoch {ep:>3}/{ALPHA_PRETRAIN_EPOCHS}  loss={ep_loss/nb:.4f}"
                     f"  ret_corr={r_corr:+.3f}  p50_corr={p50_corr:+.3f}"
                     f"  tp_acc={tp_acc:.1%}  sl_acc={sl_acc:.1%}"
                     f"  var_mse={var_mse:.6f}  tail_mse={tail_mse:.5f}")
    log.info(f"  └" + "─" * (W - 2))

    # ── STAGE 3: Joint fine-tune (encoder + all heads) ────────────────────────
    JOINT_EPOCHS = 10
    log.info("")
    log.info(f"  ┌─ STAGE 3: Joint fine-tune  ({JOINT_EPOCHS} epochs) " + "─" * 23)
    joint_opt = torch.optim.Adam(
        shared_model.parameters(), lr=SUPERVISED_PRETRAIN_LR * 0.3
    )
    for ep in range(1, JOINT_EPOCHS + 1):
        # Beta pass
        perm       = np.random.permutation(n_beta)
        b_loss_tot = 0.0; nb = 0
        for s in range(0, n_beta, B):
            ib  = perm[s: s + B]
            obs = _build_obs_batch(feat_arr, b_idx[ib], N_PORTFOLIO_FEATS, device)
            shared_model.train()
            z   = shared_model.encoder(obs)
            bo  = shared_model.beta(z)
            l   = (F.cross_entropy(bo["regime_logits"],      b_reg[ib])      * 0.50
                 + F.cross_entropy(bo["vol_class_logits"], b_vol_class[ib]) * 0.15   # TIA v3
                 + 0.25 * F.binary_cross_entropy(
                       bo["regime_stability"].clamp(1e-6, 1-1e-6), b_stab[ib])
                 + 0.15 * F.binary_cross_entropy(                                    # TIA v3
                       bo["transition_prob"].clamp(1e-6, 1-1e-6), b_trans[ib]))
            joint_opt.zero_grad(); l.backward()
            torch.nn.utils.clip_grad_norm_(shared_model.parameters(), 1.0)
            joint_opt.step()
            b_loss_tot += l.item(); nb += 1

        # Alpha pass
        perm       = np.random.permutation(n_alpha)
        a_loss_tot = 0.0; na = 0
        for s in range(0, n_alpha, B):
            ib  = perm[s: s + B]
            obs = _build_obs_batch(feat_arr, a_idx[ib], N_PORTFOLIO_FEATS, device)
            shared_model.train()
            z   = shared_model.encoder(obs)
            ao  = shared_model.alpha(z)
            l   = (F.mse_loss(ao["ret_pred"], a_ret[ib])
                 + _pinball(ao["ret_p50"], a_ret[ib], 0.50)
                 + F.mse_loss(ao["mfe_pred"], a_mfe[ib])
                 + F.mse_loss(ao["mae_pred"], a_mae[ib])
                 + F.binary_cross_entropy(ao["tp_prob"].clamp(1e-6, 1-1e-6), a_tp[ib])
                 + F.binary_cross_entropy(ao["sl_prob"].clamp(1e-6, 1-1e-6), a_sl[ib])
                 + F.mse_loss(ao["exp_variance"], a_var[ib])    # TIA v3
                 + F.mse_loss(ao["tail_risk"],    a_tail[ib])   # TIA v3
                 + F.mse_loss(ao["exp_max_dd"],   a_maxdd[ib])  # TIA v3
                 )
            joint_opt.zero_grad(); l.backward()
            torch.nn.utils.clip_grad_norm_(shared_model.parameters(), 1.0)
            joint_opt.step()
            a_loss_tot += l.item(); na += 1

        log.info(f"  │  epoch {ep:>2}/{JOINT_EPOCHS}"
                 f"  beta={b_loss_tot/nb:.4f}  alpha={a_loss_tot/na:.4f}")
    log.info(f"  └" + "─" * (W - 2))

    # ── Final diagnostics ─────────────────────────────────────────────────────
    log.info("")
    shared_model.eval()

    # Beta final
    samp_b = np.random.choice(n_beta, min(2000, n_beta), replace=False)
    obs_b  = _build_obs_batch(feat_arr, b_idx[samp_b], N_PORTFOLIO_FEATS, device)
    with torch.no_grad():
        z_b   = shared_model.encoder(obs_b)
        bo_f  = shared_model.beta(z_b)
        reg_acc_f = (bo_f["regime_logits"].argmax(-1) == b_reg[samp_b]).float().mean().item()
        vc_acc_f  = (bo_f["vol_class_logits"].argmax(-1) == b_vol_class[samp_b]).float().mean().item()

    # Alpha final
    samp = np.random.choice(n_alpha, min(2000, n_alpha), replace=False)
    obs  = _build_obs_batch(feat_arr, a_idx[samp], N_PORTFOLIO_FEATS, device)
    with torch.no_grad():
        z  = shared_model.encoder(obs)
        ao = shared_model.alpha(z)
        r_corr_final = float(np.corrcoef(
            ao["ret_pred"].cpu().numpy(), a_ret[samp].cpu().numpy())[0, 1])
        tp_acc_final = float(((ao["tp_prob"] > 0.5).float() == a_tp[samp]).float().mean())
        sl_acc_final = float(((ao["sl_prob"] > 0.5).float() == a_sl[samp]).float().mean())
        var_mse_f    = F.mse_loss(ao["exp_variance"], a_var[samp]).item()
        tail_mse_f   = F.mse_loss(ao["tail_risk"],    a_tail[samp]).item()
        maxdd_mse_f  = F.mse_loss(ao["exp_max_dd"],   a_maxdd[samp]).item()

    log.info(f"  Supervised pretrain complete (TIA v3):")
    log.info(f"    Beta  regime_acc      = {reg_acc_f:.1%}")
    log.info(f"    Beta  vol_class_acc   = {vc_acc_f:.1%}")
    log.info(f"    Alpha ret_corr        = {r_corr_final:+.3f}")
    log.info(f"    Alpha tp_acc          = {tp_acc_final:.1%}")
    log.info(f"    Alpha sl_acc          = {sl_acc_final:.1%}")
    log.info(f"    Alpha exp_var MSE     = {var_mse_f:.6f}")
    log.info(f"    Alpha tail_risk MSE   = {tail_mse_f:.5f}")
    log.info(f"    Alpha exp_max_dd MSE  = {maxdd_mse_f:.5f}")
    log.info(f"  Ready → shared_model.copy_encoder_to(actor)")
