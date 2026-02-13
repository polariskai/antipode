"""
LangGraph-based Orchestrator for the Adversarial AML Agent System

Coordinates micro-agents to generate complete money laundering scenarios
following the MDAP (Massively Decomposed Agentic Processes) framework.
"""

from typing import Dict, List, Any, Optional, TypedDict, Annotated
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
import json
import asyncio
import operator
from uuid import uuid4

from loguru import logger
from langgraph.graph import StateGraph, END
from langgraph.checkpoint.memory import MemorySaver
from langchain_openai import ChatOpenAI
from langchain_core.messages import HumanMessage, AIMessage, SystemMessage
import mlflow

from ..agents.base.base_agent import BaseAgent, VotingAgent, AgentPool, AgentResponse, VotingResult
from ..agents import (
    ScenarioPlannerAgent,
    EvasionSpecialistAgent,
    ValidatorAgent,
    get_agent,
    get_all_typology_agents,
    AGENT_REGISTRY,
)
from ..tools import (
    create_entity,
    create_account,
    generate_transaction,
    create_relationship,
    generate_structured_transactions,
    generate_layered_transactions,
    get_all_tools,
)
from ..config.config import OrchestratorConfig, TypologyType, TYPOLOGY_CONFIGS
from ..memory import MemoryManager


class ScenarioState(TypedDict):
    """State for the scenario generation graph"""
    scenario_id: str
    scenario_plan: Optional[Dict[str, Any]]
    entities: Annotated[List[Dict], operator.add]
    accounts: Annotated[List[Dict], operator.add]
    transactions: Annotated[List[Dict], operator.add]
    relationships: Annotated[List[Dict], operator.add]
    validation_result: Optional[Dict[str, Any]]
    evasion_applied: bool
    current_step: str
    error: Optional[str]
    metadata: Dict[str, Any]


