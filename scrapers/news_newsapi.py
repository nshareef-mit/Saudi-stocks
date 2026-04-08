import logging
import requests
from datetime import datetime, timedelta

from db.connection import DatabaseConnection
from scrapers.sentiment import SentimentAnalyzer


class NewsAPIFetcher:
    API_KEY = "005df31b5e7c48b2817130cea473373e"

    QUERY_KEYWORDS = [
        "saudi arabia oil",
        "saudi vision 2030",
        "OPEC oil price",
        "tadawul stock market",
        "middle east geopolitics",
    ]

    BASE_URL = "https://newsapi.org/v2/everything"

    def __init__(self, db_connection: DatabaseConnection):
        self.db = db_connection
        self.sentiment = SentimentAnalyzer()
        self.logger = logging.getLogger(__name__)

    # ✅ Get last saved date
    def get_last_published_date(self):
        rows = self.db.fetch_all("SELECT MAX(published_date) FROM news;")
        last_date = rows[0][0]
        if last_date:
            return last_date
        return None

    def fetch_range(self, start_date: datetime, end_date: datetime):
        inserted_total = 0
        skipped_total = 0

        current_date = start_date

        try:
            while current_date < end_date:
                next_date = current_date + timedelta(days=1)

                print(f"Fetching {current_date.date()}")

                for query in self.QUERY_KEYWORDS:
                    for page in range(1, 6):

                        params = {
                            "q": query,
                            "from": current_date.strftime("%Y-%m-%d"),
                            "to": next_date.strftime("%Y-%m-%d"),
                            "sortBy": "publishedAt",
                            "language": "en",
                            "pageSize": 100,
                            "page": page,
                            "apiKey": self.API_KEY,
                        }

                        try:
                            response = requests.get(self.BASE_URL, params=params, timeout=20)
                            response.raise_for_status()
                            payload = response.json()
                        except Exception:
                            self.logger.exception("Request failed")
                            continue

                        articles = payload.get("articles", [])
                        if not articles:
                            break

                        for article in articles:
                            title = article.get("title")
                            summary = article.get("description")
                            link = article.get("url")
                            published_at = article.get("publishedAt")
                            source = None

                            source_data = article.get("source")
                            if isinstance(source_data, dict):
                                source = source_data.get("name")

                            if not title or not link:
                                skipped_total += 1
                                continue

                            sentiment_text = f"{title} {summary or ''}"
                            sentiment_score = self.sentiment.score(sentiment_text)

                            try:
                                with self.db.connection() as conn:
                                    with conn.cursor() as cursor:
                                        cursor.execute(
                                            """
                                            INSERT INTO news 
                                            (source, published_date, title, summary, url, sentiment_score)
                                            VALUES (%s, %s, %s, %s, %s, %s)
                                            ON CONFLICT (url) DO NOTHING;
                                            """,
                                            (
                                                source,
                                                published_at,
                                                title,
                                                summary,
                                                link,
                                                sentiment_score,
                                            ),
                                        )

                                        if cursor.rowcount == 1:
                                            inserted_total += 1
                                        else:
                                            skipped_total += 1

                            except Exception:
                                self.logger.exception("Insert failed")
                                skipped_total += 1

                current_date = next_date

        except KeyboardInterrupt:
            print("\nStopped safely. Resume will continue from last saved date.")
            return

        print(f"Done. Inserted={inserted_total}, Skipped={skipped_total}")


# ✅ Runnable
if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)

    db = DatabaseConnection()
    fetcher = NewsAPIFetcher(db)

    end = datetime.utcnow()

    last_date = fetcher.get_last_published_date()

    if last_date:
        start = last_date + timedelta(seconds=1)
        print(f"Resuming from {start}")
    else:
        start = end - timedelta(days=180)
        print(f"No data found. Starting 6 months back from {start}")

    fetcher.fetch_range(start, end)