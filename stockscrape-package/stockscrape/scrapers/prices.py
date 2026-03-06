"""Fetch daily OHLCV price data from ROIC.ai API."""

import logging
from datetime import date, timedelta

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from stockscrape.config import PRICE_START_DATE
from stockscrape.models import Company, DailyPrice
from stockscrape.roic_client import RoicClient

logger = logging.getLogger(__name__)


def _last_stored_date(session: Session, company_id: int) -> date | None:
    result = session.execute(
        select(func.max(DailyPrice.date)).where(DailyPrice.company_id == company_id)
    ).scalar()
    return result


def scrape_prices_for_company(client: RoicClient, session: Session, company: Company) -> int:
    """Download price history for one company. Returns count of new rows inserted."""
    last = _last_stored_date(session, company.id)
    start = (last + timedelta(days=1)).isoformat() if last else PRICE_START_DATE

    try:
        data = client.get_stock_prices(company.ticker, date_start=start)
    except Exception as e:
        logger.warning("Failed prices for %s: %s", company.ticker, e)
        return 0

    if not isinstance(data, list) or not data:
        logger.debug("%s: no new price data since %s", company.ticker, start)
        return 0

    rows: list[DailyPrice] = []
    for row in data:
        try:
            d = date.fromisoformat(str(row["date"])[:10])
        except (ValueError, KeyError):
            continue
        rows.append(DailyPrice(
            company_id=company.id,
            date=d,
            open=row.get("open"),
            high=row.get("high"),
            low=row.get("low"),
            close=row.get("close"),
            adj_close=row.get("adj_close"),
            volume=row.get("volume"),
        ))

    session.add_all(rows)
    session.commit()
    logger.info("%s: inserted %d price rows (from %s)", company.ticker, len(rows), start)
    return len(rows)


def scrape_all_prices(session: Session, tickers: list[str] | None = None) -> int:
    """Scrape prices for all (or specified) companies. Returns total new rows."""
    query = select(Company).order_by(Company.ticker)
    if tickers:
        query = query.where(Company.ticker.in_(tickers))
    companies = session.execute(query).scalars().all()

    logger.info("Scraping prices for %d companies", len(companies))
    total = 0

    with RoicClient() as client:
        for company in companies:
            total += scrape_prices_for_company(client, session, company)

    logger.info("Total new price rows: %d", total)
    return total
