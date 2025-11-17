"""
LLM-Powered Strategy Generation System

Integrates local LLM with PyneCore validation for
automated strategy creation and mutation.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass
from enum import Enum
from typing import Dict, List, Optional

from ..backtest.strategy_genome import StrategyGenome
from .llm_client import LLMRequest, LocalLLMClient
from .prompts import PromptContext
from .validators import PyneCoreValidator, ValidationResult


class GeneratorMode(Enum):
    """Strategy generation modes."""

    CREATE = "create"  # Create new strategy from scratch
    MUTATE = "mutate"  # Mutate existing strategy
    IMPROVE = "improve"  # Improve existing strategy
    HYBRID = "hybrid"  # Combine multiple strategies


@dataclass
class GenerationRequest:
    """Request for strategy generation."""

    mode: GeneratorMode
    context: PromptContext
    base_strategy: Optional[str] = None
    mutation_type: Optional[str] = None
    max_retries: int = 3
    validate_runtime: bool = False


@dataclass
class GenerationResult:
    """Result of strategy generation."""

    success: bool
    generated_code: Optional[str]
    metadata: Optional[Dict]
    validation_result: Optional[ValidationResult]
    attempts_made: int
    generation_time: float
    error_message: Optional[str] = None
    improvement_suggestions: List[str] = None


class LLMStrategyGenerator:
    """Main strategy generation system using LLM."""

    def __init__(self, llm_client: LocalLLMClient):
        self.client = llm_client
        self.validator = PyneCoreValidator()

        # Statistics tracking
        self.gen_stats = {
            "total_generated": 0,
            "successful_generations": 0,
            "failed_generations": 0,
            "avg_attempts_per_success": 0.0,
        }

        self.logger = logging.getLogger(__name__)

    def generate_strategy(self, request: GenerationRequest) -> GenerationResult:
        """Generate strategy according to request specifications."""
        import time

        start_time = time.time()

        self.gen_stats["total_generated"] += 1

        # Build appropriate LLM request based on mode
        llm_request = self._build_llm_request(request)

        # Generate with retry logic
        best_response = None
        last_validation = None

        for attempt in range(request.max_retries):
            self.logger.info(f"Generation attempt {attempt + 1}/{request.max_retries}")

            # Generate response
            response = self.client.generate_with_retry(llm_request, max_retries=2)

            # Add code extraction and validation
            if response.success and response.code_blocks:
                generated_code = response.code_blocks[0]

                # Validate generated code
                validation = self.validator.validate_pyne_code(generated_code, check_runtime=request.validate_runtime)

                # If valid, we're done
                if validation.is_valid:
                    best_response = response
                    last_validation = validation
                    break
                else:
                    self.logger.warning(f"Generated code invalid on attempt {attempt + 1}: {validation.error_message}")
                    last_validation = validation

                    # Modify request for next attempt based on validation feedback
                    llm_request = self._modify_request_for_retry(llm_request, validation, request)
            else:
                self.logger.error(f"LLM generation failed: {response.error_message}")

        # Calculate generation time
        generation_time = time.time() - start_time

        # Determine result
        success = best_response is not None and validation is not None and validation.is_valid

        if success:
            self.gen_stats["successful_generations"] += 1
            improvements = self.validator.suggest_improvements(best_response.code_blocks[0])
        else:
            self.gen_stats["failed_generations"] += 1
            improvements = []

        # Update statistics
        self._update_success_rate()

        return GenerationResult(
            success=success,
            generated_code=best_response.code_blocks[0] if best_response else None,
            metadata=best_response.metadata if best_response else None,
            validation_result=last_validation,
            attempts_made=attempt + 1,
            generation_time=generation_time,
            error_message=None if success else "Failed to generate valid strategy",
            improvement_suggestions=improvements,
        )

    def generate_multiple_strategies(self, requests: List[GenerationRequest]) -> List[GenerationResult]:
        """Generate multiple strategies in batch."""
        results = []

        for i, request in enumerate(requests):
            self.logger.info(f"Generating strategy {i + 1}/{len(requests)}")
            result = self.generate_strategy(request)
            results.append(result)

        return results

    def mutate_strategy(self, base_code: str, mutation_type: str, context: PromptContext) -> GenerationResult:
        """Specialized mutation of existing strategy."""
        mutation_request = GenerationRequest(
            mode=GeneratorMode.MUTATE,
            context=context,
            base_strategy=base_code,
            mutation_type=mutation_type,
            max_retries=3,
        )

        return self.generate_strategy(mutation_request)

    def improve_strategy(self, base_code: str, focus_area: str, context: PromptContext) -> GenerationResult:
        """Improve existing strategy in specific area."""
        # Modify context for improvement
        context.examples = [base_code]
        context.constraints["focus_area"] = focus_area

        improvement_request = GenerationRequest(
            mode=GeneratorMode.IMPROVE,
            context=context,
            base_strategy=base_code,
            max_retries=3,
        )

        return self.generate_strategy(improvement_request)

    def create_indicator(self, indicators: List[str], context: PromptContext) -> GenerationRequest:
        """Create indicator-focused generation request."""
        context.strategy_type = "indicator"
        context.indicators_to_include = indicators

        return GenerationRequest(mode=GeneratorMode.CREATE, context=context, max_retries=3)

    def create_signal_strategy(self, signal_logic: str, risk_profile: str, context: PromptContext) -> GenerationRequest:
        """Create signal strategy generation request."""
        context.strategy_type = "signal"
        context.signal_logic = signal_logic
        context.risk_profile = risk_profile

        return GenerationRequest(mode=GeneratorMode.CREATE, context=context, max_retries=3)

    def _build_llm_request(self, request: GenerationRequest) -> LLMRequest:
        """Build LLM request from generation request."""
        if request.mode == GeneratorMode.CREATE:
            if request.context.strategy_type == "indicator":
                return self.client.prompt_engine.generate_indicator_prompt(request.context)
            else:
                return self.client.prompt_engine.generate_signal_strategy_prompt(request.context)

        elif request.mode == GeneratorMode.MUTATE:
            mutation_type = request.mutation_type or self._default_mutation_type(request.context)
            return self.client.prompt_engine.generate_mutation_prompt(request.base_strategy, mutation_type, request.context)

        elif request.mode == GeneratorMode.IMPROVE:
            # Build improvement prompt based on focus area
            mutation_type = request.mutation_type or self._improve_mutation_type(request.context)
            return self.client.prompt_engine.generate_mutation_prompt(request.base_strategy, mutation_type, request.context)

        else:
            # Default to strategy creation
            return self.client.prompt_engine.generate_signal_strategy_prompt(request.context)

    def _modify_request_for_retry(
        self,
        original_request: LLMRequest,
        validation: ValidationResult,
        generation_request: GenerationRequest,
    ) -> LLMRequest:
        """Modify LLM request based on validation feedback for retry."""
        # Extract key validation issues
        errors = [i for i in validation.issues if i.severity == "error"]
        suggestions = self.validator.generate_fix_suggestions(errors)

        # Build feedback to add to prompt
        feedback_text = "\n\n## GENERATION FEEDBACK:\nPrevious attempt had these issues:\n"
        for suggestion in suggestions[:3]:  # Limit feedback
            feedback_text += f"- {suggestion}\n"

        feedback_text += "\nPlease fix these issues and generate corrected code.\n"

        # Create new request with feedback
        modified_prompt = original_request.prompt + feedback_text
        modified_request = LLMRequest(
            prompt=modified_prompt,
            system_prompt=original_request.system_prompt,
            temperature=max(0.3, original_request.temperature * 0.8),  # Lower temperature for correction
            max_tokens=original_request.max_tokens,
            context=original_request.context,
        )

        return modified_request

    def _default_mutation_type(self, context: PromptContext) -> str:
        """Select appropriate mutation type based on context."""
        mutation_hierarchy = {
            "indicator": ["parameter", "logic", "indicator"],
            "signal": ["logic", "parameter", "indicator"],
            "strategy": ["indicator", "logic", "risk"],
        }

        type_options = mutation_hierarchy.get(context.strategy_type, ["parameter", "logic"])
        # TODO: Make this more intelligent based on previous mutations
        import random

        return random.choice(type_options)

    def _improve_mutation_type(self, context: PromptContext) -> str:
        """Select mutation type for improvement focus."""
        if context.risk_profile == "conservative":
            return "risk"
        elif context.signal_logic == "trend_following":
            return "logic"
        else:
            return "parameter"

    def _update_success_rate(self):
        """Update success rate statistics."""
        total = self.gen_stats["total_generated"]
        if total > 0:
            avg_attempts = (self.gen_stats["successful_generations"] * 2 + self.gen_stats["failed_generations"] * 3) / total  # Assume successful take 2 attempts avg  # Failed take 3 attempts
            self.gen_stats["avg_attempts_per_success"] = avg_attempts

    def get_generation_stats(self) -> Dict[str, any]:
        """Get generation statistics."""
        total = self.gen_stats["total_generated"]
        success_rate = (self.gen_stats["successful_generations"] / total) if total > 0 else 0.0

        return {
            **self.gen_stats,
            "success_rate": success_rate,
            "client_stats": self.client.get_stats(),
        }

    def reset_stats(self):
        """Reset all statistics."""
        self.gen_stats = {
            "total_generated": 0,
            "successful_generations": 0,
            "failed_generations": 0,
            "avg_attempts_per_success": 0.0,
        }
        self.client.reset_stats()

    def convert_to_strategy_genome(self, result: GenerationResult, name: str, description: str = "") -> Optional[StrategyGenome]:
        """Convert generation result to StrategyGenome if successful."""
        if not result.success or not result.generated_code:
            return None

        # Extract metadata from result
        metadata = result.metadata or {}

        # Create genome
        return StrategyGenome(
            name=name,
            description=description or metadata.get("description", "LLM-generated strategy"),
            pine_code="# Generated from PyneCore\n" + result.generated_code,
            pyne_code=result.generated_code,
            parameters=metadata.get("parameters", {}),
            fitness=0.0,  # Will be calculated during evaluation
        )

    @staticmethod
    def strategy_types() -> List[str]:
        """List available strategy types."""
        return ["indicator", "signal", "strategy", "mutation", "improvement"]

    @staticmethod
    def signal_types() -> List[str]:
        """List available signal logic types."""
        return ["trend_following", "mean_reversion", "breakout", "exhaustion"]

    @staticmethod
    def mutation_types() -> List[str]:
        """List available mutation types."""
        return ["parameter", "logic", "indicator", "timeframe", "risk"]
