"""
bl/scorer.py
────────────────────────────────────────────────────────────────
Weekly ranking scorer for the 52-stock Saudi Exchange universe.

HOW TO CALL:
    from bl.scorer import get_weekly_rankings

    # Latest available date in DB (normal weekly use)
    df = get_weekly_rankings()

    # Specific date (backtest / debug)
    df = get_weekly_rankings(as_of_date="2026-04-09")

RETURNS:
    pd.DataFrame — one row per symbol, sorted best → worst, with columns:
        symbol, sector, close, score, rank, signal (BUY/SELL/HOLD),
        confidence, scoring_date
"""

import os
import json
import warnings
from math import erf, sqrt
from pathlib import Path

import joblib
import numpy as np
import pandas as pd
import psycopg2
from dotenv import load_dotenv

warnings.filterwarnings("ignore")
load_dotenv()

# ─────────────────────────────────────────────────────────────────────────────
# PATHS  (relative to project root, not bl/)
# ─────────────────────────────────────────────────────────────────────────────
_ROOT       = Path(__file__).resolve().parent.parent
MODEL_PATH  = _ROOT / "models" / "lgbm_rolling_quarterly.pkl"
META_PATH   = _ROOT / "models" / "lgbm_rolling_quarterly_meta.json"

# ─────────────────────────────────────────────────────────────────────────────
# UNIVERSE  (must stay identical to the training notebook)
# ─────────────────────────────────────────────────────────────────────────────
SYMBOLS = [
    "2222","2380","2381","2382","4030","2030",
    "2010","2020","2060","2310","2350","1211","1321","1322","2223","2250","2290","2150",
    "3030","3092","3004","3050",
    "1212","2320","2040","4142",
    "4190","4001","2280","2050","4164","4240","4003","4161",
    "4013","4004","4009","4017",
    "1120","1180","1150","1050","1060","1080",
    "7010","7020",
    "2082","2080",
    "4300","4321",
    "7203","7202",
]

SECTOR_MAP = {
    "2222":"Energy",  "2380":"Energy",  "2381":"Energy",  "2382":"Energy",
    "4030":"Energy",  "2030":"Energy",
    "2010":"Materials","2020":"Materials","2060":"Materials","2310":"Materials",
    "2350":"Materials","1211":"Materials","1321":"Materials","1322":"Materials",
    "2223":"Materials","2250":"Materials","2290":"Materials","2150":"Materials",
    "3030":"Cement",  "3092":"Cement",  "3004":"Cement",  "3050":"Cement",
    "1120":"Banks",   "1180":"Banks",   "1150":"Banks",   "1050":"Banks",
    "1060":"Banks",   "1080":"Banks",
    "7010":"Telecom", "7020":"Telecom",
    "2082":"Utilities","2080":"Utilities",
    "4013":"Healthcare","4004":"Healthcare","4009":"Healthcare","4017":"Healthcare",
    "4190":"Consumer","4001":"Consumer","2280":"Consumer","2050":"Consumer",
    "4164":"Consumer","4240":"Consumer","4003":"Consumer","4161":"Consumer",
    "4300":"RealEstate","4321":"RealEstate",
    "7203":"Software","7202":"Software",
    "1212":"CapitalGoods","2320":"CapitalGoods","2040":"CapitalGoods","4142":"CapitalGoods",
}

# ─────────────────────────────────────────────────────────────────────────────
# FEATURE COLUMNS  (exact same order as training — do NOT reorder)
# ─────────────────────────────────────────────────────────────────────────────
FEATURE_COLS = [
    "ret_1d",
    "mom_1w", "mom_1m", "mom_3m",
    "dist_sma_20", "dist_sma_60",
    "vol_5", "vol_20", "vol_ratio_20_60",
    "vol_surge",
    "turnover", "num_trades",
]

# ─────────────────────────────────────────────────────────────────────────────
# PORTFOLIO SETTINGS
# ─────────────────────────────────────────────────────────────────────────────
K_BUY             = 10
K_SELL            = 10
MAX_SECTOR_FRAC   = 0.30   # soft sector cap per side

# How many calendar days of history to pull (covers 63-day momentum + buffers)
_HISTORY_DAYS     = 200


# ─────────────────────────────────────────────────────────────────────────────
# PRIVATE HELPERS
# ─────────────────────────────────────────────────────────────────────────────
def _zscore_cs(frame: pd.DataFrame, cols: list) -> pd.DataFrame:
    """Cross-sectional z-score: for each date, standardise across all stocks."""
    out = frame.copy()
    def _z(s):
        sd = s.std(ddof=0)
        return s * 0.0 if (sd == 0 or np.isnan(sd)) else (s - s.mean()) / sd
    out[cols] = out.groupby("date")[cols].transform(_z)
    return out


