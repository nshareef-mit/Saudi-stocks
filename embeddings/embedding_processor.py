import os
import psycopg2
from openai import OpenAI
from dotenv import load_dotenv
from datetime import datetime, timezone

load_dotenv()

OPENAI_MODEL = "text-embedding-3-small"
BATCH_SIZE = 100

client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))

conn = psycopg2.connect(
    host=os.getenv("DB_HOST"),
    database=os.getenv("DB_NAME"),
    user=os.getenv("DB_USER"),
    password=os.getenv("DB_PASSWORD"),
    port=os.getenv("DB_PORT", 5432)
)

cur = conn.cursor()


def embed_and_store(rows, entity_type):
    if not rows:
        return 0

    texts = []
    meta = []

    for row in rows:
        if entity_type == "news":
            entity_id, title, summary, date_value, symbol = row
            text = f"{title}\n{summary or ''}"
        else:  # announcement
            entity_id, title_ar, date_value, symbol = row
            text = title_ar

        texts.append(text)
        meta.append((entity_id, date_value, symbol))

    # Create embeddings
    response = client.embeddings.create(
        model=OPENAI_MODEL,
        input=texts
    )

    embeddings = [item.embedding for item in response.data]
    created_at = datetime.now(timezone.utc)

    # Insert
    for (entity_id, news_date, symbol), embedding in zip(meta, embeddings):

        cur.execute("""
            INSERT INTO embeddings
            (entity_type, entity_id, symbol, embedding, created_at, news_date)
            VALUES (%s, %s, %s, %s, %s, %s)
            ON CONFLICT (entity_type, entity_id) DO NOTHING
        """, (
            entity_type,
            entity_id,
            symbol,
            embedding,
            created_at,
            news_date
        ))

    conn.commit()
    return len(rows)


# =====================================================
# ✅ PROCESS NEWS
# =====================================================
print("Embedding NEWS...")

while True:
    cur.execute(f"""
        SELECT n.id, n.title, n.summary, n.published_date, n.related_symbols
        FROM news n
        LEFT JOIN embeddings e
            ON e.entity_type = 'news'
            AND e.entity_id = n.id
        WHERE e.id IS NULL
        LIMIT {BATCH_SIZE}
    """)

    rows = cur.fetchall()

    if not rows:
        print("✅ All news embedded.")
        break

    count = embed_and_store(rows, "news")
    print(f"Embedded {count} news articles")


# =====================================================
# ✅ PROCESS ANNOUNCEMENTS
# =====================================================
print("\nEmbedding ANNOUNCEMENTS...")

while True:
    cur.execute(f"""
        SELECT a.announcement_number,
               a.title_ar,
               a.announcement_date,
               a.symbol
        FROM announcements a
        LEFT JOIN embeddings e
            ON e.entity_type = 'announcement'
            AND e.entity_id = a.announcement_number
        WHERE e.id IS NULL
        LIMIT {BATCH_SIZE}
    """)

    rows = cur.fetchall()

    if not rows:
        print("✅ All announcements embedded.")
        break

    count = embed_and_store(rows, "announcement")
    print(f"Embedded {count} announcements")


cur.close()
conn.close()

print("\n✅ ALL EMBEDDINGS COMPLETE")