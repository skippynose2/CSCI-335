# Stockscrape — S&P 500 Earnings Call Data Pipeline

Pre-scraped dataset of earnings call transcripts, stock prices, and financial fundamentals for ~500 S&P 500 companies (2005–2026). Built for FinBERT sentiment analysis → post-earnings volatility prediction.

## Cloning (Git LFS Required)

Data files are stored with Git LFS. Install it first:
```bash
git lfs install    # one-time setup
git clone <repo>   # LFS files download automatically
```

If you already cloned without LFS, run `git lfs pull` to fetch the data files.

## Quick Start (Using Pre-scraped Data)

The `data/` folder has everything you need:

| File | Rows | Description |
|------|------|-------------|
| `companies.csv` | 503 | Ticker, name, sector, sub-industry |
| `earnings_dataset.csv` | 33,287 | Transcripts + post-earnings metrics (direction, return%, volatility) for 5/10/15/20-day windows |
| `daily_prices.csv` | 1,367,384 | Daily OHLCV prices (2015–2026) |
| `fundamentals.csv` | 192,360 | Quarterly income statements, balance sheets, cash flow |

Load in Python:
```python
import pandas as pd
transcripts = pd.read_csv("data/earnings_dataset.csv")
prices = pd.read_csv("data/daily_prices.csv")
fundamentals = pd.read_csv("data/fundamentals.csv")
```

## Loading Into a Database (Optional)

If you want the data in PostgreSQL for querying:

### Prerequisites
- **Python 3.11+**
- **PostgreSQL** installed and running locally

### Setup
```bash
pip install -r requirements.txt
cp .env.example .env
# Edit .env: set DATABASE_URL=postgresql://user:password@localhost:5432/stockscrape
```

Create the database:
```bash
psql -U postgres -c "CREATE DATABASE stockscrape;"
```

Run migrations and import:
```bash
alembic upgrade head
python -m stockscrape.pipeline companies
python -m stockscrape.pipeline import-transcripts --file data/earnings_dataset.csv
```

## Pipeline Commands (For Re-scraping)

Requires a ROIC.ai API key ($40/mo Premium plan). Add `ROIC_API_KEY=...` to `.env`.

| Command | What it does |
|---------|-------------|
| `python -m stockscrape.pipeline companies` | Populate S&P 500 list from Wikipedia |
| `python -m stockscrape.pipeline transcripts` | Fetch transcripts from ROIC.ai |
| `python -m stockscrape.pipeline prices` | Fetch daily stock prices from ROIC.ai |
| `python -m stockscrape.pipeline fundamentals` | Fetch income/balance/cashflow from ROIC.ai |
| `python -m stockscrape.pipeline metrics` | Compute post-earnings direction/return/volatility |
| `python -m stockscrape.pipeline export` | Dump all data to CSVs in `exports/` |
| `python -m stockscrape.pipeline run` | Run all steps above in order |

Add `--tickers AAPL,MSFT` to any command to limit scope.

## Data Schema

**earnings_dataset.csv columns:**
- `ticker`, `call_date`, `fiscal_year`, `fiscal_quarter`, `transcript_text`
- Per window (5d, 10d, 15d, 20d): `direction` (UP/DOWN/FLAT), `return_pct`, `realized_volatility`
- Direction: UP if return > 0.5%, DOWN if < -0.5%, FLAT otherwise

**fundamentals.csv columns:**
- `ticker`, `statement_type` (income/balance/cashflow), `period_date`, `period`, `fiscal_year`
- Income: `revenue`, `gross_profit`, `operating_income`, `net_income`, `eps`, `diluted_eps`, `ebitda`
- Balance: `total_assets`, `total_liabilities`, `total_equity`, `cash_and_equivalents`, `total_debt`
- Cash flow: `operating_cash_flow`, `investing_cash_flow`, `financing_cash_flow`, `free_cash_flow`

**daily_prices.csv columns:**
- `ticker`, `date`, `open`, `high`, `low`, `close`, `adj_close`, `volume`
