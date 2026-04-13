
```bash
sudo apt-get update
sudo apt-get install -y postgresql postgresql-contrib
sudo service postgresql start
sudo su - postgres -c "psql -c \"CREATE USER stockuser WITH PASSWORD 'stockpass123';\""
sudo su - postgres -c "psql -c \"CREATE DATABASE saudi_stocks OWNER stockuser;\""

sudo su - postgres -c "psql -d saudi_stocks -c \"SELECT date, LAG(date) OVER (ORDER BY date) AS prev_date, date - LAG(date) OVER(ORDER BY date) AS gap FROM public.prices WHERE symbol ='2222' ORDER BY date;\""
```
sudo su - postgres -c "psql -d saudi_stocks -c \"SELECT COUNT(*) FROM companies;\""


sudo su - postgres -c "psql -d saudi_stocks -c \" SELECT * FROM news ORDER BY published_date DESC LIMIT 1;\""

sudo su - postgres -c "psql -d saudi_stocks -c \"
CREATE TABLE IF NOT EXISTS social_posts (
    id SERIAL PRIMARY KEY,
    platform VARCHAR(50),
    account VARCHAR(100),
    post_id VARCHAR(50) UNIQUE,
    content TEXT,
    published_date TIMESTAMP,
    likes INT,
    retweets INT,
    replies INT,
    url VARCHAR(500),
    related_symbols TEXT,
    fetched_at TIMESTAMP DEFAULT NOW()
);\""

sudo su - postgres -c "psql -d saudi_stocks -c \" ALTER TABLE embeddings ADD COLUMN IF NOT EXISTS exec_date TIMESTAMP;\""


sudo su - postgres -c "psql -d saudi_stocks -c \"ALTER TABLE public.embeddings RENAME COLUMN exec_date TO news_date;\""

pip install playwright
playwright install


Then install Python dependencies:

```bash
pip install psycopg2-binary python-dotenv
```

Create a `.env` file in the project root:

```
DATABASE_URL=postgresql://stockuser:stockpass123@localhost:5432/saudi_stocks
```

---

**Step 2: Create the following files with these exact names.**

Create folder structure first:

```
project/
├── db/
│   ├── connection.py
│   └── schema.py
```

**File: `db/connection.py`**

Create a class called `DatabaseConnection` that:
- Reads `DATABASE_URL` from `.env` using `python-dotenv`
- Has a method `get_connection()` that returns a psycopg2 connection
- Has a method `execute_query(query, params=None)` for INSERT/UPDATE
- Has a method `fetch_all(query, params=None)` for SELECT
- Uses context manager pattern (with statement support)
- Handles connection errors with proper logging

**File: `db/schema.py`**

Create a class called `SchemaManager` that:
- Takes a `DatabaseConnection` instance
- Has a method `create_all_tables()` that runs CREATE TABLE IF NOT EXISTS for all 6 tables:

Table 1 — `companies`
```
symbol VARCHAR(10) PRIMARY KEY, name_ar VARCHAR(255), name_en VARCHAR(255),
sector_ar VARCHAR(100), sector_en VARCHAR(100), share_type VARCHAR(50),
total_shares BIGINT, paid_capital BIGINT, isin VARCHAR(20),
founded_date DATE, fiscal_year_end VARCHAR(5), auditor VARCHAR(100),
market_cap DECIMAL(15,2), company_url VARCHAR(500), last_updated TIMESTAMP DEFAULT NOW()
```

Table 2 — `daily_prices`
```
symbol VARCHAR(10), trade_date DATE, open_price DECIMAL(10,2),
high_price DECIMAL(10,2), low_price DECIMAL(10,2), close_price DECIMAL(10,2),
prev_close DECIMAL(10,2), change_value DECIMAL(10,2), change_pct DECIMAL(6,2),
volume BIGINT, value_traded DECIMAL(15,2), num_trades INT,
best_bid_price DECIMAL(10,2), best_bid_qty INT,
best_offer_price DECIMAL(10,2), best_offer_qty INT,
PRIMARY KEY (symbol, trade_date)
```

