#!/usr/bin/env python3
"""
ui/advisor_page.py — Streamlit app for weekly stock recommendations

Integrates:
  • RecentNewsFetcher → real Tadawul news items
  • Scorer (get_weekly_rankings) → Nora Finance model BUY/SELL signals
  • OpenAIAdvisor → GPT-4o analysis of news + prices

Run with:  streamlit run ui/advisor_page.py
"""

import os
import sys
import logging
from datetime import datetime
from typing import Optional

import streamlit as st
import pandas as pd
from dotenv import load_dotenv

# Add project root to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from bl.constants import SECTOR_LABELS
from bl.news_fetcher import RecentNewsFetcher
from bl.openai_advisor import OpenAIAdvisor
from bl.scorer import get_weekly_rankings
from scrapers.prices_tadawul import PriceLoader
import psycopg2
import psycopg2.extras

load_dotenv()
logging.basicConfig(level=logging.INFO)
log = logging.getLogger("advisor_page")

# ─────────────────────────────────────────────────────────────────────────────
# STREAMLIT CONFIG
# ─────────────────────────────────────────────────────────────────────────────
st.set_page_config(
    page_title="Nora Finance — Weekly Stock Advisor",
    page_icon="🏦",
    layout="wide",
)

# ─────────────────────────────────────────────────────────────────────────────
# HELPER FUNCTIONS
# ─────────────────────────────────────────────────────────────────────────────


@st.cache_data(ttl=3600)
def fetch_company_names() -> dict:
    """Fetch company names from database."""
    try:
        db_config = {
            "dbname": os.getenv("DB_NAME"),
            "user": os.getenv("DB_USER"),
            "password": os.getenv("DB_PASSWORD"),
            "host": os.getenv("DB_HOST"),
            "port": os.getenv("DB_PORT"),
        }
        conn = psycopg2.connect(**db_config)
        cur = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
        cur.execute("SELECT symbol, name_en FROM companies ORDER BY symbol")
        companies = cur.fetchall()
        cur.close()
        conn.close()
        
        # Convert to dict: symbol -> name
        company_map = {c["symbol"]: c["name_en"] for c in companies}
        log.info(f"Loaded {len(company_map)} company names from DB")
        return company_map
    except Exception as e:
        log.warning(f"Could not fetch company names from DB: {e}")
        return {}


@st.cache_data(ttl=3600)
def fetch_recent_news(days_back: int) -> list[str]:
    """Fetch recent Tadawul news and announcements."""
    try:
        fetcher = RecentNewsFetcher(days_back=days_back)
        headlines = fetcher.fetch()
        log.info(f"Fetched {len(headlines)} headlines from last {days_back} days")
        return headlines
    except Exception as e:
        log.error(f"Error fetching news: {e}")
        st.error(f"❌ Failed to fetch news: {str(e)}")
        return []


def get_stock_prices_from_scores(df_scores: pd.DataFrame, company_names: dict) -> list[dict]:
    """Convert scoring DataFrame to price list format for OpenAI."""
    prices = []
    for _, row in df_scores.iterrows():
        symbol = row["symbol"]
        prices.append({
            "ticker": symbol,
            "name": company_names.get(symbol, symbol),
            "price": float(row.get("close", 0)),
            "change_pct": "—",  # Not available from scorer directly
        })
    return prices


def estimate_5day_price(current_price: float, rank: int) -> float:
    """Estimate 5-day price based on rank alone (no confidence).
    
    Better rank (lower number) = higher expected price appreciation.
    Rank 1–10: 2.5%–3.5% upside
    Rank 11–20: 1.5%–2.4% upside
    Rank 21+: 0.5%–1.4% upside
    """
    if rank <= 10:
        # Distribute 2.5–3.5% across top 10
        price_increase_pct = 2.5 + ((10 - rank) / 10) * 1.0
    elif rank <= 20:
        # Distribute 1.5–2.4% across ranks 11–20
        price_increase_pct = 1.5 + ((20 - rank) / 10) * 0.9
    else:
        # Distribute 0.5–1.4% for ranks 21+
        price_increase_pct = 0.5 + max(0, ((52 - rank) / 32) * 0.9)
    
    return current_price * (1 + price_increase_pct / 100)

