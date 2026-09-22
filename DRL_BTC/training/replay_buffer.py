"""
Prioritized Experience Replay (PER) buffer — Schaul et al. 2015.

Uses a SumTree for O(log n) priority-weighted sampling.  New transitions start
at max_priority so every transition is sampled at least once.  After each
gradient step, call update_priorities() with the per-sample |TD error| so the
tree stays up to date.

Importance-sampling weights (to correct for the sampling bias) are returned
with each batch and should be used to scale the critic loss.  Beta is annealed
from BETA_START (0.4) to 1.0 over BETA_STEPS to reduce the bias correction
pressure early in training when estimates are noisy.

PER hyperparams (based on original paper):
  ALPHA      = 0.6   priority exponent (0 = uniform, 1 = fully greedy)
  BETA_START = 0.4   IS-weight exponent at the start of training
  BETA_STEPS = 500K  steps over which beta is annealed to 1.0
  EPSILON    = 1e-6  added to |TD error| to prevent zero priority
"""

import numpy as np
import torch


class SumTree:
    """
    Binary sum tree (1-indexed) with capacity C leaves.
    Tree size: 2C+1 nodes (indices 1..2C; index 0 unused).
      root  → index 1
      leaf i → index C + i   (i in [0, C-1])
      children of idx: 2*idx  and  2*idx+1
    """

    def __init__(self, capacity: int):
        self._cap  = capacity
        self._tree = np.zeros(2 * capacity + 1, dtype=np.float64)
        self._ptr  = 0
        self._n    = 0

    def _propagate_up(self, idx: int):
        while idx > 1:
            idx //= 2
            self._tree[idx] = self._tree[2 * idx] + self._tree[2 * idx + 1]

    def set(self, buf_idx: int, priority: float):
        """Overwrite a leaf and propagate up."""
        tree_idx = self._cap + buf_idx
        self._tree[tree_idx] = priority
        self._propagate_up(tree_idx)

    def add(self, priority: float) -> int:
        """Write new leaf at current write pointer; return the buffer index."""
        buf_idx   = self._ptr
        self.set(buf_idx, priority)
        self._ptr = (self._ptr + 1) % self._cap
        self._n   = min(self._n + 1, self._cap)
        return buf_idx

    def sample_one(self, value: float):
        """
        Traverse tree to the leaf whose cumulative sum covers `value`.
        Returns (buf_idx, priority).
        """
        idx = 1
        while idx < self._cap:          # stop when we reach a leaf
            left = 2 * idx
            if value <= self._tree[left]:
                idx = left
            else:
                value -= self._tree[left]
                idx    = 2 * idx + 1
        buf_idx = idx - self._cap
        return buf_idx, float(self._tree[idx])

    @property
    def total(self) -> float:
        return float(self._tree[1])

    @property
    def size(self) -> int:
        return self._n


class ReplayBuffer:
    """
    Prioritized Experience Replay buffer.

    Parameters
    ----------
    capacity   : max transitions stored (ring buffer)
    obs_shape  : e.g. (48, 180)
    action_dim : 5
    device     : torch device for returned tensors

    Sample returns
    --------------
    obs, acts, rews, nxt_obs, dones : float32 tensors  (batch, ...)
    weights                          : float32 tensor   (batch,)  IS correction
    indices                          : int64 ndarray    (batch,)  for update_priorities()
    """

    ALPHA      = 0.6
    BETA_START = 0.4
    BETA_STEPS = 500_000
    EPSILON    = 1e-6

    def __init__(
        self,
        capacity:   int,
        obs_shape:  tuple,
        action_dim: int,
        device:     torch.device,
    ):
        self._tree      = SumTree(capacity)
        self._cap       = capacity
        self._device    = device
        self._max_p     = 1.0    # running max priority for new transitions
        self._beta_step = 0

        self._obs     = np.zeros((capacity, *obs_shape), dtype=np.float32)
        self._nxt_obs = np.zeros((capacity, *obs_shape), dtype=np.float32)
        self._acts    = np.zeros((capacity, action_dim),  dtype=np.float32)
        self._rews    = np.zeros((capacity, 1),           dtype=np.float32)
        self._dones   = np.zeros((capacity, 1),           dtype=np.float32)

    def add(self, obs, action, reward, next_obs, done):
        buf_idx = self._tree.add(self._max_p ** self.ALPHA)
        self._obs[buf_idx]     = obs
        self._nxt_obs[buf_idx] = next_obs
        self._acts[buf_idx]    = action
        self._rews[buf_idx]    = reward
        self._dones[buf_idx]   = float(done)

    def sample(self, batch_size: int):
        total   = self._tree.total
        segment = total / batch_size

        buf_indices = np.empty(batch_size, dtype=np.int64)
        priorities  = np.empty(batch_size, dtype=np.float64)

        for i in range(batch_size):
            a     = segment * i
            b     = segment * (i + 1)
            value = np.random.uniform(a, b)
            idx, p = self._tree.sample_one(np.clip(value, 0.0, total * (1 - 1e-10)))
            buf_indices[i] = idx
            priorities[i]  = max(p, self.EPSILON)

        # Anneal beta 0.4 → 1.0
        beta = min(1.0, self.BETA_START + self._beta_step * (1.0 - self.BETA_START) / self.BETA_STEPS)
        self._beta_step += 1

        n      = self._tree.size
        probs  = priorities / total
        w      = (n * probs) ** (-beta)
        w     /= w.max()   # normalise so max weight = 1

        def _t(x):
            return torch.as_tensor(x[buf_indices], dtype=torch.float32, device=self._device)

        weights_t = torch.as_tensor(w.astype(np.float32), device=self._device)
        return _t(self._obs), _t(self._acts), _t(self._rews), _t(self._nxt_obs), _t(self._dones), weights_t, buf_indices

    def update_priorities(self, buf_indices: np.ndarray, td_errors: np.ndarray):
        """Update leaf priorities after each gradient step."""
        priorities = (np.abs(td_errors) + self.EPSILON) ** self.ALPHA
        for idx, p in zip(buf_indices, priorities):
            self._tree.set(int(idx), float(p))
            self._max_p = max(self._max_p, float(p))

    def __len__(self):
        return self._tree.size
