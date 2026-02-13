"""
Realistic data pools and generators for bank-schema-aligned synthetic data.

Provides helper functions to generate realistic KYC, account, and transaction
details that match the banking schema defined in db/BANK_SCHEMA.md.
"""

import random
import string
from datetime import datetime, date, timedelta
from uuid import uuid4
from typing import Dict, Any, Optional, List, Literal


# ============================================================================
# NAME POOLS
# ============================================================================

FIRST_NAMES_MALE = [
    "James", "John", "Robert", "Michael", "David", "William", "Richard", "Joseph",
    "Thomas", "Charles", "Daniel", "Matthew", "Anthony", "Mark", "Donald", "Steven",
    "Andrew", "Paul", "Joshua", "Kenneth", "Kevin", "Brian", "George", "Timothy",
    "Carlos", "Ahmed", "Wei", "Hiroshi", "Raj", "Dmitri", "Hans", "Pierre",
    "Mohammed", "Yusuf", "Takeshi", "Liam", "Noah", "Ethan", "Lucas", "Oliver",
]

FIRST_NAMES_FEMALE = [
    "Mary", "Patricia", "Jennifer", "Linda", "Barbara", "Elizabeth", "Susan",
    "Jessica", "Sarah", "Karen", "Lisa", "Nancy", "Betty", "Margaret", "Sandra",
    "Ashley", "Emily", "Donna", "Michelle", "Dorothy", "Carol", "Amanda",
    "Fatima", "Mei", "Yuki", "Priya", "Olga", "Marie", "Ana", "Sofia",
    "Aisha", "Sakura", "Isabella", "Olivia", "Emma", "Ava", "Mia", "Charlotte",
]

LAST_NAMES = [
    "Smith", "Johnson", "Williams", "Brown", "Jones", "Garcia", "Miller", "Davis",
    "Rodriguez", "Martinez", "Hernandez", "Lopez", "Gonzalez", "Wilson", "Anderson",
    "Thomas", "Taylor", "Moore", "Jackson", "Martin", "Lee", "Perez", "Thompson",
    "White", "Harris", "Sanchez", "Clark", "Ramirez", "Lewis", "Robinson",
    "Walker", "Young", "Allen", "King", "Wright", "Scott", "Torres", "Nguyen",
    "Hill", "Flores", "Green", "Adams", "Nelson", "Baker", "Hall", "Rivera",
    "Campbell", "Mitchell", "Carter", "Roberts", "Chen", "Kim", "Patel", "Khan",
    "Muller", "Tanaka", "Ivanov", "Santos", "Silva", "Costa", "Dubois", "Weber",
]

COMPANY_PREFIXES = [
    "Global", "Pacific", "Atlantic", "Continental", "Premier", "Pinnacle", "Summit",
    "Apex", "Horizon", "Sterling", "Legacy", "Heritage", "Capital", "Allied",
    "United", "First", "National", "Royal", "Majestic", "Noble", "Prime",
    "Quantum", "Nexus", "Vertex", "Zenith", "Olympus", "Titan", "Atlas",
]

COMPANY_SUFFIXES = [
    "Holdings", "Enterprises", "Industries", "Group", "Corporation", "Partners",
    "Associates", "Ventures", "Solutions", "Investments", "Trading", "Services",
    "International", "Capital", "Management", "Consulting", "Resources", "Systems",
    "Technologies", "Logistics", "Development", "Properties", "Financial",
]

LEGAL_FORMS = {
    "US": ["LLC", "Inc.", "Corp.", "LP"],
    "UK": ["Ltd", "PLC", "LLP"],
    "DE": ["GmbH", "AG", "KG"],
    "FR": ["SARL", "SA", "SAS"],
    "CH": ["AG", "GmbH", "SA"],
    "SG": ["Pte Ltd", "Ltd"],
    "HK": ["Ltd", "Holdings Ltd"],
    "KY": ["Ltd", "Corp.", "LP"],
    "PA": ["S.A.", "Corp.", "Inc."],
    "VG": ["Ltd", "Corp."],
}

# ============================================================================
# OCCUPATION AND INDUSTRY DATA
# ============================================================================