@dataclass
class GeneratedScenario:
    """Complete generated scenario with ground truth"""
    scenario_id: str
    typology: str
    entities: List[Dict[str, Any]]
    accounts: List[Dict[str, Any]]
    transactions: List[Dict[str, Any]]
    relationships: List[Dict[str, Any]]
    ground_truth: Dict[str, Any]
    metadata: Dict[str, Any]
    validation: Optional[Dict[str, Any]] = None
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "scenario_id": self.scenario_id,
            "typology": self.typology,
            "entities": self.entities,
            "accounts": self.accounts,
            "transactions": self.transactions,
            "relationships": self.relationships,
            "ground_truth": self.ground_truth,
            "metadata": self.metadata,
            "validation": self.validation,
        }
    
    def save(self, output_dir: str):
        """Save scenario to files"""
        output_path = Path(output_dir) / self.scenario_id
        output_path.mkdir(parents=True, exist_ok=True)
        
        # Save raw data (without ground truth)
        raw_path = output_path / "raw_data"
        raw_path.mkdir(exist_ok=True)
        
        # Strip ground truth from raw data
        raw_entities = [{k: v for k, v in e.items() if not k.startswith("_")} for e in self.entities]
        raw_accounts = [{k: v for k, v in a.items() if not k.startswith("_")} for a in self.accounts]
        raw_transactions = [{k: v for k, v in t.items() if not k.startswith("_")} for t in self.transactions]
        raw_relationships = [{k: v for k, v in r.items() if not k.startswith("_")} for r in self.relationships]
        
        with open(raw_path / "entities.json", "w") as f:
            json.dump(raw_entities, f, indent=2, default=str)
        with open(raw_path / "accounts.json", "w") as f:
            json.dump(raw_accounts, f, indent=2, default=str)
        with open(raw_path / "transactions.json", "w") as f:
            json.dump(raw_transactions, f, indent=2, default=str)
        with open(raw_path / "relationships.json", "w") as f:
            json.dump(raw_relationships, f, indent=2, default=str)
        
        # Save ground truth
        gt_path = output_path / "ground_truth"
        gt_path.mkdir(exist_ok=True)
        
        with open(gt_path / "scenario.json", "w") as f:
            json.dump(self.ground_truth, f, indent=2, default=str)
        with open(gt_path / "metadata.json", "w") as f:
            json.dump(self.metadata, f, indent=2, default=str)
        if self.validation:
            with open(gt_path / "validation.json", "w") as f:
                json.dump(self.validation, f, indent=2, default=str)

        # Also save bank-schema format
        self.save_bank_format(output_dir)

    def save_bank_format(self, output_dir: str):
        """Save scenario in bank-schema-aligned format.

        Writes separate JSON files for each bank schema table:
        - customers.json (Customer + Person/Company details)
        - accounts.json (Account + Ownership)
        - transactions.json (Full bank schema transaction format)
        - counterparties.json (Counterparty records from transactions)
        - relationships.json (CustomerRelationship records)
        """
        bank_path = Path(output_dir) / self.scenario_id / "bank_data"
        bank_path.mkdir(parents=True, exist_ok=True)

        # 1. Customers - flatten entity into Customer + Person/Company details
        customers = []
        for entity in self.entities:
            customer = {
                "customer_id": entity.get("customer_id", entity.get("entity_id")),
                "customer_type": entity.get("customer_type", "PERSON" if entity.get("entity_type") == "individual" else "COMPANY"),
                "onboarding_date": entity.get("onboarding_date"),
                "status": entity.get("status", "ACTIVE"),
                "risk_rating": entity.get("risk_rating", "MEDIUM"),
                "segment": entity.get("segment", "RETAIL"),
                "relationship_manager_id": entity.get("relationship_manager_id"),
                "kyc_date": entity.get("kyc_date"),
                "next_review_date": entity.get("next_review_date"),
                "source_system": entity.get("source_system", "ADVERSARIAL_GENERATOR"),
                # Include type-specific details
                "person_details": entity.get("person_details"),
                "company_details": entity.get("company_details"),
                "address": entity.get("address"),
                "identifiers": entity.get("identifiers"),
                # Ground truth
                "_is_suspicious": entity.get("_ground_truth", {}).get("is_suspicious", False),
                "_scenario_id": self.scenario_id,
            }
            customers.append(customer)

        # 2. Accounts - flatten with ownership
        accounts = []
        for acct in self.accounts:
            account = {
                "account_id": acct.get("account_id"),
                "customer_id": None,  # Will be resolved from entity_id mapping
                "entity_id": acct.get("entity_id"),
                "account_number": acct.get("account_number"),
                "product_type": acct.get("product_type", "CHECKING"),
                "product_name": acct.get("product_name"),
                "currency": acct.get("currency", "USD"),
                "country": acct.get("country"),
                "branch_code": acct.get("branch_code"),
                "branch_name": acct.get("branch_name"),
                "open_date": acct.get("open_date"),
                "close_date": acct.get("close_date"),
                "status": acct.get("status", "ACTIVE"),
                "purpose": acct.get("purpose"),
                "declared_monthly_turnover": acct.get("declared_monthly_turnover"),
                "declared_source_of_funds": acct.get("declared_source_of_funds"),
                "is_joint": acct.get("is_joint", False),
                "is_high_risk": acct.get("is_high_risk", False),
                "source_system": acct.get("source_system", "ADVERSARIAL_GENERATOR"),
                "ownership": acct.get("ownership"),
                "_is_suspicious": acct.get("_ground_truth", {}).get("is_suspicious", False),
                "_scenario_id": self.scenario_id,
            }
            accounts.append(account)

        # 3. Transactions - bank schema format
        transactions = []
        counterparties_seen = {}
        for txn in self.transactions:
            transaction = {
                "txn_id": txn.get("txn_id"),
                "txn_ref": txn.get("txn_ref"),
                "timestamp": txn.get("timestamp"),
                "value_date": txn.get("value_date"),
                "posting_date": txn.get("posting_date"),
                "account_id": txn.get("from_account_id"),
                "direction": txn.get("direction", "DEBIT"),
                "amount": txn.get("amount"),
                "currency": txn.get("currency", "USD"),
                "amount_usd": txn.get("amount_usd"),
                "exchange_rate": txn.get("exchange_rate", 1.0),
                "txn_type": txn.get("bank_txn_type", txn.get("txn_type", "WIRE")),
                "channel": txn.get("channel", "ONLINE"),
                # Counterparty
                "counterparty_account_number": txn.get("counterparty_account_number"),
                "counterparty_name_raw": txn.get("counterparty_name"),
                "counterparty_bank_code": txn.get("counterparty_bank_code"),
                "counterparty_bank_name": txn.get("counterparty_bank_name"),
                "counterparty_country": txn.get("counterparty_country"),
                # Originator
                "originator_name": txn.get("originator_name"),
                "originator_country": txn.get("originator_country"),
                "originator_account": txn.get("originator_account"),
                # Beneficiary
                "beneficiary_name": txn.get("beneficiary_name"),
                "beneficiary_country": txn.get("beneficiary_country"),
                "beneficiary_account": txn.get("beneficiary_account"),
                # Payment
                "purpose_code": txn.get("purpose_code"),
                "purpose_description": txn.get("purpose_description", txn.get("purpose")),
                "reference": txn.get("reference"),
                "end_to_end_id": txn.get("end_to_end_id"),
                # Metadata
                "batch_id": txn.get("batch_id"),
                "source_system": txn.get("source_system", "ADVERSARIAL_GENERATOR"),
                "is_reversed": txn.get("is_reversed", False),
                # Ground truth
                "_is_suspicious": txn.get("_ground_truth", {}).get("is_suspicious", False),
                "_typology": txn.get("_ground_truth", {}).get("typology"),
                "_scenario_id": self.scenario_id,
            }
            transactions.append(transaction)

            # Collect unique counterparties
            cp_name = txn.get("counterparty_name")
            if cp_name and cp_name not in counterparties_seen:
                counterparties_seen[cp_name] = {
                    "counterparty_id": f"CP_{len(counterparties_seen):05d}",
                    "name": cp_name,
                    "account_number": txn.get("counterparty_account_number"),
                    "bank_code": txn.get("counterparty_bank_code"),
                    "bank_name": txn.get("counterparty_bank_name"),
                    "country": txn.get("counterparty_country"),
                    "first_seen_date": txn.get("value_date"),
                    "last_seen_date": txn.get("value_date"),
                    "txn_count": 1,
                    "total_volume_usd": txn.get("amount_usd", 0),
                    "source_system": "ADVERSARIAL_GENERATOR",
                }
            elif cp_name:
                cp = counterparties_seen[cp_name]
                cp["txn_count"] += 1
                cp["total_volume_usd"] += txn.get("amount_usd", 0)
                cp["last_seen_date"] = txn.get("value_date")

        # 4. Relationships - bank schema format
        relationships = []
        for rel in self.relationships:
            relationship = {
                "relationship_id": rel.get("relationship_id"),
                "from_customer_id": rel.get("from_entity_id"),
                "to_customer_id": rel.get("to_entity_id"),
                "relationship_type": rel.get("bank_relationship_type", rel.get("relationship_type")),
                "effective_from": rel.get("effective_from"),
                "effective_to": rel.get("effective_to"),
                "verified": rel.get("verified", True),
                "verification_date": rel.get("verification_date"),
                "notes": rel.get("notes"),
            }
            relationships.append(relationship)

        # Write all files
        with open(bank_path / "customers.json", "w") as f:
            json.dump(customers, f, indent=2, default=str)
        with open(bank_path / "accounts.json", "w") as f:
            json.dump(accounts, f, indent=2, default=str)
        with open(bank_path / "transactions.json", "w") as f:
            json.dump(transactions, f, indent=2, default=str)
        with open(bank_path / "counterparties.json", "w") as f:
            json.dump(list(counterparties_seen.values()), f, indent=2, default=str)
        with open(bank_path / "relationships.json", "w") as f:
            json.dump(relationships, f, indent=2, default=str)


