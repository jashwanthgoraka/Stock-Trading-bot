"""
settings.py — Centralized Configuration

All bot parameters are defined here. Sensitive credentials are loaded
securely from environment variables using python-dotenv.

Never hardcode API keys. Set them in a .env file (gitignored).
"""

import os
from dotenv import load_dotenv

# Load variables from .env file if present
load_dotenv()

# ------------------------------------------------------------------
# Alpaca API Credentials (set these in your .env file)
# ------------------------------------------------------------------
ALPACA_API_KEY: str = os.getenv("ALPACA_API_KEY", "")
ALPACA_SECRET_KEY: str = os.getenv("ALPACA_SECRET_KEY", "")
ALPACA_BASE_URL: str = os.getenv(
    "ALPACA_BASE_URL", "https://paper-api.alpaca.markets"
)

# ------------------------------------------------------------------
# Strategy Parameters
# ------------------------------------------------------------------
FAST_MA_WINDOW: int = 10       # Fast (short-term) moving average period in days
SLOW_MA_WINDOW: int = 50       # Slow (long-term) moving average period in days
STOP_LOSS_THRESHOLD: float = 0.10  # 10% stop-loss on daily position change

# ------------------------------------------------------------------
# Universe of Stocks
# ------------------------------------------------------------------
TICKER_LIMIT: int = 200        # Number of S&P 500 tickers to monitor
SP500_SYMBOLS_CSV: str = "data/SP500-Symbols.csv"
SP500_INFO_CSV: str = "data/SP500-Info.csv"

# ------------------------------------------------------------------
# Loop Configuration
# ------------------------------------------------------------------
LOOP_INTERVAL_SECONDS: int = 3600  # How often the bot runs (default: 1 hour)

# ------------------------------------------------------------------
# Logging
# ------------------------------------------------------------------
LOG_LEVEL: str = os.getenv("LOG_LEVEL", "INFO")
LOG_FILE: str = "logs/trading_bot.log"
