"""
Base Agent Classes for the Adversarial AML System

Implements the Massively Decomposed Agentic Processes (MDAP) principles:
1. Minimal focused agents (MAD)
2. Voting for error correction
3. Red-flagging for unreliable responses
"""

from abc import ABC, abstractmethod
from typing import Dict, List, Any, Optional, Tuple
from dataclasses import dataclass, field
from collections import Counter
import json
import asyncio
import os
from datetime import datetime
from dotenv import load_dotenv

# Load .env file at module import time (safe to call multiple times)
load_dotenv()

from pydantic import BaseModel
from openai import OpenAI
from loguru import logger
import mlflow

from ...config.config import AgentConfig, TypologyConfig
from ....tracking import tracker


@dataclass
class AgentResponse:
    """Structured response from an agent"""
    success: bool
    data: Any
    agent_name: str
    execution_time_ms: float
    prompt_tokens: int = 0
    completion_tokens: int = 0
    total_tokens: int = 0
    red_flagged: bool = False
    red_flag_reason: Optional[str] = None
    raw_response: Optional[str] = None


@dataclass
class VotingResult:
    """Result of the voting process"""
    winner: Any
    vote_count: int
    total_votes: int
    confidence: float
    all_candidates: Dict[str, int] = field(default_factory=dict)


class RedFlagDetector:
    """
    Detects signs of unreliable LLM responses.
    
    Based on the paper's findings that:
    1. Overly long responses tend to have more errors
    2. Incorrectly formatted responses indicate confusion
    """
    
    def __init__(self, max_tokens: int = 2000):
        self.max_tokens = max_tokens
    
    def check(self, response: str, expected_format: str = "json") -> Tuple[bool, Optional[str]]:
        """
        Check if response should be red-flagged.
        
        Returns:
            (is_flagged, reason)
        """
        # Check 1: Response too long
        estimated_tokens = len(response.split()) * 1.3  # Rough estimate
        if estimated_tokens > self.max_tokens:
            return True, f"Response too long ({int(estimated_tokens)} estimated tokens)"
        
        # Check 2: Format validation
        if expected_format == "json":
            try:
                # Try to parse JSON
                json.loads(response)
            except json.JSONDecodeError as e:
                return True, f"Invalid JSON format: {str(e)[:100]}"
        
        # Check 3: Empty or minimal response
        if len(response.strip()) < 10:
            return True, "Response too short or empty"
        
        # Check 4: Signs of confusion
        confusion_markers = [
            "I'm not sure",
            "I cannot",
            "I don't understand",
            "unclear",
            "ambiguous",
            "error",
            "sorry",
        ]
        response_lower = response.lower()
        for marker in confusion_markers:
            if marker in response_lower:
                return True, f"Confusion marker detected: '{marker}'"
        
        return False, None


