import os
from pathlib import Path

from dotenv import load_dotenv

load_dotenv()

# ── Database ────────────────────────────────────────────────────────────────
DATABASE_URL: str = os.getenv(
    "DATABASE_URL", "sqlite:///stockscrape.db"
)

# ── ROIC.ai ─────────────────────────────────────────────────────────────────
ROIC_API_KEY: str = os.getenv("ROIC_API_KEY", "")
ROIC_BASE_URL: str = "https://api.roic.ai"

# ── Scraping windows ───────────────────────────────────────────────────────
PRICE_START_DATE: str = "2015-01-01"
METRIC_WINDOWS: list[int] = [5, 10, 15, 20]

# ── Direction threshold (%) ─────────────────────────────────────────────────
DIRECTION_THRESHOLD: float = float(os.getenv("DIRECTION_THRESHOLD", "0.5"))

# ── Paths ───────────────────────────────────────────────────────────────────
PROJECT_ROOT: Path = Path(__file__).resolve().parent.parent
EXPORT_DIR: Path = PROJECT_ROOT / "exports"
