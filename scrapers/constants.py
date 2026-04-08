"""
Saudi Exchange Constants
Version: 2.0
Purpose: Central configuration for market ingestion & filtering
"""

from typing import Dict


# ==========================================================
# PRODUCT TYPES
# ==========================================================

PRODUCT_TYPES: Dict[str, Dict[str, str]] = {
    "MAIN_MARKET": {
        "value": "MAIN_MARKET",
        "label_ar": "السوق الرئيسية",
    },
    "NOMU_MARKET": {
        "value": "NOMU_MARKET",
        "label_ar": "نمو - السوق الموازية",
    },
    "REITS": {
        "value": "REITs",
        "label_ar": "صناديق الاستثمار العقارية",
    },
    "ETFS": {
        "value": "ETFs",
        "label_ar": "صناديق المؤشرات",
    },
    "CEFS": {
        "value": "CEFs",
        "label_ar": "صناديق الاستثمار المغلقة",
    },
    "MUTUAL_FUNDS": {
        "value": "MF",
        "label_ar": "صناديق الإستثمار",
    },
}

PRODUCT_VALUE_TO_KEY = {
    data["value"]: key
    for key, data in PRODUCT_TYPES.items()
}


# ==========================================================
# SECTORS
# ==========================================================

SECTORS: Dict[str, Dict[str, str]] = {

    # Core
    "ENERGY": {"id": "31", "name_ar": "الطاقة", "name_en": "Energy"},
    "MATERIALS": {"id": "32", "name_ar": "المواد الأساسية", "name_en": "Materials"},
    "CAPITAL_GOODS": {"id": "33", "name_ar": "السلع الرأسمالية", "name_en": "Capital Goods"},
    "COMMERCIAL_SERVICES": {"id": "34", "name_ar": "الخدمات التجارية والمهنية", "name_en": "Commercial Services"},
    "TRANSPORTATION": {"id": "35", "name_ar": "النقل", "name_en": "Transportation"},

    # Consumer
    "CONSUMER_DURABLES": {"id": "37", "name_ar": "السلع طويلة الاجل", "name_en": "Consumer Durables"},
    "CONSUMER_SERVICES": {"id": "38", "name_ar": "الخدمات الإستهلاكية", "name_en": "Consumer Services"},
    "MEDIA_ENTERTAINMENT": {"id": "39", "name_ar": "الإعلام والترفيه", "name_en": "Media & Entertainment"},
    "RETAIL_DISCRETIONARY": {"id": "40", "name_ar": "تجزئة وتوزيع السلع الكمالية", "name_en": "Retail - Discretionary"},
    "RETAIL_STAPLES": {"id": "41", "name_ar": "تجزئة وتوزيع السلع الاستهلاكية", "name_en": "Retail - Staples"},
    "FOOD_BEVERAGE": {"id": "42", "name_ar": "إنتاج الأغذية", "name_en": "Food & Beverage"},
    "HOUSEHOLD_PRODUCTS": {"id": "43", "name_ar": "المنتجات المنزلية و الشخصية", "name_en": "Household Products"},

    # Healthcare
    "HEALTHCARE": {"id": "44", "name_ar": "الرعاية الصحية", "name_en": "Healthcare"},
    "PHARMACEUTICALS": {"id": "45", "name_ar": "الادوية", "name_en": "Pharmaceuticals"},

    # Financial
    "BANKS": {"id": "46", "name_ar": "البنوك", "name_en": "Banks"},
    "FINANCIAL_SERVICES": {"id": "47", "name_ar": "الخدمات المالية", "name_en": "Financial Services"},
    "INSURANCE": {"id": "48", "name_ar": "التأمين", "name_en": "Insurance"},

    # Tech / Telecom
    "SOFTWARE_SERVICES": {"id": "49", "name_ar": "التطبيقات وخدمات التقنية", "name_en": "Software & Services"},
    "TELECOMMUNICATIONS": {"id": "52", "name_ar": "الإتصالات", "name_en": "Telecommunications"},

    # Utilities / Real Estate
    "UTILITIES": {"id": "53", "name_ar": "المرافق العامة", "name_en": "Utilities"},
    "REIT_FUNDS": {"id": "21", "name_ar": "الصناديق العقارية المتداولة", "name_en": "REIT Funds"},
    "REAL_ESTATE_DEVELOPMENT": {"id": "54", "name_ar": "إدارة وتطوير العقارات", "name_en": "Real Estate Development"},
}

