import requests
import json
import re
from pathlib import Path
import psycopg2
import os
from dotenv import load_dotenv
from datetime import datetime

load_dotenv()


CATEGORY_URLS = {
    "sports": "https://www.aleqt.com/%D8%A7%D9%84%D8%B1%D9%8A%D8%A7%D8%B6%D8%A9",
    "art": "https://www.aleqt.com/%D8%A7%D9%84%D9%81%D9%86-%D8%A7%D9%84%D8%B3%D8%A7%D8%A8%D8%B9",
    "tech": "https://www.aleqt.com/%D8%A7%D9%84%D8%AA%D9%83%D9%86%D9%88%D9%84%D9%88%D8%AC%D9%8A%D8%A7",
    "general": "https://www.aleqt.com/%D8%A7%D9%84%D8%A3%D8%AE%D8%A8%D8%A7%D8%B1",
    "realestates": "https://www.aleqt.com/%D8%A7%D9%84%D8%B9%D9%82%D8%A7%D8%B1%D8%A7%D8%AA",
    "energy": "https://www.aleqt.com/%D8%A7%D9%84%D8%B7%D8%A7%D9%82%D8%A9",
    "reports": "https://www.aleqt.com/%D8%AA%D9%82%D8%A7%D8%B1%D9%8A%D8%B1-%D9%88%D8%AA%D8%AD%D9%84%D9%8A%D9%84%D8%A7%D8%AA",
    "companies": "https://www.aleqt.com/%D8%A7%D9%84%D8%B4%D8%B1%D9%83%D8%A7%D8%AA",
}

BASE_HEADERS = {
    "Accept": "text/x-component",
    "Content-Type": "text/plain;charset=UTF-8",
    "Next-Action": "7fc228a0fe93b14fff7ca3650290806e62c9e3956f", #--hardcoded, yes, because i will execute this code only once--
    "Origin": "https://www.aleqt.com",
    "User-Agent": "Mozilla/5.0"#,
    #"Next-Router-State-Tree": "%5B%22%22%2C%7B%22children%22%3A%5B%22(root)%22%2C%7B%22children%22%3A%5B%5B%22slug%22%2C%22%25D8%25A7%25D9%2584%25D8%25B1%25D9%258A%25D8%25A7%25D8%25B6%25D8%25A9%2２%2C%２２c％２２％５Ｂ％２２__PAGE__％２２％７Ｂ％７D％２Cnull％２Cnull％５D％7D％２Cnull％２Cnull％５D％7D％２Cnull％２Cnull％２Ctrue％５D"
}
#BASE_HEADERS["Next-Router-State-Tree"] = BASE_HEADERS["Next-Router-State-Tree"].encode(
#    "latin-1", "ignore"
#).decode("latin-1")

ARTICLE_RE = re.compile(
    r'"publish_time":"(.*?)".*?"article_title":"(.*?)".*?"permalink":"(.*?)"'
)

def extract_articles_from_rsc(text: str, article_type: str):
    articles = []
    for publish_time, title, permalink in ARTICLE_RE.findall(text):
        articles.append({
            "type": article_type,
            "title": title,
            "publish_time": publish_time,
            "url": permalink,
        })
    return articles

def fetch_all_articles(article_type: str, stop_year: int = 2022, limit: int = 9):
    if article_type not in CATEGORY_URLS:
        raise ValueError(f"Unknown type '{article_type}'. Valid: {list(CATEGORY_URLS)}")

    url = CATEGORY_URLS[article_type]
    print(f"🌐 URL: {url}")

    headers = dict(BASE_HEADERS)
    headers["Referer"] = url

    page = 0
    all_articles = []

    while True:
        payload = [{
            "page": page,
            "limit": limit,
            "id": 1764
        }]

        resp = requests.post(url, headers=headers, data=json.dumps(payload, ensure_ascii=False))
        resp.encoding = "utf-8"

        if resp.status_code != 200:
            print(f"❌ {article_type}: request failed ({resp.status_code})")
            break

        articles = extract_articles_from_rsc(resp.text, article_type)

        if not articles:
            print(f"✅ {article_type}: no more articles.")
            break

        for a in articles:
            year = int(a["publish_time"][:4])
            if year < stop_year:
                print(f"✅ {article_type}: reached < {stop_year}. stopping.")
                return all_articles
            all_articles.append(a)

        print(f"✅ {article_type}: page {page} fetched ({len(articles)} articles)")
        page += 1

    return all_articles

