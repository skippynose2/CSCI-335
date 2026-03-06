"""Scrape S&P 500 constituent list from Wikipedia and upsert into DB."""

import io
import logging
import urllib.request

import pandas as pd
from sqlalchemy import select
from sqlalchemy.orm import Session

from stockscrape.models import Company

logger = logging.getLogger(__name__)

WIKI_URL = "https://en.wikipedia.org/wiki/List_of_S%26P_500_companies"


def fetch_sp500_table() -> pd.DataFrame:
    """Read the first table on the Wikipedia S&P 500 page."""
    req = urllib.request.Request(
        WIKI_URL,
        headers={"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"},
    )
    with urllib.request.urlopen(req) as resp:
        html = resp.read().decode("utf-8")
    tables = pd.read_html(io.StringIO(html))
    df = tables[0]
    # Normalise column names we care about
    df = df.rename(columns={
        "Symbol": "ticker",
        "Security": "name",
        "GICS Sector": "sector",
        "GICS Sub-Industry": "sub_industry",
    })
    # Some tickers use dots on Wikipedia (BRK.B) but Finnhub/yfinance use dashes (BRK-B)
    df["ticker"] = df["ticker"].str.replace(".", "-", regex=False)
    return df[["ticker", "name", "sector", "sub_industry"]]


def upsert_companies(session: Session) -> int:
    """Fetch S&P 500 list and upsert into the companies table. Returns count upserted."""
    df = fetch_sp500_table()
    logger.info("Fetched %d companies from Wikipedia", len(df))

    existing = {
        c.ticker: c
        for c in session.execute(select(Company)).scalars().all()
    }

    added = 0
    for _, row in df.iterrows():
        ticker = row["ticker"]
        if ticker in existing:
            # Update fields in case name/sector changed
            comp = existing[ticker]
            comp.name = row["name"]
            comp.sector = row["sector"]
            comp.sub_industry = row["sub_industry"]
        else:
            session.add(Company(
                ticker=ticker,
                name=row["name"],
                sector=row["sector"],
                sub_industry=row["sub_industry"],
            ))
            added += 1

    session.commit()
    logger.info("Upserted companies: %d new, %d updated", added, len(df) - added)
    return len(df)