@st.cache_data(ttl=3600)
def validate_stock_with_openai(symbol: str, company_name: str, current_price: float, 
                                confidence: float, sector: str, news_items: list[str]) -> str:
    """Ask OpenAI to validate stock with structured decision framework."""
    try:
        # Build context from relevant news
        news_context = "\n".join(news_items[:8]) if news_items else "No recent news"
        
        prompt = f"""You are a Saudi (Tadawul) equity analyst writing a concise "trade check".

Stock:
- Symbol: {symbol}
- Company: {company_name}
- Sector: {sector}
- Current price (SAR): {current_price:.2f}
- Model signal: BUY
- Model confidence (0-1): {confidence:.2f}

Context:
- The confidence score comes from a quantitative momentum model; it is NOT fundamental analysis.
- The news list may be macro/sector-wide and may be unrelated to the specific company. Treat as context only—do not claim company-specific impacts unless a headline explicitly names the company or its ticker.

Recent headlines (macro/sector context, may be unrelated):
{news_context}

Task:
1) Give a clear stance label: one of [BUY_NOW, WAIT, AVOID].
2) Explain the current situation in 3–6 short bullets, grounded in the inputs (momentum/confidence + sector + headlines).
3) List 2 specific "what would change my mind" triggers (e.g., what news/price action would upgrade/downgrade).
4) Provide a simple risk note: one key risk and one risk-control idea (not financial advice).

Rules:
- If evidence is insufficient for BUY_NOW, choose WAIT (default to WAIT, not vague text).
- Don't say "monitor" without naming exactly what to monitor.
- No disclaimers beyond one short risk note.

Return in this exact format:

STANCE: <label>
WHY:
- ...
- ...
TRIGGERS:
- Upgrade if ...
- Downgrade if ...
RISK:
- Risk: ...
- Control: ...
"""
        
        advisor = OpenAIAdvisor()
        response = advisor.client.chat.completions.create(
            model="gpt-4o",
            messages=[
                {
                    "role": "system",
                    "content": "You are a disciplined Tadawul equity analyst. Follow the exact format requested. Use WAIT as default when evidence is mixed."
                },
                {"role": "user", "content": prompt}
            ],
            temperature=0.4,
            max_tokens=300,
        )
        
        validation = response.choices[0].message.content.strip()
        log.info(f"OpenAI validation for {symbol}: {validation}")
        return validation
    except Exception as e:
        log.warning(f"OpenAI validation failed for {symbol}: {e}")
        return "⚠️ Unable to validate"


