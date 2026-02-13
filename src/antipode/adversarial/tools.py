"""
Tools for the Adversarial AML Agent System

These are atomic operations that micro-agents can invoke to build
money laundering scenarios. Each tool is designed to be minimal and focused,
following the Maximal Agentic Decomposition (MAD) principle.

Tool outputs are enriched with bank-schema-aligned fields matching
the comprehensive banking data model defined in db/BANK_SCHEMA.md.
"""

from typing import Dict, List, Optional, Any, Literal
from dataclasses import dataclass, field, asdict
from datetime import datetime, date, timedelta
from uuid import uuid4
import random
import json
from langchain_core.tools import tool
from pydantic import BaseModel, Field

from .tools_data import (
    generate_customer_id,
    generate_account_number,
    generate_bic,
    generate_bank_name,
    generate_txn_ref,
    generate_end_to_end_id,
    random_person_details,
    random_company_details,
    random_address,
    random_identifier,
    random_counterparty_name,
    random_counterparty_country,
    determine_segment,
    determine_risk_rating,
    TXN_TYPE_MAP,
    CHANNELS,
    PURPOSE_CODES,
    ACCOUNT_TYPE_MAP,
    PRODUCT_NAMES,
    ACCOUNT_PURPOSES,
    SOURCES_OF_FUNDS,
    BRANCHES,
    BANKS,
    DEFAULT_BANKS,
)


class EntityInput(BaseModel):
    """Input for creating an entity"""
    entity_type: Literal["individual", "company", "LLC", "trust", "partnership", "foundation", "shell_company", "mule", "intermediary", "business"] = Field(
        description="Type of entity: individual (person), company (corporation), LLC, trust, partnership, foundation, shell_company, mule, intermediary, or business"
    )
    name: str = Field(description="Full name of the entity")
    country: str = Field(description="Country of residence/incorporation")
    risk_indicators: List[str] = Field(default_factory=list, description="Risk indicators")
    is_shell: bool = Field(default=False, description="Whether this is a shell company")
    is_nominee: bool = Field(default=False, description="Whether this is a nominee")


class AccountInput(BaseModel):
    """Input for creating an account"""
    entity_id: str = Field(description="ID of the entity owning the account")
    account_type: Literal["checking", "savings", "investment", "crypto", "trade_finance"] = Field(description="Type of account")
    currency: str = Field(default="USD", description="Account currency")
    country: str = Field(description="Country where account is held")
    bank_name: Optional[str] = Field(default=None, description="Name of the bank")
    is_offshore: bool = Field(default=False, description="Whether this is an offshore account")


class TransactionInput(BaseModel):
    """Input for generating a transaction"""
    from_account_id: str = Field(description="Source account ID")
    to_account_id: str = Field(description="Destination account ID")
    amount: float = Field(description="Transaction amount")
    currency: str = Field(default="USD", description="Transaction currency")
    txn_type: Literal["wire", "ach", "cash", "check", "crypto", "trade"] = Field(description="Transaction type")
    purpose: str = Field(description="Stated purpose of transaction")
    timestamp: Optional[str] = Field(default=None, description="Transaction timestamp (ISO format)")
    is_suspicious: bool = Field(default=True, description="Ground truth: is this suspicious")
    typology: Optional[str] = Field(default=None, description="Associated typology")
    scenario_id: Optional[str] = Field(default=None, description="Scenario this belongs to")


class RelationshipInput(BaseModel):
    """Input for creating a relationship between entities"""
    from_entity_id: str = Field(description="Source entity ID")
    to_entity_id: str = Field(description="Target entity ID")
    relationship_type: Literal["owns", "controls", "employs", "related_to", "transacts_with", "nominee_for"] = Field(description="Type of relationship")
    ownership_percent: Optional[float] = Field(default=None, description="Ownership percentage if applicable")
    is_hidden: bool = Field(default=False, description="Whether this relationship is hidden/obscured")


