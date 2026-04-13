# ==========================================
# File: aggregate_daily_embeddings.py
# ==========================================

import os
import psycopg2
import numpy as np
import pandas as pd
from dotenv import load_dotenv
from sklearn.decomposition import PCA

load_dotenv()

# -------------------------------
# Config
# -------------------------------
OUTPUT_RAW = "analysis/daily_mean_embeddings_raw.csv"
OUTPUT_PCA = "daily_mean_embeddings_pca.csv"
N_COMPONENTS = 50  # adjust if needed

# -------------------------------
# DB Connection
# -------------------------------
conn = psycopg2.connect(
    host=os.getenv("DB_HOST"),
    database=os.getenv("DB_NAME"),
    user=os.getenv("DB_USER"),
    password=os.getenv("DB_PASSWORD"),
    port=os.getenv("DB_PORT", 5432)
)

cur = conn.cursor()

# -------------------------------
# Fetch embeddings grouped by day
# -------------------------------
cur.execute("""
    SELECT news_date, embedding
    FROM embeddings
    WHERE entity_type IN ('news', 'announcement')
    ORDER BY news_date ASC
""")

rows = cur.fetchall()

cur.close()
conn.close()

print(f"Fetched {len(rows)} total embedding rows")

# -------------------------------
# Organize by date
# -------------------------------
daily_embeddings = {}
import ast

for news_date, embedding in rows:
    if news_date is None:
        continue

    date_key = news_date.date()

    if date_key not in daily_embeddings:
        daily_embeddings[date_key] = []

    vector = np.array(ast.literal_eval(embedding), dtype=float)
    daily_embeddings[date_key].append(vector)

print(f"Found {len(daily_embeddings)} unique days")

# -------------------------------
# Compute mean embedding per day
# -------------------------------
dates = []
mean_vectors = []

for date, vectors in daily_embeddings.items():
    mean_vec = np.mean(vectors, axis=0)
    dates.append(date)
    mean_vectors.append(mean_vec)

X = np.array(mean_vectors)

print("Shape before PCA:", X.shape)

# -------------------------------
# Save RAW (1536 dims)
# -------------------------------
raw_df = pd.DataFrame(X)
raw_df.insert(0, "date", dates)
raw_df.sort_values("date", inplace=True)
raw_df.to_csv(OUTPUT_RAW, index=False)

print(f"Saved raw daily embeddings → {OUTPUT_RAW}")

# -------------------------------
# Apply PCA
# -------------------------------
pca = PCA(n_components=N_COMPONENTS)
X_reduced = pca.fit_transform(X)

print("Shape after PCA:", X_reduced.shape)
print("Explained variance ratio sum:", pca.explained_variance_ratio_.sum())

# -------------------------------
# Save PCA version
# -------------------------------
pca_df = pd.DataFrame(X_reduced)
pca_df.insert(0, "date", dates)
pca_df.sort_values("date", inplace=True)
pca_df.to_csv(OUTPUT_PCA, index=False)

print(f"Saved PCA daily embeddings → {OUTPUT_PCA}")

print("✅ Aggregation Complete")