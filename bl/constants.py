# bl/constants.py
"""
Shared constants across the Nora Finance system.
"""

SECTOR_MAP: dict[str, str] = {
    # ── Energy ──────────────────────────────────────────────────────────────
    "2222": "Energy", "2380": "Energy", "2381": "Energy",
    "2382": "Energy", "4030": "Energy", "2030": "Energy",
    # ── Materials ────────────────────────────────────────────────────────────
    "2010": "Materials", "2020": "Materials", "2060": "Materials",
    "2310": "Materials", "2350": "Materials", "1211": "Materials",
    "1321": "Materials", "1322": "Materials", "2223": "Materials",
    "2250": "Materials", "2290": "Materials", "2150": "Materials",
    # ── Cement ───────────────────────────────────────────────────────────────
    "3030": "Cement", "3092": "Cement", "3004": "Cement", "3050": "Cement",
    # ── Banks ────────────────────────────────────────────────────────────────
    "1120": "Banks", "1180": "Banks", "1150": "Banks",
    "1050": "Banks", "1060": "Banks", "1080": "Banks",
    # ── Telecom ──────────────────────────────────────────────────────────────
    "7010": "Telecom", "7020": "Telecom",
    # ── Utilities ────────────────────────────────────────────────────────────
    "2082": "Utilities", "2080": "Utilities",
    # ── Healthcare ───────────────────────────────────────────────────────────
    "4013": "Healthcare", "4004": "Healthcare",
    "4009": "Healthcare", "4017": "Healthcare",
    # ── Consumer ─────────────────────────────────────────────────────────────
    "4190": "Consumer", "4001": "Consumer", "2280": "Consumer",
    "2050": "Consumer", "4164": "Consumer", "4240": "Consumer",
    "4003": "Consumer", "4161": "Consumer",
    # ── Real Estate ──────────────────────────────────────────────────────────
    "4300": "RealEstate", "4321": "RealEstate",
    # ── Software ─────────────────────────────────────────────────────────────
    "7203": "Software", "7202": "Software",
    # ── Capital Goods ────────────────────────────────────────────────────────
    "1212": "CapitalGoods", "2320": "CapitalGoods",
    "2040": "CapitalGoods", "4142": "CapitalGoods",
}

# Human-friendly sector labels for display
SECTOR_LABELS: dict[str, str] = {
    "Energy":       "⛽ Energy",
    "Materials":    "🧪 Materials",
    "Cement":       "🏗️ Cement",
    "Banks":        "🏦 Banks",
    "Telecom":      "📡 Telecom",
    "Utilities":    "💡 Utilities",
    "Healthcare":   "🏥 Healthcare",
    "Consumer":     "🛍️ Consumer",
    "RealEstate":   "🏢 Real Estate",
    "Software":     "💻 Software",
    "CapitalGoods": "⚙️ Capital Goods",
}