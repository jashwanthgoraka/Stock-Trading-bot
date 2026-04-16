"""
main.py — Entry Point

Configures logging and starts the TradingBot.

Usage:
    python main.py

Environment:
    Set ALPACA_API_KEY, ALPACA_SECRET_KEY in a .env file before running.
    See .env.example for the required variables.
"""

import logging
import logging.handlers
import os
import sys

from config.settings import LOG_LEVEL, LOG_FILE
from src.bot import TradingBot


def configure_logging() -> None:
    """
    Set up structured logging to both console and a rotating log file.

    Log files rotate at 5 MB and keep up to 3 backups in the logs/ directory.
    """
    os.makedirs("logs", exist_ok=True)

    log_format = "%(asctime)s | %(levelname)-8s | %(name)s | %(message)s"
    date_format = "%Y-%m-%d %H:%M:%S"

    handlers = [
        logging.StreamHandler(sys.stdout),
        logging.handlers.RotatingFileHandler(
            LOG_FILE, maxBytes=5 * 1024 * 1024, backupCount=3
        ),
    ]

    logging.basicConfig(
        level=getattr(logging, LOG_LEVEL.upper(), logging.INFO),
        format=log_format,
        datefmt=date_format,
        handlers=handlers,
    )


def validate_config() -> None:
    """
    Validate that required environment variables are set before starting.

    Raises:
        SystemExit: If any required credential is missing.
    """
    from config.settings import ALPACA_API_KEY, ALPACA_SECRET_KEY

    missing = []
    if not ALPACA_API_KEY:
        missing.append("ALPACA_API_KEY")
    if not ALPACA_SECRET_KEY:
        missing.append("ALPACA_SECRET_KEY")

    if missing:
        print(f"❌ Missing required environment variables: {', '.join(missing)}")
        print("   Copy .env.example to .env and fill in your Alpaca API credentials.")
        raise SystemExit(1)


if __name__ == "__main__":
    configure_logging()
    validate_config()

    logger = logging.getLogger(__name__)
    logger.info("=" * 60)
    logger.info("  Alpaca Golden Cross / Death Cross Trading Bot")
    logger.info("=" * 60)

    bot = TradingBot()
    bot.run()
