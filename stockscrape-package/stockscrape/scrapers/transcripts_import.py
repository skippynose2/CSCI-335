"""Import earnings call transcripts from the Kaggle Motley Fool dataset (.pkl).

Download from: https://www.kaggle.com/datasets/tpotterer/motley-fool-scraped-earnings-call-transcripts
Place the .pkl file in the project root or pass its path to import_kaggle_transcripts().
"""

import logging
import re
from pathlib import Path

import pandas as pd
from sqlalchemy import select
from sqlalchemy.orm import Session

from stockscrape.models import Company, EarningsCall

logger = logging.getLogger(__name__)

# Map quarter strings like "Q1" → 1
_QUARTER_MAP = {"Q1": 1, "Q2": 2, "Q3": 3, "Q4": 4}


def _parse_quarter(raw: str) -> int | None:
    """Parse quarter from strings like 'Q3 2021', 'Q1', 'FQ2', etc."""
    m = re.search(r"Q(\d)", str(raw), re.IGNORECASE)
    return int(m.group(1)) if m else None


def _parse_fiscal_year(date_val, quarter_str: str) -> int | None:
    """Try to extract fiscal year from the quarter string or fall back to date."""
    m = re.search(r"(\d{4})", str(quarter_str))
    if m:
        return int(m.group(1))
    try:
        return pd.Timestamp(date_val).year
    except Exception:
        return None


def import_kaggle_transcripts(session: Session, pkl_path: str | Path) -> int:
    """Import transcripts from the Kaggle .pkl file. Returns count imported."""
    pkl_path = Path(pkl_path)
    if not pkl_path.exists():
        raise FileNotFoundError(f"Dataset not found: {pkl_path}")

    df = pd.read_pickle(pkl_path)
    logger.info("Loaded %d rows from %s", len(df), pkl_path.name)
    logger.info("Columns: %s", list(df.columns))

    # Build ticker → company lookup
    companies = {
        c.ticker: c
        for c in session.execute(select(Company)).scalars().all()
    }
    if not companies:
        logger.warning("No companies in DB. Run 'pipeline companies' first.")
        return 0

    # Build set of existing (company_id, year, quarter) to skip duplicates
    existing = set(
        session.execute(
            select(EarningsCall.company_id, EarningsCall.fiscal_year, EarningsCall.fiscal_quarter)
        ).all()
    )

    imported = 0
    skipped_no_company = 0
    skipped_duplicate = 0
    skipped_parse = 0

    for _, row in df.iterrows():
        ticker = str(row.get("ticker", "")).strip().upper()
        if not ticker or ticker not in companies:
            skipped_no_company += 1
            continue

        company = companies[ticker]
        quarter = _parse_quarter(row.get("quarter", ""))
        fiscal_year = _parse_fiscal_year(row.get("date"), row.get("quarter", ""))

        if quarter is None or fiscal_year is None:
            skipped_parse += 1
            continue

        if (company.id, fiscal_year, quarter) in existing:
            skipped_duplicate += 1
            continue

        # Parse call date
        call_date = None
        try:
            call_date = pd.Timestamp(row["date"]).date()
        except Exception:
            pass

        transcript = str(row.get("transcript", "")).strip()
        if not transcript:
            continue

        session.add(EarningsCall(
            company_id=company.id,
            call_date=call_date,
            fiscal_year=fiscal_year,
            fiscal_quarter=quarter,
            transcript_text=transcript,
            transcript_source="kaggle_motley_fool",
        ))
        existing.add((company.id, fiscal_year, quarter))
        imported += 1

        if imported % 500 == 0:
            session.commit()
            logger.info("Progress: %d imported so far...", imported)

    session.commit()
    logger.info(
        "Import complete: %d imported, %d skipped (no matching company), "
        "%d skipped (duplicate), %d skipped (parse error)",
        imported, skipped_no_company, skipped_duplicate, skipped_parse,
    )
    return imported
