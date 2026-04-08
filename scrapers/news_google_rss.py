import logging

import feedparser

from db.connection import DatabaseConnection
from scrapers.sentiment import SentimentAnalyzer


class GoogleRSSFetcher:
    FEED_URLS = [
        "https://news.google.com/rss/search?q=saudi+arabia+oil+price&hl=en-US&gl=US&ceid=US:en",
        "https://news.google.com/rss/search?q=saudi+vision+2030&hl=en-US&gl=US&ceid=US:en",
        "https://news.google.com/rss/search?q=OPEC+production&hl=en",
        "https://news.google.com/rss/search?q=saudi+aramco&hl=en",
        "https://news.google.com/rss/search?q=tadawul+saudi+stock&hl=en",
        "https://news.google.com/rss/search?q=brent+crude+oil+price&hl=en",
        "https://news.google.com/rss/search?q=interest+rate+federal+reserve&hl=en",
        "https://news.google.com/rss/search?q=saudi+government+spending+budget&hl=en",
        "https://news.google.com/rss/search?q=middle+east+war+conflict&hl=en",
        "https://news.google.com/rss/search?q=global+recession+economy&hl=en",
    ]

    def __init__(self, db_connection: DatabaseConnection):
        self.db = db_connection
        self.sentiment = SentimentAnalyzer()
        self.logger = logging.getLogger(__name__)

    def fetch_all(self):
        total_inserted = 0
        total_skipped = 0

        for url in self.FEED_URLS:
            try:
                feed = feedparser.parse(url)
            except Exception:
                self.logger.exception("Failed to parse RSS feed: %s", url)
                continue

            if getattr(feed, "bozo", False):
                self.logger.warning("RSS feed parse issue for %s: %s", url, getattr(feed, "bozo_exception", None))

            feed_title = getattr(feed.feed, "title", None)
            entries = getattr(feed, "entries", [])
            inserted = 0
            skipped = 0

            for entry in entries:
                title = entry.get("title")
                link = entry.get("link")
                published = entry.get("published")
                source = None
                source_data = entry.get("source")
                if isinstance(source_data, dict):
                    source = source_data.get("title")
                if not source:
                    source = feed_title

                if not title or not link:
                    skipped += 1
                    continue

                sentiment_score = self.sentiment.score(title)

                try:
                    with self.db.connection() as conn:
                        with conn.cursor() as cursor:
                            cursor.execute(
                                "INSERT INTO news (source, published_date, title, summary, url, sentiment_score) "
                                "VALUES (%s, %s, %s, %s, %s, %s) "
                                "ON CONFLICT (url) DO NOTHING;",
                                (source, published, title, "", link, sentiment_score),
                            )
                            if cursor.rowcount == 1:
                                inserted += 1
                            else:
                                skipped += 1
                except Exception:
                    self.logger.exception("Failed to insert RSS article: %s", link)
                    skipped += 1

            total_inserted += inserted
            total_skipped += skipped
            self.logger.info(
                "Feed %s processed: inserted=%s skipped=%s", url, inserted, skipped
            )

        self.logger.info(
            "Google RSS fetch complete: total inserted=%s total skipped=%s", total_inserted, total_skipped
        )
