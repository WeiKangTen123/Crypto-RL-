"""
Soft Actor-Critic (SAC) with automatic temperature tuning — TIA v3 / v3.1.

Key differences from vanilla SAC:
 • LSTM encoder — obs is (batch, seq_len, n_features), not flat
 • 4D continuous action with tanh squashing already handled in Actor
 • Alpha frozen at ALPHA_FIXED (auto-tuning disabled — prevents entropy collapse)
 • Gradient clipping for stability with LSTM
 • CPU inference copy — actor runs on CPU for batch=1 env steps (avoids CUDA
   launch overhead), GPU reserved for large-batch training updates only.
   CPU copy syncs from GPU actor every CPU_SYNC_EVERY policy updates.

TIA v3 / v3.1 additions:
 • KnowledgeMemory — ring buffer of closed-trade embeddings; populated via
   store_trade(); now WIRED INTO the live decision path via Actor.forward().
   - At inference (batch=1): actor retrieves real memory_feat via KM.retrieve_feat()
   - At batch training: sac_agent computes memory_feat_batch via KM.retrieve_feat_batch()
     and passes it explicitly to actor/critic forward calls.
 • DriftManager — ACTIVE: get_beta_temperature() calibrates beta probs;
   get_memory_k() gates memory retrieval; drift alerts NORMAL/WARNING/BLOCK.
"""

import copy
import torch
import torch.nn as nn
import torch.nn.functional as F
import torch.optim as optim
import numpy as np
from pathlib import Path

from DRL_BTC.config import (
    LR_ACTOR, LR_CRITIC, LR_ALPHA,
    GAMMA, TAU, TARGET_ENTROPY, ALPHA_FIXED, GRAD_CLIP,
    BATCH_SIZE, BUFFER_SIZE, SEQ_LEN, CKPT_DIR,
    G_STEPS, WEIGHT_DECAY,
    KNOWLEDGE_MEMORY_SIZE, KNOWLEDGE_MEMORY_K,
)
from DRL_BTC.models.actor_critic import make_networks
from DRL_BTC.models.knowledge_memory import KnowledgeMemory
from DRL_BTC.models.diagnostics import DriftManager
from DRL_BTC.training.replay_buffer import ReplayBuffer