OCCUPATIONS = [
    "Software Engineer", "Accountant", "Lawyer", "Doctor", "Teacher",
    "Business Owner", "Sales Manager", "Marketing Director", "Financial Analyst",
    "Real Estate Agent", "Consultant", "Engineer", "Architect", "Pharmacist",
    "Dentist", "Veterinarian", "Pilot", "Nurse", "Professor", "Researcher",
    "Chef", "Journalist", "Photographer", "Artist", "Musician",
    "Project Manager", "Data Scientist", "Product Manager", "HR Director",
    "Operations Manager", "Investment Banker", "Trader", "Retired", "Self-employed",
]

EMPLOYERS = [
    "TechCorp Inc.", "Global Finance LLC", "HealthFirst Medical", "EduGroup International",
    "BuildRight Construction", "DataFlow Systems", "CloudNet Solutions", "GreenEnergy Corp",
    "PharmaLife Sciences", "RetailMax Holdings", "AutoDrive Motors", "AeroSpace Dynamics",
    "FoodChain Industries", "MediaWave Group", "LegalShield Associates", "AgriWorld",
    "CyberSecure Technologies", "FinTech Innovations", "BioGenesis Labs", "MetalWorks Inc.",
    "Self-employed", "Freelance", "Government", "Non-profit Organization",
]

INDUSTRIES = [
    ("5411", "Legal Services"),
    ("5221", "Banking & Financial Services"),
    ("5242", "Insurance"),
    ("5239", "Investment & Securities"),
    ("3254", "Pharmaceuticals"),
    ("5112", "Software & Technology"),
    ("2362", "Construction"),
    ("4471", "Retail Trade"),
    ("4245", "Wholesale Trade"),
    ("4811", "Transportation"),
    ("7211", "Hospitality"),
    ("5311", "Real Estate"),
    ("2111", "Oil & Gas"),
    ("3361", "Manufacturing"),
    ("6111", "Education"),
    ("6211", "Healthcare"),
    ("5191", "Media & Publishing"),
    ("4931", "Warehousing & Logistics"),
    ("5614", "Staffing & Recruitment"),
    ("8111", "Repair & Maintenance"),
]

SOURCES_OF_WEALTH = [
    "Employment income", "Business profits", "Inheritance", "Investment returns",
    "Real estate income", "Professional fees", "Stock options", "Pension",
    "Savings", "Sale of business", "Royalties", "Rental income",
    "Trust distributions", "Gift", "Legal settlement", "Lottery winnings",
]

SOURCES_OF_FUNDS = [
    "Salary deposits", "Business revenue", "Investment income",
    "Rental income", "Sale of property", "Transfer from savings",
    "Pension payments", "Insurance proceeds", "Legal settlement",
    "Gift from family", "Loan proceeds", "Dividend income",
]

# ============================================================================
# BANK AND GEOGRAPHIC DATA
# ============================================================================

BANKS = {
    "US": [
        ("CHASUS33", "JPMorgan Chase", "New York"),
        ("BOFAUS3N", "Bank of America", "Charlotte"),
        ("WFBIUS6S", "Wells Fargo", "San Francisco"),
        ("CITIUS33", "Citibank", "New York"),
        ("USBKUS44", "U.S. Bank", "Minneapolis"),
    ],
    "UK": [
        ("BARCGB22", "Barclays", "London"),
        ("HBUKGB4B", "HSBC UK", "London"),
        ("LOYDGB2L", "Lloyds Bank", "London"),
        ("NWBKGB2L", "NatWest", "London"),
        ("STDRGB22", "Standard Chartered", "London"),
    ],
    "CH": [
        ("UBSWCHZH", "UBS", "Zurich"),
        ("CRESCHZZ", "Credit Suisse", "Zurich"),
        ("ZKBKCHZZ", "Zurcher Kantonalbank", "Zurich"),
    ],
    "SG": [
        ("DBSSSGSG", "DBS Bank", "Singapore"),
        ("OCBCSGSG", "OCBC Bank", "Singapore"),
        ("UABORUMU", "United Overseas Bank", "Singapore"),
    ],
    "HK": [
        ("HSBCHKHH", "HSBC Hong Kong", "Hong Kong"),
        ("BKCHHKHH", "Bank of China HK", "Hong Kong"),
        ("SCBLHKHH", "Standard Chartered HK", "Hong Kong"),
    ],
    "DE": [
        ("DEUTDEFF", "Deutsche Bank", "Frankfurt"),
        ("COBADEFF", "Commerzbank", "Frankfurt"),
    ],
    "KY": [
        ("CABORWKY", "Cayman National Bank", "George Town"),
        ("BFLIKY1A", "Butterfield Bank", "George Town"),
    ],
    "PA": [
        ("BGNPPAPA", "Banistmo", "Panama City"),
        ("BBLIPAPA", "Bladex", "Panama City"),
    ],
}

