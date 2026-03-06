"""Compute post-earnings direction, return, and volatility metrics."""

import logging
from datetime import timedelta

import numpy as np
from sqlalchemy import and_, select
from sqlalchemy.orm import Session

from stockscrape.config import DIRECTION_THRESHOLD, METRIC_WINDOWS
from stockscrape.models import DailyPrice, EarningsCall, PostEarningsMetric

logger = logging.getLogger(__name__)


def _get_trading_days(
    session: Session, company_id: int, anchor: "date", before: int, after: int
) -> list[DailyPrice]:
    """Return sorted daily prices in a window around an anchor date.

    Fetches `before` trading days before the anchor and `after` trading days
    after (inclusive of anchor date).
    """
    # Generous calendar window to capture enough trading days
    cal_margin = max(before, after) * 2 + 10
    start = anchor - timedelta(days=cal_margin)
    end = anchor + timedelta(days=cal_margin)

    rows = (
        session.execute(
            select(DailyPrice)
            .where(
                and_(
                    DailyPrice.company_id == company_id,
                    DailyPrice.date >= start,
                    DailyPrice.date <= end,
                )
            )
            .order_by(DailyPrice.date)
        )
        .scalars()
        .all()
    )
    return list(rows)


def _classify_direction(return_pct: float, threshold: float = DIRECTION_THRESHOLD) -> str:
    if return_pct > threshold:
        return "UP"
    elif return_pct < -threshold:
        return "DOWN"
    return "FLAT"


def _annualized_volatility(prices: list[DailyPrice]) -> float | None:
    """Compute annualized realized volatility from daily log returns."""
    closes = [p.close for p in prices if p.close is not None]
    if len(closes) < 2:
        return None
    log_returns = np.diff(np.log(closes))
    return float(np.std(log_returns, ddof=1) * np.sqrt(252))


def compute_metrics_for_call(
    session: Session, call: EarningsCall, windows: list[int] = METRIC_WINDOWS
) -> int:
    """Compute post-earnings metrics for a single call across all windows.
    Returns count of new metric rows.
    """
    if call.call_date is None:
        return 0

    max_window = max(windows)
    prices = _get_trading_days(session, call.company_id, call.call_date, before=5, after=max_window + 5)
    if not prices:
        return 0

    # Split into pre and post relative to call_date
    pre = [p for p in prices if p.date < call.call_date]
    post = [p for p in prices if p.date >= call.call_date]

    if not pre:
        return 0

    pre_close_price = pre[-1].close  # last trading day before earnings
    if pre_close_price is None:
        return 0

    # Check which windows already exist
    existing = set(
        session.execute(
            select(PostEarningsMetric.window_days).where(
                PostEarningsMetric.earnings_call_id == call.id
            )
        ).scalars().all()
    )

    new_count = 0
    for w in windows:
        if w in existing:
            continue

        # Need at least w trading days after the call
        if len(post) < w:
            continue

        window_prices = post[:w]
        post_close_price = window_prices[-1].close
        if post_close_price is None:
            continue

        return_pct = (post_close_price - pre_close_price) / pre_close_price * 100
        direction = _classify_direction(return_pct)

        # Volatility over the window (pre-close day + post window)
        vol_prices = pre[-1:] + window_prices
        vol = _annualized_volatility(vol_prices)

        session.add(PostEarningsMetric(
            earnings_call_id=call.id,
            window_days=w,
            pre_close=pre_close_price,
            post_close=post_close_price,
            direction=direction,
            return_pct=round(return_pct, 4),
            realized_volatility=round(vol, 6) if vol is not None else None,
        ))
        new_count += 1

    if new_count:
        session.commit()
    return new_count


def compute_all_metrics(session: Session, tickers: list[str] | None = None) -> int:
    """Compute metrics for all earnings calls. Returns total new metric rows."""
    query = select(EarningsCall).where(EarningsCall.call_date.isnot(None))
    if tickers:
        from stockscrape.models import Company
        query = query.join(Company).where(Company.ticker.in_(tickers))
    calls = session.execute(query.order_by(EarningsCall.call_date)).scalars().all()

    logger.info("Computing metrics for %d earnings calls", len(calls))
    total = 0
    for call in calls:
        total += compute_metrics_for_call(session, call)

    logger.info("Total new metric rows: %d", total)
    return total
