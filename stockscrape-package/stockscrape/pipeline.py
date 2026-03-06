"""CLI entrypoint orchestrating all pipeline steps.

Usage:
    python -m stockscrape.pipeline run                  # all steps
    python -m stockscrape.pipeline test                 # quick test (3 tickers)
    python -m stockscrape.pipeline companies            # step 1
    python -m stockscrape.pipeline transcripts          # step 2
    python -m stockscrape.pipeline prices               # step 3
    python -m stockscrape.pipeline fundamentals         # step 4
    python -m stockscrape.pipeline metrics              # step 5
    python -m stockscrape.pipeline export               # dump CSV
    python -m stockscrape.pipeline import-transcripts   # import Kaggle .pkl

    Optional flags:
        --tickers AAPL,MSFT,GOOG   only process these tickers
        --file path/to/dataset.pkl  for import-transcripts
"""

import argparse
import csv
import logging
from pathlib import Path

from sqlalchemy import distinct, select

from stockscrape.config import EXPORT_DIR, METRIC_WINDOWS
from stockscrape.db import get_session
from stockscrape.metrics import compute_all_metrics
from stockscrape.models import Company, EarningsCall, PostEarningsMetric
from stockscrape.scrapers.companies import upsert_companies
from stockscrape.scrapers.fundamentals import scrape_all_fundamentals
from stockscrape.scrapers.prices import scrape_all_prices
from stockscrape.scrapers.transcripts import scrape_transcripts
from stockscrape.scrapers.transcripts_import import import_kaggle_transcripts

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)-5s %(name)s: %(message)s",
    datefmt="%H:%M:%S",
)
logger = logging.getLogger(__name__)


def parse_tickers(raw: str | None) -> list[str] | None:
    if not raw:
        return None
    return [t.strip().upper() for t in raw.split(",") if t.strip()]


# ── Individual step runners ─────────────────────────────────────────────────

def step_companies(session, args):
    logger.info("=== Step 1: Populating companies ===")
    count = upsert_companies(session)
    logger.info("Companies in DB: %d", count)


def step_transcripts(session, args):
    logger.info("=== Step 2: Scraping transcripts (ROIC.ai) ===")
    count = scrape_transcripts(session, args.tickers)
    logger.info("New transcripts: %d", count)


def step_import_transcripts(session, args):
    logger.info("=== Step 2 (import): Importing transcripts from Kaggle dataset ===")
    if not args.file:
        logger.error("--file is required for import-transcripts. Pass the path to the .pkl file.")
        return
    count = import_kaggle_transcripts(session, args.file)
    logger.info("Imported transcripts: %d", count)


def step_prices(session, args):
    logger.info("=== Step 3: Scraping prices (ROIC.ai) ===")
    count = scrape_all_prices(session, args.tickers)
    logger.info("New price rows: %d", count)


def step_fundamentals(session, args):
    logger.info("=== Step 4: Scraping fundamentals (ROIC.ai) ===")
    count = scrape_all_fundamentals(session, args.tickers)
    logger.info("New fundamental rows: %d", count)


def step_metrics(session, args):
    logger.info("=== Step 5: Computing metrics ===")
    count = compute_all_metrics(session, args.tickers)
    logger.info("New metric rows: %d", count)


def step_export(session, args):
    logger.info("=== Step 6: Exporting CSV ===")
    export_csv(session, args.tickers)


def step_run(session, args):
    """Run all steps in order."""
    step_companies(session, args)
    step_transcripts(session, args)
    step_prices(session, args)
    step_fundamentals(session, args)
    step_metrics(session, args)


def step_test(session, args):
    """Quick test: run full pipeline for AAPL (free on ROIC.ai without a subscription)."""
    step_companies(session, args)
    test_tickers = ["AAPL"]
    logger.info("=== Test: running pipeline for %s ===", test_tickers)
    args.tickers = test_tickers
    step_transcripts(session, args)
    step_prices(session, args)
    step_fundamentals(session, args)
    step_metrics(session, args)
    step_export(session, args)


# ── CSV export ──────────────────────────────────────────────────────────────

def export_csv(session, tickers: list[str] | None = None) -> Path:
    query = (
        select(EarningsCall, Company.ticker)
        .join(Company)
        .order_by(Company.ticker, EarningsCall.call_date)
    )
    if tickers:
        query = query.where(Company.ticker.in_(tickers))

    calls = session.execute(query).all()

    EXPORT_DIR.mkdir(parents=True, exist_ok=True)
    out_path = EXPORT_DIR / "earnings_dataset.csv"

    # Build header
    base_cols = ["ticker", "call_date", "fiscal_year", "fiscal_quarter", "transcript_text"]
    metric_cols = []
    for w in METRIC_WINDOWS:
        metric_cols.extend([
            f"window_{w}d_direction",
            f"window_{w}d_return",
            f"window_{w}d_vol",
        ])

    with open(out_path, "w", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)
        writer.writerow(base_cols + metric_cols)

        for call, ticker in calls:
            metrics_by_window: dict[int, PostEarningsMetric] = {}
            for m in session.execute(
                select(PostEarningsMetric).where(PostEarningsMetric.earnings_call_id == call.id)
            ).scalars().all():
                metrics_by_window[m.window_days] = m

            row = [
                ticker,
                call.call_date.isoformat() if call.call_date else "",
                call.fiscal_year,
                call.fiscal_quarter,
                call.transcript_text or "",
            ]
            for w in METRIC_WINDOWS:
                m = metrics_by_window.get(w)
                if m:
                    row.extend([m.direction, m.return_pct, m.realized_volatility])
                else:
                    row.extend(["", "", ""])

            writer.writerow(row)

    logger.info("Exported %d rows to %s", len(calls), out_path)
    return out_path


# ── CLI ─────────────────────────────────────────────────────────────────────

COMMANDS = {
    "run": step_run,
    "test": step_test,
    "companies": step_companies,
    "transcripts": step_transcripts,
    "import-transcripts": step_import_transcripts,
    "prices": step_prices,
    "fundamentals": step_fundamentals,
    "metrics": step_metrics,
    "export": step_export,
}


def main():
    parser = argparse.ArgumentParser(description="Stockscrape earnings data pipeline")
    parser.add_argument("command", choices=COMMANDS.keys(), help="Pipeline step to run")
    parser.add_argument(
        "--tickers",
        type=str,
        default=None,
        help="Comma-separated list of tickers to process (default: all)",
    )
    parser.add_argument(
        "--file",
        type=str,
        default=None,
        help="Path to .pkl file (for import-transcripts)",
    )
    args = parser.parse_args()
    args.tickers = parse_tickers(args.tickers)

    session = get_session()
    try:
        COMMANDS[args.command](session, args)
    finally:
        session.close()


if __name__ == "__main__":
    main()