def _z_to_confidence(z: float) -> float:
    """Map a z-score to a [0.50, 0.99] confidence value."""
    p = 0.5 * (1 + erf(abs(float(z)) / sqrt(2)))
    return round(float(min(0.99, max(0.50, p))), 4)


def _soft_sector_pick(df_day: pd.DataFrame, score_col: str = "score"):
    """
    Sector-neutral soft selection: returns (buy_set, sell_set).
    Cap per sector = floor(K * MAX_SECTOR_FRAC), relaxed if needed to fill K.
    """
    cap = max(1, int(np.floor(K_BUY * MAX_SECTOR_FRAC)))

    r_desc = df_day.sort_values(score_col, ascending=False).reset_index(drop=True)
    r_asc  = df_day.sort_values(score_col, ascending=True).reset_index(drop=True)

    buy,  sell   = [], []
    buy_ct, sell_ct = {}, {}

    # — First pass: respect sector cap —
    for _, row in r_desc.iterrows():
        if len(buy) >= K_BUY: break
        sym, sec = row["symbol"], row["sector"]
        if sym in sell: continue
        if buy_ct.get(sec, 0) < cap:
            buy.append(sym)
            buy_ct[sec] = buy_ct.get(sec, 0) + 1

    for _, row in r_asc.iterrows():
        if len(sell) >= K_SELL: break
        sym, sec = row["symbol"], row["sector"]
        if sym in buy: continue
        if sell_ct.get(sec, 0) < cap:
            sell.append(sym)
            sell_ct[sec] = sell_ct.get(sec, 0) + 1

    # — Second pass: relax cap to fill remaining slots —
    for sym in r_desc["symbol"].tolist():
        if len(buy) >= K_BUY: break
        if sym not in buy and sym not in sell:
            buy.append(sym)

    for sym in r_asc["symbol"].tolist():
        if len(sell) >= K_SELL: break
        if sym not in buy and sym not in sell:
            sell.append(sym)

    return set(buy[:K_BUY]), set(sell[:K_SELL])


def _build_features(df: pd.DataFrame) -> pd.DataFrame:
    """
    Compute all features on the raw price DataFrame.
    Mirrors the notebook's feature engineering cell exactly.
    """
    g = df.groupby("symbol", group_keys=False)

    df["ret_1d"]          = g["close"].pct_change()
    df["mom_1w"]          = g["close"].transform(lambda s: s / s.shift(5)  - 1)
    df["mom_1m"]          = g["close"].transform(lambda s: s / s.shift(21) - 1)
    df["mom_3m"]          = g["close"].transform(lambda s: s / s.shift(63) - 1)
    df["sma_20"]          = g["close"].transform(lambda s: s.rolling(20).mean())
    df["sma_60"]          = g["close"].transform(lambda s: s.rolling(60).mean())
    df["dist_sma_20"]     = df["close"] / df["sma_20"] - 1
    df["dist_sma_60"]     = df["close"] / df["sma_60"] - 1
    df["vol_5"]           = g["ret_1d"].transform(lambda s: s.rolling(5).std())
    df["vol_20"]          = g["ret_1d"].transform(lambda s: s.rolling(20).std())
    df["vol_60"]          = g["ret_1d"].transform(lambda s: s.rolling(60).std())
    df["vol_ratio_20_60"] = df["vol_20"] / df["vol_60"]
    df["vol_sma_20"]      = g["volume"].transform(lambda s: s.rolling(20).mean())
    df["vol_surge"]       = df["volume"] / df["vol_sma_20"] - 1

    return df


# ─────────────────────────────────────────────────────────────────────────────
# PUBLIC FUNCTION
# ─────────────────────────────────────────────────────────────────────────────

import sys
import os

# Add project root to path so sibling packages are importable
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from scrapers.prices_tadawul import PriceLoader