@tool(args_schema=EntityInput)
def create_entity(
    entity_type: str,
    name: str,
    country: str,
    risk_indicators: List[str] = None,
    is_shell: bool = False,
    is_nominee: bool = False,
) -> Dict[str, Any]:
    """
    Create a new entity (individual or company) for the money laundering scenario.

    This is an atomic operation that creates a single entity with the specified attributes.
    The entity can be used as a participant in transactions or as part of a corporate structure.
    Output is enriched with bank-schema-aligned fields for Customer, CustomerPerson/CustomerCompany,
    CustomerAddress, and CustomerIdentifier tables.
    """
    entity_id = f"ENT_{uuid4().hex[:12]}"
    customer_id = generate_customer_id()

    # Entities should be created in the past (1-5 years ago for realistic history)
    days_ago = random.randint(365, 1825)
    created_at = (datetime.now() - timedelta(days=days_ago)).isoformat()
    onboarding_date = (datetime.now() - timedelta(days=days_ago)).date().isoformat()

    # Normalize entity type
    normalized_type = "individual" if entity_type == "individual" else "company"
    customer_type = "PERSON" if normalized_type == "individual" else "COMPANY"

    # Determine risk rating and segment
    risk_rating = determine_risk_rating(is_shell, is_nominee, risk_indicators or [], country)
    segment = determine_segment(normalized_type, is_shell, 0)

    # KYC dates
    kyc_date = (datetime.now() - timedelta(days=random.randint(30, 365))).date().isoformat()
    next_review_date = (datetime.now() + timedelta(days=random.randint(90, 365))).date().isoformat()

    entity = {
        # Legacy fields (backward compatibility)
        "entity_id": entity_id,
        "entity_type": normalized_type,
        "entity_subtype": entity_type if entity_type != normalized_type else None,
        "name": name,
        "country": country,
        "created_at": created_at,

        # Bank schema: Customer table
        "customer_id": customer_id,
        "customer_type": customer_type,
        "onboarding_date": onboarding_date,
        "status": "ACTIVE",
        "risk_rating": risk_rating,
        "segment": segment,
        "relationship_manager_id": f"RM{random.randint(100, 999)}",
        "kyc_date": kyc_date,
        "next_review_date": next_review_date,
        "source_system": "ADVERSARIAL_GENERATOR",

        # Bank schema: Type-specific details
        "person_details": random_person_details(name, country) if normalized_type == "individual" else None,
        "company_details": random_company_details(
            name, country,
            entity_subtype=entity_type if entity_type != normalized_type else None,
            is_shell=is_shell,
        ) if normalized_type == "company" else None,

        # Bank schema: Address
        "address": random_address(
            country,
            address_type="RESIDENTIAL" if normalized_type == "individual" else "REGISTERED",
        ),

        # Bank schema: Identifiers
        "identifiers": random_identifier(normalized_type, country),

        # Ground truth (unchanged)
        "_ground_truth": {
            "risk_indicators": risk_indicators or [],
            "is_shell": is_shell,
            "is_nominee": is_nominee,
            "is_suspicious": is_shell or is_nominee or bool(risk_indicators),
        }
    }

    return entity


