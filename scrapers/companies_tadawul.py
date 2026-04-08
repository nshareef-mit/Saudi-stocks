# scrapers/companies_tadawul.py

import os
import time
import logging
import argparse
import requests
import psycopg2
from psycopg2.extras import execute_values
from datetime import datetime, timezone

# ── Constants import ──────────────────────────────────────────────────────────
try:
    from constants import SECTORS, SECTOR_ID_TO_KEY
except ImportError:
    try:
        from scrapers.constants import SECTORS, SECTOR_ID_TO_KEY
    except ImportError:
        SECTORS = {}
        SECTOR_ID_TO_KEY = {}

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)
logger = logging.getLogger("companies_tadawul")


# ─────────────────────────────────────────────────────────────────────────────
# Helpers
# ─────────────────────────────────────────────────────────────────────────────

def _sector_names_from_id(sector_id: str) -> tuple[str, str]:
    """Return (name_en, name_ar) for a numeric sector ID like '32'."""
    key = SECTOR_ID_TO_KEY.get(str(sector_id))
    if key and key in SECTORS:
        s = SECTORS[key]
        return s.get("name_en", ""), s.get("name_ar", "")
    return "", ""


# ─────────────────────────────────────────────────────────────────────────────
# Loader
# ─────────────────────────────────────────────────────────────────────────────