class BaseAgent(ABC):
    """Base agent implementing MDAP principles with Groq support"""
    
    def __init__(self, config: AgentConfig):
        self.config = config
        self.name = config.name
        self.model = config.model
        self.temperature = config.temperature
        self.max_tokens = config.max_tokens

        # Initialize LLM client - read API keys directly from environment
        # (.env already loaded at module import time)
        groq_key = os.getenv("GROQ_API_KEY")
        openai_key = os.getenv("OPENAI_API_KEY")

        if groq_key:
            # Use Groq (primary)
            self.client = OpenAI(
                api_key=groq_key,
                base_url="https://api.groq.com/openai/v1"
            )
            self.provider = "groq"
            logger.info(f"Initialized {self.name} with Groq ({self.model})")
        elif openai_key:
            # Fallback to OpenAI
            self.client = OpenAI(api_key=openai_key)
            self.provider = "openai"
            logger.info(f"Initialized {self.name} with OpenAI ({self.model})")
        else:
            # No API key found - fail fast
            raise ValueError(
                f"Agent {self.name} requires GROQ_API_KEY or OPENAI_API_KEY environment variable. "
                f"Please set one in your .env file."
            )
        
        # Statistics
        self.execution_count = 0
        self.red_flag_count = 0
        self.success_count = 0
        
        # Initialize red flag detector
        self.red_flag_detector = RedFlagDetector()
    
    @abstractmethod
    def get_system_prompt(self) -> str:
        """Return the focused system prompt for this agent"""
        pass
    
    @abstractmethod
    def get_output_schema(self) -> type:
        """Return the Pydantic model for expected output"""
        pass
    
    async def execute(self, input_data: Dict[str, Any]) -> AgentResponse:
        """
        Execute the agent's task with a single input.

        This is the minimal unit of work following MAD principles.
        """
        start_time = datetime.now()

        try:
            # Build prompt
            system_prompt = self.get_system_prompt()
            user_prompt = self._format_input(input_data)

            # Create a child span within the parent trace (if parent exists)
            # This will be a child of the generate_scenario span
            with mlflow.start_span(name=f"{self.name}") as span:
                span.set_attribute("agent.name", self.name)
                span.set_attribute("agent.provider", self.provider)
                span.set_attribute("agent.model", self.model)
                span.set_inputs({"task": input_data.get("task", ""), "input_size": len(str(input_data))})

                raw_response, usage = self._call_llm(user_prompt, system_prompt)

                # Strip chain-of-thought tags BEFORE red-flag check for proper JSON validation
                cleaned_response = self._strip_think_tags(raw_response)

                # Red-flag check (on cleaned response so JSON validation works)
                is_flagged, flag_reason = self.red_flag_detector.check(cleaned_response)
                if is_flagged:
                    self.red_flag_count += 1
                    span.set_attribute("agent.red_flagged", True)
                    span.set_attribute("agent.red_flag_reason", flag_reason)
                    span.set_attribute("agent.success", False)
                    logger.warning(f"{self.name} red-flagged: {flag_reason}. Raw response preview: {raw_response[:1000] if raw_response else '[EMPTY]'}")
                    return AgentResponse(
                        success=False,
                        data=None,
                        agent_name=self.name,
                        execution_time_ms=(datetime.now() - start_time).total_seconds() * 1000,
                        prompt_tokens=usage.get("prompt_tokens", 0),
                        completion_tokens=usage.get("completion_tokens", 0),
                        total_tokens=usage.get("total_tokens", 0),
                        red_flagged=True,
                        red_flag_reason=flag_reason,
                        raw_response=raw_response,
                    )

                # Parse response (use cleaned response)
                parsed_data = self._parse_response(cleaned_response)
                span.set_outputs({"success": True, "data_size": len(str(parsed_data))})
                span.set_attribute("agent.success", True)
                span.set_attribute("agent.prompt_tokens", usage.get("prompt_tokens", 0))
                span.set_attribute("agent.completion_tokens", usage.get("completion_tokens", 0))
                span.set_attribute("agent.total_tokens", usage.get("total_tokens", 0))
            
            self.execution_count += 1
            self.success_count += 1
            
            execution_time_ms = (datetime.now() - start_time).total_seconds() * 1000
            
            # Log to MLflow
            try:
                tracker.log_agent_execution(
                    agent_name=self.name,
                    input_data=input_data,
                    response_data=parsed_data,
                    execution_time_ms=execution_time_ms,
                    success=True,
                    red_flagged=False
                )
            except Exception as e:
                logger.warning(f"Failed to log to MLflow: {e}")
            
            return AgentResponse(
                success=True,
                data=parsed_data,
                agent_name=self.name,
                execution_time_ms=execution_time_ms,
                prompt_tokens=usage.get("prompt_tokens", 0),
                completion_tokens=usage.get("completion_tokens", 0),
                total_tokens=usage.get("total_tokens", 0),
                raw_response=raw_response,
            )
            
        except Exception as e:
            execution_time_ms = (datetime.now() - start_time).total_seconds() * 1000
            
            # Log to MLflow
            try:
                tracker.log_agent_execution(
                    agent_name=self.name,
                    input_data=input_data,
                    response_data=None,
                    execution_time_ms=execution_time_ms,
                    success=False,
                    red_flagged=True,
                    red_flag_reason=f"Execution error: {str(e)}"
                )
            except Exception as log_e:
                logger.warning(f"Failed to log to MLflow: {log_e}")
            
            return AgentResponse(
                success=False,
                data=None,
                agent_name=self.name,
                execution_time_ms=execution_time_ms,
                red_flagged=True,
                red_flag_reason=f"Execution error: {str(e)}",
            )
    
    def _call_llm(self, prompt: str, system_prompt: Optional[str] = None) -> tuple[str, dict]:
        """Call LLM API with prompt using structured output (returns content and usage dict)"""
        if not self.client:
            logger.warning("No LLM API key configured, returning placeholder")
            return "LLM analysis unavailable - API key not configured", {}

        messages = []
        if system_prompt:
            messages.append({"role": "system", "content": system_prompt})
        messages.append({"role": "user", "content": prompt})

        # Get output schema for structured output
        output_schema = self.get_output_schema()

        try:
            # Wrap the LLM call in a nested span for proper tracing
            with mlflow.start_span(name=f"{self.name}.llm_call") as llm_span:
                llm_span.set_attribute("llm.provider", self.provider)
                llm_span.set_attribute("llm.model", self.model)
                llm_span.set_attribute("llm.temperature", self.temperature)
                llm_span.set_attribute("llm.max_tokens", self.max_tokens)
                llm_span.set_inputs({"messages": messages})

                # Check if provider supports structured output
                # OpenAI: Uses beta.chat.completions.parse() with Pydantic schema
                # Groq: Uses response_format={"type": "json_object"} for JSON mode
                use_openai_structured = self.provider == "openai"
                llm_span.set_attribute("llm.structured_output", use_openai_structured)
                llm_span.set_attribute("llm.json_mode", True)  # Both use JSON

                if use_openai_structured:
                    # OpenAI structured output with Pydantic schema
                    response = self.client.beta.chat.completions.parse(
                        model=self.model,
                        messages=messages,
                        temperature=self.temperature,
                        max_tokens=self.max_tokens,
                        response_format=output_schema
                    )
                else:
                    # Groq JSON mode (per API docs: response_format={"type": "json_object"})
                    # Requires system/user prompt to mention JSON
                    response = self.client.chat.completions.create(
                        model=self.model,
                        messages=messages,
                        temperature=self.temperature,
                        max_tokens=self.max_tokens,
                        response_format={"type": "json_object"}
                    )

                content = response.choices[0].message.content
                usage = {
                    "prompt_tokens": response.usage.prompt_tokens if response.usage else 0,
                    "completion_tokens": response.usage.completion_tokens if response.usage else 0,
                    "total_tokens": response.usage.total_tokens if response.usage else 0
                }

                llm_span.set_outputs({"content": content})
                llm_span.set_attribute("llm.usage.prompt_tokens", usage["prompt_tokens"])
                llm_span.set_attribute("llm.usage.completion_tokens", usage["completion_tokens"])
                llm_span.set_attribute("llm.usage.total_tokens", usage["total_tokens"])

                return content, usage
        except Exception as e:
            logger.error(f"LLM call failed ({self.provider}): {e}")
            raise
    
    def _strip_think_tags(self, response: str) -> str:
        """Strip chain-of-thought thinking tags from response"""
        if not response:
            return response

        # Remove chain-of-thought thinking tags (Groq/Qwen3 format)
        if "<think>" in response:
            if "</think>" in response:
                # Extract content after </think> tag
                think_end = response.find("</think>") + len("</think>")
                return response[think_end:].strip()
            else:
                # Incomplete <think> tag - extract content between <think> and end
                think_start = response.find("<think>") + len("<think>")
                return response[think_start:].strip()

        return response

    def _format_input(self, input_data: Dict[str, Any]) -> str:
        """Format input data for the prompt"""
        return json.dumps(input_data, indent=2, default=str)
    
    def _parse_response(self, response: str) -> Any:
        """Parse the LLM response into structured data (assumes think tags already stripped)"""
        # Try to extract JSON from response
        try:
            # Handle markdown code blocks
            if "```json" in response:
                start = response.find("```json") + 7
                end = response.find("```", start)
                response = response[start:end].strip()
            elif "```" in response:
                start = response.find("```") + 3
                end = response.find("```", start)
                response = response[start:end].strip()

            return json.loads(response)
        except json.JSONDecodeError:
            # Return as string if not valid JSON
            return response.strip()
    
    def get_stats(self) -> Dict[str, Any]:
        """Get execution statistics"""
        return {
            "agent_name": self.name,
            "execution_count": self.execution_count,
            "red_flag_count": self.red_flag_count,
            "red_flag_rate": self.red_flag_count / max(1, self.execution_count + self.red_flag_count),
        }


