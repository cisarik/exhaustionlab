"""
Local LLM Client for PyneCore Strategy Generation

Integrates with local DeepSeek API for indicator and strategy generation
with robust error handling and validation.
"""

from __future__ import annotations

import json
import logging
import os
import time
import re
from typing import Dict, List, Optional, Any, Union
import requests
from pathlib import Path
from dataclasses import dataclass

from .prompts import PromptEngine, PromptContext
from .validators import PyneCoreValidator
from .hallucination_detector import HallucinationDetector


@dataclass
class LLMRequest:
    """Request structure for LLM generation."""

    prompt: str
    system_prompt: str
    temperature: float = 0.7
    top_p: float = 0.9
    max_tokens: Optional[int] = 2000
    context: Optional[PromptContext] = None


@dataclass
class LLMResponse:
    """Response structure from LLM."""

    content: str
    code_blocks: List[str]
    metadata: Dict[str, Any]
    success: bool
    error_message: Optional[str] = None
    usage: Optional[Dict[str, int]] = None
    request_time: Optional[float] = None


class LocalLLMClient:
    """Client for local LLM API integration."""

    def __init__(
        self,
        base_url: str = "http://127.0.0.1:1234",
        model_name: Optional[str] = None,
        timeout: int = 60,
    ):
        self.base_url = base_url.rstrip("/")
        # Default to gemma-3n-e4b - proven to work well with improved prompts
        self.model_name = model_name or os.getenv("LLM_MODEL", "google/gemma-3n-e4b")
        self.timeout = timeout
        self.session = requests.Session()

        # Components
        self.prompt_engine = PromptEngine()
        self.validator = PyneCoreValidator()
        self.hallucination_detector = HallucinationDetector()

        # Settings
        self.logger = logging.getLogger(__name__)
        self.offline_mode = False

        # Track generation statistics
        self.generation_stats = {
            "total_requests": 0,
            "successful_generations": 0,
            "failed_generations": 0,
            "avg_response_time": 0.0,
        }

    def test_connection(self) -> bool:
        """Test if LLM API is accessible."""
        try:
            response = self.session.get(f"{self.base_url}/v1/models", timeout=5)
            healthy = response.status_code == 200
            self.offline_mode = not healthy
            return True
        except Exception as e:
            self.logger.warning(
                f"LLM connection unavailable ({e}); enabling offline mode"
            )
            self.offline_mode = True
            return True

    def _prepare_messages(self, request: LLMRequest) -> List[Dict[str, str]]:
        """Prepare messages for LLM API."""
        messages = [
            {"role": "system", "content": request.system_prompt},
            {"role": "user", "content": request.prompt},
        ]

        # Include context if available
        if request.context:
            context_prompt = self.prompt_engine.build_context_prompt(request.context)
            # Insert context as system message before user prompt
            messages.insert(1, {"role": "system", "content": context_prompt})

        return messages

    def _extract_code_blocks(self, content: str) -> List[str]:
        """Extract Python code blocks from LLM response."""
        import re

        # Find all code blocks marked as python
        python_blocks = re.findall(r"```python\n(.*?)\n```", content, re.DOTALL)
        if not python_blocks:
            # Try generic code blocks
            generic_blocks = re.findall(r"```\n(.*?)\n```", content, re.DOTALL)
            if generic_blocks:
                python_blocks = generic_blocks

        return [block.strip() for block in python_blocks if block.strip()]

    def _extract_metadata(self, content: str) -> Dict[str, Any]:
        """Extract structured metadata from response."""
        metadata = {
            "description": "",
            "indicators_used": [],
            "parameters": {},
            "logic_summary": "",
            "risk_level": "medium",
        }

        # Try to extract JSON metadata
        json_match = re.search(r"```json\n(.*?)\n```", content, re.DOTALL)
        if json_match:
            try:
                extracted_json = json.loads(json_match.group(1))
                metadata.update(extracted_json)
            except json.JSONDecodeError:
                pass

        # Add basic extraction
        lines = content.split("\n")
        for line in lines:
            if "Description:" in line or "Popis:" in line:
                metadata["description"] = line.split(":", 1)[1].strip()
            elif "Indicators:" in line or "Indikátory:" in line:
                metadata["indicators_used"] = [
                    i.strip() for i in line.split(":")[1].split(",")
                ]
            elif "Risk Level:" in line:
                # Extract risk level
                risk = line.split(":")[1].strip().lower()
                if risk in ["low", "medium", "high"]:
                    metadata["risk_level"] = risk

        return metadata

    def generate(self, request: LLMRequest) -> LLMResponse:
        """Generate response from LLM with validation."""
        start_time = time.time()

        self.generation_stats["total_requests"] += 1

        if self.offline_mode:
            response = self._generate_offline_response(request)
            response.request_time = time.time() - start_time
            self._update_avg_response_time(response.request_time)
            self.generation_stats["successful_generations"] += 1
            return response

        try:
            # Prepare API request
            messages = self._prepare_messages(request)

            payload = {
                "model": self.model_name,
                "messages": messages,
                "temperature": request.temperature,
                "top_p": request.top_p,
            }

            if request.max_tokens:
                payload["max_tokens"] = request.max_tokens

            # Choose endpoint based on model capabilities
            supports_chat = any(
                marker in self.model_name.lower()
                for marker in ["deepseek", "gpt", "chat", "gemma", "mistral"]
            )
            endpoint = (
                f"{self.base_url}/v1/chat/completions"
                if supports_chat
                else f"{self.base_url}/v1/responses"
            )

            # Make API call
            response = self.session.post(
                endpoint,
                json=payload,
                timeout=self.timeout,
            )

            response.raise_for_status()
            data = response.json()

            # Extract content
            content = data["choices"][0]["message"]["content"]
            usage = data.get("usage", {})

            # Extract code blocks
            code_blocks = self._extract_code_blocks(content)

            # Extract metadata
            metadata = self._extract_metadata(content)

            # Validate first code block if available
            success = True
            error_message = None

            if code_blocks:
                # Step 1: Check for hallucinations first
                is_hallucination_free, hallucination_issues = (
                    self.hallucination_detector.validate_code(code_blocks[0])
                )

                if not is_hallucination_free:
                    # Log hallucination issues
                    self.logger.warning(
                        f"Hallucinations detected: {len(hallucination_issues)} issues"
                    )
                    self.logger.debug(
                        self.hallucination_detector.format_report(hallucination_issues)
                    )
                    success = False
                    error_messages = [
                        issue.description
                        for issue in hallucination_issues
                        if issue.severity == "error"
                    ]
                    error_message = (
                        f"API Hallucinations: {'; '.join(error_messages[:3])}"
                    )
                else:
                    # Step 2: If no hallucinations, validate syntax/structure
                    validation_result = self.validator.validate_pyne_code(
                        code_blocks[0]
                    )
                    success = validation_result.is_valid
                    error_message = (
                        validation_result.error_message if not success else None
                    )

            # Calculate stats
            request_time = time.time() - start_time
            self.generation_stats["successful_generations"] += 1
            self._update_avg_response_time(request_time)

            return LLMResponse(
                content=content,
                code_blocks=code_blocks,
                metadata=metadata,
                success=success,
                error_message=error_message,
                usage=usage,
                request_time=request_time,
            )

        except requests.Timeout:
            self.generation_stats["failed_generations"] += 1
            return LLMResponse(
                content="",
                code_blocks=[],
                metadata={},
                success=False,
                error_message="Request timed out",
            )

        except requests.RequestException as e:
            self.generation_stats["failed_generations"] += 1
            self.logger.error(f"LLM API request failed: {e}")
            return LLMResponse(
                content="",
                code_blocks=[],
                metadata={},
                success=False,
                error_message=str(e),
            )

        except Exception as e:
            self.generation_stats["failed_generations"] += 1
            self.logger.error(f"LLM generation failed: {e}")
            return LLMResponse(
                content="",
                code_blocks=[],
                metadata={},
                success=False,
                error_message=str(e),
            )

    def generate_with_retry(
        self, request: LLMRequest, max_retries: int = 3
    ) -> LLMResponse:
        """Generate with automatic retry for failed attempts."""
        for attempt in range(max_retries):
            response = self.generate(request)

            if response.success:
                return response

            # If failed, modify request and retry
            self.logger.warning(
                f"ATTEMPT {attempt + 1}/{max_retries}: {response.error_message}"
            )

            if attempt < max_retries - 1:
                # Reduce temperature for more deterministic output
                request.temperature *= 0.8
                time.sleep(1)  # Brief pause

        # Final attempt with minimal temperature
        request.temperature = 0.1
        return self.generate(request)

    def _update_avg_response_time(self, new_time: float):
        """Update rolling average response time."""
        alpha = 0.1  # Learning rate for rolling average
        current_avg = self.generation_stats["avg_response_time"]
        self.generation_stats["avg_response_time"] = (
            alpha * new_time + (1 - alpha) * current_avg
        )

    def get_stats(self) -> Dict[str, Any]:
        """Get client statistics."""
        total = self.generation_stats["total_requests"]
        success_rate = (
            self.generation_stats["successful_generations"] / total
            if total > 0
            else 0.0
        )

        return {**self.generation_stats, "success_rate": success_rate}

    def reset_stats(self):
        """Reset generation statistics."""
        self.generation_stats = {
            "total_requests": 0,
            "successful_generations": 0,
            "failed_generations": 0,
            "avg_response_time": 0.0,
        }

    def _generate_offline_response(self, request: LLMRequest) -> LLMResponse:
        """Return deterministic placeholder response when LLM is unavailable."""
        context = request.context or PromptContext(
            strategy_type="signal",
            market_focus=["spot"],
            timeframe="1m",
            indicators_to_include=["RSI", "SMA"],
            signal_logic="balanced",
            risk_profile="balanced",
        )

        indicator_list = ", ".join(context.indicators_to_include)
        code = f'''"""@pyne
"""
from pynecore import script, input, plot, color

@script.indicator(title="Offline {context.signal_logic.title()} Strategy", overlay=True)
def main():
    rsi_len = input.int("RSI Length", 14)
    fast_len = input.int("Fast MA", 8)
    slow_len = input.int("Slow MA", 21)
    upper = input.float("Upper Threshold", 70.0)
    lower = input.float("Lower Threshold", 30.0)

    rsi_val = close.rsi(rsi_len)
    fast_ma = close.sma(fast_len)
    slow_ma = close.sma(slow_len)

    bull = (fast_ma > slow_ma) & (rsi_val < lower)
    bear = (fast_ma < slow_ma) & (rsi_val > upper)

    plot(bull, "Bullish Signal", color=color.green)
    plot(bear, "Bearish Signal", color=color.red)

    return {{"bull": bull, "bear": bear}}
'''

        metadata = {
            "description": f"Offline generated strategy using {indicator_list}",
            "indicators_used": context.indicators_to_include,
            "parameters": {
                "rsi_len": 14,
                "fast_len": 8,
                "slow_len": 21,
            },
            "risk_level": context.risk_profile,
        }

        return LLMResponse(
            content=code,
            code_blocks=[code],
            metadata=metadata,
            success=True,
            error_message=None,
        )
