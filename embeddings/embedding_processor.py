import os
import psycopg2
import numpy as np
from dotenv import load_dotenv
from openai import OpenAI

# ------------------------
# Load environment
# ------------------------
load_dotenv()

client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))

# ------------------------
# DB connection
# ------------------------
conn = psycopg2.connect(
    dbname=os.getenv("DB_NAME"),
    user=os.getenv("DB_USER"),
    password=os.getenv("DB_PASSWORD"),
    host=os.getenv("DB_HOST"),
    port=os.getenv("DB_PORT"),
)

cursor = conn.cursor()
print("✅ Connected to DB")

MODEL = "text-embedding-3-small"


# ------------------------
# Function to generate embedding
# ------------------------
def generate_embedding(text):
    response = client.embeddings.create(
        model=MODEL,
        input=text
    )
    return response.data[0].embedding


# ------------------------
# 1️⃣ Embed NEWS
# ------------------------
cursor.execute("""
    SELECT n.id, n.title, n.summary
    FROM news n
    LEFT JOIN embeddings e
        ON e.entity_type = 'news'
        AND e.entity_id = n.id
    WHERE e.id IS NULL
""")

news_rows = cursor.fetchall()
print(f"📰 News to embed: {len(news_rows)}")

for row in news_rows:
    news_id, title, summary = row
    text = f"{title or ''} {summary or ''}"

    embedding = generate_embedding(text)

    cursor.execute("""
        INSERT INTO embeddings (entity_type, entity_id, embedding)
        VALUES (%s, %s, %s)
    """, ("news", news_id, embedding))

    conn.commit()
    print(f"✅ Embedded news {news_id}")


# ------------------------
# 2️⃣ Embed ANNOUNCEMENTS
# ------------------------
cursor.execute("""
    SELECT a.id, a.symbol, a.title_ar
    FROM announcements a
    LEFT JOIN embeddings e
        ON e.entity_type = 'announcement'
        AND e.entity_id = a.id
    WHERE e.id IS NULL
""")

announcement_rows = cursor.fetchall()
print(f"📢 Announcements to embed: {len(announcement_rows)}")

for row in announcement_rows:
    ann_id, symbol, title_ar = row
    text = title_ar or ""

    embedding = generate_embedding(text)

    cursor.execute("""
        INSERT INTO embeddings (entity_type, entity_id, symbol, embedding)
        VALUES (%s, %s, %s, %s)
    """, ("announcement", ann_id, symbol, embedding))

    conn.commit()
    print(f"✅ Embedded announcement {ann_id}")


cursor.close()
conn.close()
print("🚀 Embedding process completed")