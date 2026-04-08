# news_tadawul.py

import requests
import json
import math
import time
from datetime import datetime
import os
import psycopg2
from dotenv import load_dotenv



class NewsTadawul:
    """Fetches all market news from Saudi Exchange (Tadawul) API."""

    BASE_URL = "https://www.saudiexchange.sa"
    API_PATH = (
        "/wps/portal/saudiexchange/newsandreports/issuer-news/"
        "!ut/p/z1/04_Sj9CPykssy0xPLMnMz0vMAfIjo8ziTR3NDIw8LAz8_R0tzQ0C3byc3D19HI0tzMz1w1EV"
        "GAQHmAIVBPga-xgEGbgbmOlHEaPfAAdwNCCsPwpViYWvu5lBoJ9joL-RuamBe5gBugIsTgQrwOOG4MQi_YLc"
        "0AiDzIB0AAdsuwE!/p0/IZ7_5A602H80O0TRC068TFQ7NN00C3="
        "CZ6_5A602H80OOA970QFJBGILA3867=NJgetNewsListData=/"
    )

    HEADERS = {
        "Accept": "*/*",
        "Accept-Encoding": "gzip, deflate, br",
        "Accept-Language": "en-US,en;q=0.9",
        "Content-Type": "application/x-www-form-urlencoded; charset=UTF-8",
        "Origin": "https://www.saudiexchange.sa",
        "Referer": (
            "https://www.saudiexchange.sa/wps/portal/saudiexchange/"
            "newsandreports/issuer-news?locale=ar"
        ),
        "User-Agent": (
            "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
            "AppleWebKit/605.1.15 (KHTML, like Gecko) Version/18.5 Safari/605.1.15"
        ),
        "X-Requested-With": "XMLHttpRequest",
        "Sec-Fetch-Dest": "empty",
        "Sec-Fetch-Mode": "cors",
        "Sec-Fetch-Site": "same-origin",
    }

    def __init__(
        self,
        from_date: str = "01/01/2023",
        to_date: str | None = None,
        page_size: int = 50,
        locale: str = "ar",
        delay: float = 1.0,
        max_retries: int = 3,
    ):
        """
        Args:
            from_date:    Start date in MM/DD/YYYY format.
            to_date:      End date in MM/DD/YYYY format (defaults to today).
            page_size:    Number of results per page.
            locale:       'ar' for Arabic, 'en' for English.
            delay:        Seconds to wait between requests.
            max_retries:  Number of retries on failure per page.
        """
        self.from_date = from_date
        self.to_date = to_date or datetime.now().strftime("%m/%d/%Y")
        self.page_size = page_size
        self.locale = locale
        self.delay = delay
        self.max_retries = max_retries

        self.session = requests.Session()
        self.session.headers.update(self.HEADERS)

        self.all_news: list[dict] = []

    # ------------------------------------------------------------------ #
    #  Internal helpers
    # ------------------------------------------------------------------ #

    def _build_payload(self, page_number: int) -> dict:
        return {
            "annoucmentType": "",
            "symbol": "",
            "fromDate": self.from_date,
            "toDate": self.to_date,
            "datePeriod": "",
            "textSearch": "",
            "pageNumberDb": str(page_number),
            "pageSize": str(self.page_size),
            "requestLocale": self.locale,
        }

    @staticmethod
    def _parse_timestamp(raw: str) -> str:
        """Convert 'Mar 25, 2026 3:35:08 PM' → '2026-03-25 15:35:08'."""
        try:
            dt = datetime.strptime(raw.strip(), "%b %d, %Y %I:%M:%S %p")
            return dt.strftime("%Y-%m-%d %H:%M:%S")
        except (ValueError, TypeError):
            return raw

    def _transform(self, item: dict) -> dict:
        announcement_path = item.get("announcementUrl", "")
        full_url = f"{self.BASE_URL}{announcement_path}" if announcement_path else ""
        return {
            "title": item.get("TITLE", "").strip(),
            "publish_time": self._parse_timestamp(item.get("timestamp", "")),
            "url": full_url,
        }

    # ------------------------------------------------------------------ #
    #  Network
    # ------------------------------------------------------------------ #

    def _fetch_page(self, page_number: int) -> dict:
        """Fetch a single page with retry logic."""
        url = f"{self.BASE_URL}{self.API_PATH}"
        payload = self._build_payload(page_number)

        for attempt in range(1, self.max_retries + 1):
            try:
                resp = self.session.post(url, data=payload, timeout=30)
                resp.raise_for_status()
                return resp.json()
            except (requests.RequestException, json.JSONDecodeError) as exc:
                print(f"  ⚠  Page {page_number} attempt {attempt}/{self.max_retries} failed: {exc}")
                if attempt < self.max_retries:
                    time.sleep(self.delay * attempt)
                else:
                    raise

    # ------------------------------------------------------------------ #
    #  Public API
    # ------------------------------------------------------------------ #

    def fetch_all(self) -> list[dict]:
        """Paginate through every page and return the full list of news."""

        print(
            f"{'='*60}\n"
            f"  Tadawul News Scraper\n"
            f"  From : {self.from_date}\n"
            f"  To   : {self.to_date}\n"
            f"  Size : {self.page_size}  |  Locale : {self.locale}\n"
            f"{'='*60}"
        )

        # -- first page to discover totalCount -------------------------
        print(f"\n▶ Fetching page 1 …")
        data = self._fetch_page(1)
        total_count = data.get("totalCount", 0)
        items = data.get("announcementList", [])
        self.all_news.extend(self._transform(i) for i in items)

        total_pages = math.ceil(total_count / self.page_size)
        print(f"  Total records : {total_count}")
        print(f"  Total pages   : {total_pages}")
        print(f"  Fetched so far: {len(self.all_news)}")

        # -- remaining pages -------------------------------------------
        for page in range(2, total_pages + 1):
            time.sleep(self.delay)
            print(f"▶ Fetching page {page}/{total_pages} …", end=" ")
            try:
                data = self._fetch_page(page)
                items = data.get("announcementList", [])
                if not items:
                    print("empty → stopping.")
                    break
                self.all_news.extend(self._transform(i) for i in items)
                print(f"OK  ({len(self.all_news)} total)")
            except Exception as exc:
                print(f"SKIPPED ({exc})")
                continue

        print(f"\n✅ Done. Total news fetched: {len(self.all_news)}\n")
        return self.all_news

    def save(self, filepath: str = "tadawul_news.json") -> None:
        """Save collected news to a JSON file."""
        with open(filepath, "w", encoding="utf-8") as fh:
            json.dump(self.all_news, fh, ensure_ascii=False, indent=2)
        print(f"💾 Saved {len(self.all_news)} items → {filepath}")

