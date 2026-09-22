import pandas as pd
import numpy as np
from typing import Optional, Tuple
import ta

from strategy_backtest.base_strategy import BaseStrategy

class EMAStreakStrategy(BaseStrategy):
    """
    EMA Streak 1H - Abacussa
    Streaming EMA fast/slow crossover entries with streak protection
    and safety pin ratchet stops.
    """

    VALID_ACTIONS: frozenset = frozenset({'SL', 'TP', 'REVERSE', 'EXIT', 'HOLD', 'SKIP'})

    SIGNAL_PARAMS: frozenset = frozenset({
        'fast', 'slow', 'streakWin', 'momentumPct', 'useStreak',
        'stopLossPct', 'leverage_param', 'riskPerTrade',
        'useTP', 'takeProfitPct', 'safetyPinPct', 'safetyPinLockPct'
    })

    def __init__(self, df: pd.DataFrame,
                 fast: int = 15,
                 slow: int = 83,
                 streakWin: int = 60,
                 momentumPct: float = 0.14,
                 useStreak: bool = True,
                 stopLossPct: float = 0.02,
                 leverage_param: int = 20,
                 riskPerTrade: float = 0.06,
                 useTP: bool = False,
                 takeProfitPct: float = 0.0,
                 safetyPinPct: float = 0.08,
                 safetyPinLockPct: float = 0.04,
                 **kwargs):
        super().__init__(df, **kwargs)
        self.fast = int(fast)
        self.slow = int(slow)
        self.streakWin = int(streakWin)
        self.momentumPct = float(momentumPct)
        self.useStreak = bool(useStreak)
        self.stopLossPct = float(stopLossPct)
        self.leverage_param = int(leverage_param)
        self.riskPerTrade = float(riskPerTrade)
        self.useTP = bool(useTP)
        self.takeProfitPct = float(takeProfitPct)
        self.safetyPinPct = float(safetyPinPct)
        self.safetyPinLockPct = float(safetyPinLockPct)

        denom = max(self.riskPerTrade * self.leverage_param, 1e-9)
        self.slPct = self.stopLossPct / denom
        rawLock = self.safetyPinLockPct / denom
        self.lockPct = min(rawLock, self.safetyPinPct) if self.safetyPinPct > 0 else rawLock

        # State dict for exit tracking
        self._s = {
            1:  dict(entry_price=None, cnt=0, skip=False, skipped=False, safetyPin=False),
            -1: dict(entry_price=None, cnt=0, skip=False, skipped=False, safetyPin=False),
        }

    def generate_signals(self) -> pd.DataFrame:
        df = self.df.copy()
        
        # EMA
        df['emaF'] = df['Close'].ewm(span=self.fast, adjust=False).mean()
        df['emaS'] = df['Close'].ewm(span=self.slow, adjust=False).mean()
        
        df['signal'] = 0
        
        # Crossovers
        cross_up = (df['emaF'] > df['emaS']) & (df['emaF'].shift(1) <= df['emaS'].shift(1))
        cross_down = (df['emaF'] < df['emaS']) & (df['emaF'].shift(1) >= df['emaS'].shift(1))
        
        df.loc[cross_up, 'signal'] = 1
        df.loc[cross_down, 'signal'] = -1
        
        # Wait for the slow EMA to warm up
        df.iloc[:self.slow, df.columns.get_loc('signal')] = 0
        
        self.df = df
        return self.df

    def manage_trade(self, row: pd.Series, position: float, entry_price: float, wallet: float = 0) -> Tuple[str, Optional[float]]:
        if position == 0:
            return 'HOLD', None
            
        side = int(np.sign(position))
        s = self._s[side]

        # Reset state on new trade
        if s['entry_price'] != entry_price:
            s['entry_price'] = entry_price
            s['cnt'] = 0
            s['skip'] = False
            s['skipped'] = False
            s['safetyPin'] = False

        s['cnt'] += 1
        pnlPct = (row.Close - entry_price) / entry_price * side

        # Streak detection
        if self.useStreak and s['cnt'] >= self.streakWin and not s['skip'] and not s['skipped']:
            move = (row.Close - entry_price) / entry_price
            if (side == 1 and move >= self.momentumPct) or (side == -1 and move <= -self.momentumPct):
                s['skip'] = True

        # Safety pin activation
        if self.safetyPinPct > 0 and not s['safetyPin'] and pnlPct >= self.safetyPinPct:
            s['safetyPin'] = True

        # TP Check
        if self.useTP and pnlPct >= self.takeProfitPct:
            return 'TP', row.Close

        # Reversal check
        sig = getattr(row, 'signal', 0)
        if sig != 0 and sig != side:
            if s['skip']:
                s['skip'] = False
                s['skipped'] = True
                return 'SKIP', None
            else:
                return 'REVERSE', None

        # Stop loss logic
        stopPrice = entry_price * (1.0 + side * self.lockPct) if s['safetyPin'] else entry_price * (1.0 - side * self.slPct)
        
        if side == 1 and row.Low <= stopPrice:
            return 'SL', stopPrice
        elif side == -1 and row.High >= stopPrice:
            return 'SL', stopPrice

        return 'HOLD', None
