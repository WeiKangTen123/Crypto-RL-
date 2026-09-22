import numpy as np
import pandas as pd

def calculate_trade_params(features: pd.DataFrame, bar_idx: int, direction: int, current_price: float, true_confidence: float) -> dict:
    """
    Computes trade parameters based on a provided true confidence score
    and dynamically sizes the trade (margin & leverage).
    Uses parameters optimized for highest ROI based on grid search.
    """
    true_confidence = min(1.0, true_confidence)
    
    # Based on our 5-YEAR backtest ROI optimization:
    # Best global ROI achieved at conf >= 0.70, 50k margin, 3.0x leverage, 6% TP, 3% SL.
    
    if true_confidence >= 0.70:
        margin = 50000.0
        leverage = 3.0
        tp_pct = 0.06
        sl_pct = 0.03
    else:
        margin = 5000.0
        leverage = 1.0
        tp_pct = 0.02
        sl_pct = 0.01
    
    take_profit = None
    stop_loss = None
    
    if direction == 1:
        take_profit = current_price * (1 + tp_pct)
        stop_loss = current_price * (1 - sl_pct)
    elif direction == -1:
        take_profit = current_price * (1 - tp_pct)
        stop_loss = current_price * (1 + sl_pct)
        
    return {
        "confidence": true_confidence,
        "margin": margin,
        "leverage": leverage,
        "take_profit_price": take_profit,
        "stop_loss_price": stop_loss
    }