def get_db_connection():
    return psycopg2.connect(
        dbname=os.getenv("DB_NAME"),
        user=os.getenv("DB_USER"),
        password=os.getenv("DB_PASSWORD"),
        host=os.getenv("DB_HOST"),
        port=os.getenv("DB_PORT"),
    )

def load_json_list(path: Path):
    if not path.exists():
        return []

    if path.stat().st_size == 0:   # ✅ file exists but empty
        return []

    try:
        with path.open("r", encoding="utf-8") as f:
            data = json.load(f)

        if not isinstance(data, list):
            return []

        return data

    except json.JSONDecodeError:
        print("⚠ Warning: JSON file corrupted or empty. Resetting.")
        return []

def append_to_json_file(new_articles, path: Path, dedupe=True):
    existing = load_json_list(path) if path.exists() else []

    if dedupe:
        seen = {item.get("url") for item in existing if isinstance(item, dict)}
        new_articles = [a for a in new_articles if a.get("url") not in seen]

    combined = existing + new_articles

    with path.open("w", encoding="utf-8") as f:
        json.dump(combined, f, ensure_ascii=False, indent=2)

    print(f"💾 appended {len(new_articles)} articles. total = {len(combined)}")

def load_all_json_articles(data_dir: Path):
    json_files = list(data_dir.glob("aleqt_news_*.json"))

    if not json_files:
        print("❌ No JSON files found.")
        return []

    all_articles = []

    for file_path in json_files:
        print(f"📂 Reading {file_path.name}")
        articles = load_json_list(file_path)
        print(f"   → {len(articles)} articles found")
        all_articles.extend(articles)

    return all_articles


def save_articles_to_db(articles):
    if not articles:
        print("❌ No articles to insert.")
        return

    conn = get_db_connection()
    cur = conn.cursor()

    inserted = 0

    for a in articles:
        try:
            published_date = datetime.fromisoformat(
                a["publish_time"].replace("Z", "+00:00")
            )

            cur.execute("""
                INSERT INTO news
                (source, published_date, title, summary, url)
                VALUES (%s, %s, %s, %s, %s)
                ON CONFLICT (url) DO NOTHING;
            """, (
                "aleqt",
                published_date,
                a["title"],
                None,
                a["url"]
            ))

            if cur.rowcount > 0:
                inserted += 1

        except Exception as e:
            print("❌ Insert error:", e)

    conn.commit()
    cur.close()
    conn.close()

    print(f"✅ Inserted {inserted} new articles.")
    conn = get_db_connection()
    cur = conn.cursor()

    inserted = 0

    for a in articles:
        try:
            published_date = datetime.fromisoformat(
                a["publish_time"].replace("Z", "+00:00")
            )

            cur.execute("""
                INSERT INTO news
                (source, published_date, title, summary, url)
                VALUES (%s, %s, %s, %s, %s)
                ON CONFLICT (url) DO NOTHING;
            """, (
                "aleqt",
                published_date,
                a["title"],
                None,   # ما عندنا summary حالياً
                a["url"]
            ))

            if cur.rowcount > 0:
                inserted += 1

        except Exception as e:
            print("❌ Insert error:", e)

    conn.commit()
    cur.close()
    conn.close()

    print(f"✅ Inserted {inserted} new articles.")

if __name__ == "__main__":
    #category = "art"

    #out_file = Path(f"scrapers/aleqt-data/aleqt_news_{category}.json")
    #out_file.parent.mkdir(parents=True, exist_ok=True)

    #if not out_file.exists():
    #    print("📁 Creating new JSON file...")
    #    out_file.write_text("[]", encoding="utf-8")

    print("🌐 Fetching articles...")
    #articles = fetch_all_articles(category)

    #append_to_json_file(articles, out_file)

    # Example: fetch multiple categories in one run
    # for t in ["general", "energy", "companies", "sports", "tech", "art", "reports", "realestates"]:
    #     articles = fetch_all_articles(t)
    #     append_to_json_file(articles, OUT_FILE)

if __name__ == "__main__":
    data_dir = Path("scrapers/aleqt-data")

    print("📥 Loading articles from JSON files...")
    articles = load_all_json_articles(data_dir)

    print(f"🚀 Saving {len(articles)} articles to DB...")
    save_articles_to_db(articles)