class companies_tadawul:
    """
    Fetches the full company listing from the Saudi Exchange sector-by-sector
    portal API and upserts into the `companies` table.

    Iterates through every sector ID defined in constants.py, building the
    request URL by injecting `sectorParameter=<ID>` into the portal endpoint.

    Columns populated
    -----------------
    symbol       – ticker  (companySymbol from response)
    name_en      – empty   (endpoint only returns Arabic names)
    name_ar      – Arabic full company name
    sector_en    – resolved from constants.py via sectorRef
    sector_ar    – resolved from constants.py via sectorRef
    sector_code  – numeric sector ID matching constants.py  e.g. "32"
    market       – PRODUCT_TYPES key from constants.py      e.g. "MAIN_MARKET"
    last_updated – UTC timestamp of this upsert

    The `market` value is derived from `tableViewParameter`:
        "1"  →  "MAIN_MARKET"
        "2"  →  "NOMU_MARKET"
    (endpoint name is getMainNomucMarketDetails, covering both products)
    """

    # Portal endpoint — sectorParameter is injected per-request.
    # The !ut/p/z1/… fragment is WebSphere Portal navigation state; it is
    # stable across sessions but may need updating if the portal is redeployed.
    _BASE_URL = (
        "https://www.saudiexchange.sa/wps/portal/saudiexchange/ourmarkets/"
        "main-market-watch/!ut/p/z1/04_Sj9CPykssy0xPLMnMz0vMAfIjo8ziTR3NDIw8"
        "LAz8LVxcnA0C3bwtPLwM_I0MzMz1w1EVGAQHmAIVBPga-xgEGbgbmOlHEaPfAAdwNCC"
        "sPwpNia-7mUGgn2Ogv5G5qYFBsBG6AixOBCvA44bgxCL9gtzQCIPMgHQAVrLIOQ!!/p0/"
        "IZ7_IPG41I82KGASC06S67RB9A0080=CZ6_5A602H80O8DDC0QFK8HJ0O2067="
        "NJgetMainNomucMarketDetails=/"
    )

    # tableViewParameter  →  PRODUCT_TYPES key (constants.py)
    _TABLE_VIEW_TO_MARKET: dict[str, str] = {
        "1": "MAIN_MARKET",
        "2": "NOMU_MARKET",
    }

    _HEADERS = {
        "User-Agent": (
            "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
            "AppleWebKit/605.1.15 (KHTML, like Gecko) "
            "Version/18.5 Safari/605.1.15"
        ),
        "Accept":          "application/json, */*",
        "Accept-Language": "en-US,en;q=0.9",
        "Referer":         "https://www.saudiexchange.sa/",
    }

    _UPSERT_SQL = """
        INSERT INTO companies (
            symbol,
            name_en,     name_ar,
            sector_en,   sector_ar,
            sector_code, market,
            last_updated
        )
        VALUES %s
        ON CONFLICT (symbol) DO UPDATE SET
            name_en      = EXCLUDED.name_en,
            name_ar      = EXCLUDED.name_ar,
            sector_en    = EXCLUDED.sector_en,
            sector_ar    = EXCLUDED.sector_ar,
            sector_code  = EXCLUDED.sector_code,
            market       = EXCLUDED.market,
            last_updated = EXCLUDED.last_updated;
    """

    def __init__(
        self,
        db_config: dict,
        request_timeout: int = 30,
        sleep_between_sectors: float = 1.0,
    ):
        self.db_config             = db_config
        self.request_timeout       = request_timeout
        self.sleep_between_sectors = sleep_between_sectors
        self._conn                 = None

    # ── Database ──────────────────────────────────────────────────────────────

    def _connect(self) -> None:
        self._conn = psycopg2.connect(**self.db_config)
        logger.info("Connected to PostgreSQL (%s).", self.db_config.get("dbname"))

    def _disconnect(self) -> None:
        if self._conn and not self._conn.closed:
            self._conn.close()
            logger.info("Database connection closed.")

    def _ensure_columns(self) -> None:
        """
        Idempotently add sector_code and market to `companies` if absent.
        Safe to run against a DB that already has them.

        Equivalent manual SQL:
            ALTER TABLE companies
                ADD COLUMN IF NOT EXISTS sector_code VARCHAR(10),
                ADD COLUMN IF NOT EXISTS market      VARCHAR(30) DEFAULT 'MAIN_MARKET';
        """
        with self._conn.cursor() as cur:
            cur.execute("""
                ALTER TABLE companies
                    ADD COLUMN IF NOT EXISTS sector_code VARCHAR(10),
                    ADD COLUMN IF NOT EXISTS market      VARCHAR(30)
                        DEFAULT 'MAIN_MARKET';
            """)
        self._conn.commit()
        logger.info("Schema check complete — sector_code / market columns ready.")

    # ── API ───────────────────────────────────────────────────────────────────

    def _fetch_sector(
        self,
        sector_id: str,
        table_view: str = "1",
    ) -> list[dict]:
        """
        Fetch all company records for one sector from the Tadawul portal API.

        Args:
            sector_id:   Numeric string matching constants.py, e.g. "32".
            table_view:  "1" = MAIN_MARKET, "2" = NOMU_MARKET.
        """
        params = {
            "sectorParameter":     sector_id,
            "tableViewParameter":  table_view,
            "iswatchListSelected": "NO",
            "requestLocale":       "ar",
            "_":                   int(time.time() * 1000),   # cache buster
        }
        logger.info(
            "  Fetching sector_id=%s  tableView=%s …", sector_id, table_view
        )
        resp = requests.get(
            self._BASE_URL,
            params=params,
            headers=self._HEADERS,
            timeout=self.request_timeout,
        )
        resp.raise_for_status()
        records = resp.json().get("data", [])
        logger.info("    → %d records received.", len(records))
        return records

    def fetch_all_sectors(self, table_view: str = "1") -> list[dict]:
        """
        Loop through every sector ID in constants.py and collect all records.
        A configurable sleep between requests avoids rate-limiting.
        """
        all_records: list[dict] = []
        # Pull every numeric sector ID defined in constants.py — single source of truth
        sector_ids = sorted({data["id"] for data in SECTORS.values()})

        logger.info(
            "Starting fetch for %d sectors (market=%s) …",
            len(sector_ids),
            self._TABLE_VIEW_TO_MARKET.get(table_view, "UNKNOWN"),
        )

        for sector_id in sector_ids:
            try:
                records = self._fetch_sector(sector_id, table_view=table_view)
                all_records.extend(records)
            except Exception as exc:
                logger.warning(
                    "Skipping sector %s — fetch failed: %s", sector_id, exc
                )
            time.sleep(self.sleep_between_sectors)

        logger.info(
            "Collected %d total records across %d sectors.",
            len(all_records),
            len(sector_ids),
        )
        return all_records

    # ── Transformation ────────────────────────────────────────────────────────

    @staticmethod
    def _parse_record(record: dict, market: str) -> tuple:
        """
        Map one raw API record to a DB row tuple.

        Response fields used:
            companySymbol  → symbol
            companyName    → name_ar   (Arabic only; no English name in response)
            sectorRef      → sector_code  (e.g. "32")  — also the key for constants.py

        Returns:
            (symbol, name_en, name_ar, sector_en, sector_ar, sector_code, market)
        """
        symbol = str(record.get("companySymbol", "")).strip()

        # sector_code comes directly from sectorRef in the response;
        # it is the same numeric ID used as "id" in constants.py SECTORS dict.
        sector_code = str(record.get("sectorRef", "")).strip()

        # Resolve human-readable names from constants.py using that ID
        sector_en, sector_ar = _sector_names_from_id(sector_code)

        # Fall back to the Arabic name supplied inline by the API
        sector_ar = sector_ar or str(record.get("sectorName", "")).strip()

        name_ar = str(record.get("companyName", "")).strip()
        name_en = ""  # this endpoint does not return English company names

        return (symbol, name_en, name_ar, sector_en, sector_ar, sector_code, market)

    # ── Load ──────────────────────────────────────────────────────────────────

    def _upsert(self, rows: list[tuple]) -> int:
        now = datetime.now(tz=timezone.utc)
        timestamped = [(*row, now) for row in rows]

        with self._conn.cursor() as cur:
            execute_values(cur, self._UPSERT_SQL, timestamped, page_size=500)

        self._conn.commit()
        logger.info("Upserted %d rows into companies.", len(timestamped))
        return len(timestamped)

    # ── Orchestration ─────────────────────────────────────────────────────────

    def run(self, table_view: str = "1") -> int:
        """
        Full pipeline: connect → ensure schema → fetch all sectors → upsert.

        Args:
            table_view: "1" = MAIN_MARKET (default), "2" = NOMU_MARKET.
        """
        market = self._TABLE_VIEW_TO_MARKET.get(table_view, "MAIN_MARKET")

        try:
            self._connect()
            self._ensure_columns()

            raw_records = self.fetch_all_sectors(table_view=table_view)
            rows = [self._parse_record(r, market=market) for r in raw_records]

            # Discard malformed records that produced an empty symbol
            valid_rows = [r for r in rows if r[0]]
            if len(valid_rows) < len(rows):
                logger.warning(
                    "Dropped %d records with empty symbol.",
                    len(rows) - len(valid_rows),
                )

            total = self._upsert(valid_rows)
            logger.info(
                "Sync complete — %d companies loaded (market=%s).", total, market
            )
            return total

        except Exception:
            if self._conn:
                self._conn.rollback()
            logger.exception("companies_tadawul encountered an error.")
            raise

        finally:
            self._disconnect()

    # ── Diagnostics ───────────────────────────────────────────────────────────

    def dump_raw_fields(self, sector_id: str = "32", n: int = 3) -> None:
        """
        Fetch one sector and print raw field names + sample values.
        Run this first to verify the exact keys the API returns.
        """
        records = self._fetch_sector(sector_id)
        sample  = records[:n]
        print(
            f"\n── Raw API fields  (sector_id={sector_id}, "
            f"first {len(sample)} records) ───────────────────"
        )
        for i, rec in enumerate(sample, start=1):
            print(f"\n  Record {i}:")
            for key, val in sorted(rec.items()):
                print(f"    {key:<40} = {val!r}")
        print()

    def audit_missing(self) -> None:
        """
        Show how many companies are missing sector_code / market after a sync.
        """
        self._connect()
        try:
            with self._conn.cursor() as cur:
                cur.execute("""
                    SELECT
                        COUNT(*)                                       AS total,
                        COUNT(*) FILTER (WHERE sector_code IS NULL
                                           OR  sector_code = '')      AS no_sector_code,
                        COUNT(*) FILTER (WHERE market IS NULL)        AS no_market
                    FROM companies;
                """)
                total, no_sec, no_mkt = cur.fetchone()
        finally:
            self._disconnect()

        print("\n── companies column coverage ────────────────────────────────")
        print(f"  total rows          : {total}")
        print(f"  missing sector_code : {no_sec}")
        print(f"  missing market      : {no_mkt}\n")