def get_weekly_rankings(as_of_date: str = None) -> pd.DataFrame:
    # ── Auto-refresh prices before scoring ──────────────────
    PriceLoader.auto_refresh()
    """
    Score all 52 stocks and return BUY / SELL / HOLD rankings for the coming week.

    Parameters
    ----------
    as_of_date : str, optional
        Cut-off date in 'YYYY-MM-DD' format.
        None  → uses the latest available date in the DB  (production use).
        str   → scores as if today were that date          (backtest / debug).

    Returns
    -------
    pd.DataFrame  — one row per symbol, sorted rank 1 → 52

        Column          Type     Description
        ─────────────── ──────── ──────────────────────────────────────────
        rank            int      1 = strongest BUY candidate
        symbol          str      Tadawul symbol
        sector          str      Sector label
        close           float    Last closing price (SAR)
        score           float    Raw model prediction
        signal          str      BUY | SELL | HOLD
        confidence      float    [0.50 – 0.99]  higher = more conviction
        scoring_date    date     Date the features were computed on
    """

    # ── 1. Load model ─────────────────────────────────────────────────────────
    if not MODEL_PATH.exists():
        raise FileNotFoundError(
            f"Model not found at {MODEL_PATH}. "
            "Run the training notebook and save the model first."
        )
    model = joblib.load(MODEL_PATH)

    # ── 2. Pull price data from DB ────────────────────────────────────────────
    db_config = {
        "dbname":   os.getenv("DB_NAME"),
        "user":     os.getenv("DB_USER"),
        "password": os.getenv("DB_PASSWORD"),
        "host":     os.getenv("DB_HOST"),
        "port":     os.getenv("DB_PORT"),
    }

    symbols_tuple = tuple(SYMBOLS)
    date_ceil     = f"AND date <= '{as_of_date}'" if as_of_date else ""
    cutoff_ref    = f"'{as_of_date}'"             if as_of_date else "CURRENT_DATE"

    query = f"""
        SELECT date, symbol, open, high, low, close, volume, turnover, num_trades
        FROM   public.prices
        WHERE  symbol IN {symbols_tuple}
          AND  date >= ({cutoff_ref}::date - INTERVAL '{_HISTORY_DAYS} days')
          {date_ceil}
        ORDER  BY symbol, date ASC;
    """

    conn = psycopg2.connect(**db_config)
    df   = pd.read_sql_query(query, conn)
    conn.close()

    if df.empty:
        raise ValueError("No data returned from DB. Check DB connection or date range.")

    df["date"]   = pd.to_datetime(df["date"])
    df["symbol"] = df["symbol"].astype(str)
    df           = df.sort_values(["symbol", "date"]).reset_index(drop=True)
    df["sector"] = df["symbol"].map(SECTOR_MAP)

    # ── 3. Feature engineering ────────────────────────────────────────────────
    df = _build_features(df)

    # ── 4. Keep only fully-featured rows ─────────────────────────────────────
    df_feat = df.dropna(subset=FEATURE_COLS).copy()

    if df_feat.empty:
        raise ValueError(
            "No rows with complete features. "
            "DB may not have enough history (need ~90 trading days)."
        )

    # ── 5. Cross-sectional z-score  ───────────────────────────────────────────
    df_feat = _zscore_cs(df_feat, FEATURE_COLS)

    # ── 6. Isolate scoring date ───────────────────────────────────────────────
    scoring_date = df_feat["date"].max()
    today        = df_feat[df_feat["date"] == scoring_date].copy()

    missing = set(SYMBOLS) - set(today["symbol"].tolist())
    if missing:
        print(f"[scorer] Warning: {len(missing)} symbols missing on {scoring_date.date()}: {missing}")

    # ── 7. Model inference ────────────────────────────────────────────────────
    today["score"] = model.predict(today[FEATURE_COLS])

    # ── 8. Rank  ──────────────────────────────────────────────────────────────
    today = today.sort_values("score", ascending=False).reset_index(drop=True)
    today["rank"] = np.arange(1, len(today) + 1)

    # ── 9. Sector-neutral BUY / SELL selection ────────────────────────────────
    buy_set, sell_set = _soft_sector_pick(today, score_col="score")

    today["signal"] = today["symbol"].apply(
        lambda s: "BUY" if s in buy_set else ("SELL" if s in sell_set else "HOLD")
    )

    # ── 10. Confidence  ───────────────────────────────────────────────────────
    score_std        = float(today["score"].std())
    today["confidence"] = today["score"].apply(
        lambda z: _z_to_confidence(z / score_std) if score_std > 0 else 0.5
    )

    # ── 11. Final clean output ────────────────────────────────────────────────
    result = (
        today[["rank", "symbol", "sector", "close", "score", "signal", "confidence"]]
        .copy()
    )
    result["scoring_date"] = scoring_date.date()
    result = result.sort_values("rank").reset_index(drop=True)

    return result


# ─────────────────────────────────────────────────────────────────────────────
# CLI  — python -m bl.scorer
# ─────────────────────────────────────────────────────────────────────────────
if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="Score 52 Saudi stocks for the coming week.")
    parser.add_argument("--date", default=None, help="As-of date YYYY-MM-DD (default: latest in DB)")
    args = parser.parse_args()

    rankings = get_weekly_rankings(as_of_date=args.date)

    print(f"\n{'━'*60}")
    print(f"  Scoring date : {rankings['scoring_date'].iloc[0]}")
    print(f"  Universe     : {len(rankings)} stocks")
    print(f"{'━'*60}\n")

    for signal in ("BUY", "SELL", "HOLD"):
        subset = rankings[rankings["signal"] == signal]
        print(f"── {signal} ({len(subset)}) {'─'*40}")
        print(
            subset[["rank", "symbol", "sector", "close", "score", "confidence"]]
            .to_string(index=False)
        )
        print()