@tool(args_schema=AccountInput)
def create_account(
    entity_id: str,
    account_type: str,
    currency: str = "USD",
    country: str = "US",
    bank_name: Optional[str] = None,
    is_offshore: bool = False,
) -> Dict[str, Any]:
    """
    Create a new account for an entity.

    This is an atomic operation that creates a single account linked to an entity.
    Output is enriched with bank-schema-aligned fields for Account and AccountOwnership tables.
    """
    account_id = f"ACCT_{uuid4().hex[:12]}"

    if not bank_name:
        bank_name = generate_bank_name(country)

    # Map account type to bank schema product type
    product_type = ACCOUNT_TYPE_MAP.get(account_type, "CHECKING")
    product_names = PRODUCT_NAMES.get(product_type, ["Standard Account"])
    product_name = random.choice(product_names)

    # Branch
    branch_code, branch_name = random.choice(BRANCHES)

    # Account opened in the past (6 months to 3 years ago)
    days_ago = random.randint(180, 1095)
    opened_at = (datetime.now() - timedelta(days=days_ago)).isoformat()
    open_date = (datetime.now() - timedelta(days=days_ago)).date().isoformat()

    # Declared monthly turnover
    if product_type in ("BUSINESS_CHECKING", "TREASURY"):
        declared_monthly_turnover = round(random.uniform(10000, 500000), 2)
    elif product_type == "BROKERAGE":
        declared_monthly_turnover = round(random.uniform(5000, 200000), 2)
    else:
        declared_monthly_turnover = round(random.uniform(2000, 20000), 2)

    purposes = ACCOUNT_PURPOSES.get(product_type, ["General banking"])

    account = {
        # Legacy fields
        "account_id": account_id,
        "entity_id": entity_id,
        "account_type": account_type,
        "currency": currency,
        "country": country,
        "bank_name": bank_name,
        "opened_at": opened_at,

        # Bank schema: Account table
        "account_number": generate_account_number(country),
        "product_type": product_type,
        "product_name": product_name,
        "open_date": open_date,
        "close_date": None,
        "status": "ACTIVE",
        "branch_code": branch_code,
        "branch_name": branch_name,
        "purpose": random.choice(purposes),
        "declared_monthly_turnover": declared_monthly_turnover,
        "declared_source_of_funds": random.choice(SOURCES_OF_FUNDS),
        "is_joint": False,
        "is_high_risk": is_offshore,
        "kyc_date": (datetime.now() - timedelta(days=random.randint(30, 365))).date().isoformat(),
        "next_review_date": (datetime.now() + timedelta(days=random.randint(90, 365))).date().isoformat(),
        "source_system": "ADVERSARIAL_GENERATOR",

        # Bank schema: AccountOwnership
        "ownership": {
            "ownership_type": "PRIMARY",
            "ownership_pct": 100.0,
            "signing_authority": "SOLE",
            "daily_limit": round(random.uniform(10000, 100000), 2),
            "is_active": True,
        },

        # Ground truth
        "_ground_truth": {
            "is_offshore": is_offshore,
            "is_suspicious": is_offshore,
        }
    }

    return account