# ── Entry point ───────────────────────────────────────────────────────────────

if __name__ == "__main__":
    from dotenv import load_dotenv
    load_dotenv()                        # ← reads .env from the project root

    DB_CONFIG = {
        "dbname":   os.getenv("DB_NAME",     "saudi_stocks"),
        "user":     os.getenv("DB_USER",     "stockuser"),
        "password": os.getenv("DB_PASSWORD", ""),
        "host":     os.getenv("DB_HOST",     "localhost"),
        "port":     int(os.getenv("DB_PORT", "5432")),
    }

    parser = argparse.ArgumentParser(
        description="Sync Tadawul company list into PostgreSQL, sector by sector."
    )
    parser.add_argument(
        "--market",
        choices=["MAIN_MARKET", "NOMU_MARKET"],
        default="MAIN_MARKET",
        help="Which market to sync (default: MAIN_MARKET).",
    )
    parser.add_argument(
        "--dump-raw",
        action="store_true",
        help="Print raw API fields for a sample sector, then exit.",
    )
    parser.add_argument(
        "--dump-sector",
        default="32",
        metavar="SECTOR_ID",
        help="Sector ID to use with --dump-raw (default: 32 = Materials).",
    )
    parser.add_argument(
        "--dump-n",
        type=int,
        default=3,
        metavar="N",
        help="Number of records to print with --dump-raw (default: 3).",
    )
    parser.add_argument(
        "--audit",
        action="store_true",
        help="Show sector_code / market coverage stats, then exit.",
    )
    args = parser.parse_args()

    table_view_map = {"MAIN_MARKET": "1", "NOMU_MARKET": "2"}
    table_view = table_view_map[args.market]

    loader = companies_tadawul(db_config=DB_CONFIG)

    if args.dump_raw:
        loader.dump_raw_fields(sector_id=args.dump_sector, n=args.dump_n)
    elif args.audit:
        loader.audit_missing()
    else:
        total = loader.run(table_view=table_view)
        print(f"✓ {total} companies synced successfully ({args.market}).")