SECTOR_ID_TO_KEY = {
    data["id"]: key
    for key, data in SECTORS.items()
}


# ==========================================================
# ANNOUNCEMENT TYPES (Issuer)
# ==========================================================

ANNOUNCEMENT_TYPES: Dict[str, Dict[str, str]] = {

    # Financial Results
    "FINANCIAL_RESULTS_ANNUAL_COMPANIES": {"code": "1_17"},
    "FINANCIAL_RESULTS_PRELIM_COMPANIES": {"code": "1_18"},
    "FINANCIAL_RESULTS_ANNUAL_BANKS": {"code": "1_19"},
    "FINANCIAL_RESULTS_PRELIM_BANKS": {"code": "1_20"},
    "FINANCIAL_RESULTS_ANNUAL_INSURANCE": {"code": "1_21"},
    "FINANCIAL_RESULTS_PRELIM_INSURANCE": {"code": "1_22"},

    # Capital
    "CAPITAL_INCREASE_BONUS": {"code": "1_46"},
    "CAPITAL_INCREASE_RIGHTS": {"code": "1_24"},
    "CAPITAL_DECREASE": {"code": "1_49"},

    # M&A
    "MOU_SIGNED": {"code": "1_61"},
    "ACQUISITION_AGREEMENT": {"code": "1_51"},

    # Governance
    "BOARD_CHANGES": {"code": "1_23"},
}

ANNOUNCEMENT_CODE_TO_KEY = {
    data["code"]: key
    for key, data in ANNOUNCEMENT_TYPES.items()
}


# ==========================================================
# LOOKUP HELPERS
# ==========================================================

def get_sector_key_by_id(sector_id: str) -> str | None:
    return SECTOR_ID_TO_KEY.get(str(sector_id))


def get_sector_id_by_key(sector_key: str) -> str | None:
    sector = SECTORS.get(sector_key)
    return sector["id"] if sector else None


def get_product_key_by_value(value: str) -> str | None:
    return PRODUCT_VALUE_TO_KEY.get(value)


def get_product_value_by_key(key: str) -> str | None:
    product = PRODUCT_TYPES.get(key)
    return product["value"] if product else None


def get_announcement_key_by_code(code: str) -> str | None:
    return ANNOUNCEMENT_CODE_TO_KEY.get(code)


def get_announcement_code_by_key(key: str) -> str | None:
    ann = ANNOUNCEMENT_TYPES.get(key)
    return ann["code"] if ann else None


# ==========================================================
# PAYLOAD BUILDER
# ==========================================================

def build_filter_payload(
    product_key: str,
    sector_key: str,
    announcement_key: str,
    from_date: str,
    to_date: str,
    page: int = 1,
    page_size: int = 50
) -> dict:

    product_value = get_product_value_by_key(product_key)
    sector_id = get_sector_id_by_key(sector_key)
    announcement_code = get_announcement_code_by_key(announcement_key)

    if not all([product_value, sector_id, announcement_code]):
        raise ValueError("Invalid product, sector, or announcement key")

    return {
        "annoucmentType": announcement_code,
        "symbol": "",
        "sectorDpId": sector_id,
        "searchType": "1",
        "fromDate": from_date,
        "toDate": to_date,
        "datePeriod": "",
        "productType": product_value,
        "advisorsList": "-1",
        "textSearch": "",
        "pageNumberDb": str(page),
        "pageSize": str(page_size),
    }