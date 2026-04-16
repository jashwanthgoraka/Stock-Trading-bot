"""
setup.py — S&P 500 Universe Initializer

Fetches the current list of S&P 500 companies from Wikipedia and saves
ticker symbols and company metadata to CSV files for use by the trading bot.

Run this script once before starting the bot:
    python setup.py
"""

import os
import logging
import pandas as pd

logging.basicConfig(level=logging.INFO, format="%(asctime)s | %(levelname)s | %(message)s")
logger = logging.getLogger(__name__)

SP500_URL = "https://en.wikipedia.org/wiki/List_of_S%26P_500_companies"
DATA_DIR = "data"


def fetch_sp500() -> pd.DataFrame:
    """
    Scrape the S&P 500 company list from Wikipedia.

    Returns:
        pd.DataFrame: Full S&P 500 company table with tickers, names, sectors, etc.

    Raises:
        ValueError: If the expected table cannot be found on the page.
    """
    logger.info("Fetching S&P 500 data from Wikipedia...")
    tables = pd.read_html(SP500_URL)

    if not tables:
        raise ValueError("No tables found on Wikipedia S&P 500 page.")

    df = tables[0]
    logger.info("Found %d companies in S&P 500.", len(df))
    return df


def save_data(df: pd.DataFrame) -> None:
    """
    Save S&P 500 data to CSV files in the data/ directory.

    Files created:
        - data/SP500-Info.csv   — Full company info
        - data/SP500-Symbols.csv — Ticker symbols only

    Args:
        df (pd.DataFrame): S&P 500 DataFrame from Wikipedia.
    """
    os.makedirs(DATA_DIR, exist_ok=True)

    info_path = os.path.join(DATA_DIR, "SP500-Info.csv")
    symbols_path = os.path.join(DATA_DIR, "SP500-Symbols.csv")

    df.to_csv(info_path, index=False)
    df[["Symbol"]].to_csv(symbols_path, index=False)

    logger.info("Saved full info to '%s'", info_path)
    logger.info("Saved symbols to '%s'", symbols_path)


if __name__ == "__main__":
    try:
        df = fetch_sp500()
        save_data(df)
        logger.info("✅ Setup complete. You can now run: python main.py")
    except Exception as exc:
        logger.error("❌ Setup failed: %s", exc, exc_info=True)
        raise SystemExit(1)
