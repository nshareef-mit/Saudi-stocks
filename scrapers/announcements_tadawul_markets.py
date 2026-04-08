import requests
import time
import psycopg2
import os
from dotenv import load_dotenv
from datetime import datetime

# ---------- LOAD ENV ----------
load_dotenv()

DB_NAME = os.getenv("DB_NAME")
DB_USER = os.getenv("DB_USER")
DB_PASSWORD = os.getenv("DB_PASSWORD")
DB_HOST = os.getenv("DB_HOST")
DB_PORT = os.getenv("DB_PORT")

# ---------- DB CONNECTION ----------
conn = psycopg2.connect(
    dbname=DB_NAME,
    user=DB_USER,
    password=DB_PASSWORD,
    host=DB_HOST,
    port=DB_PORT
)

cursor = conn.cursor()
print("✅ Database connected")

# ---------- API ----------
URL = "https://www.saudiexchange.sa/wps/portal/saudiexchange/newsandreports/issuer-news/issuer-announcements/!ut/p/z1/lY_NDoIwHMOfhQcwqxD-zOPUODAgTBjiLmYHY0h0ejA-v8Qb-BHsrcmvacsMa5hx9tGe7L29Onvu_N7QIRQEP-bIEVcLEEpJuuLTpU9s1wd4JglqI1TuRyFkDWb-yqMsQqhVkQUptpCgcXl8kRjRb_pILmZRt2A9l0kqAk7REPhwcVDy_uEF_BhZHh27XbRu0CYT4XlP_MzK5g!!/p0/IZ7_5A602H80O0HTC060SG6UT81DI1=CZ6_5A602H80O0HTC060SG6UT81D26=NJgetAnnouncementListData=/"

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)",
    "Accept": "*/*",
    "Accept-Encoding": "gzip, deflate, br",
    "Accept-Language": "en-US,en;q=0.9",
    "Content-Type": "application/x-www-form-urlencoded; charset=UTF-8",
    "Origin": "https://www.saudiexchange.sa",
    "Referer": "https://www.saudiexchange.sa/wps/portal/saudiexchange/newsandreports/issuer-news/issuer-announcements/?page=1",
    "X-Requested-With": "XMLHttpRequest",
    "Connection": "keep-alive",
    "Cookie": "RT=z=1&dm=www.saudiexchange.sa&si=f16268f8-dfb1-468b-b404-744343d9f414&ss=mnplzuun&sl=3&tt=10u&bcn=%2F%2F173bf10a.akstat.io%2F&ld=165v&nu=207re2x3&cl=1nyo&ul=yi3&hd=yuo; marqueePosition_ltr=-6153.599999999685; _ga_DC6H7ZFCGP=GS2.1.s1775626204$o18$g1$t1775626257$j7$l0$h0; _ga_P0MCK0BGCX=GS2.1.s1775626204$o18$g1$t1775626257$j7$l0$h0; _ga=GA1.1.1162039479.1759921645; _ga_3T6X01KMEX=GS2.1.s1775626204$o14$g1$t1775626248$j16$l0$h0; TS01fdeb15=0102d17fade2cf5e40e908a0b0100ab307a17b6d759f5ee5af7f5327c5f027fa388c68830d0914fa5bde24481c106898832c950e161fd2dfd45276a52b936b874ce5cfa0107fb7c15ad245691f73647c1c4c9f424406eb9d5e8ef8de0723eb1ce423e72d32; marqueePosition_rtl=64.08; com.ibm.wps.state.preprocessors.locale.LanguageCookie=en; JSESSIONID=!Klh/zRxQspN15oVJkmmjrB1xdL66i+6SthrrlojtV0p75eG9nMAokx6D0FEFv6aXXaG61Loi7kFSTJNkmf3SK57FixN3KfAp2P8H; BIGipServerSaudiExchange.sa.app~SaudiExchange.sa_pool=2617184684.20480.0000; __utma=44173222.1162039479.1759921645.1759924382.1759924382.1; __utmz=44173222.1759924382.1.1.utmcsr=(direct)|utmccn=(direct)|utmcmd=(none)"
}

PAGE_SIZE = 10
page = 1

while True:

    payload = {
        "annoucmentType": "1_-1",
        "symbol": "",
        "sectorDpId": "",
        "searchType": "",
        "fromDate": "",
        "toDate": "",
        "datePeriod": "1 year",
        "productType": "",
        "advisorsList": "",
        "textSearch": "",
        "pageNumberDb": str(page),
        "pageSize": str(PAGE_SIZE)
    }
    

    response = requests.post(URL, headers=HEADERS, data=payload)

    if response.status_code != 200:
        print("❌ Request failed:", response.status_code)
        break

    data = response.json()
    announcements = data.get("announcementList", [])

    if not announcements:
        print("✅ No more data. Finished.")
        break

    print(f"\n--- Page {page} ---")

    for item in announcements:

        print("Inserting:", item["announcementNumber"])

        cursor.execute("""
            INSERT INTO announcements (
                announcement_number,
                symbol,
                announcement_date,
                title_ar,
                price_on_date,
                change_pct_on_date
            )
            VALUES (%s, %s, %s, %s, %s, %s)
            ON CONFLICT (announcement_number) DO NOTHING;
        """, (
            item["announcementNumber"],
            item["SYMBOL"],
            datetime.strptime(
                item["newsDateStr"],
                "%d/%m/%Y %H:%M:%S"
            ),
            item["SHORT_DESC"],
            item.get("indexChangeValue"),
            item.get("indexStockChangePresentage")
        ))

    conn.commit()  # ✅ Commit each page

    page += 1
    time.sleep(0.5)

cursor.close()
conn.close()

print("✅ Script completed successfully")