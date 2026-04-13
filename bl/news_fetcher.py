# bl/news_fetcher.py
"""
Fetches recent Tadawul news AND issuer announcements for the last N days
directly from the Saudi Exchange API — no database required.

Returns a flat, deduplicated list of formatted headline strings
ready to be fed into the OpenAI prompt.
"""

import json
import math
import time
import logging
from datetime import datetime, timedelta
from typing import Optional

import requests

log = logging.getLogger(__name__)


class RecentNewsFetcher:
    """
    Combines two Saudi Exchange API endpoints:
      1. General market news  →  /newsandreports/issuer-news/ endpoint
      2. Issuer announcements →  /issuer-announcements/ endpoint

    Both are queried for the last `days_back` days.
    Results are formatted as rich one-line strings and deduplicated.

    Usage
    -----
        fetcher = RecentNewsFetcher(days_back=7)
        headlines: list[str] = fetcher.fetch()
    """

    BASE_URL = "https://www.saudiexchange.sa"

    # General market news endpoint (same as NewsTadawul class)
    _NEWS_URL = (
        BASE_URL
        + "/wps/portal/saudiexchange/newsandreports/issuer-news/"
        "!ut/p/z1/04_Sj9CPykssy0xPLMnMz0vMAfIjo8ziTR3NDIw8LAz8_R0tzQ0C3byc3D19HI0tzMz1w1EV"
        "GAQHmAIVBPga-xgEGbgbmOlHEaPfAAdwNCCsPwpViYWvu5lBoJ9joL-RuamBe5gBugIsTgQrwOOG4MQi_YLc"
        "0AiDzIB0AAdsuwE!/p0/IZ7_5A602H80O0TRC068TFQ7NN00C3="
        "CZ6_5A602H80OOA970QFJBGILA3867=NJgetNewsListData=/"
    )

    # Issuer announcements endpoint (same as the announcement scraper)
    _ANN_URL = (
        BASE_URL
        + "/wps/portal/saudiexchange/newsandreports/issuer-news/issuer-announcements/"
        "!ut/p/z1/lY_NDoIwHMOfhQcwqxD-zOPUODAgTBjiLmYHY0h0ejA-v8Qb-BHsrcmvacsMa5hx9tGe7L29"
        "Onvu_N7QIRQEP-bIEVcLEEpJuuLTpU9s1wd4JglqI1TuRyFkDWb-yqMsQqhVkQUptpCgcXl8kRjRb_pILmZR"
        "t2A9l0kqAk7REPhwcVDy_uEF_BhZHh27XbRu0CYT4XlP_MzK5g!!/p0/IZ7_5A602H80O0HTC060SG6UT81DI1="
        "CZ6_5A602H80O0HTC060SG6UT81D26=NJgetAnnouncementListData=/"
    )

    _HEADERS = {
        "Accept": "*/*",
        "Accept-Encoding": "gzip, deflate, br",
        "Accept-Language": "en-US,en;q=0.9",
        "Content-Type": "application/x-www-form-urlencoded; charset=UTF-8",
        "Origin": "https://www.saudiexchange.sa",
        "Referer": "https://www.saudiexchange.sa/wps/portal/saudiexchange/newsandreports/issuer-news",
        "User-Agent": (
            "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
            "AppleWebKit/605.1.15 (KHTML, like Gecko) Version/18.5 Safari/605.1.15"
        ),
        "X-Requested-With": "XMLHttpRequest",
    }

    def __init__(
        self,
        days_back: int = 7,
        page_size: int = 50,
        locale: str = "en",
        delay: float = 0.4,
        max_retries: int = 3,
        max_pages_per_source: int = 10,
    ):
        """
        Parameters
        ----------
        days_back             : How many calendar days back to fetch (default 7).
        page_size             : Items per API request (max ~100).
        locale                : 'en' for English headlines, 'ar' for Arabic.
        delay                 : Seconds to sleep between paginated requests.
        max_retries           : Retries per failed HTTP call.
        max_pages_per_source  : Hard cap on pagination per endpoint.
        """
        self.days_back  = days_back
        self.page_size  = page_size
        self.locale     = locale
        self.delay      = delay
        self.max_retries = max_retries
        self.max_pages  = max_pages_per_source

        now = datetime.now()
        self._to_dt   = now
        self._from_dt = now - timedelta(days=days_back)

        # API date format: MM/DD/YYYY
        self._from_str = self._from_dt.strftime("%m/%d/%Y")
        self._to_str   = now.strftime("%m/%d/%Y")

        self._session = requests.Session()
        self._session.headers.update(self._HEADERS)

    # ── Public ───────────────────────────────────────────────────────────────

    def fetch(self) -> list[str]:
        """
        Fetch recent news + announcements and return as deduplicated
        list of headline strings.

        Each string looks like:
          "[2026-04-10] [1211] MAADEN – Invites shareholders to AGM (stock -0.36%)"
          "[2026-04-11] Market News: Saudi banks report strong Q1 earnings"
        """
        log.info(
            "RecentNewsFetcher: %s → %s  (%d days back)",
            self._from_str, self._to_str, self.days_back,
        )

        news  = self._fetch_from_news_endpoint()
        annts = self._fetch_from_announcements_endpoint()

        combined = news + annts

        # Deduplicate while preserving order
        seen:   set[str]  = set()
        unique: list[str] = []
        for item in combined:
            if item not in seen:
                seen.add(item)
                unique.append(item)

        log.info("RecentNewsFetcher: %d unique headlines total.", len(unique))
        return unique

    # ── News endpoint ────────────────────────────────────────────────────────

    def _fetch_from_news_endpoint(self) -> list[str]:
        results: list[str] = []

        # Page 1 — also tells us the totalCount
        data  = self._post(self._NEWS_URL, self._news_payload(1))
        items = data.get("announcementList", [])
        results.extend(filter(None, (self._fmt_news(i) for i in items)))

        total   = data.get("totalCount", 0)
        n_pages = min(math.ceil(total / self.page_size), self.max_pages)

        for page in range(2, n_pages + 1):
            time.sleep(self.delay)
            try:
                data  = self._post(self._NEWS_URL, self._news_payload(page))
                items = data.get("announcementList", [])
                if not items:
                    break

                # Early-stop: if the LAST item on this page is older than our window
                oldest_ts = self._parse_ts_news(items[-1].get("timestamp", ""))
                if oldest_ts and oldest_ts < self._from_dt:
                    # Include only items still inside the window
                    for i in items:
                        ts = self._parse_ts_news(i.get("timestamp", ""))
                        if ts and ts >= self._from_dt:
                            fmt = self._fmt_news(i)
                            if fmt:
                                results.append(fmt)
                    break

                results.extend(filter(None, (self._fmt_news(i) for i in items)))

            except Exception as exc:
                log.warning("News page %d skipped: %s", page, exc)
                break

        log.info("  news endpoint → %d items", len(results))
        return results

    def _news_payload(self, page: int) -> dict:
        return {
            "annoucmentType": "",
            "symbol": "",
            "fromDate": self._from_str,
            "toDate": self._to_str,
            "datePeriod": "",
            "textSearch": "",
            "pageNumberDb": str(page),
            "pageSize": str(self.page_size),
            "requestLocale": self.locale,
        }

    def _fmt_news(self, item: dict) -> Optional[str]:
        """Format a single news item into a one-line string."""
        date_str  = self._reformat_ddmmyyyy(item.get("newsDateStr", "")[:10])
        symbol    = item.get("SYMBOL", "").strip()
        title     = item.get("TITLE", "").strip()
        desc      = item.get("SHORT_DESC", "").strip()
        chg       = item.get("indexStockChangePresentage")

        if not title:
            return None

        parts = [f"[{date_str}]"]
        if symbol:
            parts.append(f"[{symbol}]")
        parts.append(title)
        if desc and desc.lower() != title.lower():
            parts.append(f"– {desc}")
        if chg is not None and chg != 0:
            parts.append(f"(stock {chg:+.2f}%)")

        return " ".join(parts)

    # ── Announcements endpoint ────────────────────────────────────────────────

    def _fetch_from_announcements_endpoint(self) -> list[str]:
        results: list[str] = []

        for page in range(1, self.max_pages + 1):
            if page > 1:
                time.sleep(self.delay)
            try:
                data  = self._post(self._ANN_URL, self._ann_payload(page))
                items = data.get("announcementList", [])
                if not items:
                    break

                reached_cutoff = False
                for item in items:
                    # Announcements are newest-first; stop when we pass the cutoff
                    ts = self._parse_ts_ann(item.get("newsDateStr", ""))
                    if ts and ts < self._from_dt:
                        reached_cutoff = True
                        break
                    fmt = self._fmt_announcement(item)
                    if fmt:
                        results.append(fmt)

                if reached_cutoff:
                    break

            except Exception as exc:
                log.warning("Announcements page %d skipped: %s", page, exc)
                break

        log.info("  announcements endpoint → %d items", len(results))
        return results

    def _ann_payload(self, page: int) -> dict:
        return {
            "annoucmentType": "1_-1",
            "symbol": "",
            "sectorDpId": "",
            "searchType": "",
            "fromDate": self._from_str,
            "toDate": self._to_str,
            "datePeriod": "",
            "productType": "",
            "advisorsList": "",
            "textSearch": "",
            "pageNumberDb": str(page),
            "pageSize": str(self.page_size),
        }

    def _fmt_announcement(self, item: dict) -> Optional[str]:
        """Format a single announcement into a one-line string."""
        date_str = self._reformat_ddmmyyyy(item.get("newsDateStr", "")[:10])
        symbol   = item.get("SYMBOL", "").strip()
        title    = item.get("TITLE", "").strip()
        desc     = item.get("SHORT_DESC", "").strip()
        chg      = item.get("indexStockChangePresentage")

        if not title:
            return None

        parts = [f"[{date_str}]"]
        if symbol:
            parts.append(f"[{symbol}]")
        parts.append(title)
        if desc and desc.lower() != title.lower():
            # Truncate very long descriptions
            short = desc[:160] + "…" if len(desc) > 160 else desc
            parts.append(f"– {short}")
        if chg is not None and chg != 0:
            parts.append(f"(stock {chg:+.2f}%)")

        return " ".join(parts)

    # ── HTTP helpers ──────────────────────────────────────────────────────────

    def _post(self, url: str, payload: dict) -> dict:
        """POST with retry. Raises on final failure."""
        for attempt in range(1, self.max_retries + 1):
            try:
                resp = self._session.post(url, data=payload, timeout=30)
                resp.raise_for_status()
                return resp.json()
            except (requests.RequestException, json.JSONDecodeError) as exc:
                log.warning("HTTP attempt %d/%d failed: %s", attempt, self.max_retries, exc)
                if attempt < self.max_retries:
                    time.sleep(self.delay * attempt)
                else:
                    raise

    # ── Date helpers ──────────────────────────────────────────────────────────

    @staticmethod
    def _parse_ts_news(raw: str) -> Optional[datetime]:
        """'Mar 25, 2026 3:35:08 PM'  →  datetime"""
        for fmt in ("%b %d, %Y %I:%M:%S %p", "%b %d, %Y"):
            try:
                return datetime.strptime(raw.strip(), fmt)
            except (ValueError, TypeError):
                pass
        return None

    @staticmethod
    def _parse_ts_ann(raw: str) -> Optional[datetime]:
        """'12/04/2026 16:21:05'  →  datetime (date only for comparison)"""
        try:
            return datetime.strptime(raw.strip()[:10], "%d/%m/%Y")
        except (ValueError, TypeError):
            return None

    @staticmethod
    def _reformat_ddmmyyyy(raw: str) -> str:
        """'12/04/2026'  →  '2026-04-12' (ISO format for readability)"""
        try:
            return datetime.strptime(raw, "%d/%m/%Y").strftime("%Y-%m-%d")
        except ValueError:
            return raw or "????-??-??"