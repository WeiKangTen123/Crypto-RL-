"""
MarketDiagnostics + DriftManager — TIA v3 OOD detection and drift monitoring.

MarketDiagnostics
─────────────────
EMA-based OOD detector over encoder z-space (unchanged from TIA v2).
Tracks the distribution of z during training and scores inference-time
observations against that distribution.

  OOD Score ∈ [0, 1]:
    ≈ 0  → z is within training distribution (normal market)
    ≈ 1  → z deviates from training distribution (regime shift / OOD market)

  The OOD score feeds:
    1. DecisionFusionLayer — gate becomes more conservative above OOD_BLOCK_THRESH
    2. extract_beta_context() — regime probs dampened toward uniform as OOD → 1
    3. Policy net — raw score as 1-dim input (agent learns to size down)

DriftManager (TIA v3 NEW)
──────────────────────────
Monitors multiple drift signals and provides actionable alerts:

  • z-space drift       — same as OOD score, but tracked over a rolling window
  • prediction drift    — BetaEngine regime distribution shift over time
  • calibration drift   — alpha_confidence mean vs. actual win rate
  • return drift        — rolling trade returns vs. training baseline

Alert states:
  NORMAL  (ood ≤ 0.7)  — nothing to do
  WARNING (ood > 0.7)  — consider reducing position sizes
  BLOCK   (ood > 0.9)  — DecisionFusionLayer forces SKIP via OOD block weight

Usage
─────
    diag = MarketDiagnostics(z_dim=FC_HIDDEN)
    drift_mgr = DriftManager(diag)

    # During training (SACAgent.update()):
    diag.update(z_batch)   # updates EMA buffers every 10 update cycles
    drift_mgr.record_trade(outcome, confidence, regime)   # per closed trade

    # During inference (Actor.forward()):
    ood_score = diag(z)   # (B,) ∈ [0, 1]

    # Periodic monitoring (train loop):
    alert = drift_mgr.check()   # → "NORMAL" | "WARNING" | "BLOCK"
"""

from __future__ import annotations

from collections import deque

import torch
import torch.nn as nn

from DRL_BTC.config import OOD_EMA_ALPHA, OOD_WARN_THRESH, OOD_BLOCK_THRESH


# ── MarketDiagnostics ─────────────────────────────────────────────────────────

