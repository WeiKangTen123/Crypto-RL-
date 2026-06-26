class RiskManager:
    """
    Binance Cross-Margin Futures position sizing.

    risk_per_trade        : Margin per trade as % of available balance (e.g. 0.10 = 10%)
    leverage              : Notional = margin * leverage
    trading_fee           : Taker fee rate per side — Binance perp default 0.0005 (0.05%)
    slippage_pct          : Market impact + spread per side — 0.0005 (0.05%) for BTC/ETH perps
    maintenance_margin_rate: Minimum margin ratio before liquidation (Binance BTC default 0.005 = 0.5%)

    Note: The engine uses cross-margin liquidation (full account balance as collateral).
    """
    def __init__(self,
                 risk_per_trade=0.10,
                 leverage=1,
                 trading_fee=0.0005,
                 slippage_pct=0.0005,
                 maintenance_margin_rate=0.005):
        self.risk_per_trade = risk_per_trade
        self.leverage = leverage
        self.trading_fee = trading_fee
        self.slippage_pct = slippage_pct
        self.maintenance_margin_rate = maintenance_margin_rate

    def calculate_position(self, balance, price):
        """
        Returns (margin, notional, quantity).
          margin   = collateral locked from balance
          notional = margin * leverage  (position value)
          quantity = notional / price   (units of asset)
        """
        margin = balance * self.risk_per_trade
        notional = margin * self.leverage
        quantity = notional / price
        return margin, notional, quantity

    def position_size(self, balance, price, stop_loss_pct=None):
        """Convenience wrapper — returns quantity only. stop_loss_pct unused."""
        _, _, quantity = self.calculate_position(balance, price)
        return quantity

    def liquidation_price(self, entry_price, side, qty, account_balance):
        """
        Cross-margin liquidation price for a single-position account (Binance formula).

        Derived from: account_balance + qty*(liq - entry)*side == qty*liq*mm
          Long : liq = (account_balance - qty*entry) / (qty*(mm - 1))
          Short: liq = (account_balance + qty*entry) / (qty*(mm + 1))

        This matches the inline liquidation check in BacktestEngine.
        """
        mm = self.maintenance_margin_rate
        if side > 0:
            denom = qty * (mm - 1)
            return (account_balance - qty * entry_price) / denom if denom != 0 else 0.0
        else:
            denom = qty * (mm + 1)
            return (account_balance + qty * entry_price) / denom if denom != 0 else 0.0