Table 3 — `financials`
```
symbol VARCHAR(10), period_end DATE, period_type VARCHAR(10),
total_revenue DECIMAL(15,2), net_profit_before_zakat DECIMAL(15,2),
zakat_tax DECIMAL(15,2), net_profit DECIMAL(15,2), eps DECIMAL(10,2),
total_assets DECIMAL(15,2), total_liabilities DECIMAL(15,2),
total_equity DECIMAL(15,2), operating_cash_flow DECIMAL(15,2),
investing_cash_flow DECIMAL(15,2), financing_cash_flow DECIMAL(15,2),
cash_end DECIMAL(15,2),
PRIMARY KEY (symbol, period_end, period_type)
```

Table 4 — `dividends`
```
symbol VARCHAR(10), announcement_date DATE, eligibility_date DATE,
distribution_date DATE, amount_per_share DECIMAL(10,2),
PRIMARY KEY (symbol, eligibility_date)
```

Table 5 — `announcements`
```
id SERIAL PRIMARY KEY, symbol VARCHAR(10), announcement_date TIMESTAMP,
title_ar TEXT, price_on_date DECIMAL(10,2), change_pct_on_date DECIMAL(6,2)
```

Table 6 — `news`
```
id SERIAL PRIMARY KEY, source VARCHAR(100), published_date TIMESTAMP,
title TEXT, summary TEXT, url VARCHAR(500) UNIQUE,
sentiment_score DECIMAL(4,2), related_symbols TEXT,
fetched_at TIMESTAMP DEFAULT NOW()
```

- Has a method `drop_all_tables()` for development reset
- Has a method `verify_tables()` that checks all 6 tables exist and prints row counts

**Then create `db/__init__.py`** that exports both classes.

**Finally create `


setup_db.py`** in the project root that:
1. Imports `DatabaseConnection` and `SchemaManager`
2. Connects to the database
3. Calls `create_all_tables()`
4. Calls `verify_tables()` to confirm everything was created
5. Prints success message

Run `setup_db.py` after creating it to verify everything works.

---
Now Scrapper code ! 

## Step 1: Install all dependencies

Run this in the terminal:

```bash
pip install selenium webdriver-manager beautifulsoup4 requests feedparser textblob apscheduler psycopg2-binary python-dotenv
python -m textblob.download_corpora
```

Also install Chrome for Selenium:

```bash
sudo apt-get update
sudo apt-get install -y chromium-browser
```

**Test:** Run `python -c "from selenium import webdriver; print('Selenium OK')"` and `python -c "import feedparser; print('feedparser OK')"` — both should print OK.

---

## Step 2: Create `scrapers/sentiment.py`

Create the file `scrapers/sentiment.py` with a class called `SentimentAnalyzer` that:
- Has a method `score(text)` that takes a string (title + summary combined)
- Uses `TextBlob` to compute polarity
- Returns a float between -1.0 and 1.0
- If text is None or empty, return 0.0
- Handle exceptions gracefully, return 0.0 on error

Also create `scrapers/__init__.py` (empty file).

**Test:** Run this in terminal:
```bash
python -c "from scrapers.sentiment import SentimentAnalyzer; s = SentimentAnalyzer(); print(s.score('Oil prices surge dramatically')); print(s.score('Market crash and recession fears'))"
```
First should be positive, second negative.

---

## Step 3: Create `scrapers/news_newsapi.py`

Create `scrapers/news_newsapi.py` with a class called `NewsAPIFetcher` that:
- Takes a `DatabaseConnection` instance in __init__
- Has a constant `API_KEY = "005df31b5e7c48b2817130cea473373e"`
- Has a list of 5 query URLs:
  - `https://newsapi.org/v2/everything?q=saudi+arabia+oil&apiKey={API_KEY}`
  - `https://newsapi.org/v2/everything?q=saudi+vision+2030&apiKey={API_KEY}`
  - `https://newsapi.org/v2/everything?q=OPEC+oil+price&apiKey={API_KEY}`
  - `https://newsapi.org/v2/everything?q=tadawul+stock+market&apiKey={API_KEY}`
  - `https://newsapi.org/v2/everything?q=middle+east+geopolitics&apiKey={API_KEY}`
