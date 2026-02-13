"""
MLflow Tracking for Adversarial AML Agent System

Provides experiment tracking for scenario generation, agent performance,
and dataset quality metrics using Databricks managed MLflow.
"""

import mlflow
import mlflow.pytorch
import mlflow.langchain  # For LangGraph autologging
from typing import Dict, Any, Optional
from datetime import datetime
import json
import os
import warnings
from loguru import logger

# Simple config fallback for MLflow
class SimpleConfig:
    class mlflow:
        tracking_uri = "databricks"
        # Use absolute path for Databricks experiment, with env var fallback
        experiment_name = os.getenv("MLFLOW_EXPERIMENT_NAME", "/Users/mohammed.roondiwala@gmail.com/regulon_adv_agents")
        run_name_prefix = "aml-scenario"
        enable_system_metrics = True
        enable_autologging = True
        # Read from env vars if available
        databricks_host = os.getenv("DATABRICKS_HOST")
        databricks_token = os.getenv("DATABRICKS_TOKEN")

# Use simple config directly
config = SimpleConfig()


class MLflowTracker:
    """MLflow tracker for adversarial AML experiments"""
    
    def __init__(self):
        """Initialize MLflow tracking for Databricks"""
        self.tracking_uri = config.mlflow.tracking_uri
        self.experiment_name = config.mlflow.experiment_name
        self.run_name_prefix = config.mlflow.run_name_prefix
        self.enable_system_metrics = config.mlflow.enable_system_metrics
        self.enable_autologging = config.mlflow.enable_autologging
        
        # Configure Databricks MLflow
        if self.tracking_uri == "databricks":
            # Set Databricks authentication
            if hasattr(config.mlflow, 'databricks_host') and config.mlflow.databricks_host:
                os.environ['DATABRICKS_HOST'] = config.mlflow.databricks_host
                logger.info(f"Databricks MLflow configured for host: {config.mlflow.databricks_host}")
            else:
                logger.info("Using default Databricks configuration")
            
            if hasattr(config.mlflow, 'databricks_token') and config.mlflow.databricks_token:
                os.environ['DATABRICKS_TOKEN'] = config.mlflow.databricks_token
                logger.info("Databricks token configured")
            else:
                logger.warning("DATABRICKS_TOKEN not configured - tracking may be limited")
        
        # Set tracking URI
        mlflow.set_tracking_uri(self.tracking_uri)
        logger.info(f"MLflow tracking set to: {self.tracking_uri}")
        
        # Set experiment
        mlflow.set_experiment(self.experiment_name)
        logger.info(f"MLflow experiment set to: {self.experiment_name}")
        
        # Enable comprehensive autologging and tracing for MLflow 3.9+
        if self.enable_autologging:
            try:
                # Configure MLflow to suppress context propagation warnings in async environments
                # These warnings are non-blocking and don't affect trace capture
                warnings.filterwarnings(
                    "ignore",
                    message=".*Token var=.*was created in a different Context.*",
                    category=UserWarning,
                    module="mlflow"
                )

                # Enable LangChain autologging for LangGraph execution tracing
                # MLflow 3.9+ uses contextvars for async context propagation
                # Note: log_models parameter removed in MLflow 3.9+ (models not logged by default)
                mlflow.langchain.autolog(
                    disable=False,
                    exclusive=False,
                    disable_for_unsupported_versions=True,  # Gracefully handle version issues
                    silent=True  # Reduce verbose logging
                )
                logger.info("MLflow LangChain autologging enabled for LangGraph tracing")
                logger.info("Traces will capture complete graph execution flow, LLM calls, and tool invocations")
                logger.info("Context propagation warnings suppressed (async contexts handled via contextvars)")

            except Exception as e:
                logger.warning(f"Failed to enable MLflow autologging: {e}")
    
    def start_run(self, run_name: Optional[str] = None, tags: Optional[Dict[str, str]] = None) -> str:
        """Start a new MLflow run"""
        if not run_name:
            run_name = f"{self.run_name_prefix}_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
        
        run = mlflow.start_run(run_name=run_name, tags=tags)
        logger.info(f"Started MLflow run: {run.info.run_id}")
        return run.info.run_id
    
    def log_scenario_generation(self, 
                            scenario_id: str,
                            typology: str,
                            total_amount: float,
                            num_entities: int,
                            num_transactions: int,
                            generation_time_ms: float,
                            agent_stats: Dict[str, Any],
                            success: bool = True,
                            error_message: Optional[str] = None):
        """Log scenario generation metrics"""
        
        # Basic metrics
        mlflow.log_metrics({
            "scenario_total_amount": total_amount,
            "scenario_num_entities": num_entities,
            "scenario_num_transactions": num_transactions,
            "generation_time_ms": generation_time_ms,
            "generation_success": int(success),
        })
        
        # Agent execution statistics
        for agent_name, stats in agent_stats.items():
            prefix = f"agent_{agent_name}"
            mlflow.log_metrics({
                f"{prefix}_execution_count": stats.get("execution_count", 0),
                f"{prefix}_success_count": stats.get("success_count", 0),
                f"{prefix}_red_flag_count": stats.get("red_flag_count", 0),
                f"{prefix}_success_rate": stats.get("success_rate", 0.0),
            })
        
        # Parameters
        mlflow.log_params({
            "scenario_id": scenario_id,
            "typology": typology,
            "llm_provider": "groq",
            "llm_model": "qwen/qwen3-32b",
        })
        
        # Log error if any
        if error_message:
            mlflow.log_text(error_message, artifact_file="error.txt")
        
        logger.info(f"Logged scenario generation for {scenario_id}")
    
    def log_mixed_dataset(self,
                        dataset_id: str,
                        num_entities: int,
                        num_accounts: int,
                        num_transactions: int,
                        label_distribution: Dict[str, int],
                        generation_time_ms: float):
        """Log mixed dataset generation metrics"""
        
        # Calculate percentages
        total_txns = sum(label_distribution.values())
        label_percentages = {
            f"{label}_pct": (count / total_txns) * 100 
            for label, count in label_distribution.items()
        }
        
        # Metrics
        mlflow.log_metrics({
            "dataset_num_entities": num_entities,
            "dataset_num_accounts": num_accounts,
            "dataset_num_transactions": num_transactions,
            "dataset_generation_time_ms": generation_time_ms,
            **label_percentages,
            **{f"dataset_{label}_count": count for label, count in label_distribution.items()},
        })
        
        # Parameters
        mlflow.log_params({
            "dataset_id": dataset_id,
            "dataset_type": "mixed_aml",
            "llm_provider": "groq",
            "llm_model": "qwen/qwen3-32b",
        })
        
        # Log label distribution as JSON
        mlflow.log_dict(
            label_distribution, 
            artifact_file="label_distribution.json"
        )
        
        logger.info(f"Logged mixed dataset generation for {dataset_id}")
    
    def log_agent_execution(self,
                          agent_name: str,
                          input_data: Dict[str, Any],
                          response_data: Any,
                          execution_time_ms: float,
                          success: bool,
                          red_flagged: bool = False,
                          red_flag_reason: Optional[str] = None):
        """Log individual agent execution"""
        
        with mlflow.start_run(nested=True, run_name=f"agent_{agent_name}"):
            mlflow.log_metrics({
                "execution_time_ms": execution_time_ms,
                "success": int(success),
                "red_flagged": int(red_flagged),
            })
            
            mlflow.log_params({
                "agent_name": agent_name,
                "input_size": len(json.dumps(input_data, default=str)),
                "llm_provider": "groq",
                "llm_model": "qwen/qwen3-32b",
            })
            
            # Log input/output as artifacts (truncated if too large)
            input_json = json.dumps(input_data, default=str, indent=2)
            if len(input_json) < 10000:  # Only log if not too large
                mlflow.log_text(input_json, artifact_file="input.json")
            
            if response_data and success:
                response_json = json.dumps(response_data, default=str, indent=2)
                if len(response_json) < 10000:
                    mlflow.log_text(response_json, artifact_file="response.json")
            
            if red_flagged and red_flag_reason:
                mlflow.log_text(red_flag_reason, artifact_file="red_flag.txt")
    
    def log_dataset_artifact(self, dataset_path: str, artifact_name: str):
        """Log dataset as MLflow artifact"""
        mlflow.log_artifact(dataset_path, artifact_path=artifact_name)
        logger.info(f"Logged dataset artifact: {artifact_name}")
    
    def end_run(self):
        """End current MLflow run"""
        try:
            mlflow.end_run()
            logger.info("Ended MLflow run")
        except Exception as e:
            logger.warning(f"Failed to end MLflow run: {e}")
    
    def get_run_url(self, run_id: str) -> str:
        """Get URL for MLflow run"""
        if self.tracking_uri:
            return f"{self.tracking_uri}/#/experiments/{self.experiment_name}/runs/{run_id}"
        return f"Run ID: {run_id}"


# Global tracker instance (lazy initialization)
_tracker = None

def get_tracker():
    """Get or create the global tracker instance (lazy initialization)"""
    global _tracker
    if _tracker is None:
        _tracker = MLflowTracker()
    return _tracker

# For backward compatibility
@property
def tracker():
    """Property that returns the lazy-initialized tracker"""
    return get_tracker()

# Make tracker available at module level but only initialize when accessed
class TrackerProxy:
    """Proxy object that lazy-initializes the tracker on first use"""
    def __getattr__(self, name):
        return getattr(get_tracker(), name)

tracker = TrackerProxy()