class VotingAgent:
    """
    Implements first-to-ahead-by-k voting for error correction.
    
    Runs an agent multiple times and selects the response that
    achieves k more votes than any alternative.
    """
    
    def __init__(self, agent: BaseAgent, k: int = 2, max_samples: int = 10):
        self.agent = agent
        self.k = k
        self.max_samples = max_samples
    
    async def execute_with_voting(self, input_data: Dict[str, Any]) -> Tuple[AgentResponse, VotingResult]:
        """
        Execute the agent with voting to ensure correctness.
        
        Keeps sampling until one candidate is ahead by k votes,
        or max_samples is reached.
        """
        candidates: Dict[str, int] = {}  # response_hash -> vote_count
        responses: Dict[str, AgentResponse] = {}  # response_hash -> response
        
        samples_taken = 0
        
        while samples_taken < self.max_samples:
            # Get a sample
            response = await self.agent.execute(input_data)
            samples_taken += 1

            if not response.success:
                # Red-flagged responses don't count
                logger.debug(f"{self.agent.name} voting attempt {samples_taken} failed: {response.red_flag_reason}")
                continue
            
            # Hash the response for voting
            response_hash = self._hash_response(response.data)
            
            if response_hash not in candidates:
                candidates[response_hash] = 0
                responses[response_hash] = response
            
            candidates[response_hash] += 1
            
            # Check if we have a winner
            if candidates:
                sorted_candidates = sorted(candidates.values(), reverse=True)
                if len(sorted_candidates) == 1:
                    # Only one candidate, check if it has k votes
                    if sorted_candidates[0] >= self.k:
                        break
                else:
                    # Check if leader is ahead by k
                    if sorted_candidates[0] - sorted_candidates[1] >= self.k:
                        break
        
        # Determine winner
        if not candidates:
            return AgentResponse(
                success=False,
                data=None,
                agent_name=self.agent.name,
                execution_time_ms=0,
                red_flagged=True,
                red_flag_reason="No valid responses after voting",
            ), VotingResult(
                winner=None,
                vote_count=0,
                total_votes=samples_taken,
                confidence=0,
            )
        
        winner_hash = max(candidates, key=candidates.get)
        winner_response = responses[winner_hash]
        winner_votes = candidates[winner_hash]
        
        voting_result = VotingResult(
            winner=winner_response.data,
            vote_count=winner_votes,
            total_votes=sum(candidates.values()),
            confidence=winner_votes / sum(candidates.values()),
            all_candidates={h: v for h, v in candidates.items()},
        )
        
        return winner_response, voting_result
    
    def _hash_response(self, data: Any) -> str:
        """Create a hash of the response for voting comparison"""
        if isinstance(data, dict):
            # Sort keys for consistent hashing
            return json.dumps(data, sort_keys=True, default=str)
        return str(data)


