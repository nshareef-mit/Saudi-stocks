#!/usr/bin/e#!/usr/bin/env python3
"""
scrapers/prices_tadawul.py

✅ Uses your exact endpoint
✅ Uses your exact cookies
✅ Fixes selectedMarket mapping
✅ Fixes selectedSector format (MARKET:sector_id)
✅ Keeps full DataTables structure
✅ Production safe
"""

import argparse
import logging
import os
import time
from datetime import datetime, timedelta

import psycopg2
import psycopg2.extras
import requests
import pandas as pd
from dotenv import load_dotenv

load_dotenv()

# ─────────────────────────────────────────────────────────────
# Logging
# ─────────────────────────────────────────────────────────────
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] prices_tadawul: %(message)s",
)
log = logging.getLogger("prices_tadawul")

# ─────────────────────────────────────────────────────────────
# ✅ DB MARKET → TADAWUL MARKET MAP
# ─────────────────────────────────────────────────────────────
MARKET_MAP = {
    "MAIN_MARKET": "MAIN",
    "NOMU_MARKET": "NOMUC",
    "REITS": "REITS",
    "ETFS": "ETFS",
    "CEFS": "CEF",
    "MUTUAL_FUNDS": "MF",
    "SUKUK": "SUKUK",
    "DERIVATIVES": "DERIVATIVE",
    "INDICES": "INDICES",
    "TRADABLE_RIGHTS": "TR",
}

def map_market(db_market):
    if not db_market:
        return None
    return MARKET_MAP.get(db_market.strip())


# ─────────────────────────────────────────────────────────────
# ✅ YOUR ORIGINAL COOKIE (UNCHANGED)
# ─────────────────────────────────────────────────────────────
COOKIE_HEADER = (
    'RT="z=1&dm=www.saudiexchange.sa&si=f16268f8-dfb1-468b-b404-744343d9f414&ss=mnnf6kb4&sl=0&tt=0&nu=9y8m6cy&cl=all8y&ld=83z7f&ul=83z7f&hd=8402a"; '
    'marqueePosition_ltr=-131567.759999998; '
    'TS01fdeb15=0102d17fadc92cba7ef2addc249e17d12e9066f4984eeaade8256d6c2a07dd6b100c2648ce9338141947893eb8de2d23b8dd81db47becd2bc3fbbd920c3baf446073219138126e88947ed151ef0ff74e8ceff264c131b8027ef223d4b3190f33030be62020; '
    'com.ibm.wps.state.preprocessors.locale.LanguageCookie=en; '
    '_ga_DC6H7ZFCGP=GS2.1.s1775596132$o16$g0$t1775596132$j60$l0$h0; '
    '_ga_P0MCK0BGCX=GS2.1.s1775596132$o16$g0$t1775596132$j60$l0$h0; '
    'marqueePosition_rtl=52171.20000000095; '
    '_ga=GA1.1.1162039479.1759921645; '
    '_ga_3T6X01KMEX=GS2.1.s1775591992$o12$g1$t1775592057$j58$l0$h0; '
    '_ga_DC6H7ZFCGP=deleted; '
    'JSESSIONID=!Klh/zRxQspN15oVJkmmjrB1xdL66i+6SthrrlojtV0p75eG9nMAokx6D0FEFv6aXXaG61Loi7kFSTJNkmf3SK57FixN3KfAp2P8H; '
    'BIGipServerSaudiExchange.sa.app~SaudiExchange.sa_pool=2617184684.20480.0000; '
    '__utma=44173222.1162039479.1759921645.1759924382.1759924382.1; '
    '__utmz=44173222.1759924382.1.1.utmcsr=(direct)|utmccn=(direct)|utmcmd=(none)'
)

HEADERS = {
    "Accept": "application/json, text/javascript, */*; q=0.01",
    "Accept-Encoding": "gzip, deflate, br",
    "Accept-Language": "en-US,en;q=0.9",
    "Referer": "https://www.saudiexchange.sa/wps/portal/saudiexchange/newsandreports/reports-publications/historical-reports/",
    "User-Agent": (
        "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
        "AppleWebKit/605.1.15 (KHTML, like Gecko) "
        "Version/18.5 Safari/605.1.15"
    ),
    "X-Requested-With": "XMLHttpRequest",
    "Cookie": COOKIE_HEADER,
}

