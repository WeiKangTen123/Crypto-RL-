"""
KnowledgeMemory — TIA v3 experience memory, wired into the live decision path.

Distinct from the RL replay buffer (which trains the Q-function):
  • Replay buffer  : stores (obs, action, reward, next_obs) for gradient updates
  • KnowledgeMemory: stores completed-trade embeddings for nearest-neighbour
    retrieval at inference time, enriching DecisionFusion with historical context

Pipeline position (v3.1):
  Encoder → z
    ↓
  KnowledgeMemory.retrieve_feat(z, ood, regime)
    → memory_feat (10-dim compact summary)
    ↓
  DecisionFusion (receives memory_feat alongside beta/alpha/ood/rule/risk)
    ↓
  Actor

OOD-gated retrieval:
  ood ≤ 0.60 → k = 20   (confident; rich memory context)
  ood  0.6–0.8 → k = 10  (cautious; partial context)
  ood  0.8–0.9 → k =  5   (uncertain; minimal context)
  ood > 0.90  → k =  0   (OOD; memory not trustworthy — return zeros)

Memory summary (10-dim, all ∈ [−1, 1] or [0, 1]):
  [0] avg_return       — mean outcome of retrieved trades
  [1] win_rate         — fraction of retrieved trades with positive outcome
  [2] avg_mfe          — mean max favorable excursion (≥ 0)
  [3] avg_mae          — mean max adverse excursion (≥ 0)
  [4] avg_hold         — mean hold duration (normalized / 96.0, ∈ [0, 1])
  [5] tp_rate          — fraction of retrieved trades that hit TP
  [6] sample_count     — k_actual / KNOWLEDGE_MEMORY_K (normalized, ∈ [0, 1])
  [7] avg_similarity   — mean cosine similarity of retrieved trades ∈ [−1, 1]
  [8] memory_confidence— sample_count × avg_similarity (quality signal, ∈ [0, 1])
  [9] regime_match     — fraction with same regime as query ∈ [0, 1]
"""

from __future__ import annotations

from collections import deque

import numpy as np
import torch

from DRL_BTC.config import KNOWLEDGE_MEMORY_SIZE, KNOWLEDGE_MEMORY_K, MEMORY_FEAT_DIM