# Default fallback bank for countries not in the list
DEFAULT_BANKS = [
    ("BNPAFRPP", "BNP Paribas", "Paris"),
    ("DEUTDEFF", "Deutsche Bank", "Frankfurt"),
    ("HSBCSGSG", "HSBC", "Singapore"),
]

BRANCHES = [
    ("BR001", "Main Street Branch"),
    ("BR002", "Downtown Branch"),
    ("BR003", "Airport Branch"),
    ("BR004", "Financial District"),
    ("BR005", "Midtown Branch"),
    ("BR006", "Harbor Branch"),
    ("BR007", "University Branch"),
    ("BR008", "Tech Park Branch"),
    ("BR009", "Suburban Branch"),
    ("BR010", "Corporate Center"),
]

HIGH_RISK_COUNTRIES = [
    "AF", "IR", "KP", "SY", "YE", "IQ", "LY", "SO", "SS", "MM",
    "VE", "NI", "CU", "BY", "RU", "CD", "CF", "ER", "GN", "ML",
]

OFFSHORE_JURISDICTIONS = [
    "KY", "VG", "BM", "BZ", "PA", "LI", "MC", "JE", "GG", "IM",
    "GI", "SC", "MU", "BS", "AG", "TC", "AI", "MS", "VU", "WS",
]

COUNTRIES = [
    "US", "UK", "CA", "DE", "FR", "CH", "SG", "HK", "JP", "AU",
    "NL", "BE", "IT", "ES", "SE", "NO", "DK", "FI", "AT", "IE",
    "NZ", "KR", "TW", "IL", "AE", "SA", "QA", "BR", "MX", "IN",
]

# City data for addresses
CITIES = {
    "US": [("New York", "NY", "10001"), ("Los Angeles", "CA", "90001"), ("Chicago", "IL", "60601"),
           ("Houston", "TX", "77001"), ("Miami", "FL", "33101"), ("San Francisco", "CA", "94101"),
           ("Boston", "MA", "02101"), ("Seattle", "WA", "98101"), ("Denver", "CO", "80201")],
    "UK": [("London", "England", "EC1A 1BB"), ("Manchester", "England", "M1 1AA"),
           ("Birmingham", "England", "B1 1AA"), ("Edinburgh", "Scotland", "EH1 1AA")],
    "CH": [("Zurich", "ZH", "8001"), ("Geneva", "GE", "1200"), ("Basel", "BS", "4000")],
    "SG": [("Singapore", "", "018956"), ("Singapore", "", "049315"), ("Singapore", "", "238839")],
    "HK": [("Hong Kong", "Central", ""), ("Hong Kong", "Kowloon", ""), ("Hong Kong", "Wan Chai", "")],
    "DE": [("Frankfurt", "Hessen", "60311"), ("Berlin", "Berlin", "10115"), ("Munich", "Bavaria", "80331")],
}

STREET_NAMES = [
    "Main Street", "Oak Avenue", "Park Lane", "High Street", "Broadway",
    "Market Street", "King Street", "Victoria Road", "Church Street", "Mill Lane",
    "Cedar Drive", "Elm Street", "Maple Avenue", "River Road", "Lake Boulevard",
    "Orchard Road", "Commerce Drive", "Industrial Way", "Trade Center Blvd", "Financial Row",
]

# ============================================================================
# TRANSACTION REFERENCE DATA
# ============================================================================

TXN_TYPE_MAP = {
    "wire": "WIRE",
    "ach": "ACH",
    "cash": "CASH_DEPOSIT",
    "cash_deposit": "CASH_DEPOSIT",
    "cash_withdrawal": "CASH_WITHDRAWAL",
    "check": "CHECK",
    "crypto": "WIRE",  # Map crypto to wire for bank schema
    "trade": "WIRE",   # Map trade to wire
    "transfer": "INTERNAL_TRANSFER",
    "card": "CARD",
    "fx": "FX",
    "loan": "LOAN_PAYMENT",
    "payroll": "PAYROLL",
    "remittance": "REMITTANCE",
    "deposit": "CASH_DEPOSIT",
    "withdrawal": "CASH_WITHDRAWAL",
}