class SACAgent:
    def __init__(
        self,
        market_cols:  list[str],
        n_portfolio:  int,
        action_dim:   int,
        device:       torch.device,
    ):
        self.device      = device
        self.market_cols = market_cols
        self.n_portfolio = n_portfolio
        n_features       = len(market_cols) + n_portfolio
        obs_shape        = (SEQ_LEN, n_features)

        actor, critic, critic_tgt = make_networks(market_cols, n_portfolio, device)

        # Actor is NOT compiled: it is called in both grad and no_grad contexts inside
        # update(), which causes torch.compile to hit the recompile limit and fall back
        # to eager anyway. Critics are compiled — they are always called under the same
        # grad context and benefit cleanly from aot_eager.
        self.actor = actor
        if device.type in ("cuda", "mps"):
            self.critic     = torch.compile(critic,     backend="aot_eager")
            self.critic_tgt = torch.compile(critic_tgt, backend="aot_eager")
        else:
            self.critic, self.critic_tgt = critic, critic_tgt

        # TIA v2: L2 weight decay regularises encoder + heads to improve OOS generalisation
        self.actor_opt  = optim.Adam(self.actor.parameters(),  lr=LR_ACTOR,  weight_decay=WEIGHT_DECAY)
        self.critic_opt = optim.Adam(self.critic.parameters(), lr=LR_CRITIC, weight_decay=WEIGHT_DECAY)

        # Alpha fixed at ALPHA_FIXED — auto-tuning disabled (LR_ALPHA=0 → optimizer is no-op).
        # Avoids the collapse where logπ=-3.4 < TARGET_ENTROPY=-2.5 causes alpha→0 indefinitely.
        self.log_alpha  = torch.tensor(np.log(ALPHA_FIXED), requires_grad=True, device=device, dtype=torch.float32)
        self.alpha_opt  = optim.Adam([self.log_alpha], lr=LR_ALPHA)  # lr=0 → frozen
        self.target_ent = torch.tensor(TARGET_ENTROPY, device=device)

        self.buffer = ReplayBuffer(
            capacity=BUFFER_SIZE,
            obs_shape=obs_shape,
            action_dim=action_dim,
            device=device,
        )

        # TIA v3: KnowledgeMemory — populated per closed trade via store_trade()
        self.knowledge_memory = KnowledgeMemory(
            capacity=KNOWLEDGE_MEMORY_SIZE,
            k=KNOWLEDGE_MEMORY_K,
        )

        # TIA v3 / v3.1: DriftManager + wire references onto actor
        _actor_mod = getattr(self.actor, "_orig_mod", self.actor)
        self.drift_manager = DriftManager(_actor_mod.diagnostics)
        # Actor reads _drift_manager for get_beta_temperature() at every forward()
        _actor_mod._drift_manager    = self.drift_manager
        # Actor reads _knowledge_memory for single-sample inference retrieval
        _actor_mod._knowledge_memory = self.knowledge_memory

        # Mixed-precision scaler — only on CUDA (T4 Tensor Cores give ~2× speedup)
        self._scaler = torch.amp.GradScaler("cuda") if device.type == "cuda" else None

        self._update_count  = 0
        self._actor_cpu     = None   # CPU inference copy, built lazily on first select_action
        self._cpu_sync_step = 0
        self.CPU_SYNC_EVERY = 20     # re-sync CPU actor every N policy updates

    @property
    def alpha(self) -> torch.Tensor:
        return self.log_alpha.exp()

    @property
    def last_actor_info(self) -> dict:
        """Scalars stashed by Actor.forward() on the most recent CPU inference call."""
        if self._actor_cpu is not None and hasattr(self._actor_cpu, "_last_actor_info"):
            return self._actor_cpu._last_actor_info
        return {}

    # ── CPU inference copy ─────────────────────────────────────────────────────

    def _sync_actor_cpu(self) -> None:
        """
        Build (or update) a CPU copy of the actor for single-sample inference.

        Why CPU for batch=1?
          GPU CUDA launch overhead is ~2-4 ms regardless of batch size.
          For batch=1 the actual compute is <0.1 ms — overhead dominates.
          Running on CPU eliminates all transfer + launch costs and frees
          the GPU exclusively for large-batch training updates (batch=512).

        Diagnostics isolation:
          The GPU actor's diagnostics are calibrated to replay-buffer z-vectors
          (mixed from all past episodes). The CPU actor's diagnostics must be
          calibrated to INFERENCE z-vectors (current episode, current encoder).
          These differ enough to cause spurious OOD BLOCK if the GPU stats are
          copied across. Fix: save and restore CPU diagnostics through every sync
          so they accumulate purely from inference — never overwritten by GPU stats.
        """
        src = getattr(self.actor, "_orig_mod", self.actor)   # unwrap torch.compile
        if self._actor_cpu is None:
            self._actor_cpu = copy.deepcopy(src).cpu().eval()
            # Reset CPU diagnostics so they build from inference z only (not GPU init values)
            self._actor_cpu.diagnostics.running_mean.zero_()
            self._actor_cpu.diagnostics.running_std.fill_(1.0)
            self._actor_cpu.diagnostics.n_updates.zero_()
        else:
            # Preserve CPU diagnostics (inference-z calibrated) before overwrite.
            # GPU diagnostics are replay-buffer calibrated and corrupt inference OOD
            # if copied across — especially after val-checkpoint resets on the GPU side.
            saved_diag = {k: v.clone() for k, v in
                          self._actor_cpu.diagnostics.state_dict().items()}
            self._actor_cpu.load_state_dict(src.state_dict())
            self._actor_cpu.eval()
            self._actor_cpu.diagnostics.load_state_dict(saved_diag)
        # Share references with CPU copy so inference benefits from live KM + DriftManager
        self._actor_cpu._knowledge_memory = self.knowledge_memory
        self._actor_cpu._drift_manager    = self.drift_manager

    # ── data collection ────────────────────────────────────────────────────────

    def select_action(self, obs: np.ndarray, deterministic: bool = False) -> np.ndarray:
        """
        Batch=1 inference on CPU.  Zero GPU involvement → GPU reserved for
        training updates only.  CPU copy is synced from GPU every
        CPU_SYNC_EVERY policy updates (≈ every 20 trades).

        OOD diagnostics are recalibrated inside Actor.forward() (B=1, eval mode)
        so no explicit encoder call is needed here.
        """
        if self._actor_cpu is None:
            self._sync_actor_cpu()
        obs_t = torch.as_tensor(obs, dtype=torch.float32).unsqueeze(0)   # CPU tensor
        with torch.no_grad():
            action = self._actor_cpu.act(obs_t, deterministic=deterministic)
        return action.numpy().squeeze(0)

    def store(self, obs, action, reward, next_obs, done):
        self.buffer.add(obs, action, reward, next_obs, done)

    def store_trade(
        self,
        entry_obs: np.ndarray,
        action:    np.ndarray,
        outcome:   float,
        step:      int,
        mfe:       float = 0.0,
        mae:       float = 0.0,
        hold_bars: float = 0.0,
        tp_hit:    int   = 0,
    ) -> None:
        """
        Called after each trade closes. Encodes entry_obs via the CPU actor copy
        (batch=1, no GPU round-trip), extracts regime + alpha_confidence, then
        stores in KnowledgeMemory and records in DriftManager.

        Parameters
        ──────────
        entry_obs : raw observation at trade entry  (SEQ_LEN, n_features)
        action    : decoded action at entry  [pos_size, sl_atr, tp_atr, trail]
        outcome   : total realised trade PnL fraction  (e.g. +0.03 = +3%)
        step      : global training step (for temporal ordering in memory)
        mfe       : max favorable excursion fraction (from env info)
        mae       : max adverse excursion fraction (from env info)
        hold_bars : bars held (from env info)
        tp_hit    : 1 if TP triggered, 0 otherwise (from env info)
        """
        if self._actor_cpu is None:
            self._sync_actor_cpu()

        obs_t = torch.as_tensor(entry_obs, dtype=torch.float32).unsqueeze(0)  # (1, SEQ_LEN, n_feat) — CPU
        with torch.no_grad():
            z         = self._actor_cpu.encoder(obs_t)      # (1, z_dim)
            beta_out  = self._actor_cpu.beta(z)
            alpha_out = self._actor_cpu.alpha(z)

        regime     = int(beta_out["regime_logits"].argmax(dim=-1).item())
        confidence = float(alpha_out["alpha_confidence"].item())

        self.knowledge_memory.store(
            z=z.squeeze(0),
            regime=regime,
            action=action,
            outcome=outcome,
            confidence=confidence,
            mfe=mfe,
            mae=mae,
            hold_bars=hold_bars,
            tp_hit=tp_hit,
            timestamp=step,
        )
        self.drift_manager.record_trade(outcome, confidence, regime)

    def set_drift_baseline(self) -> None:
        """
        Set DriftManager baseline from current KnowledgeMemory contents.
        Call once after warmup (before RL begins) so drift is measured
        relative to the warmup distribution, not from zero.
        """
        n = len(self.knowledge_memory)
        if n == 0:
            return
        wr  = self.knowledge_memory.win_rate()
        avg = float(sum(e["outcome"] for e in self.knowledge_memory._buffer) / n)
        self.drift_manager.set_baseline(win_rate=wr, avg_return=avg)
        print(f"[DriftManager] Baseline set from {n} warmup trades: "
              f"win_rate={wr:.1%}  avg_return={avg:+.4f}")

    def km_summary(self) -> str:
        """One-line KnowledgeMemory status for logging."""
        return self.knowledge_memory.summary()

    def drift_status(self) -> str:
        """One-line DriftManager status for logging."""
        return self.drift_manager.summary()

    # ── update ─────────────────────────────────────────────────────────────────

    def update(self) -> dict:
        if len(self.buffer) < BATCH_SIZE:
            return {}

        use_amp = self._scaler is not None
        amp_ctx = lambda: torch.autocast("cuda", dtype=torch.float16, enabled=use_amp)  # noqa: E731

        obs, acts, rews, nxt_obs, dones, weights, buf_indices = self.buffer.sample(BATCH_SIZE)

        # ── Memory feat for this batch (v3.1) ──────────────────────────────────
        # Vectorised KM retrieval: one matrix multiply over all B samples.
        # Only meaningful when KM has enough trades; falls back to zeros otherwise.
        mem_feat_batch     = None
        mem_feat_nxt_batch = None
        if len(self.knowledge_memory) >= 20:
            actor_mod = getattr(self.actor, "_orig_mod", self.actor)
            try:
                with torch.no_grad():
                    z_batch     = actor_mod.encoder(obs)
                    z_nxt_batch = actor_mod.encoder(nxt_obs)
                    # Synchronize before CPU transfer to surface any async CUDA errors early
                    # rather than blocking indefinitely in .cpu()
                    if torch.cuda.is_available():
                        torch.cuda.synchronize()
                    ood_batch   = actor_mod.diagnostics(z_batch).cpu().numpy().astype("float32")
                    ood_nxt     = actor_mod.diagnostics(z_nxt_batch).cpu().numpy().astype("float32")
                    reg_batch   = actor_mod.beta(z_batch)["regime_logits"].argmax(-1).cpu().numpy().astype("int32")
                    reg_nxt     = actor_mod.beta(z_nxt_batch)["regime_logits"].argmax(-1).cpu().numpy().astype("int32")
                z_np     = z_batch.cpu().numpy().astype("float32")
                z_nxt_np = z_nxt_batch.cpu().numpy().astype("float32")
                mem_feat_batch     = self.knowledge_memory.retrieve_feat_batch(
                    z_np, ood_batch, reg_batch, device=self.device)
                mem_feat_nxt_batch = self.knowledge_memory.retrieve_feat_batch(
                    z_nxt_np, ood_nxt, reg_nxt, device=self.device)
            except RuntimeError as _km_err:
                # CUDA error in KM encoder pass — skip memory retrieval this update
                import logging as _lg
                _lg.getLogger("train_s42").warning(
                    f"KM encoder forward failed ({_km_err}); skipping memory retrieval this update."
                )
                mem_feat_batch     = None
                mem_feat_nxt_batch = None

        # ── Critic update (PER-weighted) ───────────────────────────────────────
        with torch.no_grad(), amp_ctx():
            nxt_acts, nxt_log_pi, _ = self.actor(nxt_obs, memory_feat=mem_feat_nxt_batch)
            q1_tgt, q2_tgt = self.critic_tgt(nxt_obs, nxt_acts)
            q_tgt    = torch.min(q1_tgt, q2_tgt) - self.alpha * nxt_log_pi
            q_backup = (rews + GAMMA * (1.0 - dones) * q_tgt).to(torch.float32)

        with amp_ctx():
            q1, q2 = self.critic(obs, acts)
            # Weighted MSE: high-priority transitions get larger gradient
            td1 = F.mse_loss(q1.float(), q_backup, reduction="none")
            td2 = F.mse_loss(q2.float(), q_backup, reduction="none")
            critic_loss = (weights.unsqueeze(1) * (td1 + td2)).mean()

            # Per-sample TD error for priority update (detached, on CPU)
            with torch.no_grad():
                td_errors = (0.5 * (q1.float() + q2.float()) - q_backup).abs().squeeze(1).cpu().numpy()

        self.critic_opt.zero_grad()
        if use_amp:
            self._scaler.scale(critic_loss).backward()
            self._scaler.unscale_(self.critic_opt)
            nn.utils.clip_grad_norm_(self.critic.parameters(), GRAD_CLIP)
            self._scaler.step(self.critic_opt)
        else:
            critic_loss.backward()
            nn.utils.clip_grad_norm_(self.critic.parameters(), GRAD_CLIP)
            self.critic_opt.step()

        # Update replay priorities with fresh TD errors
        self.buffer.update_priorities(buf_indices, td_errors)

        # ── Actor update ───────────────────────────────────────────────────────
        # Direction is now rule-based in the env — no detach needed.
        # SAC freely trains all 5 output dims; Q becomes insensitive to action[0]
        # because it doesn't affect env behaviour, so the gradient on dim[0] → 0.
        with amp_ctx():
            new_acts, log_pi, _ = self.actor(obs, memory_feat=mem_feat_batch)
            q1_pi, q2_pi = self.critic(obs, new_acts)
            q_pi       = torch.min(q1_pi, q2_pi)
            actor_loss = (self.alpha.detach() * log_pi.float() - q_pi.float()).mean()

        self.actor_opt.zero_grad()
        if use_amp:
            self._scaler.scale(actor_loss).backward()
            self._scaler.unscale_(self.actor_opt)
            nn.utils.clip_grad_norm_(self.actor.parameters(), GRAD_CLIP)
            self._scaler.step(self.actor_opt)
        else:
            actor_loss.backward()
            nn.utils.clip_grad_norm_(self.actor.parameters(), GRAD_CLIP)
            self.actor_opt.step()

        # ── Alpha update ───────────────────────────────────────────────────────
        alpha_loss = -(self.log_alpha * (log_pi.detach().float() + self.target_ent)).mean()

        self.alpha_opt.zero_grad()
        if use_amp:
            self._scaler.scale(alpha_loss).backward()
            self._scaler.step(self.alpha_opt)
            self._scaler.update()
        else:
            alpha_loss.backward()
            self.alpha_opt.step()

        # ── Soft-update target ─────────────────────────────────────────────────
        for p_tgt, p in zip(self.critic_tgt.parameters(), self.critic.parameters()):
            p_tgt.data.mul_(1 - TAU).add_(TAU * p.data)

        self._update_count += 1

        # ── Update OOD diagnostics + DriftManager from current batch (TIA v3) ──
        # If memory retrieval already computed z_batch above, reuse it.
        # Otherwise encode fresh every 10 cycles to keep cost low.
        if self._update_count % 10 == 0:
            actor_mod = getattr(self.actor, "_orig_mod", self.actor)
            if mem_feat_batch is not None:
                # z_batch and ood_batch already computed in memory block above
                with torch.no_grad():
                    actor_mod.diagnostics.update(z_batch)
                    ood_val = float(actor_mod.diagnostics(z_batch).mean().item())
            else:
                with torch.no_grad():
                    z_batch = actor_mod.encoder(obs)
                    actor_mod.diagnostics.update(z_batch)
                    ood_val = float(actor_mod.diagnostics(z_batch).mean().item())
            self.drift_manager.record_ood(ood_val)

        # ── Sync CPU inference copy periodically ───────────────────────────────
        # Keep lag small (≤20 policy updates) so env rollout uses a fresh policy.
        self._cpu_sync_step += 1
        if self._cpu_sync_step >= self.CPU_SYNC_EVERY:
            self._sync_actor_cpu()
            self._cpu_sync_step = 0

        return {
            "critic_loss": critic_loss.item(),
            "actor_loss":  actor_loss.item(),
            "alpha_loss":  alpha_loss.item(),
            "alpha":       self.alpha.item(),
            "log_pi_mean": log_pi.float().mean().item(),
        }

    # ── checkpointing ──────────────────────────────────────────────────────────

    def _sd(self, model) -> dict:
        """Return state_dict from the underlying module (works with torch.compile)."""
        m = getattr(model, "_orig_mod", model)
        return m.state_dict()

    def _load_sd(self, m: nn.Module, state_dict: dict):
        # strict=False: silently skip mismatched / missing keys.
        # This handles loading old Session 7/8 checkpoints into the TIA v2 architecture
        # (new head keys like stability_head, sl_head, diagnostics buffers will
        # keep their random / zero initialisation from __init__).
        m.load_state_dict(state_dict, strict=False)

    def save(self, tag: str = "latest", train_state: dict = None):
        """
        Save full checkpoint.  train_state dict (step, ep_num, best_val_eq)
        is embedded so the training loop can resume from the exact position.
        """
        CKPT_DIR.mkdir(parents=True, exist_ok=True)
        path = CKPT_DIR / f"sac_{tag}.pt"
        data = {
            "actor":        self._sd(self.actor),
            "critic":       self._sd(self.critic),
            "critic_tgt":   self._sd(self.critic_tgt),
            "log_alpha":    self.log_alpha.detach().cpu(),
            # Optimizer states preserve Adam momentum — critical for proper resume
            "actor_opt":    self.actor_opt.state_dict(),
            "critic_opt":   self.critic_opt.state_dict(),
            "alpha_opt":    self.alpha_opt.state_dict(),
            "update_count": self._update_count,
        }
        if train_state is not None:
            data["train_state"] = train_state
        torch.save(data, path)
        print(f"[SAC] Saved → {path}")

    def load(self, tag: str = "latest") -> dict:
        """
        Load checkpoint.  Returns the embedded train_state dict (step, ep_num,
        best_val_eq) so the training loop can resume — or {} for old checkpoints.
        """
        path = CKPT_DIR / f"sac_{tag}.pt"
        if not path.exists():
            raise FileNotFoundError(f"Checkpoint not found: {path}\n"
                                    f"Available: {[f.stem for f in CKPT_DIR.glob('sac_*.pt')]}")
        # weights_only=False needed because optimizer state dicts contain Python scalars
        ckpt = torch.load(path, map_location=self.device, weights_only=False)
        self._load_sd(self.actor,      ckpt["actor"])
        self._load_sd(self.critic,     ckpt["critic"])
        self._load_sd(self.critic_tgt, ckpt["critic_tgt"])
        self.log_alpha.data = ckpt["log_alpha"].to(self.device)
        self._update_count  = ckpt.get("update_count", 0)
        # Restore Adam momentum if present (missing in old checkpoints — silently skipped)
        for attr, key in [
            ("actor_opt", "actor_opt"),
            ("critic_opt", "critic_opt"),
            ("alpha_opt", "alpha_opt")
        ]:
            if hasattr(self, attr) and getattr(self, attr) is not None and key in ckpt:
                try:
                    getattr(self, attr).load_state_dict(ckpt[key])
                except Exception as e:
                    print(f"Skipping optimizer {attr} load: {e}")
        self._sync_actor_cpu()   # build CPU inference copy immediately after load
        print(f"[SAC] Loaded ← {path}")
        return ckpt.get("train_state", {})
