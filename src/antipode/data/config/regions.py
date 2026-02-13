"""
Regional configuration for synthetic data generation.
Covers Americas, EMEA, and APAC regions with country-specific settings.
"""

from typing import Dict, List, Any


REGIONS: Dict[str, Dict[str, Any]] = {
    "americas": {
        "countries": {
            "US": {"weight": 0.50, "currency": "USD", "locale": "en_US"},
            "CA": {"weight": 0.08, "currency": "CAD", "locale": "en_CA"},
            "BR": {"weight": 0.05, "currency": "BRL", "locale": "pt_BR"},
            "MX": {"weight": 0.03, "currency": "MXN", "locale": "es_MX"},
        },
        "reporting_threshold": 10000,  # USD
        "regulators": ["FinCEN", "FINTRAC", "COAF"],
    },
    "emea": {
        "countries": {
            "GB": {"weight": 0.12, "currency": "GBP", "locale": "en_GB"},
            "DE": {"weight": 0.08, "currency": "EUR", "locale": "de_DE"},
            "FR": {"weight": 0.06, "currency": "EUR", "locale": "fr_FR"},
            "CH": {"weight": 0.04, "currency": "CHF", "locale": "de_CH"},
            "NL": {"weight": 0.03, "currency": "EUR", "locale": "nl_NL"},
            "AE": {"weight": 0.03, "currency": "AED", "locale": "ar_AE"},
            "ZA": {"weight": 0.02, "currency": "ZAR", "locale": "en_ZA"},
            "SA": {"weight": 0.02, "currency": "SAR", "locale": "ar_SA"},
        },
        "reporting_threshold": 10000,  # EUR equivalent
        "regulators": ["FCA", "BaFin", "ACPR", "FINMA", "DNB"],
    },
    "apac": {
        "countries": {
            "IN": {"weight": 0.15, "currency": "INR", "locale": "en_IN"},
            "SG": {"weight": 0.06, "currency": "SGD", "locale": "en_SG"},
            "HK": {"weight": 0.05, "currency": "HKD", "locale": "zh_HK"},
            "AU": {"weight": 0.04, "currency": "AUD", "locale": "en_AU"},
            "JP": {"weight": 0.04, "currency": "JPY", "locale": "ja_JP"},
            "CN": {"weight": 0.03, "currency": "CNY", "locale": "zh_CN"},
            "MY": {"weight": 0.02, "currency": "MYR", "locale": "ms_MY"},
        },
        "reporting_threshold": 500000,  # INR / varies by country
        "regulators": ["FIU-IND", "MAS", "HKMA", "AUSTRAC", "JAFIC"],
    },
}

# High-risk jurisdictions (for corridor risk)
HIGH_RISK_JURISDICTIONS: List[str] = [
    # Sanctioned
    "IR", "KP", "SY", "CU", "VE", "MM", "AF", "YE", "LY", "SS",
    # Grey list (FATF)
    "PK", "NG", "PH", "TZ", "UG",
]

# Offshore financial centers
OFFSHORE_JURISDICTIONS: List[str] = [
    "KY", "VG", "BM", "PA", "JE", "GG", "IM", "LI", "MC", "AD",
]

# India-specific configuration
INDIA_CONFIG: Dict[str, Any] = {
    "states": [
        "Maharashtra", "Karnataka", "Tamil Nadu", "Delhi", "Gujarat",
        "Telangana", "West Bengal", "Rajasthan", "Uttar Pradesh", "Kerala",
    ],
    "cities_by_state": {
        "Maharashtra": ["Mumbai", "Pune", "Nagpur", "Thane", "Nashik"],
        "Karnataka": ["Bengaluru", "Mysuru", "Hubli", "Mangaluru"],
        "Tamil Nadu": ["Chennai", "Coimbatore", "Madurai", "Tiruchirappalli"],
        "Delhi": ["New Delhi", "Noida", "Gurgaon", "Faridabad"],
        "Gujarat": ["Ahmedabad", "Surat", "Vadodara", "Rajkot"],
        "Telangana": ["Hyderabad", "Warangal", "Nizamabad"],
        "West Bengal": ["Kolkata", "Howrah", "Durgapur"],
        "Rajasthan": ["Jaipur", "Jodhpur", "Udaipur", "Kota"],
        "Uttar Pradesh": ["Lucknow", "Kanpur", "Varanasi", "Agra"],
        "Kerala": ["Kochi", "Thiruvananthapuram", "Kozhikode"],
    },
    "reporting_thresholds": {
        "cash": 1000000,           # INR 10 lakh
        "wire_international": 500000,  # INR 5 lakh
        "suspicious": 0,          # Any amount if suspicious
    },
    "regulators": ["FIU-IND", "RBI", "SEBI"],
    "id_types": ["PAN", "Aadhaar", "Passport", "Voter_ID", "Driving_License"],
    "bank_codes": {
        "SBI": "State Bank of India",
        "HDFC": "HDFC Bank",
        "ICICI": "ICICI Bank",
        "AXIS": "Axis Bank",
        "KOTAK": "Kotak Mahindra Bank",
        "PNB": "Punjab National Bank",
        "BOB": "Bank of Baroda",
        "CANARA": "Canara Bank",
        "UNION": "Union Bank of India",
        "IDBI": "IDBI Bank",
    },
}

# Country risk scores (0-100)
COUNTRY_RISK_SCORES: Dict[str, int] = {
    # Low risk
    "US": 15, "GB": 12, "DE": 10, "FR": 12, "CA": 10,
    "AU": 10, "JP": 8, "SG": 12, "NL": 10, "CH": 20,
    # Medium risk
    "IN": 35, "CN": 40, "BR": 45, "MX": 50, "ZA": 45,
    "AE": 40, "SA": 45, "HK": 30, "MY": 35,
    # High risk
    "PK": 70, "NG": 75, "PH": 55, "TZ": 65, "UG": 60,
    # Very high risk (sanctioned/offshore)
    "IR": 95, "KP": 99, "SY": 95, "CU": 85, "VE": 80,
    "KY": 60, "VG": 65, "PA": 70, "BM": 55,
}


def get_all_countries() -> Dict[str, Dict[str, Any]]:
    """Get flattened dict of all countries across regions."""
    all_countries = {}
    for region_data in REGIONS.values():
        all_countries.update(region_data["countries"])
    return all_countries


def get_country_risk(country_code: str) -> int:
    """Get risk score for a country (0-100)."""
    return COUNTRY_RISK_SCORES.get(country_code, 50)


def is_high_risk_jurisdiction(country_code: str) -> bool:
    """Check if country is high-risk."""
    return country_code in HIGH_RISK_JURISDICTIONS


def is_offshore_jurisdiction(country_code: str) -> bool:
    """Check if country is an offshore financial center."""
    return country_code in OFFSHORE_JURISDICTIONS