class KnowledgeMemory:
    """
    Fixed-capacity ring buffer of trade experiences for cosine-similarity retrieval.

    Each stored experience contains:
      z          : np.ndarray (z_dim,)  — encoder embedding at trade entry
      regime     : int                  — BetaEngine predicted regime at entry (0/1/2)
      action     : np.ndarray (4,)      — [pos_size, sl, tp, trail] at entry
      outcome    : float                — total trade PnL fraction
      confidence : float                — alpha_confidence at entry
      mfe        : float                — max favorable excursion fraction (≥ 0)
      mae        : float                — max adverse excursion fraction (≥ 0)
      hold_bars  : float                — bars held (not normalized)
      tp_hit     : int                  — 1 if TP triggered, 0 otherwise
      timestamp  : int                  — training step when trade closed

    Parameters
    ──────────
    capacity : int  — max experiences (ring buffer; oldest evicted first)
    k        : int  — default top-K for retrieval (OOD-gated down in retrieve_feat)
    """

    def __init__(
        self,
        capacity: int = KNOWLEDGE_MEMORY_SIZE,
        k:        int = KNOWLEDGE_MEMORY_K,
    ):
        self._capacity = capacity
        self._k        = k
        self._buffer: deque[dict] = deque(maxlen=capacity)

        self._embed_cache: np.ndarray | None = None
        self._dirty = True

    # ── write ────────────────────────────────────────────────────────────────

    def store(
        self,
        z:          np.ndarray | torch.Tensor,
        regime:     int,
        action:     np.ndarray | torch.Tensor,
        outcome:    float,
        confidence: float,
        mfe:        float = 0.0,
        mae:        float = 0.0,
        hold_bars:  float = 0.0,
        tp_hit:     int   = 0,
        timestamp:  int   = 0,
    ) -> None:
        """
        Add a closed trade experience to the memory.

        Parameters
        ──────────
        z          : encoder embedding at entry (z_dim,)
        regime     : BetaEngine predicted regime class (0=BULL, 1=BEAR, 2=RANGE)
        action     : decoded risk action [pos_size, sl_atr, tp_atr, trail]
        outcome    : realised trade PnL fraction (e.g. +0.03 = +3%)
        confidence : alpha_confidence scalar at entry ∈ [0, 1]
        mfe        : max favorable excursion fraction (≥ 0)
        mae        : max adverse excursion fraction (≥ 0)
        hold_bars  : bars held for this trade
        tp_hit     : 1 if TP triggered; 0 for SL/dir/timeout
        timestamp  : global training step (for temporal ordering)
        """
        if isinstance(z, torch.Tensor):
            z = z.detach().cpu().numpy()
        if isinstance(action, torch.Tensor):
            action = action.detach().cpu().numpy()

        self._buffer.append({
            "z":          z.astype(np.float32),
            "regime":     int(regime),
            "action":     np.asarray(action, dtype=np.float32),
            "outcome":    float(outcome),
            "confidence": float(confidence),
            "mfe":        float(mfe),
            "mae":        float(mae),
            "hold_bars":  float(hold_bars),
            "tp_hit":     int(tp_hit),
            "timestamp":  int(timestamp),
        })
        self._dirty = True

    # ── OOD-gated k ──────────────────────────────────────────────────────────

    @staticmethod
    def ood_k(ood_score: float, max_k: int = KNOWLEDGE_MEMORY_K) -> int:
        """Return retrieval count gated by OOD severity."""
        if ood_score > 0.90:
            return 0
        if ood_score > 0.80:
            return min(5, max_k)
        if ood_score > 0.60:
            return min(10, max_k)
        return max_k

    # ── compact feature extraction ────────────────────────────────────────────

    def retrieve_feat(
        self,
        z:              np.ndarray,
        ood_score:      float       = 0.0,
        current_regime: int | None  = None,
    ) -> torch.Tensor:
        """
        Retrieve top-k similar past trades and return a compact 10-dim summary.

        Retrieval count is OOD-gated: at ood > 0.90 returns zeros (memory
        unreliable when market is far outside the training distribution).

        Parameters
        ──────────
        z              : query encoder embedding (z_dim,) — numpy float32
        ood_score      : OOD score ∈ [0, 1] from MarketDiagnostics
        current_regime : BetaEngine predicted regime (0/1/2) for regime_match

        Returns
        ───────
        (MEMORY_FEAT_DIM,) float32 tensor on CPU
        """
        k = self.ood_k(ood_score)
        if k == 0 or len(self._buffer) == 0:
            return torch.zeros(MEMORY_FEAT_DIM, dtype=torch.float32)

        k = min(k, len(self._buffer))
        entries, sims = self._top_k(z, k)

        return self._featurise(entries, sims, current_regime, k)

    def retrieve_feat_batch(
        self,
        z_batch:        np.ndarray,              # (B, z_dim)
        ood_scores:     np.ndarray | None = None, # (B,) or None → assume 0
        regime_batch:   np.ndarray | None = None, # (B,) int or None
        device:         torch.device | None = None,
    ) -> torch.Tensor:
        """
        Vectorised batch retrieval — compute 10-dim memory_feat for each sample.

        Uses a single matrix multiply for cosine similarity across the batch:
            sims = z_norm_batch @ cache_norm.T   # (B, N)
        then per-sample top-k selection.

        Parameters
        ──────────
        z_batch     : (B, z_dim) float32 — encoder outputs for the batch
        ood_scores  : (B,) float32 — per-sample OOD scores
        regime_batch: (B,) int — per-sample predicted regimes
        device      : output tensor device (default: CPU)

        Returns
        ───────
        (B, MEMORY_FEAT_DIM) float32 tensor
        """
        B   = z_batch.shape[0]
        n   = len(self._buffer)
        out = np.zeros((B, MEMORY_FEAT_DIM), dtype=np.float32)

        if n == 0:
            t = torch.from_numpy(out)
            return t.to(device) if device else t

        if ood_scores is None:
            ood_scores = np.zeros(B, dtype=np.float32)
        if regime_batch is None:
            regime_batch = np.full(B, -1, dtype=np.int32)

        # Rebuild embedding cache once
        if self._dirty or self._embed_cache is None or len(self._embed_cache) != n:
            self._embed_cache = np.stack([e["z"] for e in self._buffer], axis=0)
            self._dirty = False

        # Vectorised cosine similarity: (B, N)
        z_norm  = z_batch / (np.linalg.norm(z_batch, axis=1, keepdims=True) + 1e-8)
        c_norm  = self._embed_cache / (np.linalg.norm(self._embed_cache, axis=1, keepdims=True) + 1e-8)
        sims_BN = z_norm @ c_norm.T   # (B, N)

        entries_list = list(self._buffer)

        for i in range(B):
            k = self.ood_k(float(ood_scores[i]))
            if k == 0:
                continue
            k_eff = min(k, n)
            # argpartition is O(N) vs argsort O(N log N) — ~12× faster at N=5000, k=20
            part_idx = np.argpartition(sims_BN[i], -k_eff)[-k_eff:]
            top_idx  = part_idx[np.argsort(sims_BN[i][part_idx])[::-1]]
            entries  = [entries_list[j] for j in top_idx]
            top_sims = sims_BN[i][top_idx]
            feat = self._featurise(entries, top_sims, int(regime_batch[i]), k)
            out[i] = feat.numpy()

        t = torch.from_numpy(out)
        return t.to(device) if device else t

    # ── low-level retrieval helpers ───────────────────────────────────────────

    def _top_k(
        self,
        z: np.ndarray,
        k: int,
    ) -> tuple[list[dict], np.ndarray]:
        """Return (entries, cosine_similarities) for top-k matches."""
        n = len(self._buffer)
        if self._dirty or self._embed_cache is None or len(self._embed_cache) != n:
            self._embed_cache = np.stack([e["z"] for e in self._buffer], axis=0)
            self._dirty = False

        z_n    = z / (np.linalg.norm(z) + 1e-8)
        c_n    = self._embed_cache / (np.linalg.norm(self._embed_cache, axis=1, keepdims=True) + 1e-8)
        sims   = c_n @ z_n                          # (n,)
        k_eff  = min(k, n)
        part_i = np.argpartition(sims, -k_eff)[-k_eff:]
        top_i  = part_i[np.argsort(sims[part_i])[::-1]]
        return [list(self._buffer)[i] for i in top_i], sims[top_i]

    def _featurise(
        self,
        entries:        list[dict],
        sims:           np.ndarray,
        current_regime: int | None,
        max_k:          int,
    ) -> torch.Tensor:
        """Build the 10-dim memory_feat from a list of retrieved entries."""
        k_actual = len(entries)
        if k_actual == 0:
            return torch.zeros(MEMORY_FEAT_DIM, dtype=torch.float32)

        outcomes   = np.array([e["outcome"]   for e in entries], dtype=np.float32)
        mfes       = np.array([e["mfe"]       for e in entries], dtype=np.float32)
        maes       = np.array([e["mae"]       for e in entries], dtype=np.float32)
        holds      = np.array([e["hold_bars"] for e in entries], dtype=np.float32)
        tp_hits    = np.array([e["tp_hit"]    for e in entries], dtype=np.float32)
        regimes    = np.array([e["regime"]    for e in entries], dtype=np.int32)

        avg_return  = float(outcomes.mean())
        win_rate    = float((outcomes > 0).mean())
        avg_mfe     = float(mfes.mean())
        avg_mae     = float(maes.mean())
        avg_hold    = float((holds / 96.0).mean())     # normalise by max hold (96 bars)
        tp_rate     = float(tp_hits.mean())
        sample_cnt  = float(k_actual / max_k)          # normalised ∈ (0, 1]
        avg_sim     = float(sims.mean())
        mem_conf    = float(sample_cnt * max(0.0, avg_sim))
        regime_match = (
            float((regimes == current_regime).mean())
            if current_regime is not None and current_regime >= 0
            else 0.5                                   # unknown regime → neutral 0.5
        )

        feat = np.array([
            avg_return, win_rate, avg_mfe, avg_mae, avg_hold,
            tp_rate, sample_cnt, avg_sim, mem_conf, regime_match,
        ], dtype=np.float32)

        return torch.from_numpy(feat)

    # ── raw retrieval (for diagnostics) ──────────────────────────────────────

    def retrieve(
        self,
        z:     np.ndarray | torch.Tensor,
        k:     int | None = None,
        device: torch.device | None = None,
    ) -> dict:
        """
        Find top-k most similar past experiences (raw; for diagnostics).

        Returns dict with embeddings, regimes, actions, outcomes, etc.
        Use retrieve_feat() for the live decision path.
        """
        if isinstance(z, torch.Tensor):
            z = z.detach().cpu().numpy()
        z = z.astype(np.float32).flatten()

        n = len(self._buffer)
        k = min(k or self._k, n)

        if n == 0:
            return self._empty_result(k, device)

        entries, sims = self._top_k(z, k)

        result = {
            "embeddings":   np.stack([e["z"]          for e in entries]),
            "regimes":      np.array([e["regime"]     for e in entries], dtype=np.int64),
            "actions":      np.stack([e["action"]     for e in entries]),
            "outcomes":     np.array([e["outcome"]    for e in entries], dtype=np.float32),
            "confidences":  np.array([e["confidence"] for e in entries], dtype=np.float32),
            "timestamps":   np.array([e["timestamp"]  for e in entries], dtype=np.int64),
            "similarities": sims.astype(np.float32),
            "n_available":  n,
        }

        if device is not None:
            return {
                k_: torch.as_tensor(v, device=device) if isinstance(v, np.ndarray) else v
                for k_, v in result.items()
            }
        return result

    def _empty_result(self, k: int, device) -> dict:
        empty = {
            "embeddings":   np.zeros((k, 1), dtype=np.float32),
            "regimes":      np.zeros(k, dtype=np.int64),
            "actions":      np.zeros((k, 4), dtype=np.float32),
            "outcomes":     np.zeros(k, dtype=np.float32),
            "confidences":  np.zeros(k, dtype=np.float32),
            "timestamps":   np.zeros(k, dtype=np.int64),
            "similarities": np.zeros(k, dtype=np.float32),
            "n_available":  0,
        }
        if device is not None:
            return {k_: torch.as_tensor(v, device=device) if isinstance(v, np.ndarray) else v
                    for k_, v in empty.items()}
        return empty

    # ── diagnostics ──────────────────────────────────────────────────────────

    def __len__(self) -> int:
        return len(self._buffer)

    def win_rate(self) -> float:
        if not self._buffer:
            return 0.0
        return float(sum(e["outcome"] > 0 for e in self._buffer) / len(self._buffer))

    def avg_outcome_by_regime(self) -> dict[int, float]:
        sums:   dict[int, float] = {0: 0.0, 1: 0.0, 2: 0.0}
        counts: dict[int, int]   = {0: 0,   1: 0,   2: 0}
        for e in self._buffer:
            r = e["regime"]
            sums[r]   += e["outcome"]
            counts[r] += 1
        return {
            r: sums[r] / counts[r] if counts[r] > 0 else 0.0
            for r in (0, 1, 2)
        }

    def summary(self) -> str:
        n   = len(self)
        wr  = self.win_rate()
        avg = self.avg_outcome_by_regime()
        return (
            f"KnowledgeMemory: {n}/{self._capacity} trades stored  "
            f"win_rate={wr:.1%}  "
            f"avg_by_regime=[BULL={avg[0]:+.3f}, BEAR={avg[1]:+.3f}, RANGE={avg[2]:+.3f}]"
        )
