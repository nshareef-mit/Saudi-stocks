# ==========================================
# File: analysis/build_tasi_returns.py
# ==========================================

import json
import pandas as pd
import numpy as np

INPUT_FILE = "analysis/tasi_historical_data.json"
OUTPUT_FILE = "analysis/tasi_daily_returns.csv"

# ----------------------------------
# Load JSON
# ----------------------------------
with open(INPUT_FILE, "r") as f:
    data = json.load(f)

df = pd.DataFrame(data)

# ----------------------------------
# Clean & format
# ----------------------------------

# Convert date
df["date"] = pd.to_datetime(df["transactionDate"], format="%Y/%m/%d")

# Remove commas and convert to float
df["previousClosePrice"] = (
    df["previousClosePrice"]
    .str.replace(",", "", regex=False)
    .astype(float)
)

# Sort by date ASCENDING (very important)
df = df.sort_values("date").reset_index(drop=True)

# ----------------------------------
# Compute Daily Return
# return_t = (P_t - P_{t-1}) / P_{t-1}
# ----------------------------------

df["tasi_return"] = df["previousClosePrice"].pct_change()

# Drop first row (no previous day)
df = df.dropna(subset=["tasi_return"])

# Keep only what we need
df_final = df[["date", "previousClosePrice", "tasi_return"]]

# ----------------------------------
# Save CSV
# ----------------------------------
df_final.to_csv(OUTPUT_FILE, index=False)

print("✅ TASI daily returns saved to:", OUTPUT_FILE)
print("Shape:", df_final.shape)
print(df_final.head())