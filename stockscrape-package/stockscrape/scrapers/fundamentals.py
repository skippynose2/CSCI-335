"""Fetch fundamental financial data (income, balance sheet, cash flow) from ROIC.ai API."""

import logging
from datetime import date

from sqlalchemy import select
from sqlalchemy.orm import Session

from stockscrape.models import Company, Fundamental
from stockscrape.roic_client import RoicClient

logger = logging.getLogger(__name__)


def _existing_keys(session: Session, company_id: int) -> set[tuple[str, str, str]]:
    """Return set of (statement_type, period_date, period) already stored."""
    rows = session.execute(
        select(Fundamental.statement_type, Fundamental.period_date, Fundamental.period).where(
            Fundamental.company_id == company_id
        )
    ).all()
    return {(r[0], str(r[1]), r[2]) for r in rows}


def _parse_date(val) -> date | None:
    try:
        return date.fromisoformat(str(val)[:10])
    except (ValueError, TypeError):
        return None


def _safe_float(val) -> float | None:
    if val is None or val == "":
        return None
    try:
        return float(val)
    except (ValueError, TypeError):
        return None


def _safe_int(val) -> int | None:
    if val is None or val == "":
        return None
    try:
        return int(val)
    except (ValueError, TypeError):
        return None


def _scrape_income(client: RoicClient, session: Session, company: Company, existing: set) -> int:
    try:
        data = client.get_income_statement(company.ticker)
    except Exception as e:
        logger.warning("%s income statement: %s", company.ticker, e)
        return 0

    if not isinstance(data, list):
        return 0

    count = 0
    for row in data:
        d = _parse_date(row.get("date"))
        period = row.get("period", "")
        if not d or not period:
            continue
        if ("income", str(d), period) in existing:
            continue

        session.add(Fundamental(
            company_id=company.id,
            statement_type="income",
            period_date=d,
            period=period,
            fiscal_year=_safe_int(row.get("fiscal_year")),
            revenue=_safe_float(row.get("is_sales_revenue_turnover")),
            gross_profit=_safe_float(row.get("is_gross_profit")),
            operating_income=_safe_float(row.get("is_oper_income")),
            net_income=_safe_float(row.get("is_net_income")),
            eps=_safe_float(row.get("eps")),
            diluted_eps=_safe_float(row.get("diluted_eps")),
            ebitda=_safe_float(row.get("ebitda")),
        ))
        count += 1
    return count


def _scrape_balance(client: RoicClient, session: Session, company: Company, existing: set) -> int:
    try:
        data = client.get_balance_sheet(company.ticker)
    except Exception as e:
        logger.warning("%s balance sheet: %s", company.ticker, e)
        return 0

    if not isinstance(data, list):
        return 0

    count = 0
    for row in data:
        d = _parse_date(row.get("date"))
        period = row.get("period", "")
        if not d or not period:
            continue
        if ("balance", str(d), period) in existing:
            continue

        session.add(Fundamental(
            company_id=company.id,
            statement_type="balance",
            period_date=d,
            period=period,
            fiscal_year=_safe_int(row.get("fiscal_year")),
            total_assets=_safe_float(row.get("bs_tot_asset")),
            total_liabilities=_safe_float(row.get("bs_tot_liab")),
            total_equity=_safe_float(row.get("bs_total_equity")),
            cash_and_equivalents=_safe_float(row.get("bs_c_and_ce_and_sti_detailed")),
            total_debt=_safe_float(row.get("short_and_long_term_debt")),
        ))
        count += 1
    return count


def _scrape_cashflow(client: RoicClient, session: Session, company: Company, existing: set) -> int:
    try:
        data = client.get_cash_flow(company.ticker)
    except Exception as e:
        logger.warning("%s cash flow: %s", company.ticker, e)
        return 0

    if not isinstance(data, list):
        return 0

    count = 0
    for row in data:
        d = _parse_date(row.get("date"))
        period = row.get("period", "")
        if not d or not period:
            continue
        if ("cashflow", str(d), period) in existing:
            continue

        # Compute free cash flow if not directly available
        op_cf = _safe_float(row.get("cf_cash_from_operating_activities"))
        capex = _safe_float(row.get("cf_cap_expend"))
        fcf = None
        if op_cf is not None and capex is not None:
            fcf = op_cf + capex  # capex is typically negative

        session.add(Fundamental(
            company_id=company.id,
            statement_type="cashflow",
            period_date=d,
            period=period,
            fiscal_year=_safe_int(row.get("fiscal_year")),
            operating_cash_flow=op_cf,
            investing_cash_flow=_safe_float(row.get("cf_cash_from_investing_activities")),
            financing_cash_flow=_safe_float(row.get("cf_cash_from_financing_activities")),
            free_cash_flow=fcf,
            net_income=_safe_float(row.get("cf_net_income")),
        ))
        count += 1
    return count


def scrape_fundamentals_for_company(client: RoicClient, session: Session, company: Company) -> int:
    existing = _existing_keys(session, company.id)
    count = 0
    count += _scrape_income(client, session, company, existing)
    count += _scrape_balance(client, session, company, existing)
    count += _scrape_cashflow(client, session, company, existing)
    if count:
        session.commit()
    logger.info("%s: %d new fundamental rows", company.ticker, count)
    return count


def scrape_all_fundamentals(session: Session, tickers: list[str] | None = None) -> int:
    """Scrape fundamentals for all (or specified) companies. Returns total new rows."""
    query = select(Company).order_by(Company.ticker)
    if tickers:
        query = query.where(Company.ticker.in_(tickers))
    companies = session.execute(query).scalars().all()

    logger.info("Scraping fundamentals for %d companies", len(companies))
    total = 0

    with RoicClient() as client:
        for company in companies:
            total += scrape_fundamentals_for_company(client, session, company)

    logger.info("Total new fundamental rows: %d", total)
    return total