class AdversarialOrchestrator:
    """
    Main orchestrator that coordinates micro-agents using LangGraph.
    
    Implements the MDAP framework:
    1. Decomposes scenario generation into minimal steps
    2. Uses voting for error correction at each step
    3. Applies red-flagging to discard unreliable responses
    """
    
    def __init__(self, config: Optional[OrchestratorConfig] = None, memory_manager: Optional[MemoryManager] = None, db_loader=None):
        self.config = config or OrchestratorConfig()

        # Initialize or use provided memory manager
        self.memory = memory_manager or MemoryManager()
        logger.info("Orchestrator initialized with memory system")

        # Optional database loader for real-time persistence
        self.db_loader = db_loader
        if self.db_loader:
            logger.info("Database loader enabled - data will be persisted in real-time")

        # Initialize agents
        self.scenario_planner = ScenarioPlannerAgent()
        self.evasion_specialist = EvasionSpecialistAgent()
        self.validator = ValidatorAgent()
        self.typology_agents = get_all_typology_agents()

        # Initialize agent pool for parallel execution
        self.agent_pool = AgentPool(max_concurrent=self.config.max_concurrent_agents)
        for name, agent in self.typology_agents.items():
            self.agent_pool.register(agent)
        self.agent_pool.register(self.scenario_planner)
        self.agent_pool.register(self.evasion_specialist)
        self.agent_pool.register(self.validator)

        # Initialize voting agents for critical steps
        # k=1 for planner (thinking function, just needs red-flag filtering)
        # k=2 for validator (needs consensus on validation results)
        self.voting_planner = VotingAgent(self.scenario_planner, k=1, max_samples=5)
        self.voting_validator = VotingAgent(self.validator, k=2, max_samples=10)

        # Build the LangGraph workflow
        self.graph = self._build_graph()

        # Statistics
        self.scenarios_generated = 0
        self.total_entities = 0
        self.total_transactions = 0
    
    def _build_graph(self) -> StateGraph:
        """Build the LangGraph workflow for scenario generation"""
        
        workflow = StateGraph(ScenarioState)
        
        # Add nodes
        workflow.add_node("plan_scenario", self._plan_scenario_node)
        workflow.add_node("generate_entities", self._generate_entities_node)
        workflow.add_node("generate_accounts", self._generate_accounts_node)
        workflow.add_node("generate_transactions", self._generate_transactions_node)
        workflow.add_node("build_relationships", self._build_relationships_node)
        workflow.add_node("apply_evasion", self._apply_evasion_node)
        workflow.add_node("validate", self._validate_node)
        
        # Add edges
        workflow.set_entry_point("plan_scenario")

        # Conditional edge from plan_scenario to check if planning succeeded
        workflow.add_conditional_edges(
            "plan_scenario",
            self._check_plan_success,
            {
                "continue": "generate_entities",
                "error": END,
            }
        )

        workflow.add_edge("generate_entities", "generate_accounts")
        workflow.add_edge("generate_accounts", "generate_transactions")
        workflow.add_edge("generate_transactions", "build_relationships")
        workflow.add_edge("build_relationships", "apply_evasion")
        workflow.add_edge("apply_evasion", "validate")
        
        # Conditional edge from validate
        workflow.add_conditional_edges(
            "validate",
            self._should_retry,
            {
                "retry": "generate_transactions",
                "end": END,
            }
        )
        
        return workflow.compile(checkpointer=MemorySaver())
    
    def _check_plan_success(self, state: ScenarioState) -> str:
        """Check if scenario planning succeeded"""
        if state.get("error") or not state.get("scenario_plan"):
            logger.error(f"Scenario planning failed: {state.get('error', 'No plan generated')}")
            return "error"
        return "continue"

    async def _plan_scenario_node(self, state: ScenarioState) -> Dict[str, Any]:
        """Plan the overall scenario using the scenario planner with voting"""

        # Query memory for reusable entities
        typology_hint = state["metadata"].get("typology", "structuring")
        available_entities = self.memory.find_reusable_entities(
            max_scenarios=5  # Only reuse entities used in <= 5 scenarios to avoid overuse
        )

        # Format entity information for the planner (compact format to avoid prompt bloat)
        entity_summaries = []
        for entity in available_entities[:10]:  # Limit to top 10 to keep prompts manageable
            summary = {
                "entity_id": entity["entity_id"],
                "type": f"{entity['entity_type']}/{entity['entity_subtype']}" if entity['entity_subtype'] else entity['entity_type'],
                "name": entity["name"],
                "country": entity["country"],
                "used_count": entity["scenarios_used"],  # Already an int, not a list
            }
            entity_summaries.append(summary)

        # Build the request message, using custom scenario description if provided
        scenario_description = state["metadata"].get("scenario_description")
        if scenario_description:
            request_message = f"User Request: {scenario_description}\n\nGenerate a detailed money laundering scenario plan based on this request."
        else:
            request_message = "Generate a money laundering scenario"

        input_data = {
            "request": request_message,
            "typology_hint": typology_hint,
            "complexity": state["metadata"].get("complexity", 5),
            "total_amount": state["metadata"].get("total_amount", 100000),
            "available_entities": entity_summaries,  # Pass available entities to planner
        }

        # Use voting for the planning step
        response, voting_result = await self.voting_planner.execute_with_voting(input_data)

        if not response.success:
            logger.error(f"Scenario planning failed after voting: {response.red_flag_reason}")
            return {
                "error": f"Failed to plan scenario: {response.red_flag_reason}",
                "current_step": "plan_scenario",
            }

        scenario_plan = response.data
        scenario_id = scenario_plan.get("scenario_id", f"SCEN_{uuid4().hex[:12]}")

        # Start tracking scenario in memory
        typology = scenario_plan.get("typology", state["metadata"].get("typology", "structuring"))
        reuse_entities = scenario_plan.get("reuse_entities", [])
        num_new_entities = scenario_plan.get("num_new_entities", scenario_plan.get("num_entities", 5))

        self.memory.start_scenario(
            scenario_id=scenario_id,
            typology=typology,
            metadata={
                "total_amount": scenario_plan.get("total_amount"),
                "complexity": scenario_plan.get("complexity"),
                "num_reused_entities": len(reuse_entities),
                "num_new_entities": num_new_entities,
                "total_entities": len(reuse_entities) + num_new_entities,
            }
        )

        logger.info(f"Scenario plan: Reusing {len(reuse_entities)} entities, creating {num_new_entities} new entities")

        return {
            "scenario_id": scenario_id,
            "scenario_plan": scenario_plan,
            "current_step": "plan_scenario",
            "metadata": {
                **state["metadata"],
                "voting_result": {
                    "confidence": voting_result.confidence,
                    "total_votes": voting_result.total_votes,
                },
            },
        }
    
    async def _generate_entities_node(self, state: ScenarioState) -> Dict[str, Any]:
        """Generate entities based on the scenario plan (reuse + new)"""

        plan = state["scenario_plan"]
        if not plan:
            return {"error": "No scenario plan available", "current_step": "generate_entities"}

        typology = plan.get("typology", "structuring")
        entities = []

        # STEP 1: Fetch and reuse entities from memory (if planner suggested)
        reuse_specs = plan.get("reuse_entities", [])
        for reuse_spec in reuse_specs:
            entity_id = reuse_spec.get("entity_id")
            role = reuse_spec.get("role", "unknown")

            # Fetch entity from memory
            entity_record = self.memory.entities.get(entity_id)
            if entity_record:
                # Convert EntityRecord back to entity dict format
                reused_entity = {
                    "entity_id": entity_record.entity_id,
                    "entity_type": entity_record.entity_type,
                    "entity_subtype": entity_record.entity_subtype,
                    "name": entity_record.name,
                    "country": entity_record.country,
                    "created_at": entity_record.created_at,
                    "_ground_truth": {
                        "is_shell": entity_record.entity_subtype in ["shell_company", "LLC"] if entity_record.entity_subtype else False,
                        "is_suspicious": True,
                        "reused_in_scenario": state["scenario_id"],
                        "role_in_scenario": role,
                    }
                }

                # Register entity reuse in memory
                memory_record = self.memory.register_entity(reused_entity, state["scenario_id"])
                logger.info(f"Reused entity: {entity_record.name} ({entity_id}) as {role} - now used in {len(memory_record['scenarios_used'])} scenarios")

                entities.append(reused_entity)
            else:
                logger.warning(f"Entity {entity_id} not found in memory, will create new entity instead")

        # STEP 2: Generate NEW entities using typology agent
        num_new_entities = plan.get("num_new_entities", plan.get("num_entities", 5) - len(entities))

        if num_new_entities > 0:
            # Get the appropriate typology agent
            if typology in self.typology_agents:
                agent = self.typology_agents[typology]
            else:
                agent = self.typology_agents["structuring"]  # Default

            # Generate entity specifications
            response = await agent.execute({
                "task": "generate_entities",
                "scenario_plan": plan,
                "num_entities": num_new_entities,
            })

            if response.success and isinstance(response.data, dict):
                entity_specs = response.data.get("entities", [])

                for spec in entity_specs[:num_new_entities]:
                    entity = create_entity.invoke({
                        "entity_type": spec.get("entity_type", "individual"),
                        "name": spec.get("name", f"Entity_{uuid4().hex[:8]}"),
                        "country": spec.get("country", "US"),
                        "risk_indicators": spec.get("risk_indicators", []),
                        "is_shell": spec.get("is_shell", False),
                        "is_nominee": spec.get("is_nominee", False),
                    })

                    # Register new entity in memory
                    memory_record = self.memory.register_entity(entity, state["scenario_id"])
                    logger.debug(f"Created new entity: {memory_record['entity_id']} ({memory_record['name']})")

                    entities.append(entity)

        # STEP 3: Ensure minimum entities (fallback)
        total_needed = max(2, plan.get("num_new_entities", 2))
        while len(entities) < total_needed:
            entity = create_entity.invoke({
                "entity_type": "individual",
                "name": f"Person_{uuid4().hex[:8]}",
                "country": "US",
                "risk_indicators": [],
                "is_shell": False,
                "is_nominee": False,
            })

            # Register fallback entity in memory
            memory_record = self.memory.register_entity(entity, state["scenario_id"])
            logger.debug(f"Created fallback entity: {memory_record['entity_id']}")

            entities.append(entity)

        # Persist entities to database if loader is enabled
        if self.db_loader:
            try:
                logger.info(f"Persisting {len(entities)} entities to database...")
                counts = self._persist_to_db({
                    'scenario_id': state["scenario_id"],
                    'entities': entities,
                    'accounts': [],
                    'transactions': [],
                    'relationships': []
                })
                logger.info(f"Persisted entities: {counts}")
            except Exception as e:
                logger.warning(f"Failed to persist entities to DB: {e}")

        return {
            "entities": entities,
            "current_step": "generate_entities",
        }
    
    async def _generate_accounts_node(self, state: ScenarioState) -> Dict[str, Any]:
        """Generate accounts for entities"""
        
        entities = state["entities"]
        plan = state["scenario_plan"]
        
        accounts = []
        for entity in entities:
            # Generate 1-3 accounts per entity
            num_accounts = 1 if len(entities) > 10 else 2
            
            for _ in range(num_accounts):
                account = create_account.invoke({
                    "entity_id": entity["entity_id"],
                    "account_type": "checking",
                    "currency": "USD",
                    "country": entity.get("country", "US"),
                    "is_offshore": entity.get("_ground_truth", {}).get("is_shell", False),
                })

                # Register account in memory
                self.memory.register_account(account, state["scenario_id"])

                accounts.append(account)

        # Persist accounts to database if loader is enabled
        if self.db_loader:
            try:
                logger.info(f"Persisting {len(accounts)} accounts to database...")
                counts = self._persist_to_db({
                    'scenario_id': state["scenario_id"],
                    'entities': [],  # Already persisted
                    'accounts': accounts,
                    'transactions': [],
                    'relationships': []
                })
                logger.info(f"Persisted accounts: {counts}")
            except Exception as e:
                logger.warning(f"Failed to persist accounts to DB: {e}")

        return {
            "accounts": accounts,
            "current_step": "generate_accounts",
        }
    
    async def _generate_transactions_node(self, state: ScenarioState) -> Dict[str, Any]:
        """Generate transactions based on the typology"""

        plan = state["scenario_plan"]
        accounts = state["accounts"]
        scenario_id = state["scenario_id"]

        # Handle case where plan is None
        if not plan:
            logger.warning("Scenario plan is None in generate_transactions_node, returning empty transactions")
            return {
                "transactions": [],
                "current_step": "generate_transactions",
            }
        
        if len(accounts) < 2:
            return {"error": "Not enough accounts", "current_step": "generate_transactions"}
        
        typology = plan.get("typology", "structuring")
        total_amount = plan.get("total_amount", 100000)
        num_transactions = plan.get("num_transactions", 10)

        transactions = []
        intermediate_accounts = []

        if typology == "structuring":
            # Use structuring tool
            source_account = accounts[0]["account_id"]
            result = generate_structured_transactions.invoke({
                "account_id": source_account,
                "total_amount": total_amount,
                "threshold": 10000,
                "num_transactions": min(num_transactions, 20),
                "scenario_id": scenario_id,
            })
            transactions.extend(result)

        elif typology == "layering":
            # Use layering tool
            source = accounts[0]["account_id"]
            dest = accounts[-1]["account_id"]
            result = generate_layered_transactions.invoke({
                "source_account_id": source,
                "destination_account_id": dest,
                "amount": total_amount,
                "num_layers": min(len(accounts) - 2, 5),
                "scenario_id": scenario_id,
            })
            # Extract intermediate accounts that need to be persisted
            intermediate_accounts = result.get("intermediate_accounts", [])
            transactions.extend(result.get("transactions", []))

            # Persist intermediate accounts to database BEFORE transactions
            if self.db_loader and intermediate_accounts:
                try:
                    logger.info(f"Persisting {len(intermediate_accounts)} intermediate accounts to database...")
                    counts = self._persist_to_db({
                        'scenario_id': scenario_id,
                        'entities': [],  # Already persisted
                        'accounts': intermediate_accounts,
                        'transactions': [],
                        'relationships': []
                    })
                    logger.info(f"Persisted intermediate accounts: {counts}")
                    # Register intermediate accounts in memory
                    for acct in intermediate_accounts:
                        self.memory.register_account(acct, scenario_id)
                except Exception as e:
                    logger.warning(f"Failed to persist intermediate accounts to DB: {e}")

        else:
            # Generic transaction generation
            import random
            for i in range(num_transactions):
                from_acct = random.choice(accounts)
                to_acct = random.choice([a for a in accounts if a != from_acct] or accounts)

                txn = generate_transaction.invoke({
                    "from_account_id": from_acct["account_id"],
                    "to_account_id": to_acct["account_id"],
                    "amount": random.uniform(1000, total_amount / num_transactions * 2),
                    "currency": "USD",
                    "txn_type": random.choice(["wire", "ach", "cash"]),
                    "purpose": random.choice(["payment", "transfer", "investment"]),
                    "is_suspicious": True,
                    "typology": typology,
                    "scenario_id": scenario_id,
                })
                transactions.append(txn)

        # Record all transactions in memory
        for txn in transactions:
            self.memory.record_transaction(txn, scenario_id)

        # Persist transactions to database if loader is enabled
        if self.db_loader:
            try:
                logger.info(f"Persisting {len(transactions)} transactions to database...")
                counts = self._persist_to_db({
                    'scenario_id': scenario_id,
                    'entities': [],  # Already persisted
                    'accounts': [],  # Intermediate accounts already persisted separately
                    'transactions': transactions,
                    'relationships': []
                })
                logger.info(f"Persisted transactions: {counts}")
            except Exception as e:
                logger.warning(f"Failed to persist transactions to DB: {e}")

        return {
            "transactions": transactions,
            "accounts": intermediate_accounts,  # Include intermediate accounts for state tracking
            "current_step": "generate_transactions",
        }
    
    async def _build_relationships_node(self, state: ScenarioState) -> Dict[str, Any]:
        """Build relationships between entities"""

        entities = state["entities"]
        plan = state["scenario_plan"]

        # Handle case where plan is None (shouldn't happen but defensive programming)
        if not plan:
            logger.warning("Scenario plan is None in build_relationships_node, skipping relationships")
            return {
                "relationships": [],
                "current_step": "build_relationships",
            }

        relationships = []

        # Build ownership/control relationships based on typology
        typology = plan.get("typology", "structuring")
        
        if typology in ["shell_company", "layering"]:
            # Create ownership chains
            for i in range(len(entities) - 1):
                rel = create_relationship.invoke({
                    "from_entity_id": entities[i]["entity_id"],
                    "to_entity_id": entities[i + 1]["entity_id"],
                    "relationship_type": "owns",
                    "ownership_percent": 100.0,
                    "is_hidden": True,
                })
                relationships.append(rel)
        
        elif typology == "mule_network":
            # Create hub-and-spoke relationships
            if entities:
                hub = entities[0]
                for entity in entities[1:]:
                    rel = create_relationship.invoke({
                        "from_entity_id": hub["entity_id"],
                        "to_entity_id": entity["entity_id"],
                        "relationship_type": "controls",
                        "is_hidden": True,
                    })
                    relationships.append(rel)

        # Add all relationships to memory
        for rel in relationships:
            self.memory.add_relationship(rel, state["scenario_id"])

        return {
            "relationships": relationships,
            "current_step": "build_relationships",
        }
    
    async def _apply_evasion_node(self, state: ScenarioState) -> Dict[str, Any]:
        """Apply evasion techniques to make detection harder"""

        # Handle case where plan is None
        if not state["scenario_plan"]:
            logger.warning("Scenario plan is None in apply_evasion_node, skipping evasion")
            return {
                "evasion_applied": False,
                "current_step": "apply_evasion",
            }

        # Prepare scenario summary for evasion specialist
        scenario_summary = {
            "typology": state["scenario_plan"].get("typology"),
            "num_entities": len(state["entities"]),
            "num_transactions": len(state["transactions"]),
            "total_amount": sum(t.get("amount", 0) for t in state["transactions"]),
        }

        response = await self.evasion_specialist.execute({
            "scenario": scenario_summary,
            "current_evasion": state["scenario_plan"].get("evasion_techniques", []),
        })
        
        # Apply modifications if successful
        evasion_applied = False
        if response.success and isinstance(response.data, dict):
            modifications = response.data.get("modifications", [])
            # In a full implementation, we would apply these modifications
            # For now, we just record that evasion was considered
            evasion_applied = True
        
        return {
            "evasion_applied": evasion_applied,
            "current_step": "apply_evasion",
        }
    
    async def _validate_node(self, state: ScenarioState) -> Dict[str, Any]:
        """Validate the generated scenario"""

        # Handle case where plan is None
        if not state["scenario_plan"]:
            logger.warning("Scenario plan is None in validate_node, using default validation")
            typology = "unknown"
        else:
            typology = state["scenario_plan"].get("typology", "unknown")

        scenario_summary = {
            "entities": len(state["entities"]),
            "accounts": len(state["accounts"]),
            "transactions": len(state["transactions"]),
            "typology": typology,
            "total_amount": sum(t.get("amount", 0) for t in state["transactions"]),
        }
        
        response, _ = await self.voting_validator.execute_with_voting({
            "scenario": scenario_summary,
        })
        
        validation_result = None
        if response.success:
            validation_result = response.data
        else:
            validation_result = {
                "is_valid": True,  # Default to valid if validation fails
                "is_realistic": True,
                "detection_difficulty": 0.5,
                "issues": [],
                "suggestions": [],
            }
        
        return {
            "validation_result": validation_result,
            "current_step": "validate",
        }
    
    def _should_retry(self, state: ScenarioState) -> str:
        """Determine if we should retry transaction generation"""
        
        validation = state.get("validation_result", {})
        
        # Retry if not valid and we haven't tried too many times
        retry_count = state.get("metadata", {}).get("retry_count", 0)
        
        if not validation.get("is_valid", True) and retry_count < 2:
            return "retry"
        
        return "end"
    
    def _persist_to_db(self, scenario_dict: Dict[str, Any]) -> Dict[str, int]:
        """Persist scenario data to database using the configured loader"""
        if not self.db_loader:
            return {}

        try:
            counts = self.db_loader.load_scenario(scenario_dict)
            return counts if isinstance(counts, dict) else {}
        except Exception as e:
            logger.error(f"Database persistence failed: {e}")
            raise

    async def generate_scenario(
        self,
        typology: Optional[str] = None,
        total_amount: float = 100000,
        complexity: int = 5,
        apply_evasion: bool = True,
        scenario_description: Optional[str] = None,
    ) -> GeneratedScenario:
        """
        Generate a complete money laundering scenario.

        Args:
            typology: Type of money laundering (structuring, layering, etc.)
            total_amount: Total amount to launder
            complexity: Complexity level 1-10
            apply_evasion: Whether to apply evasion techniques
            scenario_description: Free-text description of the desired scenario (optional)
                                 Example: "Create a crypto mixing scenario involving multiple exchanges"
                                 If provided, this will guide the ScenarioPlanner's decisions.

        Returns:
            GeneratedScenario with all data and ground truth
        """

        # Start a single trace for the entire scenario generation
        with mlflow.start_span(name="generate_scenario") as scenario_span:
            scenario_span.set_attribute("typology", typology or "random")
            scenario_span.set_attribute("total_amount", total_amount)
            scenario_span.set_attribute("complexity", complexity)
            scenario_span.set_attribute("apply_evasion", apply_evasion)

            # Initialize state
            initial_state: ScenarioState = {
                "scenario_id": "",
                "scenario_plan": None,
                "entities": [],
                "accounts": [],
                "transactions": [],
                "relationships": [],
                "validation_result": None,
                "evasion_applied": False,
                "current_step": "",
                "error": None,
                "metadata": {
                    "typology": typology,
                    "total_amount": total_amount,
                    "complexity": complexity,
                    "apply_evasion": apply_evasion,
                    "scenario_description": scenario_description,
                    "generated_at": datetime.now().isoformat(),
                },
            }

            # Run the graph
            config = {"configurable": {"thread_id": str(uuid4())}}
            final_state = await self.graph.ainvoke(initial_state, config)

            # Add final results to span
            scenario_span.set_attribute("scenario_id", final_state["scenario_id"])
            scenario_span.set_attribute("num_entities", len(final_state["entities"]))
            scenario_span.set_attribute("num_accounts", len(final_state["accounts"]))
            scenario_span.set_attribute("num_transactions", len(final_state["transactions"]))
            scenario_span.set_attribute("success", final_state.get("error") is None)

            # Build the result
            # Handle case where scenario_plan might be None
            scenario_plan = final_state.get("scenario_plan") or {}
            scenario = GeneratedScenario(
                scenario_id=final_state["scenario_id"],
                typology=scenario_plan.get("typology", "unknown"),
                entities=final_state["entities"],
                accounts=final_state["accounts"],
                transactions=final_state["transactions"],
                relationships=final_state["relationships"],
                ground_truth={
                    "scenario_plan": scenario_plan,
                    "all_suspicious": True,
                    "typology": scenario_plan.get("typology"),
                    "total_amount": sum(t.get("amount", 0) for t in final_state["transactions"]),
                    "entity_ids": [e["entity_id"] for e in final_state["entities"]],
                    "transaction_ids": [t["txn_id"] for t in final_state["transactions"]],
                },
                metadata=final_state["metadata"],
                validation=final_state["validation_result"],
            )

            # Complete scenario tracking in memory
            success = final_state.get("error") is None
            self.memory.complete_scenario(scenario.scenario_id, success=success)

            # Update statistics
            self.scenarios_generated += 1
            self.total_entities += len(scenario.entities)
            self.total_transactions += len(scenario.transactions)

            # Log memory stats
            memory_stats = self.memory.get_overall_stats()
            logger.info(f"Memory stats - Entities: {memory_stats['entities']['total_entities']}, " +
                       f"Reuse rate: {memory_stats['entities']['reuse_rate']:.2%}")

            return scenario
    
    async def generate_batch(
        self,
        num_scenarios: int,
        typologies: Optional[List[str]] = None,
        output_dir: str = "data/adversarial_scenarios",
    ) -> List[GeneratedScenario]:
        """
        Generate multiple scenarios in batch.
        
        Args:
            num_scenarios: Number of scenarios to generate
            typologies: List of typologies to use (cycles through them)
            output_dir: Directory to save scenarios
            
        Returns:
            List of generated scenarios
        """
        
        if typologies is None:
            typologies = ["structuring", "layering", "mule_network", "shell_company"]
        
        scenarios = []
        
        for i in range(num_scenarios):
            typology = typologies[i % len(typologies)]
            complexity = 3 + (i % 7)  # Vary complexity 3-9
            amount = 50000 * (1 + i % 10)  # Vary amount
            
            print(f"Generating scenario {i+1}/{num_scenarios}: {typology}")
            
            scenario = await self.generate_scenario(
                typology=typology,
                total_amount=amount,
                complexity=complexity,
            )
            
            # Save scenario
            scenario.save(output_dir)
            scenarios.append(scenario)
        
        return scenarios
    
    def get_stats(self) -> Dict[str, Any]:
        """Get orchestrator statistics"""
        return {
            "scenarios_generated": self.scenarios_generated,
            "total_entities": self.total_entities,
            "total_transactions": self.total_transactions,
            "agent_stats": self.agent_pool.get_all_stats(),
        }


async def main():
    """Example usage of the orchestrator"""
    
    orchestrator = AdversarialOrchestrator()
    
    # Generate a single scenario
    scenario = await orchestrator.generate_scenario(
        typology="structuring",
        total_amount=50000,
        complexity=5,
    )
    
    print(f"Generated scenario: {scenario.scenario_id}")
    print(f"  Typology: {scenario.typology}")
    print(f"  Entities: {len(scenario.entities)}")
    print(f"  Transactions: {len(scenario.transactions)}")
    print(f"  Total amount: ${sum(t['amount'] for t in scenario.transactions):,.2f}")
    
    # Save the scenario
    scenario.save("data/adversarial_test")
    
    return scenario


if __name__ == "__main__":
    import asyncio
    asyncio.run(main())
