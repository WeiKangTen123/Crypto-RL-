"""
SharedModel: PerspectiveEncoder + all TIA v3 prediction heads for supervised pretraining.

Used exclusively for supervised pretraining (Stages 1-3 in train.py).
After pretraining, encoder + head weights are transferred to the RL Actor:

    shared_model.copy_encoder_to(agent.actor)

The shared model itself is then discarded (GPU memory freed) before RL begins.

Architecture (TIA v3 / Session 10)
─────────────────────────────────
    obs (B, 48, 217)
         │
    PerspectiveEncoder  ← same class as in Actor / Critics
         │
       z (FC_HIDDEN)
    ┌────┴──────────────┬───────────────────────────┐
    │                   │                           │
  BetaEngine        AlphaEngine          DecisionFusionLayer
  regime(3)         ret + quantiles(3)   (not supervised; participates
  embed(32)         mfe + mae            via encoder gradients in
  vol_class(3)      tp + sl + exp_vol    joint fine-tune)
  vol_pred          hold + alpha_conf
  trend_conf        exp_variance [NEW]
  stability         tail_risk    [NEW]
  transition_prob   exp_max_dd   [NEW]
  calib_conf

Note: DecisionFusionLayer receives rule_feat=zeros during pretraining
(no env state available), so it doesn't learn rule-based gating during pretrain.
This is intentional — the fusion layer calibrates entirely through RL.
"""

from __future__ import annotations

import torch
import torch.nn as nn

from DRL_BTC.config import FC_HIDDEN, RULE_FEAT_DIM
from DRL_BTC.models.actor_critic import PerspectiveEncoder
from DRL_BTC.models.heads import (
    BetaEngine, AlphaEngine, DecisionFusionLayer,
    extract_beta_context, extract_alpha_feat,
)


class SharedModel(nn.Module):
    def __init__(self, market_cols: list[str], n_portfolio: int):
        super().__init__()
        self.encoder = PerspectiveEncoder(market_cols, n_portfolio)
        self.beta    = BetaEngine(FC_HIDDEN)
        self.alpha   = AlphaEngine(FC_HIDDEN)
        self.fusion  = DecisionFusionLayer(FC_HIDDEN)

    def forward(self, obs: torch.Tensor) -> dict:
        """
        obs : (B, seq_len, n_features)
        Returns flat dict with all head outputs plus z.

        OOD score is zero during pretraining (no training distribution established yet).
        rule_feat is zero during pretraining (no env state available).
        """
        z = self.encoder(obs)

        beta_out  = self.beta(z)
        alpha_out = self.alpha(z)

        beta_feat  = extract_beta_context(beta_out, ood_score=None)    # (B, 39) — no OOD correction during pretrain
        alpha_feat = extract_alpha_feat(alpha_out)                     # (B, 10)

        # Zero placeholders for features not available during pretraining
        ood_score = torch.zeros(z.shape[0], device=z.device)
        rule_feat = torch.zeros(z.shape[0], RULE_FEAT_DIM, device=z.device)

        gate_out = self.fusion(z, beta_feat, alpha_feat, ood_score, rule_feat)

        return {
            "z":                       z,
            # ── BetaEngine ──────────────────────────────────────────────────────
            "beta_regime_logits":      beta_out["regime_logits"],
            "beta_vol_class_logits":   beta_out["vol_class_logits"],
            "beta_vol_pred":           beta_out["vol_pred"],
            "beta_trend_confidence":   beta_out["trend_confidence"],
            "beta_regime_stability":   beta_out["regime_stability"],
            "beta_transition_prob":    beta_out["transition_prob"],
            "beta_regime_embedding":   beta_out["regime_embedding"],
            # ── AlphaEngine ─────────────────────────────────────────────────────
            "alpha_ret_pred":          alpha_out["ret_pred"],
            "alpha_ret_p10":           alpha_out["ret_p10"],
            "alpha_ret_p50":           alpha_out["ret_p50"],
            "alpha_ret_p90":           alpha_out["ret_p90"],
            "alpha_mfe_pred":          alpha_out["mfe_pred"],
            "alpha_mae_pred":          alpha_out["mae_pred"],
            "alpha_tp_prob":           alpha_out["tp_prob"],
            "alpha_sl_prob":           alpha_out["sl_prob"],
            "alpha_exp_vol":           alpha_out["exp_vol"],
            "alpha_hold_pred":         alpha_out["hold_pred"],
            "alpha_confidence":        alpha_out["alpha_confidence"],
            "alpha_exp_variance":      alpha_out["exp_variance"],
            "alpha_tail_risk":         alpha_out["tail_risk"],
            "alpha_exp_max_dd":        alpha_out["exp_max_dd"],
            # ── DecisionFusionLayer ─────────────────────────────────────────────
            "gate_logits":             gate_out["gate_logits"],
            "gate_size_mult":          gate_out["size_multiplier"],
            "gate_confidence":         gate_out["gate_confidence"],
        }

    def copy_encoder_to(self, actor) -> None:
        """
        Transfer pretrained encoder + BetaEngine + AlphaEngine + DecisionFusionLayer
        weights into the RL Actor.

        Uses strict=False so any TIA v2 → v3 architecture mismatches (new head keys)
        load with the old weights where they match, and keep random init for new keys.
        This allows warm-starting from Session 8/9 checkpoints into the TIA v3 Actor.
        """
        dst = getattr(actor, "_orig_mod", actor)
        dst.encoder.load_state_dict(self.encoder.state_dict(), strict=False)
        dst.beta.load_state_dict(self.beta.state_dict(), strict=False)
        dst.alpha.load_state_dict(self.alpha.state_dict(), strict=False)
        dst.fusion.load_state_dict(self.fusion.state_dict(), strict=False)
        print("[SharedModel] Pretrained encoder + BetaEngine + AlphaEngine + DecisionFusionLayer → Actor  ✓")

    def save(self, path) -> None:
        torch.save(self.state_dict(), path)

    def load(self, path, device) -> None:
        self.load_state_dict(
            torch.load(path, map_location=device, weights_only=True),
            strict=False,
        )