CHANNELS = {
    "wire": "SWIFT",
    "ach": "ONLINE",
    "cash": "BRANCH",
    "cash_deposit": "BRANCH",
    "cash_withdrawal": "ATM",
    "check": "BRANCH",
    "card": "ONLINE",
    "transfer": "ONLINE",
    "crypto": "API",
    "trade": "API",
    "fx": "ONLINE",
    "loan": "ONLINE",
    "payroll": "API",
    "remittance": "BRANCH",
}

PURPOSE_CODES = [
    "CASH", "CORT", "INTC", "SALA", "PENS", "TAXS", "TRAD", "INVS",
    "RENT", "LOAN", "FEES", "COMM", "INSU", "DIVD", "CHAR", "SUPP",
]

ACCOUNT_TYPE_MAP = {
    "checking": "CHECKING",
    "savings": "SAVINGS",
    "investment": "BROKERAGE",
    "crypto": "BROKERAGE",
    "trade_finance": "TREASURY",
    "money_market": "MONEY_MARKET",
    "business": "BUSINESS_CHECKING",
    "loan": "LOAN",
    "credit_card": "CREDIT_CARD",
}

PRODUCT_NAMES = {
    "CHECKING": ["Personal Checking", "Everyday Checking", "Advantage Checking"],
    "SAVINGS": ["Personal Savings", "High Yield Savings", "Growth Savings"],
    "MONEY_MARKET": ["Money Market Plus", "Premium Money Market"],
    "BUSINESS_CHECKING": ["Business Checking", "Commercial Checking", "Enterprise Account"],
    "BUSINESS_SAVINGS": ["Business Savings", "Commercial Savings"],
    "TREASURY": ["Treasury Management", "Trade Finance Account"],
    "BROKERAGE": ["Investment Account", "Securities Account", "Trading Account"],
    "LOAN": ["Personal Loan", "Business Loan", "Credit Line"],
    "CREDIT_CARD": ["Platinum Card", "Business Card", "Rewards Card"],
    "NOSTRO": ["Nostro Account"],
    "VOSTRO": ["Vostro Account"],
}

ACCOUNT_PURPOSES = {
    "CHECKING": ["Daily banking", "Personal expenses", "Bill payments"],
    "SAVINGS": ["Emergency fund", "Savings goal", "Future expenses"],
    "BUSINESS_CHECKING": ["Business operations", "Payroll", "Vendor payments"],
    "BROKERAGE": ["Investment portfolio", "Stock trading", "Retirement savings"],
    "TREASURY": ["Trade finance", "International payments", "Cash management"],
}


# ============================================================================
# GENERATOR FUNCTIONS
# ============================================================================

def generate_customer_id() -> str:
    """Generate a customer ID matching bank format: C + YYMMDD + 8 hex chars."""
    return f"C{datetime.now().strftime('%y%m%d')}{uuid4().hex[:8].upper()}"


def generate_account_number(country: str = "US") -> str:
    """Generate a realistic account number / IBAN-like string."""
    if country in ("US",):
        return f"{random.randint(1000, 9999)}{random.randint(10000000, 99999999)}"
    # IBAN-like for other countries
    check = random.randint(10, 99)
    bank_code = ''.join(random.choices(string.ascii_uppercase, k=4))
    acct = ''.join(random.choices(string.digits, k=14))
    return f"{country}{check}{bank_code}{acct}"


def generate_bic(country: str = "US") -> str:
    """Get a realistic BIC code for the country."""
    banks = BANKS.get(country, DEFAULT_BANKS)
    return random.choice(banks)[0]


def generate_bank_name(country: str = "US") -> str:
    """Get a realistic bank name for the country."""
    banks = BANKS.get(country, DEFAULT_BANKS)
    return random.choice(banks)[1]


def generate_txn_ref() -> str:
    """Generate a transaction reference number."""
    return f"REF{datetime.now().strftime('%Y%m%d')}{uuid4().hex[:10].upper()}"


def generate_end_to_end_id() -> str:
    """Generate an end-to-end identifier."""
    return f"E2E{uuid4().hex[:12].upper()}"


