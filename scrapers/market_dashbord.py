import requests
from datetime import datetime
from news_tadawul import NewsTadawul


TASI_URL = "https://www.saudiexchange.sa/tadawul.eportal.theme.helper/ThemeTASIUtilityServlet"
TICKER_URL = "https://www.saudiexchange.sa/tadawul.eportal.theme.helper/TickerServlet"


# ------------------------------------------------------------
# Hardcoded cURL-Mimicking Headers
# ------------------------------------------------------------
HEADERS = {
    "Accept": "application/json, text/plain, */*",
    "Accept-Encoding": "gzip, deflate, br",
    "Accept-Language": "en-US,en;q=0.9",
    "Cache-Control": "max-age=0",
    "Connection": "keep-alive",
    "Referer": "https://www.saudiexchange.sa/",
    "Sec-CH-UA": '"Not:A-Brand";v="99", "Google Chrome";v="145", "Chromium";v="145"',
    "Sec-CH-UA-Mobile": "?0",
    "Sec-CH-UA-Platform": '"macOS"',
    "Sec-Fetch-Dest": "document",
    "Sec-Fetch-Mode": "navigate",
    "Sec-Fetch-Site": "same-origin",
    "Upgrade-Insecure-Requests": "1",
    "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
                  "AppleWebKit/537.36 (KHTML, like Gecko) "
                  "Chrome/145.0.0.0 Safari/537.36",
}


# ------------------------------------------------------------
# Fetch TASI & Market Summary
# ------------------------------------------------------------
def get_market_data():
    resp = requests.get(TASI_URL, headers=HEADERS, timeout=30)
    resp.raise_for_status()
    return resp.json()


# ------------------------------------------------------------
# Fetch All Stocks
# ------------------------------------------------------------
def get_stocks():
    resp = requests.get(TICKER_URL, headers=HEADERS, timeout=30)
    resp.raise_for_status()
    data = resp.json()
    return data.get("stockData", [])


# ------------------------------------------------------------
# Calculate Top Gainers & Losers
# ------------------------------------------------------------
def calculate_movers(stocks, top_n=5):
    valid = [
        s for s in stocks
        if s.get("changePercent") not in (None, "")
    ]

    gainers = sorted(valid, key=lambda x: float(x["changePercent"]), reverse=True)[:top_n]
    losers = sorted(valid, key=lambda x: float(x["changePercent"]))[:top_n]

    return gainers, losers


# ------------------------------------------------------------
# Print Dashboard
# ------------------------------------------------------------
def print_dashboard():
    print("=" * 60)
    print("SAUDI MARKET DASHBOARD")
    print("=" * 60)

    # ---------------- TASI ----------------
    market = get_market_data()

    print("\nTASI INDEX")
    print("Value:", market.get("tasiValue"))
    print("Change:", market.get("tasiNetChange"))
    print("Percent:", market.get("tasiPercentageChange"), "%")

    # ---------------- Market Summary ----------------
    summary = market.get("marketBean", {})

    print("\nMARKET SUMMARY")
    print("Total Trades:", summary.get("noOfTrades"))
    print("Volume Traded:", summary.get("volumeTraded"))
    print("Turnover:", summary.get("turnover"))
    print("Ups:", summary.get("noOfUps"))
    print("Downs:", summary.get("noOfDowns"))
    print("No Change:", summary.get("noOfNoChanges"))

    # ---------------- Stocks ----------------
    stocks = get_stocks()

    print("\nSAMPLE STOCK PRICES (First 10)")
    for s in stocks[:10]:
        print(
            s.get("companyShortNameEn"),
            "| Price:", s.get("lastTradePrice"),
            "| Volume:", s.get("volumeTraded"),
            "| Change:", s.get("changePercent"), "%"
        )

    # ---------------- Gainers / Losers ----------------
    gainers, losers = calculate_movers(stocks)

    print("\nTOP GAINERS")
    for g in gainers:
        print(
            g.get("companyShortNameEn"),
            "| Price:", g.get("lastTradePrice"),
            "| Change:", g.get("changePercent"), "%"
        )

    print("\nTOP LOSERS")
    for l in losers:
        print(
            l.get("companyShortNameEn"),
            "| Price:", l.get("lastTradePrice"),
            "| Change:", l.get("changePercent"), "%"
        )

    # ---------------- Announcements ----------------
    import requests
    from datetime import datetime, timedelta
    from news_tadawul import NewsTadawul

    yesterday = (datetime.now() - timedelta(days=1)).strftime("%m/%d/%Y")
    tomorrow = (datetime.now() + timedelta(days=1)).strftime("%m/%d/%Y")


    scraper = NewsTadawul(
        from_date=yesterday,
        to_date=tomorrow,
        page_size=20,
        locale="ar"
    )

    news = scraper.fetch_all()

    print("\nTODAY ANNOUNCEMENTS")
    for n in news[:10]:
        print("-", n.get("publish_time"), "|", n.get("title"))

    print("\nDone.")


# ------------------------------------------------------------
if __name__ == "__main__":
    print_dashboard()