class MarketDiagnostics(nn.Module):
    """
    EMA-based OOD detector over the encoder's z representation.

    Parameters
    ──────────
    z_dim       : dimension of encoder output (= FC_HIDDEN)
    ema_alpha   : EMA smoothing factor (small → slow update → stable stats)
    warn_thresh : mean |z_norm| threshold where ood_score saturates to ≈1

    Buffers (non-trainable, included in state_dict for checkpoint sync):
        running_mean : (z_dim,)  — EMA of batch mean across training steps
        running_std  : (z_dim,)  — EMA of batch std  across training steps
        n_updates    : scalar    — update count (used to initialise on first call)
    """

    def __init__(
        self,
        z_dim:       int   = 256,
        ema_alpha:   float = OOD_EMA_ALPHA,
        warn_thresh: float = OOD_WARN_THRESH,
    ):
        super().__init__()
        self.ema_alpha   = ema_alpha
        self.warn_thresh = warn_thresh

        self.register_buffer("running_mean", torch.zeros(z_dim))
        self.register_buffer("running_std",  torch.ones(z_dim))
        self.register_buffer("n_updates",    torch.tensor(0, dtype=torch.long))

        # Non-buffer: rolling window of recent inference z-vectors for std estimation.
        # Not in state_dict → never overwritten by CPU sync or val-checkpoint resets.
        # Used to update running_std when B=1 (std undefined for a single sample).
        self._inf_z_buf: list = []
        self._inf_z_maxlen: int = 50

    @torch.no_grad()
    def update(self, z: torch.Tensor) -> None:
        """
        Update EMA statistics from a batch of z vectors.

        Call from training loop (SACAgent.update()) every N update cycles,
        AND from Actor.forward() at B=1 eval (inference path).
        Safe to call from GPU or CPU; detaches z automatically.

        z : (B, z_dim) — encoder output from a batch
        """
        z = z.detach()
        batch_mean = z.mean(dim=0)

        if z.shape[0] == 1:
            # Accumulate inference z for std estimation (std undefined for n=1 directly).
            self._inf_z_buf.append(z[0].cpu())
            if len(self._inf_z_buf) > self._inf_z_maxlen:
                self._inf_z_buf.pop(0)

        if self.n_updates == 0:
            self.running_mean.copy_(batch_mean)
            if z.shape[0] > 1:
                self.running_std.copy_(z.std(dim=0).clamp(min=1e-6))
            elif len(self._inf_z_buf) >= 10:
                z_stk = torch.stack(self._inf_z_buf).to(z.device)
                self.running_std.copy_(z_stk.std(dim=0).clamp(min=1e-6))
        else:
            α = self.ema_alpha
            self.running_mean.lerp_(batch_mean, α)
            if z.shape[0] > 1:
                self.running_std.lerp_(z.std(dim=0).clamp(min=1e-6), α)
            elif len(self._inf_z_buf) >= 10:
                # Estimate std from rolling inference buffer — tracks encoder z-scale
                # even when only B=1 samples arrive (std undefined for a single sample).
                z_stk = torch.stack(self._inf_z_buf).to(z.device)
                self.running_std.lerp_(z_stk.std(dim=0).clamp(min=1e-6), α)

        self.n_updates.add_(1)

    def forward(self, z: torch.Tensor) -> torch.Tensor:
        """
        Compute OOD score for each sample.

        Algorithm:
          1. Standardise z: z_norm = (z - μ) / σ
          2. Mean absolute deviation: mad = mean(|z_norm|)
          3. Sigmoid-scale: ood = σ(mad − warn_thresh)
             mad << warn_thresh → ood ≈ 0
             mad >> warn_thresh → ood ≈ 1

        Returns
        ───────
        ood_score : (B,) ∈ [0, 1]
        """
        z_norm    = (z - self.running_mean) / (self.running_std + 1e-6)
        mad       = z_norm.abs().mean(dim=-1)
        return torch.sigmoid(mad - self.warn_thresh)


# ── DriftManager ──────────────────────────────────────────────────────────────

