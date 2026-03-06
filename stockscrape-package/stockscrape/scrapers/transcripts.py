"""Fetch earnings call transcripts from ROIC.ai API."""

import logging
from datetime import date

from sqlalchemy import select
from sqlalchemy.orm import Session

from stockscrape.models import Company, EarningsCall
from stockscrape.roic_client import RoicClient

logger = logging.getLogger(__name__)


def _existing_quarters(session: Session, company_id: int) -> set[tuple[int, int]]:
    rows = session.execute(
        select(EarningsCall.fiscal_year, EarningsCall.fiscal_quarter).where(
            EarningsCall.company_id == company_id
        )
    ).all()
    return {(r[0], r[1]) for r in rows}


def scrape_transcripts_for_company(
    client: RoicClient, session: Session, company: Company
) -> int:
    """Fetch all available transcripts for one company. Returns count of new transcripts."""
    existing = _existing_quarters(session, company.id)

    try:
        calls = client.list_earnings_calls(company.ticker)
    except Exception as e:
        logger.warning("Failed to list earnings calls for %s: %s", company.ticker, e)
        return 0

    if not isinstance(calls, list):
        logger.warning("%s: unexpected response from list endpoint: %s", company.ticker, type(calls))
        return 0

    new_count = 0
    for call in calls:
        year = call.get("year")
        quarter = call.get("quarter")
        if year is None or quarter is None:
            continue
        year, quarter = int(year), int(quarter)
        if (year, quarter) in existing:
            continue

        try:
            data = client.get_transcript(company.ticker, year, quarter)
        except Exception as e:
            logger.warning("Failed transcript %s %dQ%d: %s", company.ticker, year, quarter, e)
            continue

        content = data.get("content", "") if isinstance(data, dict) else ""
        if not content:
            continue

        call_date = None
        date_str = call.get("date") or data.get("date")
        if date_str:
            try:
                call_date = date.fromisoformat(str(date_str)[:10])
            except (ValueError, TypeError):
                pass

        session.add(EarningsCall(
            company_id=company.id,
            call_date=call_date,
            fiscal_year=year,
            fiscal_quarter=quarter,
            transcript_text=content,
            transcript_source="roic_ai",
        ))
        new_count += 1

    if new_count:
        session.commit()
    logger.info("%s: %d new transcripts", company.ticker, new_count)
    return new_count


def scrape_transcripts(session: Session, tickers: list[str] | None = None) -> int:
    """Scrape transcripts for all (or specified) companies. Returns total new transcripts."""
    query = select(Company).order_by(Company.ticker)
    if tickers:
        query = query.where(Company.ticker.in_(tickers))
    companies = session.execute(query).scalars().all()

    logger.info("Scraping transcripts for %d companies", len(companies))
    total = 0

    with RoicClient() as client:
        for company in companies:
            total += scrape_transcripts_for_company(client, session, company)

    logger.info("Total new transcripts scraped: %d", total)
    return total