@tool(args_schema=TransactionInput)
def generate_transaction(
    from_account_id: str,
    to_account_id: str,
    amount: float,
    currency: str = "USD",
    txn_type: str = "wire",
    purpose: str = "payment",
    timestamp: Optional[str] = None,
    is_suspicious: bool = True,
    typology: Optional[str] = None,
    scenario_id: Optional[str] = None,
) -> Dict[str, Any]:
    """
    Generate a single transaction between two accounts.

    This is an atomic operation that creates one transaction with full audit trail.
    Output is enriched with bank-schema-aligned fields for the Transaction table,
    including counterparty details, originator/beneficiary info, and payment metadata.
    """
    txn_id = f"TXN_{uuid4().hex[:12]}"

    if timestamp is None:
        days_ago = random.randint(0, 365)
        hours_offset = random.randint(0, 23)
        timestamp = (datetime.now() - timedelta(days=days_ago, hours=hours_offset)).isoformat()

    # Parse timestamp for derived dates
    try:
        ts = datetime.fromisoformat(timestamp.replace('Z', '+00:00'))
    except (ValueError, AttributeError):
        ts = datetime.now()

    value_date = ts.date().isoformat()
    posting_date = (ts.date() + timedelta(days=random.choice([0, 0, 0, 1]))).isoformat()

    # Map transaction type to bank schema enum
    bank_txn_type = TXN_TYPE_MAP.get(txn_type, "WIRE")
    channel = CHANNELS.get(txn_type, "ONLINE")

    # Counterparty details
    cp_country = random_counterparty_country()
    cp_name = random_counterparty_name()
    cp_bank_code = generate_bic(cp_country)
    cp_bank_name = generate_bank_name(cp_country)
    cp_account = generate_account_number(cp_country)

    # Amount in USD
    if currency == "USD":
        amount_usd = round(amount, 2)
        exchange_rate = 1.0
    else:
        exchange_rate = round(random.uniform(0.5, 1.5), 6)
        amount_usd = round(amount * exchange_rate, 2)

    transaction = {
        # Legacy fields
        "txn_id": txn_id,
        "from_account_id": from_account_id,
        "to_account_id": to_account_id,
        "amount": round(amount, 2),
        "currency": currency,
        "txn_type": txn_type,
        "purpose": purpose,
        "timestamp": timestamp,

        # Bank schema: Transaction table core
        "txn_ref": generate_txn_ref(),
        "direction": "DEBIT",
        "bank_txn_type": bank_txn_type,
        "channel": channel,
        "value_date": value_date,
        "posting_date": posting_date,
        "amount_usd": amount_usd,
        "exchange_rate": exchange_rate,

        # Bank schema: Counterparty details
        "counterparty_name": cp_name,
        "counterparty_account_number": cp_account,
        "counterparty_bank_code": cp_bank_code,
        "counterparty_bank_name": cp_bank_name,
        "counterparty_country": cp_country,

        # Bank schema: Originator/Beneficiary
        "originator_name": None,
        "originator_country": None,
        "originator_account": from_account_id,
        "beneficiary_name": cp_name,
        "beneficiary_country": cp_country,
        "beneficiary_account": to_account_id,

        # Bank schema: Payment details
        "purpose_code": random.choice(PURPOSE_CODES),
        "purpose_description": purpose,
        "reference": f"INV-{datetime.now().strftime('%Y')}-{random.randint(1000, 9999)}",
        "end_to_end_id": generate_end_to_end_id(),

        # Bank schema: Metadata
        "batch_id": None,
        "source_system": "ADVERSARIAL_GENERATOR",
        "is_reversed": False,
        "reversal_of_txn_id": None,

        # Ground truth
        "_ground_truth": {
            "is_suspicious": is_suspicious,
            "typology": typology,
            "scenario_id": scenario_id,
        }
    }

    return transaction


@tool(args_schema=RelationshipInput)
def create_relationship(
    from_entity_id: str,
    to_entity_id: str,
    relationship_type: str,
    ownership_percent: Optional[float] = None,
    is_hidden: bool = False,
) -> Dict[str, Any]:
    """
    Create a relationship between two entities.

    This is an atomic operation that establishes a link between entities.
    Output is enriched with bank-schema-aligned fields for CustomerRelationship table.
    """
    rel_id = f"REL_{uuid4().hex[:12]}"

    rel_type_map = {
        "owns": "UBO_OF",
        "controls": "DIRECTOR_OF",
        "employs": "EMPLOYER",
        "related_to": "BUSINESS_PARTNER",
        "transacts_with": "BUSINESS_PARTNER",
        "nominee_for": "AUTHORIZED_FOR",
    }
    bank_rel_type = rel_type_map.get(relationship_type, "BUSINESS_PARTNER")

    relationship = {
        # Legacy fields
        "relationship_id": rel_id,
        "from_entity_id": from_entity_id,
        "to_entity_id": to_entity_id,
        "relationship_type": relationship_type,
        "ownership_percent": ownership_percent,
        "created_at": datetime.now().isoformat(),

        # Bank schema: CustomerRelationship table
        "bank_relationship_type": bank_rel_type,
        "effective_from": (datetime.now() - timedelta(days=random.randint(180, 1825))).date().isoformat(),
        "effective_to": None,
        "verified": not is_hidden,
        "verification_date": (datetime.now() - timedelta(days=random.randint(0, 365))).date().isoformat() if not is_hidden else None,
        "notes": None,

        # Ground truth
        "_ground_truth": {
            "is_hidden": is_hidden,
            "is_suspicious": is_hidden,
        }
    }

    return relationship


