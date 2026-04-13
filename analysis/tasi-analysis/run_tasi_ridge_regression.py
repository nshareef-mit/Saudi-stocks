# ==========================================
# File: analysis/run_tasi_ridge_regression.py
# ==========================================

import pandas as pd
import numpy as np
from sklearn.linear_model import Ridge
from sklearn.preprocessing import StandardScaler
from sklearn.model_selection import train_test_split
from sklearn.metrics import r2_score, mean_squared_error
import joblib

# ---------------------------------------
# Config
# ---------------------------------------
DATA_FILE = "analysis/tasi_training_dataset.csv"
MODEL_FILE = "analysis/tasi_ridge_model.pkl"
ALPHA = 10  # regularization strength

# ---------------------------------------
# Load dataset
# ---------------------------------------
df = pd.read_csv(DATA_FILE)

# Separate X and y
X = df.drop(columns=["date", "tasi_return"])
y = df["tasi_return"]

# ---------------------------------------
# Train / Test Split (80/20)
# ---------------------------------------
X_train, X_test, y_train, y_test = train_test_split(
    X, y, test_size=0.2, shuffle=False  # keep time order
)

# ---------------------------------------
# Standardize Features
# ---------------------------------------
scaler = StandardScaler()
X_train_scaled = scaler.fit_transform(X_train)
X_test_scaled = scaler.transform(X_test)

# ---------------------------------------
# Train Ridge Regression
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

print("========== Ridge Regression Results ==========")
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
# Save coefficients for inspection
# ---------------------------------------
coef_df = pd.DataFrame({
    "feature": X.columns,
    "beta": model.coef_
})

coef_df.to_csv("analysis/tasi_ridge_coefficients.csv", index=False)
print("✅ Coefficients saved to: analysis/tasi_ridge_coefficients.csv")