API_URL = (
    "https://www.saudiexchange.sa/wps/portal/saudiexchange/"
    "newsandreports/reports-publications/historical-reports/"
    "!ut/p/z1/lZDdDsFAEIWfxRPMsXStyxKtJkprW3RvpNg0DUrYSHh6"
    "jSvqf-5m8p2ZOYcUzUgV6SnPUpPvinRT9onic8vmYH2BEfpRFxzS5"
    "XEk6qzXpOkjIHyXIxza4Yi1LLgTkPpLDxlYCJ3Abwwwhgv-mx5vyv"
    "56Pyn1rbdAnZMkReqoN3pp9MpPD2ttKPFtb3g_7xUmN2dKGBooX1KV"
    "q2EsSlPS6VgCDBJV4EVqlQ3PsdyAD76lLmi_jePZJdKLtpcHWa12BZ"
    "kuXag!/p0/IZ7_5A602H80O0HTC060SG6UT81216=CZ6_5A602H80O"
    "0HTC060SG6UT812E4=NJpopulateCompanyDetails=/"
)



# ─────────────────────────────────────────────────────────────
# ✅ PARAM BUILDER
# ─────────────────────────────────────────────────────────────
def build_params(start_date, end_date, entity_id, sector_id, db_market):

    api_market = map_market(db_market)
    if not api_market:
        raise ValueError(f"Unknown market: {db_market}")

    selected_sector = f"{api_market}:{sector_id}"

    return [
        ("draw", "2"),
        ("start", "0"),
        ("length", "100"),
        ("search[value]", ""),
        ("search[regex]", "false"),
        ("selectedMarket", api_market),
        ("selectedSector", selected_sector),
        ("selectedEntity", str(entity_id)),
        ("startDate", start_date),
        ("endDate", end_date),
        ("tableTabId", "0"),
        ("startIndex", "0"),
        ("endIndex", "30"),
        ("_", str(int(datetime.now().timestamp() * 1000))),
    ]


# ─────────────────────────────────────────────────────────────
# ✅ DATE WINDOW SPLITTER (3 MONTHS)
# ─────────────────────────────────────────────────────────────
def generate_windows(start_date, end_date, window_days=90):

    start = datetime.strptime(start_date, "%d-%m-%Y")
    end = datetime.strptime(end_date, "%d-%m-%Y")

    while start <= end:
        window_end = min(start + timedelta(days=window_days), end)
        yield (
            start.strftime("%d-%m-%Y"),
            window_end.strftime("%d-%m-%Y"),
        )
        start = window_end + timedelta(days=1)


