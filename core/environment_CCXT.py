"""The CryptoEnvCCXT class is a custom environment for trading multiple cryptocurrencies using CCXT library.
This is a refactored version of environment_Alpaca.py adapted for crypto trading.

The class provides:
- Multi-cryptocurrency trading support via CCXT
- Integration with Binance data processor
- 24/7 crypto market adaptation
- Real-time order execution through CCXT
- Portfolio tracking and management
- Technical indicator integration
"""

import numpy as np
import math
import ccxt
from collections import deque
from config_main import CRYPTO_LIMITS
from config_api import API_KEY_BINANCE, API_SECRET_BINANCE


class CryptoEnvCCXT:  # custom env for crypto trading
    def __init__(self, config, env_params, initial_capital=1000000,
                 buy_cost_pct=0.001, sell_cost_pct=0.001, gamma=0.99, if_log=False,
                 exchange_name='binance'):

        self.if_log = if_log
        self.env_params = env_params
        self.lookback = env_params['lookback']
        self.initial_total_asset = initial_capital
        self.initial_cash = initial_capital
        self.buy_cost_pct = buy_cost_pct
        self.sell_cost_pct = sell_cost_pct
        self.gamma = gamma
        self.exchange_name = exchange_name

        # Initialize CCXT exchange
        try:
            if exchange_name.lower() == 'binance':
                self.exchange = ccxt.binance({
                    'apiKey': API_KEY_BINANCE,
                    'secret': API_SECRET_BINANCE,
                    'enableRateLimit': True,
                })
            else:
                # Support for other exchanges
                self.exchange = getattr(ccxt, exchange_name)({
                    'enableRateLimit': True,
                })
        except Exception as e:
            print(f"Warning: Could not initialize {exchange_name} exchange: {e}")
            print("Using sandbox mode for testing")
            self.exchange = ccxt.binance({
                'sandbox': True,
                'enableRateLimit': True,
            })

        # Get initial price array to compute eqw
        self.price_array = config['price_array']
        self.prices_initial = list(self.price_array[0, :])
        self.equal_weight_stock = np.array([self.initial_cash /
                                            len(self.prices_initial) /
                                            self.prices_initial[i] for i in
                                            range(len(self.prices_initial))])

        # read normalization of cash, stocks and tech
        self.norm_cash = env_params['norm_cash']
        self.norm_stocks = env_params['norm_stocks']
        self.norm_tech = env_params['norm_tech']
        self.norm_reward = env_params['norm_reward']
        self.norm_action = env_params['norm_action']

        # Initialize constants
        self.tech_array = config['tech_array']
        self._generate_action_normalizer()
        self.crypto_num = self.price_array.shape[1]
        self.max_step = self.price_array.shape[0] - self.lookback - 1

        # reset
        self.time = self.lookback - 1
        # Ensure we don't go out of bounds
        if self.time >= self.price_array.shape[0]:
            self.time = self.price_array.shape[0] - 1
        self.cash = self.initial_cash
        self.current_price = self.price_array[self.time]
        self.current_tech = self.tech_array[self.time]
        self.stocks = np.zeros(self.crypto_num, dtype=np.float32)
        self.stocks_cooldown = None
        self.safety_factor_stock_buy = 1 - 0.05  # 5% safety factor for crypto

        self.total_asset = self.cash + (self.stocks * self.price_array[self.time]).sum()
        self.total_asset_eqw = np.sum(self.equal_weight_stock * self.price_array[self.time])

        self.episode_return = 0.0
        self.gamma_return = 0.0
        self.step_log = []

        # Reward shaping parameters
        self.drawdown_weight      = env_params.get('drawdown_weight', 0.0)
        self.jitter_weight        = env_params.get('jitter_weight', 0.0)
        self.holding_penalty_weight = env_params.get('holding_penalty', 0.0)
        self.peak_asset   = self.initial_cash
        self.last_actions = np.zeros(self.price_array.shape[1], dtype=np.float32)
        self.recent_returns: deque = deque(maxlen=20)

        '''env information'''
        self.env_name = 'MultiCryptoEnvCCXT'

        # state_dim = cash[1,1] + stocks[1,4] + tech_array[1,44] * lookback
        self.state_dim = 1 + self.price_array.shape[1] + self.tech_array.shape[1] * self.lookback
        self.action_dim = self.price_array.shape[1]

        # Use CRYPTO_LIMITS instead of ALPACA_LIMITS
        if hasattr(CRYPTO_LIMITS, '__len__'):
            self.minimum_qty_crypto = (CRYPTO_LIMITS[:self.action_dim] * 1.1)  # 10% safety factor
        else:
            # Default minimum if not configured
            self.minimum_qty_crypto = np.ones(self.action_dim) * 0.001

        self.if_discrete = False
        self.target_return = 10**8

        # Store ticker symbols for CCXT orders
        self.ticker_list = config.get('ticker_list', [f'BTC/USDT', f'ETH/USDT'])

    def reset(self) -> np.ndarray:
        self.time = self.lookback - 1
        # Ensure we don't go out of bounds with small datasets
        if self.time >= self.price_array.shape[0]:
            self.time = min(self.lookback - 1, self.price_array.shape[0] - 1)

        self.current_price = self.price_array[self.time]
        self.current_tech = self.tech_array[self.time]
        self.cash = self.initial_cash  # reset()
        self.stocks = np.zeros(self.crypto_num, dtype=np.float32)
        self.stocks_cooldown = np.zeros_like(self.stocks)
        self.step_log = []
        self.total_asset = self.cash + (self.stocks * self.price_array[self.time]).sum()
        self.peak_asset   = self.initial_cash
        self.last_actions = np.zeros(self.crypto_num, dtype=np.float32)
        self.recent_returns.clear()

        state = self.get_state()
        return state

    def step(self, actions) -> (np.ndarray, float, bool, None):
        self.time += 1
        if self.if_log:
            _step_trades = []

        # Crypto markets are 24/7, so cooldown logic is different
        # Reduced cooldown for crypto markets
        for i in range(len(actions)):
            if self.stocks[i] > 0:
                self.stocks_cooldown[i] += 1

        price = self.price_array[self.time]
        for i in range(self.action_dim):
            norm_vector_i = self.action_norm_vector[i]
            actions[i] = actions[i] * norm_vector_i

        # Snapshot scaled action intent for jitter penalty
        scaled_actions = actions.copy()

        # Compute actions in crypto units (not dollars like in stock version)
        actions_crypto = actions  # Already in crypto units due to normalization

        # Sell
        #######################################################################################################
        #######################################################################################################
        #######################################################################################################

        for index in np.where(actions < -self.minimum_qty_crypto)[0]:

            if self.stocks[index] > 0:

                if price[index] > 0:  # Sell only if current asset is > 0
                    sell_amount = min(self.stocks[index], -actions[index])

                    assert sell_amount >= 0, "Negative sell!"

                    # In backtest mode, we simulate the sale
                    self.stocks_cooldown[index] = 0
                    self.stocks[index] -= sell_amount
                    self.cash += price[index] * sell_amount * (1 - self.sell_cost_pct)
                    if self.if_log:
                        _step_trades.append({'side': 'SELL', 'asset_idx': int(index),
                            'amount': float(sell_amount), 'price': float(price[index]),
                            'value_usd': float(sell_amount * price[index])})

                    # In live trading, this would be:
                    # try:
                    #     symbol = self.ticker_list[index]
                    #     order = self.exchange.create_market_sell_order(symbol, sell_amount)
                    # except Exception as e:
                    #     print(f"Failed to sell {symbol}: {e}")

        # Adaptive cooldown for crypto (shorter than stocks due to 24/7 market)
        for index in np.where(self.stocks_cooldown >= 24)[0]:  # 2 hours instead of 12 hours
            sell_amount = self.stocks[index] * 0.05  # Sell 5%
            self.stocks_cooldown[index] = 0
            self.stocks[index] -= sell_amount
            self.cash += price[index] * sell_amount * (1 - self.sell_cost_pct)
            if self.if_log and sell_amount > 0:
                _step_trades.append({'side': 'SELL', 'asset_idx': int(index),
                    'amount': float(sell_amount), 'price': float(price[index]),
                    'value_usd': float(sell_amount * price[index])})

        # Buy
        #######################################################################################################
        #######################################################################################################
        #######################################################################################################

        for index in np.where(actions > self.minimum_qty_crypto)[0]:
            if price[index] > 0:  # Buy only if the price is > 0

                fee_corrected_cash = self.cash / (1 + self.buy_cost_pct)
                max_crypto_can_buy = (fee_corrected_cash / price[index]) * self.safety_factor_stock_buy
                buy_amount = min(max_crypto_can_buy, actions_crypto[index])

                if buy_amount < self.minimum_qty_crypto[index]:
                    buy_amount = 0

                self.stocks[index] += buy_amount
                self.cash -= price[index] * buy_amount * (1 + self.buy_cost_pct)
                if buy_amount > 0 and self.if_log:
                    _step_trades.append({'side': 'BUY', 'asset_idx': int(index),
                        'amount': float(buy_amount), 'price': float(price[index]),
                        'value_usd': float(buy_amount * price[index])})

                # In live trading, this would be:
                # try:
                #     symbol = self.ticker_list[index]
                #     order = self.exchange.create_market_buy_order(symbol, buy_amount)
                # except Exception as e:
                #     print(f"Failed to buy {symbol}: {e}")

        """update time"""
        done = self.time == self.max_step
        state = self.get_state()
        next_total_asset = self.cash + (self.stocks * self.price_array[self.time]).sum()
        next_total_asset_eqw = np.sum(self.equal_weight_stock * self.price_array[self.time])

        # Reward shaping
        pct_bot = (next_total_asset - self.total_asset) / (self.total_asset + 1e-8)
        pct_eqw = (next_total_asset_eqw - self.total_asset_eqw) / (self.total_asset_eqw + 1e-8)  # kept for logging

        # Absolute Sharpe reward — bot earns for going up, loses for going down,
        # regardless of what HODL does. Fixes "ghost" (0 reward for copying BTC).
        self.recent_returns.append(pct_bot)
        vol = float(np.std(self.recent_returns)) if len(self.recent_returns) >= 2 else 1.0
        vol = max(vol, 1e-6)
        excess = pct_bot / vol

        # 3. Non-linear drawdown penalty (squared magnitude)
        self.peak_asset = max(self.peak_asset, next_total_asset)
        drawdown_now = (next_total_asset - self.peak_asset) / (self.peak_asset + 1e-8)
        drawdown_penalty = self.drawdown_weight * drawdown_now * abs(drawdown_now)

        # 4. Time-in-market penalty
        crypto_value = float((self.stocks * self.price_array[self.time]).sum())
        holding_ratio = crypto_value / (next_total_asset + 1e-8)
        holding_penalty = -self.holding_penalty_weight * holding_ratio

        # 1. Jitter penalty
        jitter = float(np.mean(np.abs(scaled_actions - self.last_actions)))
        self.last_actions = scaled_actions
        jitter_penalty = -self.jitter_weight * jitter

        reward = (excess + drawdown_penalty + holding_penalty + jitter_penalty) * self.norm_reward

        self.total_asset = next_total_asset
        self.total_asset_eqw = next_total_asset_eqw

        self.gamma_return = self.gamma_return * self.gamma + reward
        self.cumu_return = self.total_asset / self.initial_cash

        if done:
            reward = self.gamma_return
            self.episode_return = self.total_asset / self.initial_cash

        if self.if_log:
            coin_values = (self.stocks * self.price_array[self.time]).tolist()
            self.step_log.append({'time_idx': int(self.time), 'trades': _step_trades,
                'cash': float(self.cash), 'total_asset': float(self.total_asset),
                'coin_values': coin_values})

        return state, reward, done, None

    def get_state(self):
        state = np.hstack((self.cash * self.norm_cash, self.stocks * self.norm_stocks))
        for i in range(self.lookback):
            # Ensure we don't go out of bounds
            idx = max(0, self.time - i)
            tech_i = self.tech_array[idx]
            normalized_tech_i = tech_i * self.norm_tech
            state = np.hstack((state, normalized_tech_i)).astype(np.float32)
        return state

    def close(self):
        if hasattr(self.exchange, 'close'):
            self.exchange.close()

    def _generate_action_normalizer(self):
        action_norm_vector = []
        price_0 = self.price_array[0]
        for price in price_0:
            x = math.floor(math.log(price, 10))  # the order of magnitude
            action_norm_vector.append(1 / ((10) ** x))

        action_norm_vector = np.asarray(action_norm_vector) * self.norm_action
        self.action_norm_vector = np.asarray(action_norm_vector)

    def get_portfolio_value(self):
        """Get current portfolio value in USD"""
        crypto_value = (self.stocks * self.price_array[self.time]).sum()
        return self.cash + crypto_value

    def get_positions(self):
        """Get current cryptocurrency positions"""
        positions = {}
        for i, ticker in enumerate(self.ticker_list):
            if self.stocks[i] > 0:
                positions[ticker] = {
                    'amount': self.stocks[i],
                    'value_usd': self.stocks[i] * self.price_array[self.time][i]
                }
        return positions