class DriftManager:
    """
    TIA v3: Actionable drift monitoring layered on top of MarketDiagnostics.

    Tracks three drift signals over a rolling window:
      1. OOD score (z-space distance from training distribution)
      2. Calibration drift (alpha_confidence mean vs. actual win rate)
      3. Return drift (rolling trade returns vs. baseline)

    Alert thresholds:
      NORMAL  : ood_ema ≤ 0.70
      WARNING : ood_ema > 0.70  → log + consider halving sizes externally
      BLOCK   : ood_ema > 0.90  → DecisionFusionLayer auto-dampens via OOD block weight

    The DriftManager does NOT retrain the model — it surfaces signals that a
    human operator or future AutoDrift system can act on. Phase 2 will add:
      • PSI (Population Stability Index) on feature distributions
      • KL divergence on BetaEngine regime predictions
      • Wasserstein distance on trade return distributions

    Parameters
    ──────────
    diagnostics   : MarketDiagnostics — the underlying OOD detector
    window        : int  — rolling window for EMA smoothing of drift signals
    """

    NORMAL  = "NORMAL"
    WARNING = "WARNING"
    BLOCK   = "BLOCK"

    def __init__(
        self,
        diagnostics: MarketDiagnostics,
        window:      int = 200,
    ):
        self.diagnostics = diagnostics
        self.window      = window

        # Rolling buffers (deques with maxlen)
        self._ood_scores:   deque[float] = deque(maxlen=window)
        self._confidences:  deque[float] = deque(maxlen=window)
        self._outcomes:     deque[float] = deque(maxlen=window)
        self._regimes:      deque[int]   = deque(maxlen=window)

        # Smoothed OOD estimate (EMA)
        self._ood_ema  = 0.0
        self._ood_alpha = 0.05   # slightly faster than MarketDiagnostics EMA

        # Baseline statistics (set after warmup or from historical training data)
        self._baseline_win_rate:  float = 0.5
        self._baseline_avg_return: float = 0.0

    def record_ood(self, ood_score: float) -> None:
        """Record an OOD score observation (call at end of each env step or inference)."""
        self._ood_scores.append(float(ood_score))
        self._ood_ema = self._ood_alpha * ood_score + (1 - self._ood_alpha) * self._ood_ema

    def record_trade(
        self,
        outcome:    float,
        confidence: float,
        regime:     int = -1,
    ) -> None:
        """Record a completed trade's outcome, confidence, and regime."""
        self._outcomes.append(float(outcome))
        self._confidences.append(float(confidence))
        if regime >= 0:
            self._regimes.append(int(regime))

    def check(self) -> str:
        """
        Evaluate current drift level and return alert state.

        Returns "NORMAL", "WARNING", or "BLOCK".
        """
        if self._ood_ema > OOD_BLOCK_THRESH:
            return self.BLOCK
        if self._ood_ema > 0.70:
            return self.WARNING
        return self.NORMAL

    def calibration_drift(self) -> float:
        """
        Gap between predicted confidence and realised win rate.
        Positive = overconfident. Negative = underconfident.

        Only meaningful when len(_outcomes) > 20.
        """
        if len(self._outcomes) < 20:
            return 0.0
        actual_wr = sum(o > 0 for o in self._outcomes) / len(self._outcomes)
        pred_conf = sum(self._confidences) / len(self._confidences)
        return float(pred_conf - actual_wr)

    def return_drift(self) -> float:
        """
        Rolling average trade return vs. baseline.
        Negative = returns deteriorating vs. training baseline.
        """
        if len(self._outcomes) < 10:
            return 0.0
        rolling_avg = sum(self._outcomes) / len(self._outcomes)
        return float(rolling_avg - self._baseline_avg_return)

    def set_baseline(self, win_rate: float, avg_return: float) -> None:
        """Set the training-period baseline for calibration checks."""
        self._baseline_win_rate   = win_rate
        self._baseline_avg_return = avg_return

    # ── Active influence methods (v3.1) ───────────────────────────────────────

    def get_memory_k(self, ood_score: float, max_k: int = 20) -> int:
        """
        OOD-gated retrieval count for KnowledgeMemory.

        High OOD → fewer (or zero) memories retrieved, because the current
        market regime likely doesn't match any stored trade well.

        ood ≤ 0.60 → k = max_k   (confident; use full memory context)
        ood  0.6–0.8 → k = 10    (cautious; partial context)
        ood  0.8–0.9 → k =  5    (uncertain; minimal context)
        ood > 0.90  → k =  0    (OOD; memory unreliable — pass zeros)
        """
        if ood_score > 0.90:
            return 0
        if ood_score > 0.80:
            return min(5, max_k)
        if ood_score > 0.60:
            return min(10, max_k)
        return max_k

    def get_beta_temperature(self) -> float:
        """
        Adaptive temperature for BetaEngine regime prob calibration.

        When the model is overconfident (predicted confidence > actual win rate),
        increase temperature to smooth the regime probability distribution.
        This prevents the policy from acting on spuriously sharp regime reads.

        Returns temperature T ∈ [1.0, 3.0]:
          T = 1.0  → no change (well-calibrated or under-confident)
          T = 3.0  → heavily smoothed (badly overconfident)
        """
        cal_drift = self.calibration_drift()   # positive → overconfident
        temperature = 1.0 + max(0.0, cal_drift) * 4.0
        return float(min(3.0, temperature))

    def summary(self) -> str:
        """One-line human-readable drift summary."""
        n_ood = len(self._ood_scores)
        n_trd = len(self._outcomes)
        alert = self.check()
        cal   = self.calibration_drift()
        ret   = self.return_drift()
        return (
            f"DriftManager [{alert}]  "
            f"ood_ema={self._ood_ema:.3f}  "
            f"calib_drift={cal:+.3f}  "
            f"ret_drift={ret:+.4f}  "
            f"n_ood={n_ood}  n_trades={n_trd}"
        )