# ─────────────────────────────────────────────────────────────
# ✅ MAIN LOADER
# ─────────────────────────────────────────────────────────────
class PriceLoader:

    REQUEST_DELAY = 1.2

    def __init__(self, start_date, end_date):

        self.start_date = start_date
        self.end_date = end_date

        self.db_config = {
            "dbname": os.getenv("DB_NAME", "saudi_stocks"),
            "user": os.getenv("DB_USER", "stockuser"),
            "password": os.getenv("DB_PASSWORD", ""),
            "host": os.getenv("DB_HOST", "localhost"),
            "port": int(os.getenv("DB_PORT", "5432")),
        }

    def run(self):

        conn = psycopg2.connect(**self.db_config)
        session = requests.Session()
        session.headers.update(HEADERS)

        with conn.cursor() as cur:
            cur.execute("SELECT symbol, sector_code, market FROM companies ORDER BY symbol")
            companies = cur.fetchall()

        for symbol, sector_id, db_market in companies:

            for win_start, win_end in generate_windows(self.start_date, self.end_date):

                try:
                    params = build_params(
                        win_start,
                        win_end,
                        symbol,
                        sector_id,
                        db_market,
                    )

                    resp = session.get(API_URL, params=params, timeout=20)

                    log.info(f"{symbol} [{win_start} → {win_end}] → HTTP {resp.status_code}")

                    if resp.status_code != 200:
                        continue

                    data = resp.json().get("data", [])

                    log.info(f"{symbol} [{win_start} → {win_end}] → {len(data)} rows")

                    if not data:
                        continue

                    df = pd.DataFrame(data)

                    df.rename(columns={
                        "transactionDateStr": "date",
                        "todaysOpen": "open",
                        "highPrice": "high",
                        "lowPrice": "low",
                        "previousClosePrice": "prev_close",
                        "lastTradePrice": "close",
                        "volumeTraded": "volume",
                        "turnOver": "turnover",
                        "noOfTrades": "num_trades",
                    }, inplace=True)

                    df["date"] = pd.to_datetime(df["date"])

                    rows = []

                    for row in df.itertuples(index=False):

                        # --- clean numeric price fields ---
                        close_val = float(str(row.close).replace(",", "")) if row.close else None
                        prev_val  = float(str(row.prev_close).replace(",", "")) if row.prev_close else None
                        open_val  = float(str(row.open).replace(",", "")) if row.open else None
                        high_val  = float(str(row.high).replace(",", "")) if row.high else None
                        low_val   = float(str(row.low).replace(",", "")) if row.low else None

                        # --- clean integer fields (THIS FIXES YOUR ERROR) ---
                        volume_val = int(str(row.volume).replace(",", "")) if row.volume else None
                        turnover_val = float(str(row.turnover).replace(",", "")) if row.turnover else None
                        trades_val = int(str(row.num_trades).replace(",", "")) if row.num_trades else None

                        # --- calculate change ---
                        if close_val is not None and prev_val:
                            change = close_val - prev_val
                            change_pct = (change / prev_val) * 100
                        else:
                            change = None
                            change_pct = None

                        rows.append(
                            (
                                symbol,
                                row.date.date(),
                                open_val,
                                high_val,
                                low_val,
                                close_val,
                                prev_val,
                                volume_val,
                                turnover_val,
                                trades_val,
                                change,
                                change_pct,
                            )
                        )
                    with conn.cursor() as cur:
                        psycopg2.extras.execute_values(
                            cur,
                            """
                            INSERT INTO prices (
                                symbol, date,
                                open, high, low, close, prev_close,
                                volume, turnover, num_trades,
                                change, change_pct
                            )
                            VALUES %s
                            ON CONFLICT (symbol, date) DO UPDATE SET
                                open=EXCLUDED.open,
                                high=EXCLUDED.high,
                                low=EXCLUDED.low,
                                close=EXCLUDED.close,
                                prev_close=EXCLUDED.prev_close,
                                volume=EXCLUDED.volume,
                                turnover=EXCLUDED.turnover,
                                num_trades=EXCLUDED.num_trades,
                                change=EXCLUDED.change,
                                change_pct=EXCLUDED.change_pct;
                            """,
                            rows
                        )
                    conn.commit()

                except Exception as e:
                    log.error(f"{symbol} [{win_start} → {win_end}] → ERROR: {e}")

                time.sleep(self.REQUEST_DELAY)

        conn.close()

    @classmethod
    def auto_refresh(cls):
        db_config = {
            "dbname": os.getenv("DB_NAME", "saudi_stocks"),
            "user": os.getenv("DB_USER", "stockuser"),
            "password": os.getenv("DB_PASSWORD", ""),
            "host": os.getenv("DB_HOST", "localhost"),
            "port": int(os.getenv("DB_PORT", "5432")),
        }

        conn = psycopg2.connect(**db_config)
        with conn.cursor() as cur:
            cur.execute("SELECT MAX(date) FROM prices;")
            last_date = cur.fetchone()[0]
        conn.close()

        if last_date is None:
            log.error("prices table is empty — run a full historical load first.")
            return

        today = datetime.today().date()
        start = last_date + timedelta(days=1)

        if start > today:
            log.info(f"Prices already up to date (last date: {last_date}).")
            return

        # ── Saudi weekend = Friday (4) + Saturday (5) ──────────
        # Only fetch if there are actual trading days in the gap
        # weekday(): Mon=0, Tue=1, Wed=2, Thu=3, Fri=4, Sat=5, Sun=6
        trading_days_missed = [
            start + timedelta(days=i)
            for i in range((today - start).days + 1)
            if (start + timedelta(days=i)).weekday() not in (4, 5)
        ]

        if not trading_days_missed:
            log.info(
                f"Prices up to date — gap is Fri/Sat only "
                f"(last date: {last_date}, today: {today})."
            )
            return

        # end = today so we always include the current trading day
        end = today

        log.info(
            f"Auto-refreshing prices: "
            f"{start.strftime('%d-%m-%Y')} → {end.strftime('%d-%m-%Y')} "
            f"({len(trading_days_missed)} trading day(s) missed)"
        )

        loader = cls(
            start_date=start.strftime("%d-%m-%Y"),
            end_date=end.strftime("%d-%m-%Y"),
        )
        loader.run()

if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--start", required=True)
    parser.add_argument("--end", required=True)
    args = parser.parse_args()

    loader = PriceLoader(args.start, args.end)
    loader.run()