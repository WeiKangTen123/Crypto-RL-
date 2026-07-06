class RiskManager:
    """
    Binance Cross-Margin Futures position sizing.

    risk_per_trade        : Margin per trade as % of available balance (e.g. 0.10 = 10%)
                            Defaults to frequency-based (50% HFT, 30% intraday, 15% swing, 5% position)
    leverage              : Notional = margin * leverage
    trading_fee           : Taker fee rate per side — Binance perp default 0.0005 (0.05%)
    slippage_pct          : DEPRECATED — use CostCalculator.calculate_slippage() for square-root model
    maintenance_margin_rate: Minimum margin ratio before liquidation (Binance BTC default 0.005 = 0.5%)

    Note: The engine uses cross-margin liquidation (full account balance as collateral).

    Frequency-based defaults (SignalHive standard):
      - HFT (≤15m)    : risk_per_trade = 0.50 (50%)
      - Intraday (30m): risk_per_trade = 0.30 (30%)
      - Swing (1h–4h) : risk_per_trade = 0.15 (15%)
      - Position (1d+): risk_per_trade = 0.05 (5%)
    """

    # Frequency → risk_per_trade mapping (SignalHive standard)
    FREQUENCY_DEFAULTS = {
        '5m':  0.50,    # HFT
        '15m': 0.50,    # HFT
        '30m': 0.30,    # Intraday
        '1h':  0.15,    # Swing
        '4h':  0.15,    # Swing
        '1d':  0.05,    # Position
        '1D':  0.05,    # Position (uppercase variant)
    }

    def __init__(self,
                 risk_per_trade=None,
                 leverage=1,
                 trading_fee=0.0004,  # Taker 4 bps (SignalHive standard)
                 slippage_pct=0.0,     # DEPRECATED — use CostCalculator instead
                 maintenance_margin_rate=0.005,
                 frequency=None):
        """
        Args:
            risk_per_trade: Explicit risk (if None, uses frequency default)
            leverage: Position leverage
            trading_fee: Taker fee fraction (SignalHive: 4 bps = 0.0004)
            slippage_pct: DEPRECATED (kept for backward compat, now 0)
            maintenance_margin_rate: Binance liquidation threshold
            frequency: Bar frequency (5m, 15m, 30m, 1h, 4h, 1d) for auto-defaults
        """
        if risk_per_trade is None and frequency:
            self.risk_per_trade = self.FREQUENCY_DEFAULTS.get(frequency, 0.15)
        else:
            self.risk_per_trade = risk_per_trade if risk_per_trade is not None else 0.15

        self.leverage = leverage
        self.trading_fee = trading_fee
        self.slippage_pct = 0.0  # DEPRECATED — CostCalculator.calculate_slippage() is the new way
        self.maintenance_margin_rate = maintenance_margin_rate
        self.frequency = frequency

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
