"""
PyneCore Code Validation System

Validates LLM-generated PyneCore code for syntax,
API usage, and structural correctness.
"""

from __future__ import annotations

import ast
import subprocess
import tempfile
from dataclasses import dataclass
from pathlib import Path
from typing import List, Dict, Optional, Tuple
import re
import logging


@dataclass
class ValidationIssue:
    """Represents a validation issue in generated code."""

    severity: str  # 'error', 'warning', 'info'
    line_number: Optional[int]
    message: str
    suggestion: Optional[str] = None


@dataclass
class ValidationResult:
    """Result of PyneCore code validation."""

    is_valid: bool
    issues: List[ValidationIssue]
    error_message: Optional[str] = None
    syntax_valid: bool = True
    api_valid: bool = True
    structure_valid: bool = True


class PyneCoreValidator:
    """Comprehensive PyneCore code validator."""

    def __init__(self):
        self.logger = logging.getLogger(__name__)

        # Define valid PyneCore patterns and APIs
        self.valid_imports = [
            r"from pynecore import",
            r"import pynecore",
            r'"@pyne"',
        ]

        self.valid_decorators = [
            r"@script\.indicator\(",
            r"@script\.strategy\(",
        ]

        self.valid_functions = [
            r"plot\(",
            r"plotshape\(",
            r"plotarrow\(",
            r"input\.",
        ]

        self.valid_data_access = [
            r"close\[",
            r"open\[",
            r"high\[",
            r"low\[",
        ]

        # Common errors to check for
        self.pine_patterns_to_avoid = [
            r"ta\.",
            r"strategy\.",
            r"request\.",
            r"varip\b",
            r"ta\.sma",
            r"ta\.rsi",
            r"ta\.macd",
        ]

    def validate_pyne_code(
        self, code: str, check_runtime: bool = False
    ) -> ValidationResult:
        """Validate PyneCore code comprehensively."""
        issues = []

        # 1. Basic syntax validation
        syntax_issues = self._validate_syntax(code)
        issues.extend(syntax_issues)

        # 2. Structure validation
        structure_issues = self._validate_structure(code)
        issues.extend(structure_issues)

        # 3. API usage validation
        api_issues = self._validate_api_usage(code)
        issues.extend(api_issues)

        # 4. Pine Script pattern validation
        pine_issues = self._validate_pine_patterns(code)
        issues.extend(pine_issues)

        # 5. Optional runtime validation
        if check_runtime:
            runtime_issues = self._validate_runtime(code)
            issues.extend(runtime_issues)

        # Categorize validation result
        errors = [i for i in issues if i.severity == "error"]
        is_valid = len(errors) == 0

        # Collect overall validity flags
        syntax_valid = not any(
            i.severity == "error" and "syntax" in i.message.lower() for i in issues
        )
        api_valid = not any(
            i.severity == "error" and "api" in i.message.lower() for i in issues
        )
        structure_valid = not any(
            i.severity == "error" and "structure" in i.message.lower() for i in issues
        )

        # Get primary error message if invalid
        error_message = errors[0].message if errors and is_valid == False else None

        return ValidationResult(
            is_valid=is_valid,
            issues=issues,
            error_message=error_message,
            syntax_valid=syntax_valid,
            api_valid=api_valid,
            structure_valid=structure_valid,
        )

    def _validate_syntax(self, code: str) -> List[ValidationIssue]:
        """Validate Python syntax."""
        issues = []

        try:
            ast.parse(code)
        except SyntaxError as e:
            issues.append(
                ValidationIssue(
                    severity="error",
                    line_number=e.lineno,
                    message=f"Syntax error: {e.msg}",
                    suggestion="Check for missing parentheses, colons, or indentation",
                )
            )
        except Exception as e:
            issues.append(
                ValidationIssue(
                    severity="error",
                    line_number=1,
                    message=f"Parsing error: {str(e)}",
                    suggestion="Code may be malformed or incomplete",
                )
            )

        return issues

    def _validate_structure(self, code: str) -> List[ValidationIssue]:
        """Validate PyneCore structural requirements."""
        issues = []
        lines = code.split("\n")

        # Check for @pyne decorator
        has_pyne = any("@pyne" in line for line in lines)
        if not has_pyne:
            issues.append(
                ValidationIssue(
                    severity="error",
                    line_number=1,
                    message="Missing @pyne decorator",
                    suggestion='Add """@pyne""" at the top of the file',
                )
            )

        # Check for script decorator
        has_script = any("@script." in line for line in lines)
        if not has_script:
            issues.append(
                ValidationIssue(
                    severity="error",
                    line_number=None,
                    message="Missing @script.indicator() or @script.strategy() decorator",
                    suggestion='Add @script.indicator(title="Name") above main() function',
                )
            )

        # Check for main function
        has_main = any("def main()" in line for line in lines)
        if not has_main:
            issues.append(
                ValidationIssue(
                    severity="error",
                    line_number=None,
                    message="Missing main() function definition",
                    suggestion="Define main() function with your indicator logic",
                )
            )

        # Check for imports
        has_valid_import = any("from pynecore import" in line for line in lines)
        if not has_valid_import:
            issues.append(
                ValidationIssue(
                    severity="warning",
                    line_number=None,
                    message="No explicit pynecore import found",
                    suggestion="Add: from pynecore import Series, input, plot, color, script",
                )
            )

        return issues

    def _validate_api_usage(self, code: str) -> List[ValidationIssue]:
        """Validate correct PyneCore API usage."""
        issues = []
        lines = code.split("\n")

        for i, line in enumerate(lines, 1):
            # Check for Pine Script patterns that won't work
            for pattern in self.pine_patterns_to_avoid:
                if re.search(pattern, line):
                    issues.append(
                        ValidationIssue(
                            severity="error",
                            line_number=i,
                            message=f"Incompatible Pine Script pattern found: {pattern}",
                            suggestion="Use PyneCore API instead (e.g., close.sma() not ta.sma())",
                        )
                    )

            # Common mistakes
            if (
                "input." in line
                and "input.int" not in line
                and "input.float" not in line
                and "input.bool" not in line
            ):
                issues.append(
                    ValidationIssue(
                        severity="warning",
                        line_number=i,
                        message="Potential incorrect input usage",
                        suggestion="Use input.int(), input.float(), input.bool() with proper parameters",
                    )
                )

            # Check for proper plot usage
            if "plot(" in line and not any(
                word in line for word in ["title=", "color="]
            ):
                issues.append(
                    ValidationIssue(
                        severity="info",
                        line_number=i,
                        message="Plot lacks title or color specification",
                        suggestion="Add title and color parameters: plot(value, 'Name', color=color.blue)",
                    )
                )

        return issues

    def _validate_pine_patterns(self, code: str) -> List[ValidationIssue]:
        """Check for Pine Script patterns that need conversion."""
        issues = []

        # Look for common Pine Script patterns that need PyneCore conversion
        pine_to_pynecore_patterns = {
            r"ta\.sma\(": "Use Series.sma() method: close.sma(length)",
            r"ta\.rsi\(": "Use Series.rsi() method: close.rsi(length)",
            r"ta\.ema\(": "Use Series.ema() method: close.ema(length)",
            r"ta\.stoch\(": "Use Series.stoch() method: close.stoch(k, d)",
            r"strategy\.entry\(": "Use plot() boolean signals instead",
            r"strategy\.exit\(": "Use plot() boolean signals instead",
            r"request\.security\(": "Not available in PyneCore, focus on current timeframe",
            r"math\.\w+\(": "Use Python math library instead",
        }

        lines = code.split("\n")
        for i, line in enumerate(lines, 1):
            for pine_pattern, suggestion in pine_to_pynecore_patterns.items():
                if re.search(pine_pattern, line):
                    issues.append(
                        ValidationIssue(
                            severity="warning",
                            line_number=i,
                            message=f"Pine Script pattern detected: {pine_pattern}",
                            suggestion=suggestion,
                        )
                    )

        return issues

    def _validate_runtime(self, code: str) -> List[ValidationIssue]:
        """Attempt runtime validation of generated code."""
        issues = []

        try:
            # Create temporary test file
            with tempfile.NamedTemporaryFile(mode="w", suffix=".py", delete=False) as f:
                test_code = (
                    code
                    + '\n\n# Basic runtime test\nif __name__ == "__main__":\n    main()\n'
                )
                f.write(test_code)
                temp_path = Path(f.name)

            try:
                # Try to import and run basic syntax check
                result = subprocess.run(
                    ["python3", "-m", "py_compile", str(temp_path)],
                    capture_output=True,
                    text=True,
                    timeout=10,
                )

                if result.returncode != 0:
                    issues.append(
                        ValidationIssue(
                            severity="error",
                            line_number=None,
                            message=f"Runtime validation failed: {result.stderr}",
                            suggestion="Fix code structure and imports",
                        )
                    )

            except subprocess.TimeoutExpired:
                issues.append(
                    ValidationIssue(
                        severity="warning",
                        line_number=None,
                        message="Runtime validation timed out",
                        suggestion="Code may have infinite loops or complex calculations",
                    )
                )

            finally:
                temp_path.unlink(missing_ok=True)

        except Exception as e:
            issues.append(
                ValidationIssue(
                    severity="info",
                    line_number=None,
                    message=f"Could not perform runtime validation: {str(e)}",
                    suggestion="Manual testing recommended",
                )
            )

        return issues

    def generate_fix_suggestions(self, issues: List[ValidationIssue]) -> List[str]:
        """Generate actionable fix suggestions from validation issues."""
        suggestions = []

        errors = [i for i in issues if i.severity == "error"]
        warnings = [i for i in issues if i.severity == "warning"]

        if errors:
            suggestions.append(f"🔴 Fix {len(errors)} critical error(s):")
            for error in errors[:3]:  # Limit to top 3
                suggestions.append(
                    f"  Line {error.line_number or '?'}: {error.message}"
                )
                if error.suggestion:
                    suggestions.append(f"    💡 {error.suggestion}")

        if warnings:
            suggestions.append(f"🟡 Address {len(warnings)} warning(s):")
            for warning in warnings[:3]:  # Limit to top 3
                suggestions.append(
                    f"  Line {warning.line_number or '?'}: {warning.message}"
                )
                if warning.suggestion:
                    suggestions.append(f"    💡 {warning.suggestion}")

        return suggestions

    def quick_validate(self, code: str) -> Tuple[bool, str]:
        """Quick validation for immediate feedback."""
        result = self.validate_pyne_code(code)

        if result.is_valid:
            return True, "✅ Code looks valid"

        # Get first error for quick feedback
        error = next((i for i in result.issues if i.severity == "error"), None)
        if error:
            return False, f"❌ {error.message}"

        # If no errors, return first warning
        warning = next((i for i in result.issues if i.severity == "warning"), None)
        if warning:
            return False, f"⚠️ {warning.message}"

        return False, "❓ Code has validation issues"

    def validate_structure_template(self, template_name: str) -> str:
        """Validate a known structure template."""
        templates = {
            "exhaustion": '''
"""@pyne
"""
from pynecore import Series, input, plot, color, script, Persistent

@script.indicator(title="Exhaustion Signal", overlay=True)
def main():
    # Inputs
    level1 = input.int("Level 1", 9)
    level2 = input.int("Level 2", 12) 
    level3 = input.int("Level 3", 14)
    
    # Persistent state
    cycle: Persistent[int] = 0
    bull: Persistent[int] = 0
    bear: Persistent[int] = 0
    
    # Signal logic here
    
    # Plot signals
    plot(bull == level1, "Bull L1", color=color.green)
    # ... more plots
''',
            "trend_indicator": '''
"""@pyne
"""
from pynecore import Series, input, plot, color, script

@script.indicator(title="Trend Indicator", overlay=False)
def main():
    # Inputs
    fast_ma = input.int("Fast MA", 12)
    slow_ma = input.int("Slow MA", 26)
    
    # Calculations
    fast = close.sma(fast_ma)
    slow = close.sma(slow_ma)
    
    # Signals
    crossover = fast > slow and fast[1] <= slow[1]
    crossunder = fast < slow and fast[1] >= slow[1]
    
    # Plot results
    plot(fast, "Fast MA", color=color.blue)
    plot(slow, "Slow MA", color=color.red)
    plotshape(crossover, "Buy", shape.triangleup, color=color.green)
    plotshape(crossunder, "Sell", shape.triangledown, color=color.red)
''',
        }

        if template_name in templates:
            result = self.validate_pyne_code(templates[template_name])
            return (
                templates[template_name]
                if result.is_valid
                else "# Template validation failed"
            )

        return "# Unknown template"

    def suggest_improvements(self, code: str) -> List[str]:
        """Suggest improvements to valid code."""
        suggestions = []

        # Check for common patterns that could be improved
        if "if " in code and "elif " not in code:
            suggestions.append("Consider using elif for cleaner conditional logic")

        if "plot(" in code and "plotshape(" not in code:
            suggestions.append("Add plotshape() for clearer signal visualization")

        if "Persistent" not in code and any(
            term in code for term in ["bull", "bear", "cycle"]
        ):
            suggestions.append("Consider using Persistent[] for state preservation")

        if "input.int" in code and "input.float" not in code:
            suggestions.append("Consider using input.float() for decimal parameters")

        return suggestions
