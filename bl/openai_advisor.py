# bl/openai_advisor.py
"""
Calls OpenAI GPT-4o with:
  - Recent Tadawul news & announcements (from RecentNewsFetcher)
  - Live prices for the curated SECTOR_MAP watchlist

Recommends the best 5 stocks to buy and 5 to sell in Tadawul this week.
Only stocks present in SECTOR_MAP are considered.
"""

import os
import json
import logging
from openai import OpenAI
from dotenv import load_dotenv

from bl.constants import SECTOR_MAP, SECTOR_LABELS

load_dotenv()
log = logging.getLogger(__name__)


class OpenAIAdvisor:
    """
    Sends today's Tadawul news + live watchlist prices to GPT-4o
    and returns structured buy/sell recommendations.

    Only stocks whose ticker appears in SECTOR_MAP are eligible.
    """

    MODEL = "gpt-4o"

    SYSTEM_PROMPT = (
        "You are a professional Saudi stock market analyst specializing in "
        "the Tadawul (Saudi Stock Exchange). "
        "You have deep knowledge of Saudi macroeconomic conditions, oil prices, "
        "Vision 2030 catalysts, sector dynamics, and corporate earnings. "
        "You only recommend stocks from the curated watchlist provided. "
        "Your analysis is data-driven, concise, and actionable."
    )

    def __init__(self):
        api_key = os.getenv("OPENAI_API_KEY")
        if not api_key:
            raise ValueError(
                "OPENAI_API_KEY is not set. Add it to your .env: OPENAI_API_KEY=sk-..."
            )
        self.client = OpenAI(api_key=api_key)

    # ── Public ───────────────────────────────────────────────────────────────

    def get_recommendations(
        self,
        news_items: list[str],
        stock_prices: list[dict],
    ) -> dict:
        """
        Parameters
        ----------
        news_items   : List of formatted headline strings from RecentNewsFetcher.
        stock_prices : List of dicts (from GoogleFinanceScraper) with keys:
                         ticker, name, price, change_pct
                       Only tickers in SECTOR_MAP will be used.

        Returns
        -------
        {
            "buy":  [{"ticker":…, "name":…, "sector":…, "reason":…}, …],  # 5
            "sell": [{"ticker":…, "name":…, "sector":…, "reason":…}, …]   # 5
        }
        """
        # ── Filter + enrich with sector info ─────────────────────────────
        watchlist = [
            {**s, "sector": SECTOR_MAP[s["ticker"]]}
            for s in stock_prices
            if s.get("ticker") in SECTOR_MAP
        ]

        if not watchlist:
            raise ValueError(
                "No watchlist stocks found in the price data. "
                "Check that GoogleFinanceScraper returns tickers matching SECTOR_MAP."
            )

        news_block   = self._build_news_block(news_items)
        prices_block = self._build_prices_block(watchlist)
        prompt       = self._build_prompt(news_block, prices_block, len(watchlist))

        log.info(
            "Calling OpenAI %s | news=%d | watchlist_stocks=%d",
            self.MODEL, len(news_items), len(watchlist),
        )

        response = self.client.chat.completions.create(
            model=self.MODEL,
            messages=[
                {"role": "system", "content": self.SYSTEM_PROMPT},
                {"role": "user",   "content": prompt},
            ],
            temperature=0.2,
            response_format={"type": "json_object"},
        )

        raw    = response.choices[0].message.content.strip()
        result = json.loads(raw)

        if "buy" not in result or "sell" not in result:
            raise ValueError(f"Unexpected OpenAI response structure: {list(result.keys())}")

        result["buy"]  = result["buy"][:5]
        result["sell"] = result["sell"][:5]

        log.info(
            "OpenAI → %d buys, %d sells",
            len(result["buy"]), len(result["sell"]),
        )
        return result

    # ── Prompt builders ───────────────────────────────────────────────────────

    @staticmethod
    def _build_news_block(news_items: list[str]) -> str:
        if not news_items:
            return "No news provided — rely on your own market knowledge."
        return "\n".join(f"  • {n}" for n in news_items)

    @staticmethod
    def _build_prices_block(stocks: list[dict]) -> str:
        if not stocks:
            return "No price data available."

        # Group by sector for readability
        by_sector: dict[str, list[dict]] = {}
        for s in stocks:
            sector = s.get("sector", "Other")
            by_sector.setdefault(sector, []).append(s)

        lines: list[str] = []
        for sector in sorted(by_sector):
            label = SECTOR_LABELS.get(sector, sector)
            lines.append(f"\n  ── {label} ──")
            for s in by_sector[sector]:
                price = s.get("price", "N/A")
                chg   = s.get("change_pct", "—")
                name  = s.get("name", "Unknown")
                lines.append(
                    f"    {s['ticker']:6s} | {name:32s} | "
                    f"Price: {str(price):>10} SAR | Change: {str(chg):>8}"
                )

        return "\n".join(lines)

    @staticmethod
    def _build_prompt(
        news_block: str,
        prices_block: str,
        n_stocks: int,
    ) -> str:
        return f"""Here is the news I collected from the last few days on Tadawul \
(Saudi Exchange). I am not sure whether all of them will affect stock prices today, \
but I want you to consider them alongside your own market knowledge.

=== RECENT TADAWUL NEWS & ISSUER ANNOUNCEMENTS ===
{news_block}

=== TODAY'S LIVE PRICES — TADAWUL WATCHLIST ({n_stocks} stocks, grouped by sector) ===
{prices_block}

Based on:
1. The news and announcements listed above
2. Any other relevant market news you know about (oil prices, geopolitics, OPEC, Vision 2030, Saudi macro)
3. The live stock prices and today's % change
4. Upcoming corporate events visible in the announcements (AGMs, capital increases, asset sales, new contracts)
5. Sector rotation dynamics and risk/reward balance

Tell me the best 5 stocks to BUY and best 5 stocks to SELL in Tadawul this week.

Important constraints:
- Only recommend stocks that appear in the price list above
- Each recommendation must have a specific, one-sentence reason (not generic)
- Consider the stock's price momentum, sector tailwinds/headwinds, and news catalysts
- Avoid recommending the same sector for all 5 buys or all 5 sells — diversify

⚠️ Reply ONLY with valid JSON — no markdown, no extra text, no explanations outside the JSON:
{{
  "buy": [
    {{"ticker": "XXXX", "name": "Company Name", "sector": "Sector", "reason": "Specific one-sentence reason to buy"}},
    {{"ticker": "XXXX", "name": "Company Name", "sector": "Sector", "reason": "Specific one-sentence reason to buy"}},
    {{"ticker": "XXXX", "name": "Company Name", "sector": "Sector", "reason": "Specific one-sentence reason to buy"}},
    {{"ticker": "XXXX", "name": "Company Name", "sector": "Sector", "reason": "Specific one-sentence reason to buy"}},
    {{"ticker": "XXXX", "name": "Company Name", "sector": "Sector", "reason": "Specific one-sentence reason to buy"}}
  ],
  "sell": [
    {{"ticker": "XXXX", "name": "Company Name", "sector": "Sector", "reason": "Specific one-sentence reason to sell"}},
    {{"ticker": "XXXX", "name": "Company Name", "sector": "Sector", "reason": "Specific one-sentence reason to sell"}},
    {{"ticker": "XXXX", "name": "Company Name", "sector": "Sector", "reason": "Specific one-sentence reason to sell"}},
    {{"ticker": "XXXX", "name": "Company Name", "sector": "Sector", "reason": "Specific one-sentence reason to sell"}},
    {{"ticker": "XXXX", "name": "Company Name", "sector": "Sector", "reason": "Specific one-sentence reason to sell"}}
  ]
}}"""