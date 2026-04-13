# ==========================================
# File: analysis/run_tasi_ridge_next_day.py
# ==========================================

import pandas as pd
import numpy as np
from sklearn.linear_model import Ridge
from sklearn.preprocessing import StandardScaler
from sklearn.metrics import r2_score, mean_squared_error
import joblib

# ---------------------------------------
# Config
# ---------------------------------------
DATA_FILE = "analysis/tasi_training_dataset.csv"
MODEL_FILE = "analysis/tasi_ridge_model_next_day.pkl"
ALPHA = 10

# ---------------------------------------
# Load dataset
# ---------------------------------------
df = pd.read_csv(DATA_FILE)

# Sort by date (important)
df["date"] = pd.to_datetime(df["date"])
df = df.sort_values("date").reset_index(drop=True)

# ---------------------------------------
# Shift target to next day
# ---------------------------------------
df["tasi_return_next_day"] = df["tasi_return"].shift(-1)

# Drop last row (no next-day return available)
df = df.dropna(subset=["tasi_return_next_day"])

# ---------------------------------------
# Separate X and y
# ---------------------------------------
X = df.drop(columns=["date", "tasi_return", "tasi_return_next_day"])
y = df["tasi_return_next_day"]

# ---------------------------------------
# Time-based split (80% train, 20% test)
# ---------------------------------------
split_index = int(len(df) * 0.8)

X_train = X.iloc[:split_index]
X_test = X.iloc[split_index:]

y_train = y.iloc[:split_index]
y_test = y.iloc[split_index:]

# ---------------------------------------
# Standardize
# ---------------------------------------
scaler = StandardScaler()
X_train_scaled = scaler.fit_transform(X_train)
X_test_scaled = scaler.transform(X_test)

# ---------------------------------------
# Train Ridge
# ---------------------------------------
model = Ridge(alpha=ALPHA)
model.fit(X_train_scaled, y_train)

# ---------------------------------------
# Predictions
# ---------------------------------------
y_train_pred = model.predict(X_train_scaled)
y_test_pred = model.predict(X_test_scaled)

# ---------------------------------------
# Evaluation
# ---------------------------------------
train_r2 = r2_score(y_train, y_train_pred)
test_r2 = r2_score(y_test, y_test_pred)

train_mse = mean_squared_error(y_train, y_train_pred)
test_mse = mean_squared_error(y_test, y_test_pred)

print("========== Ridge Regression (Next-Day) ==========")
print(f"Alpha: {ALPHA}")
print()
print(f"Train R²: {train_r2:.4f}")
print(f"Test R² : {test_r2:.4f}")
print()
print(f"Train MSE: {train_mse:.6f}")
print(f"Test MSE : {test_mse:.6f}")

# ---------------------------------------
# Save model + scaler
# ---------------------------------------
joblib.dump({
    "model": model,
    "scaler": scaler
}, MODEL_FILE)

print()
print("✅ Model saved to:", MODEL_FILE)

# ---------------------------------------
# Save coefficients
# ---------------------------------------
coef_df = pd.DataFrame({
    "feature": X.columns,
    "beta": model.coef_
})

coef_df.to_csv("analysis/tasi_ridge_coefficients_next_day.csv", index=False)
print("✅ Coefficients saved to: analysis/tasi_ridge_coefficients_next_day.csv")