def random_person_details(name: str, country: str = "US") -> Dict[str, Any]:
    """Generate realistic person details for CustomerPerson table."""
    name_parts = name.split(" ", 2)
    first_name = name_parts[0] if len(name_parts) > 0 else random.choice(FIRST_NAMES_MALE + FIRST_NAMES_FEMALE)
    last_name = name_parts[-1] if len(name_parts) > 1 else random.choice(LAST_NAMES)
    middle_name = name_parts[1] if len(name_parts) > 2 else None

    # Determine gender from first name pools
    gender = "MALE" if first_name in FIRST_NAMES_MALE else "FEMALE" if first_name in FIRST_NAMES_FEMALE else "UNDISCLOSED"

    # Generate DOB (25-75 years old)
    age = random.randint(25, 75)
    dob = date.today() - timedelta(days=age * 365 + random.randint(0, 364))

    occupation = random.choice(OCCUPATIONS)
    employer = random.choice(EMPLOYERS)

    # Income based on occupation
    base_income = random.randint(35000, 250000)
    if occupation in ("Investment Banker", "Trader", "Lawyer", "Doctor"):
        base_income = random.randint(150000, 500000)
    elif occupation in ("Retired", "Self-employed"):
        base_income = random.randint(20000, 120000)

    return {
        "first_name": first_name,
        "middle_name": middle_name,
        "last_name": last_name,
        "full_name": name,
        "date_of_birth": dob.isoformat(),
        "nationality": country,
        "country_of_residence": country,
        "country_of_birth": country,
        "gender": gender,
        "occupation": occupation,
        "employer": employer,
        "industry": random.choice(INDUSTRIES)[1],
        "annual_income": round(base_income, -2),  # Round to nearest 100
        "source_of_wealth": random.choice(SOURCES_OF_WEALTH),
        "is_pep": False,
        "pep_type": "NONE",
        "pep_status": "NOT_PEP",
        "pep_position": None,
        "pep_country": None,
        "tax_residency": country,
        "fatca_status": "US_PERSON" if country == "US" else "NON_US",
        "crs_status": "REPORTABLE" if country != "US" else "NON_REPORTABLE",
    }


def random_company_details(
    name: str,
    country: str = "US",
    entity_subtype: Optional[str] = None,
    is_shell: bool = False,
) -> Dict[str, Any]:
    """Generate realistic company details for CustomerCompany table."""
    # Map entity subtype to company_type enum
    company_type_map = {
        "LLC": "PRIVATE",
        "trust": "PRIVATE",
        "partnership": "PRIVATE",
        "foundation": "NGO",
        "company": "PRIVATE",
    }

    if is_shell:
        company_type = "SHELL"
    else:
        company_type = company_type_map.get(entity_subtype, "PRIVATE")

    # Legal form based on country
    legal_forms = LEGAL_FORMS.get(country, ["Ltd", "LLC", "Corp."])
    legal_form = random.choice(legal_forms)

    # Industry
    industry_code, industry_desc = random.choice(INDUSTRIES)

    # Registration date (1-30 years ago)
    years_ago = random.randint(1, 30)
    reg_date = date.today() - timedelta(days=years_ago * 365 + random.randint(0, 364))

    # Revenue and employees (correlated)
    if is_shell:
        employee_count = random.randint(0, 3)
        annual_revenue = round(random.uniform(0, 50000), 2)
    else:
        employee_count = random.randint(5, 5000)
        annual_revenue = round(employee_count * random.uniform(50000, 200000), -3)

    return {
        "legal_name": name,
        "trading_name": name.split(" ")[0] if len(name.split()) > 2 else None,
        "company_type": company_type,
        "legal_form": legal_form,
        "registration_number": f"REG{uuid4().hex[:10].upper()}",
        "registration_country": country,
        "registration_date": reg_date.isoformat(),
        "tax_id": f"TAX{random.randint(100000000, 999999999)}",
        "lei": ''.join(random.choices(string.digits + string.ascii_uppercase, k=20)) if not is_shell else None,
        "industry_code": industry_code,
        "industry_description": industry_desc,
        "operational_countries": country,
        "employee_count": employee_count,
        "annual_revenue": annual_revenue,
        "website": f"www.{name.lower().replace(' ', '').replace(',', '')[:20]}.com" if not is_shell else None,
        "status": "ACTIVE",
        "is_regulated": random.random() < 0.2 and not is_shell,
        "regulator": None,
        "license_number": None,
        "is_listed": random.random() < 0.1 and not is_shell and company_type == "PUBLIC",
        "stock_exchange": None,
        "ticker_symbol": None,
    }


