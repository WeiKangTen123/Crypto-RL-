import sys
from pathlib import Path
ROOT = Path(__file__).parent.parent.parent
sys.path.insert(0, str(ROOT))

import numpy as np
from DRL_BTC.config import ACTION_DIM
from DRL_BTC.features.feature_builder import load_features
from DRL_BTC.env.btc_env import BTCEnv, N_PORTFOLIO_FEATS
from DRL_BTC.training.sac_agent import SACAgent
from DRL_BTC.utils import select_device

def count_trades(mode="test"):
    device = select_device()
    feats, close = load_features()
    feats = feats.fillna(0.0)
    
    env = BTCEnv(feats, close, mode=mode)
    agent = SACAgent(list(feats.columns), N_PORTFOLIO_FEATS, ACTION_DIM, device)
    agent.load("best_s42")
    
    obs, _ = env.reset()
    done = False
    
    trades = 0
    prev_pos = 0
    
    while not done:
        action = agent.select_action(obs, deterministic=True)
        obs, _, terminated, truncated, info = env.step(action)
        pos = info["position"]
        if pos != prev_pos and pos != 0:
            trades += 1
        prev_pos = pos
        done = terminated or truncated
        
    print(f"[{mode.upper()}] Total Trades: {trades}")

if __name__ == "__main__":
    count_trades("train")
    count_trades("val")
    count_trades("test")