- Has a method `fetch_all()` that:
  - Hits each URL with `requests.get()`
  - Parses JSON response, loops through `articles[]`
  - Extracts: `title`, `description` (as summary), `url`, `publishedAt` (as published_date), `source.name` (as source)
  - Scores sentiment using `SentimentAnalyzer` on title + description
  - Inserts into `news` table using `INSERT INTO news (source, published_date, title, summary, url, sentiment_score) VALUES (%s,%s,%s,%s,%s,%s) ON CONFLICT (url) DO NOTHING`
  - Logs how many articles inserted vs skipped (duplicates)
- Add error handling: if one URL fails, continue to next
- Add logging with `logging` module

**Test:**
```bash
python -c "
from db.connection import DatabaseConnection
from scrapers.news_newsapi import NewsAPIFetcher
db = DatabaseConnection()
fetcher = NewsAPIFetcher(db)
fetcher.fetch_all()
print('News count:', db.fetch_all('SELECT COUNT(*) FROM news')[0][0])
"
```
Should show articles inserted and a count > 0.

---

## Step 4: Create `scrapers/news_google_rss.py`

Create `scrapers/news_google_rss.py` with a class called `GoogleRSSFetcher` that:
- Takes a `DatabaseConnection` instance
- Has a list of 10 RSS feed URLs:
  - `https://news.google.com/rss/search?q=saudi+arabia+oil+price&hl=en-US&gl=US&ceid=US:en`
  - `https://news.google.com/rss/search?q=saudi+vision+2030&hl=en-US&gl=US&ceid=US:en`
  - `https://news.google.com/rss/search?q=OPEC+production&hl=en`
  - `https://news.google.com/rss/search?q=saudi+aramco&hl=en`
  - `https://news.google.com/rss/search?q=tadawul+saudi+stock&hl=en`
  - `https://news.google.com/rss/search?q=brent+crude+oil+price&hl=en`
  - `https://news.google.com/rss/search?q=interest+rate+federal+reserve&hl=en`
  - `https://news.google.com/rss/search?q=saudi+government+spending+budget&hl=en`
  - `https://news.google.com/rss/search?q=middle+east+war+conflict&hl=en`
  - `https://news.google.com/rss/search?q=global+recession+economy&hl=en`
- Has a method `fetch_all()` that:
  - Uses `feedparser.parse(url)` for each feed
  - Extracts from each entry: `title`, `link` (as url), `published` (as published_date), `source.title` or feed title (as source)
  - Set summary to empty string (RSS titles are enough)
  - Score sentiment on title
  - Insert into `news` table with `ON CONFLICT (url) DO NOTHING`
  - Log counts
- Handle errors per feed — if one fails, continue

**Test:**
```bash
python -c "
from db.connection import DatabaseConnection
from scrapers.news_google_rss import GoogleRSSFetcher
db = DatabaseConnection()
fetcher = GoogleRSSFetcher(db)
fetcher.fetch_all()
print('Total news:', db.fetch_all('SELECT COUNT(*) FROM news')[0][0])
"
```
Count should increase from Step 3.


sudo service postgresql start

python -c "
from db.connection import DatabaseConnection

db = DatabaseConnection()
rows = db.fetch_all('SELECT * FROM news ORDER BY published_date DESC LIMIT 5;')

for row in rows:
    print(row)
"

---

## Step 5: Create `scrapers/news_oilprice.py`

Create `scrapers/news_oilprice.py` with a class called `OilPriceRSSFetcher` that:
- Takes a `DatabaseConnection` instance
- Fetches from `https://www.oilprice.com/rss/main`
- Uses `feedparser.parse()`
- Same logic as Google RSS — extract title, link, published, source="OilPrice.com"
- Score sentiment, insert into `news` with `ON CONFLICT (url) DO NOTHING`

**Test:**
```bash
python -c "
from db.connection import DatabaseConnection
from scrapers.news_oilprice import OilPriceRSSFetcher
db = DatabaseConnection()
fetcher = OilPriceRSSFetcher(db)
fetcher.fetch_all()
print('Total news:', db.fetch_all('SELECT COUNT(*) FROM news')[0][0])
"
```