class AgentPool:
    """
    Pool of agents for parallel execution.
    
    Manages concurrent agent calls while respecting rate limits.
    """
    
    def __init__(self, max_concurrent: int = 5):
        self.max_concurrent = max_concurrent
        self.semaphore = asyncio.Semaphore(max_concurrent)
        self.agents: Dict[str, BaseAgent] = {}
    
    def register(self, agent: BaseAgent):
        """Register an agent in the pool"""
        self.agents[agent.name] = agent
    
    async def execute(self, agent_name: str, input_data: Dict[str, Any]) -> AgentResponse:
        """Execute an agent with concurrency control"""
        if agent_name not in self.agents:
            raise ValueError(f"Unknown agent: {agent_name}")
        
        async with self.semaphore:
            return await self.agents[agent_name].execute(input_data)
    
    async def execute_parallel(
        self,
        tasks: List[Tuple[str, Dict[str, Any]]]
    ) -> List[AgentResponse]:
        """Execute multiple agent tasks in parallel"""
        coroutines = [
            self.execute(agent_name, input_data)
            for agent_name, input_data in tasks
        ]
        return await asyncio.gather(*coroutines)
    
    def get_all_stats(self) -> Dict[str, Dict[str, Any]]:
        """Get stats for all agents"""
        return {name: agent.get_stats() for name, agent in self.agents.items()}