def load_json_to_db(self, filepath: str = "scrapers/tadawul_news.json") -> None:
    """Read saved JSON file and insert news into PostgreSQL."""

    # Load environment variables
    load_dotenv()

    db_config = {
        "dbname": os.getenv("DB_NAME"),
        "user": os.getenv("DB_USER"),
        "password": os.getenv("DB_PASSWORD"),
        "host": os.getenv("DB_HOST"),
        "port": os.getenv("DB_PORT"),
    }

    # Read JSON file
    with open(filepath, "r", encoding="utf-8") as fh:
        news_items = json.load(fh)

    print(f"📂 Loaded {len(news_items)} records from {filepath}")

    try:
        conn = psycopg2.connect(**db_config)
        cur = conn.cursor()

        insert_query = """
            INSERT INTO news (source, published_date, title, summary, url)
            VALUES (%s, %s, %s, %s, %s)
            ON CONFLICT (url) DO NOTHING;
        """

        inserted = 0

        for item in news_items:
            cur.execute(
                insert_query,
                (
                    "tadawul",                    # source
                    item.get("publish_time"),     # published_date
                    item.get("title"),
                    None,                         # summary
                    item.get("url"),
                ),
            )
            if cur.rowcount > 0:
                inserted += 1

        conn.commit()
        cur.close()
        conn.close()

        print(f"✅ Inserted {inserted} new records into database")
        print("✅ Done.")

    except Exception as e:
        print(f"❌ Database error: {e}")
# ====================================================================== #
#  CLI entry-point
# ====================================================================== #

if __name__ == "__main__":
    # scraper = NewsTadawul(
    #     from_date="01/01/2023",          # start date  (MM/DD/YYYY)
    #     to_date=datetime.now().strftime("%m/%d/%Y"),  # today
    #     page_size=50,                     # results per request
    #     locale="ar",                      # ar | en
    #     delay=1.0,                        # seconds between requests
    #     max_retries=3,                    # retries per failed page
    # )

    # scraper.fetch_all()
    # scraper.save("tadawul_news.json")
    load_json_to_db("scrapers/tadawul_news.json")