def run_analysis(days_back: int):
    """Run the full analysis pipeline with OpenAI validation for top 10 BUY and SELL."""
    col1, col2, col3 = st.columns(3)

    # ── Step 0: Fetch company names ──
    try:
        company_names = fetch_company_names()
    except Exception as e:
        log.warning(f"Could not fetch company names: {e}")
        company_names = {}

    # ── Step 1: Fetch News ──
    with col1:
        st.info("📰 Fetching news...")
    try:
        news_items = fetch_recent_news(days_back)
        with col1:
            st.success(f"✅ Fetched {len(news_items)} news items")
    except Exception as e:
        with col1:
            st.error(f"❌ News fetch failed: {str(e)}")
        return None, None, [], company_names

    # ── Step 2: Get Nora Finance Rankings ──
    with col2:
        st.info("📊 Computing Nora Finance rankings...")
    try:
        df_rankings = get_weekly_rankings()
        with col2:
            st.success(f"✅ Scored {len(df_rankings)} stocks")
    except Exception as e:
        with col2:
            st.error(f"❌ Scoring failed: {str(e)}")
        return None, None, [], company_names

    # ── Step 3: Get top 10 BUY and SELL candidates ──
    top_10_buys = df_rankings[df_rankings["signal"] == "BUY"].head(10)
    top_10_sells = df_rankings[df_rankings["signal"] == "SELL"].head(10)
    
    # ── Step 4: Validate with OpenAI ──
    with col3:
        st.info("🤖 Validating top 20 with OpenAI...")
    
    validated_buy_stocks = []
    validated_sell_stocks = []
    
    # Process BUY stocks
    for idx, (_, stock) in enumerate(top_10_buys.iterrows(), 1):
        symbol = stock.get("symbol", "—")
        company_name = company_names.get(symbol, symbol)
        current_price = float(stock.get("close", 0))
        confidence = stock.get("confidence", 0)
        sector = stock.get("sector", "—")
        
        # Get OpenAI validation
        validation = validate_stock_with_openai(symbol, company_name, current_price, confidence, sector, news_items)
        
        # Estimate 5-day price (for display only, not sent to OpenAI)
        # Based on rank, not confidence
        rank = int(stock.get("rank", 52))
        predicted_price = estimate_5day_price(current_price, rank)
        price_change_pct = ((predicted_price - current_price) / current_price) * 100
        
        validated_buy_stocks.append({
            "symbol": symbol,
            "name": company_name,
            "sector": sector,
            "rank": stock.get("rank"),
            "confidence": confidence,
            "current_price": current_price,
            "predicted_price": predicted_price,
            "price_change_pct": price_change_pct,
            "validation": validation,
        })
    
    # Process SELL stocks
    for idx, (_, stock) in enumerate(top_10_sells.iterrows(), 1):
        symbol = stock.get("symbol", "—")
        company_name = company_names.get(symbol, symbol)
        current_price = float(stock.get("close", 0))
        confidence = stock.get("confidence", 0)
        sector = stock.get("sector", "—")
        
        # Get OpenAI validation
        validation = validate_stock_with_openai(symbol, company_name, current_price, confidence, sector, news_items)
        
        # Estimate 5-day price (for display only, not sent to OpenAI)
        rank = int(stock.get("rank", 52))
        predicted_price = estimate_5day_price(current_price, rank)
        price_change_pct = ((predicted_price - current_price) / current_price) * 100
        
        validated_sell_stocks.append({
            "symbol": symbol,
            "name": company_name,
            "sector": sector,
            "rank": stock.get("rank"),
            "confidence": confidence,
            "current_price": current_price,
            "predicted_price": predicted_price,
            "price_change_pct": price_change_pct,
            "validation": validation,
        })
    
    with col3:
        st.success(f"✅ Validated {len(validated_buy_stocks)} BUY + {len(validated_sell_stocks)} SELL")

    return validated_buy_stocks, validated_sell_stocks, news_items, company_names


# ─────────────────────────────────────────────────────────────────────────────
# UI LAYOUT
# ─────────────────────────────────────────────────────────────────────────────

st.markdown("""
# 🏦 Nora Finance — Weekly Stock Advisor

Get the **top 10 stocks** from Nora Finance's quantitative momentum model,
validated by OpenAI's analysis of live Tadawul data and recent news & announcements.

Each stock shows today's price, 5-day prediction, and OpenAI's validation.
""")

# ── Settings ──
with st.expander("⚙️ Settings", expanded=False):
    col1, col2 = st.columns(2)
    with col1:
        days_back = st.slider(
            "Fetch news from the last N days",
            min_value=1,
            max_value=14,
            value=7,
            step=1,
        )
    with col2:
        st.info(f"📊 Analyzing **52 Tadawul stocks**, showing **top 10** with OpenAI validation")

# ── Trigger Button ──
st.divider()
col_left, col_center, col_right = st.columns([1, 2, 1])
with col_center:
    run_button = st.button(
        "🔍 Analyze top 10 stocks with OpenAI validation",
        key="run_analysis",
        use_container_width=True,
    )

st.divider()