---

## Step 6: Create `scrapers/tadawul_market.py`

Create `scrapers/tadawul_market.py` with a class called `TadawulMarketScraper` that:
- Takes a `DatabaseConnection` instance
- Uses Selenium with headless Chrome (use `webdriver_manager` to auto-install chromedriver)
- Chrome options: `--headless`, `--no-sandbox`, `--disable-dev-shm-usage`, `--disable-gpu`
- Has a method `scrape_market_watch()` that:
  1. Loads `https://www.saudiexchange.sa/wps/portal/saudiexchange/ourmarkets/main-market-watch?locale=ar`
  2. Waits up to 30 seconds for the div `id="marketWatchTable1_wrap"` to appear (use `WebDriverWait`)
  3. Scrolls down the page multiple times to trigger lazy loading of all rows (some tables load rows on scroll)
  4. Finds all `<a class="ellipsis">` elements inside that div
  5. For each link:
     - Extract the Arabic company name from the link text
     - Extract the full href URL
     - Extract `companySymbol` parameter from the URL as the symbol
  6. For each table row (same row as the link), extract price data: last price, change, change%, open, high, low, volume, value traded, number of trades, best bid price/qty, best offer price/qty
  7. Insert/update `companies` table: `INSERT INTO companies (symbol, name_ar, company_url) VALUES (%s,%s,%s) ON CONFLICT (symbol) DO UPDATE SET name_ar=EXCLUDED.name_ar, company_url=EXCLUDED.company_url, last_updated=NOW()`
  8. Insert into `daily_prices` table: `INSERT INTO daily_prices (symbol, trade_date, close_price, change_value, change_pct, open_price, high_price, low_price, volume, value_traded, num_trades, best_bid_price, best_bid_qty, best_offer_price, best_offer_qty) VALUES (...) ON CONFLICT (symbol, trade_date) DO NOTHING`
  9. Use `trade_date = date.today()`
  10. Close the browser when done
- Log how many companies found and how many price rows inserted
- Handle errors: if parsing a row fails, skip it and continue

**Important Selenium notes:**
- The page is JavaScript-rendered. After loading, wait at least 10 seconds for data to appear.
- The table rows are inside `div#marketWatchTable1_wrap`. Each row has multiple `<td>` cells.
- Numbers may have Arabic formatting (commas as thousands separators). Strip commas and convert to float.
- If a cell is empty or "-", set value to None.

**Test:**
```bash
python -c "
from db.connection import DatabaseConnection
from scrapers.tadawul_market import TadawulMarketScraper
db = DatabaseConnection()
scraper = TadawulMarketScraper(db)
scraper.scrape_market_watch()
companies = db.fetch_all('SELECT COUNT(*) FROM companies')
prices = db.fetch_all('SELECT COUNT(*) FROM daily_prices')
print(f'Companies: {companies[0][0]}, Daily prices: {prices[0][0]}')
"
```
Should show 200+ companies and 200+ price rows.

---

## Step 7: Create `scrapers/tadawul_company.py`

Create `scrapers/tadawul_company.py` with a class called `TadawulCompanyScraper` that:
- Takes a `DatabaseConnection` instance
- Uses Selenium headless Chrome (same setup as Step 6)
- Has a method `scrape_company_profile(symbol, profile_url)` that:
  1. Loads the profile URL in Selenium
  2. Waits for page to load (15 seconds)
  3. Scrapes company metadata: sector_ar, sector_en, share_type, total_shares, paid_capital, isin, founded_date, fiscal_year_end, auditor, market_cap
  4. Updates the `companies` table for that symbol
  5. Scrapes financial statements tab (if available): total_revenue, net_profit, eps, total_assets, total_liabilities, total_equity, operating_cash_flow, etc. — insert into `financials`
  6. Scrapes dividends tab: announcement_date, eligibility_date, distribution_date, amount_per_share — insert into `dividends`
  7. Scrapes announcements tab: announcement_date, title_ar — insert into `announcements`
  8. All inserts use `ON CONFLICT DO NOTHING`
