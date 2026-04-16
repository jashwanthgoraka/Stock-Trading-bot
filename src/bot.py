"""
bot.py — Core Trading Bot Engine

Implements a Golden Cross / Death Cross algorithmic trading strategy
using the Alpaca Markets paper-trading API.

Strategy:
    - Golden Cross: 10-day SMA crosses above 50-day SMA → BUY signal
    - Death Cross:  10-day SMA crosses below 50-day SMA → SELL/SHORT signal
    - Stop-Loss:    Auto-triggered at ±10% daily change

Usage:
    from src.bot import TradingBot
    bot = TradingBot()
    bot.run()
"""

import time
import logging
from typing import Optional, Tuple

import numpy as np
import pandas as pd
import alpaca_trade_api as tradeapi

from config.settings import (
    ALPACA_API_KEY,
    ALPACA_SECRET_KEY,
    ALPACA_BASE_URL,
    FAST_MA_WINDOW,
    SLOW_MA_WINDOW,
    STOP_LOSS_THRESHOLD,
    TICKER_LIMIT,
    LOOP_INTERVAL_SECONDS,
    SP500_SYMBOLS_CSV,
)

logger = logging.getLogger(__name__)


class TradingBot:
    """
    Algorithmic stock trading bot using Alpaca Markets paper-trading API.

    Implements a Moving Average Crossover strategy (Golden Cross / Death Cross)
    with automatic stop-loss protection on all open positions.

    Attributes:
        api (tradeapi.REST): Authenticated Alpaca REST API client.
    """

    def __init__(self):
        """Initialize the bot and authenticate with the Alpaca API."""
        logger.info("Initializing TradingBot...")
        self.api = tradeapi.REST(
            ALPACA_API_KEY,
            ALPACA_SECRET_KEY,
            ALPACA_BASE_URL,
            api_version="v2",
        )
        logger.info("Alpaca API connection established.")

    # ------------------------------------------------------------------
    # Account & Market Info
    # ------------------------------------------------------------------

    def get_account_info(self) -> dict:
        """
        Fetch and return current account information.

        Returns:
            dict: Account details including buying power and portfolio value.
        """
        account = self.api.get_account()
        info = {
            "buying_power": float(account.buying_power),
            "portfolio_value": float(account.portfolio_value),
            "cash": float(account.cash),
            "status": account.status,
        }
        logger.info(
            "Account | Buying Power: $%.2f | Portfolio Value: $%.2f",
            info["buying_power"],
            info["portfolio_value"],
        )
        return info

    def is_market_open(self) -> bool:
        """
        Check whether the US stock market is currently open.

        Returns:
            bool: True if the market is open, False otherwise.
        """
        clock = self.api.get_clock()
        logger.debug("Market open: %s", clock.is_open)
        return clock.is_open

    # ------------------------------------------------------------------
    # Data Fetching
    # ------------------------------------------------------------------

    def fetch_market_data(self) -> Tuple[list, np.ndarray]:
        """
        Fetch historical OHLCV bar data for the top N S&P 500 tickers.

        Reads ticker symbols from the local CSV file generated during setup,
        then retrieves daily bar data from the Alpaca API.

        Returns:
            Tuple[list, np.ndarray]:
                - List of DataFrames, one per ticker.
                - NumPy array of ticker symbol strings.

        Raises:
            FileNotFoundError: If the S&P 500 symbols CSV does not exist.
        """
        try:
            tickers_df = pd.read_csv(SP500_SYMBOLS_CSV)
        except FileNotFoundError:
            logger.error(
                "Symbols file not found at '%s'. Run setup first.", SP500_SYMBOLS_CSV
            )
            raise

        ticker_symbols = tickers_df["Symbol"].values[:TICKER_LIMIT]
        logger.info("Fetching data for %d tickers...", len(ticker_symbols))

        data_list = []
        failed = []

        for symbol in ticker_symbols:
            try:
                bars = self.api.get_bars(symbol, "1Day", limit=100).df
                data_list.append(bars)
            except Exception as exc:
                logger.warning("Failed to fetch data for %s: %s", symbol, exc)
                failed.append(symbol)

        if failed:
            logger.warning("Skipped %d tickers due to fetch errors.", len(failed))

        return data_list, ticker_symbols

    # ------------------------------------------------------------------
    # Strategy: Golden Cross / Death Cross
    # ------------------------------------------------------------------

    def evaluate_signal(
        self, data: pd.DataFrame, ticker: str
    ) -> Tuple[Optional[bool], str]:
        """
        Evaluate the Golden Cross / Death Cross signal for a given ticker.

        Strategy Logic:
            - Compute a fast (10-day) and slow (50-day) Simple Moving Average.
            - If yesterday fast SMA ≈ slow SMA AND today fast SMA > slow SMA
              → Golden Cross → BUY signal (returns True).
            - If yesterday fast SMA ≈ slow SMA AND today fast SMA < slow SMA
              → Death Cross → SELL/SHORT signal (returns False).
            - Otherwise → No signal (returns None).

        Args:
            data (pd.DataFrame): OHLCV DataFrame with a 'close' column.
            ticker (str): Stock ticker symbol.

        Returns:
            Tuple[Optional[bool], str]:
                - True for BUY, False for SELL/SHORT, None for no signal.
                - The ticker symbol.
        """
        if "close" not in data.columns or len(data) < SLOW_MA_WINDOW:
            logger.debug("Insufficient data for %s, skipping.", ticker)
            return None, ticker

        close = data["close"]
        fast_ma = close.rolling(window=FAST_MA_WINDOW).mean()
        slow_ma = close.rolling(window=SLOW_MA_WINDOW).mean()

        current_fast = fast_ma.iloc[-1]
        current_slow = slow_ma.iloc[-1]
        prev_fast = fast_ma.iloc[-2].round(2)
        prev_slow = slow_ma.iloc[-2].round(2)

        if prev_fast == prev_slow:
            if current_fast > current_slow:
                logger.info("📈 Golden Cross detected for %s — BUY signal.", ticker)
                return True, ticker
            elif current_fast < current_slow:
                logger.info("📉 Death Cross detected for %s — SELL signal.", ticker)
                return False, ticker

        return None, ticker

    # ------------------------------------------------------------------
    # Order Execution
    # ------------------------------------------------------------------

    def execute_trade(self, signal: bool, ticker: str) -> None:
        """
        Place a market order based on the evaluated signal.

        Args:
            signal (bool): True to BUY (long), False to SELL (short).
            ticker (str): Stock ticker symbol.
        """
        side = "buy" if signal else "sell"
        action = "LONG BUY" if signal else "SHORT SELL"

        try:
            self.api.submit_order(symbol=ticker, qty=1, side=side, type="market", time_in_force="day")
            logger.info("✅ Order placed | %s | %s", action, ticker)
        except Exception as exc:
            logger.error("❌ Order failed | %s | %s | Reason: %s", action, ticker, exc)

    def check_stop_loss(self) -> None:
        """
        Review all open positions and trigger stop-loss orders if thresholds are breached.

        Threshold: ±10% change in position value since market open.
            - Short positions that rose >10% are bought back to cap losses.
            - Long positions that fell >10% are sold to cap losses.
        """
        portfolio = self.api.list_positions()
        logger.info("Checking stop-loss on %d open positions...", len(portfolio))

        for position in portfolio:
            qty = int(position.qty)
            change_today = float(position.change_today)
            avg_entry = float(position.avg_entry_price)
            current_price = float(position.current_price)
            symbol = position.symbol

            if qty < 0 and change_today > STOP_LOSS_THRESHOLD:
                # Shorting: price rose above threshold — buy to cover
                stop_price = round(avg_entry * (1 + STOP_LOSS_THRESHOLD), 2)
                logger.warning(
                    "🛑 Stop-Loss (Short) | %s | Entry: $%.2f | Current: $%.2f | Trigger: $%.2f",
                    symbol, avg_entry, current_price, stop_price,
                )
                try:
                    self.api.submit_order(
                        symbol=symbol,
                        qty=abs(qty),
                        side="buy",
                        type="stop",
                        stop_price=stop_price,
                        time_in_force="day",
                    )
                except Exception as exc:
                    logger.error("Stop-loss order failed for %s: %s", symbol, exc)

            elif qty > 0 and change_today < -STOP_LOSS_THRESHOLD:
                # Long: price fell below threshold — sell to limit loss
                stop_price = round(avg_entry * (1 - STOP_LOSS_THRESHOLD), 2)
                logger.warning(
                    "🛑 Stop-Loss (Long) | %s | Entry: $%.2f | Current: $%.2f | Trigger: $%.2f",
                    symbol, avg_entry, current_price, stop_price,
                )
                try:
                    self.api.submit_order(
                        symbol=symbol,
                        qty=abs(qty),
                        side="sell",
                        type="stop",
                        stop_price=stop_price,
                        time_in_force="day",
                    )
                except Exception as exc:
                    logger.error("Stop-loss order failed for %s: %s", symbol, exc)

    # ------------------------------------------------------------------
    # Main Loop
    # ------------------------------------------------------------------

    def run(self) -> None:
        """
        Start the main trading loop.

        The bot will:
            1. Wait until the market is open.
            2. Fetch S&P 500 market data.
            3. Evaluate trading signals for each ticker.
            4. Execute trades on valid signals.
            5. Monitor stop-loss conditions.
            6. Sleep for the configured interval before repeating.
        """
        logger.info("🤖 TradingBot started. Monitoring markets...")
        self.get_account_info()

        while True:
            try:
                if not self.is_market_open():
                    logger.info("Market is closed. Waiting 60 seconds...")
                    time.sleep(60)
                    continue

                logger.info("Market is open. Running trading cycle...")
                data_list, tickers = self.fetch_market_data()

                for i, data in enumerate(data_list):
                    signal, ticker = self.evaluate_signal(data, tickers[i])
                    if signal is not None:
                        self.execute_trade(signal, ticker)

                self.check_stop_loss()
                logger.info(
                    "Cycle complete. Sleeping for %d seconds...",
                    LOOP_INTERVAL_SECONDS,
                )
                time.sleep(LOOP_INTERVAL_SECONDS)

            except KeyboardInterrupt:
                logger.info("🛑 Bot stopped by user.")
                break
            except Exception as exc:
                logger.error("Unexpected error in main loop: %s", exc, exc_info=True)
                time.sleep(60)  # Wait before retrying to avoid hammering the API
