# ==========================================
# File: analysis/build_training_dataset.py
# ==========================================

import pandas as pd

# ---------------------------------------
# File paths
# ---------------------------------------
EMBEDDINGS_FILE = "embeddings/daily_mean_embeddings_pca.csv"
RETURNS_FILE = "analysis/tasi_daily_returns.csv"
OUTPUT_FILE = "analysis/tasi_training_dataset.csv"

# ---------------------------------------
# Load data
# ---------------------------------------
emb_df = pd.read_csv(EMBEDDINGS_FILE)
ret_df = pd.read_csv(RETURNS_FILE)

# Convert date columns to datetime
emb_df["date"] = pd.to_datetime(emb_df["date"])
ret_df["date"] = pd.to_datetime(ret_df["date"])

# ---------------------------------------
# Merge on date (keep only overlapping days)
# ---------------------------------------
training_df = pd.merge(
    emb_df,
    ret_df[["date", "tasi_return"]],
    on="date",
    how="inner"
)

# Sort by date
training_df = training_df.sort_values("date").reset_index(drop=True)

# ---------------------------------------
# Save final dataset
# ---------------------------------------
training_df.to_csv(OUTPUT_FILE, index=False)

print("✅ Training dataset saved to:", OUTPUT_FILE)
print("Shape:", training_df.shape)
print(training_df.head())