- Has a method `scrape_all_companies()` that:
  1. Queries `SELECT symbol, company_url FROM companies`
  2. Loops through each, calls `scrape_company_profile()`
  3. Adds a `time.sleep(3)` between each company (respect rate limits)
  4. If one company fails, log error and continue to next
- Handle all errors gracefully with try/except and logging

**Test:**
```bash
python -c "
from db.connection import DatabaseConnection
from scrapers.tadawul_company import TadawulCompanyScraper
db = DatabaseConnection()
scraper = TadawulCompanyScraper(db)
# Test with just Aramco (symbol 2222)
row = db.fetch_all(\"SELECT symbol, company_url FROM companies WHERE symbol='2222'\")
if row:
    scraper.scrape_company_profile(row[0][0], row[0][1])
    print('Financials:', db.fetch_all(\"SELECT COUNT(*) FROM financials WHERE symbol='2222'\")[0][0])
else:
    print('Run Step 6 first to populate companies')
"
```

---

## Step 8: Create `backfill.py`

Create `backfill.py` in the project root that:
1. Imports `DatabaseConnection`, `TadawulMarketScraper`, `TadawulCompanyScraper`
2. Runs `TadawulMarketScraper.scrape_market_watch()` to get all companies
3. Runs `TadawulCompanyScraper.scrape_all_companies()` to backfill profiles, financials, dividends, announcements
4. Prints summary: total companies, financials rows, dividends rows, announcements rows

This is a ONE-TIME script. It will take a long time (200+ companies × 3 second delays = ~10 minutes minimum).

**Test:**
```bash
python backfill.py
```
Watch for progress logs. After completion, verify row counts.

---

## Step 9: Create `scheduler.py`

Create `scheduler.py` in the project root that:
- Uses `APScheduler` (`BlockingScheduler`)
- Imports all scrapers
- Defines these scheduled jobs:

| Job | Schedule | What it does |
|-----|----------|--------------|
| `scrape_daily_prices` | Every day at 16:00 (4 PM) Asia/Riyadh timezone | Run `TadawulMarketScraper.scrape_market_watch()` |
| `fetch_news_newsapi` | Every 30 minutes | Run `NewsAPIFetcher.fetch_all()` |
| `fetch_news_google_rss` | Every 30 minutes | Run `GoogleRSSFetcher.fetch_all()` |
| `fetch_news_oilprice` | Every 60 minutes | Run `OilPriceRSSFetcher.fetch_all()` |
| `scrape_announcements` | Every day at 17:00 (5 PM) Asia/Riyadh | Run `TadawulCompanyScraper.scrape_all_companies()` (only new announcements) |
| `scrape_financials` | Every Friday at 18:00 (6 PM) Asia/Riyadh | Run `TadawulCompanyScraper.scrape_all_companies()` (check for new financials) |

- Add logging for every job start and completion
- Handle errors in each job so one failure doesn't crash the scheduler
- Print "Scheduler started" when launched

**Test:**
```bash
python scheduler.py &
# Wait 1 minute, then check:
python -c "from db.connection import DatabaseConnection; db = DatabaseConnection(); print('News:', db.fetch_all('SELECT COUNT(*) FROM news')[0][0])"
# Kill the scheduler after testing:
kill %1
```

---

## Step 10: Create `requirements.txt`

Create `requirements.txt` with:
```
selenium
webdriver-manager
beautifulsoup4
requests
feedparser
textblob
apscheduler
psycopg2-binary
python-dotenv
```

**Test:**
```bash
pip install -r requirements.txt
```

---

## Final Validation

Run these checks:
```bash
python -c "
from db.connection import DatabaseConnection
db = DatabaseConnection()
tables = ['companies','daily_prices','financials','dividends','announcements','news']
for t in tables:
    count = db.fetch_all(f'SELECT COUNT(*) FROM {t}')[0][0]
    print(f'{t}: {count} rows')
"
```

Expected results:
- `companies`: 200+ rows
- `daily_prices`: 200+ rows
- `news`: 100+ rows
- `financials`: rows for major companies
- `dividends`: some rows
- `announcements`: some rows

---

**Build each file one at a time. After each file, run the test command I provided. Only move to the next step after the current one passes. If anything fails, fix it before continuing.**