# ============================================================================
# SPECIALIZED TOOLS FOR SPECIFIC TYPOLOGIES
# ============================================================================

class StructuringInput(BaseModel):
    """Input for generating structured transactions"""
    account_id: str = Field(description="Account to structure from")
    total_amount: float = Field(description="Total amount to structure")
    threshold: float = Field(default=10000, description="Reporting threshold to avoid")
    num_transactions: int = Field(default=5, description="Number of transactions to split into")
    scenario_id: str = Field(description="Scenario ID for ground truth")


@tool(args_schema=StructuringInput)
def generate_structured_transactions(
    account_id: str,
    total_amount: float,
    threshold: float = 10000,
    num_transactions: int = 5,
    scenario_id: str = None,
) -> List[Dict[str, Any]]:
    """
    Generate a set of structured transactions designed to avoid reporting thresholds.
    Output transactions are enriched with bank-schema-aligned fields.
    """
    transactions = []
    remaining = total_amount

    for i in range(num_transactions):
        if i == num_transactions - 1:
            amount = remaining
        else:
            max_amount = min(remaining / (num_transactions - i), threshold * 0.95)
            min_amount = threshold * 0.7
            amount = random.uniform(min_amount, max_amount)

        amount = round(amount + random.uniform(-50, 50), 2)
        remaining -= amount

        days_offset = i * random.randint(1, 3)
        ts = datetime.now() - timedelta(days=days_offset)

        dest_account = f"DEST_{uuid4().hex[:8]}"
        txn_type_choice = random.choice(["cash", "ach", "check"])
        bank_txn_type = TXN_TYPE_MAP.get(txn_type_choice, "CASH_DEPOSIT")
        channel = CHANNELS.get(txn_type_choice, "BRANCH")
        cp_country = random_counterparty_country()

        txn = {
            "txn_id": f"TXN_{uuid4().hex[:12]}",
            "from_account_id": account_id,
            "to_account_id": dest_account,
            "amount": abs(amount),
            "currency": "USD",
            "txn_type": txn_type_choice,
            "purpose": random.choice(["deposit", "payment", "transfer"]),
            "timestamp": ts.isoformat(),

            "txn_ref": generate_txn_ref(),
            "direction": "DEBIT",
            "bank_txn_type": bank_txn_type,
            "channel": channel,
            "value_date": ts.date().isoformat(),
            "posting_date": ts.date().isoformat(),
            "amount_usd": abs(amount),
            "exchange_rate": 1.0,

            "counterparty_name": random_counterparty_name(),
            "counterparty_account_number": generate_account_number(cp_country),
            "counterparty_bank_code": generate_bic(cp_country),
            "counterparty_bank_name": generate_bank_name(cp_country),
            "counterparty_country": cp_country,

            "purpose_code": random.choice(PURPOSE_CODES),
            "purpose_description": random.choice(["deposit", "payment", "transfer"]),
            "reference": f"STR-{uuid4().hex[:8].upper()}",
            "end_to_end_id": generate_end_to_end_id(),

            "source_system": "ADVERSARIAL_GENERATOR",
            "is_reversed": False,

            "_ground_truth": {
                "is_suspicious": True,
                "typology": "structuring",
                "scenario_id": scenario_id,
                "structure_index": i,
                "total_structured_amount": total_amount,
            }
        }
        transactions.append(txn)

    return transactions


class LayeringInput(BaseModel):
    """Input for generating layered transactions"""
    source_account_id: str = Field(description="Initial source account")
    destination_account_id: str = Field(description="Final destination account")
    amount: float = Field(description="Amount to layer")
    num_layers: int = Field(default=3, description="Number of intermediate layers")
    scenario_id: str = Field(description="Scenario ID for ground truth")