def random_address(country: str = "US", address_type: str = "RESIDENTIAL") -> Dict[str, Any]:
    """Generate a realistic address for CustomerAddress table."""
    cities = CITIES.get(country, [("Capital City", "Region", "10000")])
    city, state, postal = random.choice(cities)
    street_num = random.randint(1, 9999)
    street = random.choice(STREET_NAMES)

    return {
        "address_type": address_type,
        "line1": f"{street_num} {street}",
        "line2": random.choice([None, f"Suite {random.randint(100, 999)}", f"Floor {random.randint(1, 50)}"]),
        "city": city,
        "state_province": state,
        "postal_code": postal,
        "country": country,
        "is_primary": True,
        "verified_date": (date.today() - timedelta(days=random.randint(0, 365))).isoformat(),
    }


def random_identifier(entity_type: str = "individual", country: str = "US") -> List[Dict[str, Any]]:
    """Generate identifiers for CustomerIdentifier table."""
    identifiers = []

    if entity_type == "individual":
        # Primary ID
        id_type = "SSN" if country == "US" else "PASSPORT"
        identifiers.append({
            "id_type": id_type,
            "id_number": f"***-**-{random.randint(1000, 9999)}" if id_type == "SSN" else f"{country}{random.randint(10000000, 99999999)}",
            "issuing_country": country,
            "issue_date": (date.today() - timedelta(days=random.randint(365, 3650))).isoformat(),
            "expiry_date": (date.today() + timedelta(days=random.randint(365, 3650))).isoformat() if id_type == "PASSPORT" else None,
            "is_primary": True,
            "verified": True,
            "verification_date": (date.today() - timedelta(days=random.randint(0, 365))).isoformat(),
            "verification_method": "ELECTRONIC",
        })
    else:
        # Company registration
        identifiers.append({
            "id_type": "COMPANY_REG",
            "id_number": f"REG{random.randint(10000000, 99999999)}",
            "issuing_country": country,
            "issue_date": (date.today() - timedelta(days=random.randint(365, 10950))).isoformat(),
            "expiry_date": None,
            "is_primary": True,
            "verified": True,
            "verification_date": (date.today() - timedelta(days=random.randint(0, 365))).isoformat(),
            "verification_method": "MANUAL",
        })

    return identifiers


def random_counterparty_name() -> str:
    """Generate a random counterparty name."""
    if random.random() < 0.5:
        # Person
        first = random.choice(FIRST_NAMES_MALE + FIRST_NAMES_FEMALE)
        last = random.choice(LAST_NAMES)
        return f"{first} {last}"
    else:
        # Company
        return f"{random.choice(COMPANY_PREFIXES)} {random.choice(COMPANY_SUFFIXES)}"


def random_counterparty_country(source_country: str = "US") -> str:
    """Generate a counterparty country, biased toward same country."""
    if random.random() < 0.5:
        return source_country
    return random.choice(COUNTRIES)


def determine_segment(entity_type: str, is_shell: bool, annual_value: float) -> str:
    """Determine customer segment based on attributes."""
    if entity_type == "individual":
        if annual_value > 1000000:
            return "HNW"
        return "RETAIL"
    else:
        if is_shell:
            return "SMB"
        if annual_value > 10000000:
            return "CORPORATE"
        return "SMB"


def determine_risk_rating(
    is_shell: bool,
    is_nominee: bool,
    risk_indicators: List[str],
    country: str,
) -> str:
    """Determine risk rating based on entity attributes."""
    score = 0
    if is_shell:
        score += 3
    if is_nominee:
        score += 2
    if country in HIGH_RISK_COUNTRIES:
        score += 3
    if country in OFFSHORE_JURISDICTIONS:
        score += 2
    score += len(risk_indicators)

    if score >= 5:
        return "CRITICAL"
    elif score >= 3:
        return "HIGH"
    elif score >= 1:
        return "MEDIUM"
    return "LOW"