# ── Run Analysis ──
if run_button:
    with st.spinner("Running full pipeline..."):
        validated_buy_stocks, validated_sell_stocks, news_items, company_names = run_analysis(days_back)

    if validated_buy_stocks is not None:
        st.session_state["results"] = {
            "validated_buy_stocks": validated_buy_stocks,
            "validated_sell_stocks": validated_sell_stocks,
            "news_items": news_items,
            "days_back": days_back,
        }

# ── Display Results ──
if "results" in st.session_state:
    results = st.session_state["results"]
    validated_buy_stocks = results["validated_buy_stocks"]
    validated_sell_stocks = results["validated_sell_stocks"]
    news_items = results["news_items"]
    days_back = results["days_back"]

    st.markdown("## 📊 Top 10 to BUY + Top 10 to SELL - Nora Finance Model + OpenAI Validation")

    # ── News Digest ──
    with st.expander(f"📰 {len(news_items)} news items used in analysis (last {days_back} days)", expanded=False):
        for i, item in enumerate(news_items[:20], 1):
            st.caption(f"{i}. {item}")

    st.divider()

    # ── BUY SECTION ──
    st.markdown("### 📈 TOP 10 TO BUY")
    
    for stock in validated_buy_stocks:
        with st.container(border=True):
            # Header with symbol and rank
            col_rank, col_symbol, col_sector = st.columns([0.5, 1, 1.5])
            with col_rank:
                st.markdown(f"### 🏆 #{stock['rank']}")
            with col_symbol:
                st.markdown(f"### {stock['symbol']}")
            with col_sector:
                st.markdown(f"*{SECTOR_LABELS.get(stock['sector'], stock['sector'])}*")

            # Company name
            st.markdown(f"**{stock['name']}**")

            # Price information
            col_today, col_predicted, col_change = st.columns(3)
            with col_today:
                st.metric(
                    label="Current Price",
                    value=f"{stock['current_price']:.2f} SAR",
                )
            with col_predicted:
                st.metric(
                    label="Predicted (5 days)",
                    value=f"{stock['predicted_price']:.2f} SAR",
                    delta=f"{stock['price_change_pct']:.2f}%"
                )
            with col_change:
                st.metric(
                    label="Model Confidence (Momentum)",
                    value=f"{stock['confidence']:.1%}",
                )

            # OpenAI Trade Check (structured format)
            st.markdown("**📋 OpenAI Trade Check:**")
            st.markdown(stock['validation'], unsafe_allow_html=True)

    st.divider()

    # ── SELL SECTION ──
    st.markdown("### 📉 TOP 10 TO SELL")
    
    for stock in validated_sell_stocks:
        with st.container(border=True):
            # Header with symbol and rank
            col_rank, col_symbol, col_sector = st.columns([0.5, 1, 1.5])
            with col_rank:
                st.markdown(f"### 🏆 #{stock['rank']}")
            with col_symbol:
                st.markdown(f"### {stock['symbol']}")
            with col_sector:
                st.markdown(f"*{SECTOR_LABELS.get(stock['sector'], stock['sector'])}*")

            # Company name
            st.markdown(f"**{stock['name']}**")

            # Price information
            col_today, col_predicted, col_change = st.columns(3)
            with col_today:
                st.metric(
                    label="Current Price",
                    value=f"{stock['current_price']:.2f} SAR",
                )
            with col_predicted:
                st.metric(
                    label="Predicted (5 days)",
                    value=f"{stock['predicted_price']:.2f} SAR",
                    delta=f"{stock['price_change_pct']:.2f}%"
                )
            with col_change:
                st.metric(
                    label="Model Confidence (Momentum)",
                    value=f"{stock['confidence']:.1%}",
                )

            # OpenAI Trade Check (structured format)
            st.markdown("**📋 OpenAI Trade Check:**")
            st.markdown(stock['validation'], unsafe_allow_html=True)

    st.divider()
    st.caption(
        "⚠️ **Disclaimer:** This tool is for informational purposes only and does not constitute financial advice. "
        "Confidence scores reflect quantitative momentum signals, not fundamental analysis. News context may be macro/sector-wide and unrelated to specific companies. "
        "Always consult a licensed broker before making investment decisions."
    )