@tool(args_schema=LayeringInput)
def generate_layered_transactions(
    source_account_id: str,
    destination_account_id: str,
    amount: float,
    num_layers: int = 3,
    scenario_id: str = None,
) -> Dict[str, Any]:
    """
    Generate a layered transaction chain with intermediate accounts.
    Output is enriched with bank-schema-aligned fields.
    """
    intermediate_accounts = []
    for i in range(num_layers):
        layer_country = random.choice(["US", "UK", "SG", "HK", "CH"])
        acct = {
            "account_id": f"LAYER_{uuid4().hex[:12]}",
            "entity_id": f"ENT_{uuid4().hex[:12]}",
            "account_type": "checking",
            "currency": "USD",
            "country": layer_country,

            "account_number": generate_account_number(layer_country),
            "product_type": "CHECKING",
            "product_name": "Standard Checking",
            "open_date": (datetime.now() - timedelta(days=random.randint(180, 1095))).date().isoformat(),
            "status": "ACTIVE",
            "branch_code": random.choice(BRANCHES)[0],
            "branch_name": random.choice(BRANCHES)[1],
            "bank_name": generate_bank_name(layer_country),
            "source_system": "ADVERSARIAL_GENERATOR",

            "_ground_truth": {
                "is_intermediary": True,
                "layer_index": i,
                "scenario_id": scenario_id,
            }
        }
        intermediate_accounts.append(acct)

    transactions = []
    accounts_chain = [source_account_id] + [a["account_id"] for a in intermediate_accounts] + [destination_account_id]

    current_amount = amount
    for i in range(len(accounts_chain) - 1):
        if i > 0:
            current_amount = current_amount * random.uniform(0.95, 0.99)

        days_offset = i * random.randint(1, 5)
        ts = datetime.now() - timedelta(days=days_offset)
        txn_type_choice = random.choice(["wire", "ach"])
        cp_country = random_counterparty_country()

        txn = {
            "txn_id": f"TXN_{uuid4().hex[:12]}",
            "from_account_id": accounts_chain[i],
            "to_account_id": accounts_chain[i + 1],
            "amount": round(current_amount, 2),
            "currency": "USD",
            "txn_type": txn_type_choice,
            "purpose": random.choice(["investment", "consulting fee", "payment", "loan"]),
            "timestamp": ts.isoformat(),

            "txn_ref": generate_txn_ref(),
            "direction": "DEBIT",
            "bank_txn_type": TXN_TYPE_MAP.get(txn_type_choice, "WIRE"),
            "channel": CHANNELS.get(txn_type_choice, "SWIFT"),
            "value_date": ts.date().isoformat(),
            "posting_date": (ts.date() + timedelta(days=random.choice([0, 1]))).isoformat(),
            "amount_usd": round(current_amount, 2),
            "exchange_rate": 1.0,

            "counterparty_name": random_counterparty_name(),
            "counterparty_account_number": generate_account_number(cp_country),
            "counterparty_bank_code": generate_bic(cp_country),
            "counterparty_bank_name": generate_bank_name(cp_country),
            "counterparty_country": cp_country,

            "purpose_code": random.choice(PURPOSE_CODES),
            "purpose_description": random.choice(["investment", "consulting fee", "payment", "loan"]),
            "reference": f"LAY-{uuid4().hex[:8].upper()}",
            "end_to_end_id": generate_end_to_end_id(),

            "source_system": "ADVERSARIAL_GENERATOR",
            "is_reversed": False,

            "_ground_truth": {
                "is_suspicious": True,
                "typology": "layering",
                "scenario_id": scenario_id,
                "layer_index": i,
                "total_layers": num_layers,
            }
        }
        transactions.append(txn)

    return {
        "intermediate_accounts": intermediate_accounts,
        "transactions": transactions,
        "scenario_id": scenario_id,
    }


# Tool registry for easy access
TOOL_REGISTRY = {
    "create_entity": create_entity,
    "create_account": create_account,
    "generate_transaction": generate_transaction,
    "create_relationship": create_relationship,
    "generate_structured_transactions": generate_structured_transactions,
    "generate_layered_transactions": generate_layered_transactions,
}


def get_all_tools():
    """Return all available tools for agent binding"""
    return list(TOOL_REGISTRY.values())
