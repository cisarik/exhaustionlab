"""
Hallucination Detection for LLM-Generated Code

Detects common hallucination patterns where LLMs invent
API features that don't exist in PyneCore.
"""

import re
from dataclasses import dataclass
from typing import Dict, List, Tuple


@dataclass
class HallucinationIssue:
    """Represents a detected hallucination."""

    pattern: str
    line_number: int
    line_content: str
    severity: str  # 'error' or 'warning'
    description: str
    suggestion: str


class HallucinationDetector:
    """Detects API hallucinations in generated PyneCore code."""

    # Forbidden patterns that indicate hallucinations
    FORBIDDEN_PATTERNS = [
        # plot() parameter hallucinations
        (
            r"plot\([^)]*\bstyle\s*=",
            "error",
            "plot() does NOT support 'style=' parameter",
            'Remove style= parameter, use only: plot(value, "label", color=color.xxx)',
        ),
        (
            r"plot\([^)]*\btitle\s*=",
            "error",
            "plot() does NOT support 'title=' parameter (title only in @script decorator)",
            'Remove title= from plot(), title goes in @script.indicator(title="...")',
        ),
        (
            r"plot\([^)]*\blinewidth\s*=",
            "error",
            "plot() does NOT support 'linewidth=' parameter",
            "Remove linewidth=, PyneCore plot() only accepts 3 parameters",
        ),
        (
            r"plot\([^)]*\blinestyle\s*=",
            "error",
            "plot() does NOT support 'linestyle=' parameter",
            'Remove linestyle=, use only: plot(value, "label", color=color.xxx)',
        ),
        (
            r"plot\([^)]*\bmarker\s*=",
            "error",
            "plot() does NOT support 'marker=' parameter",
            "Remove marker=, PyneCore uses simple plot() syntax",
        ),
        (
            r"plot\([^)]*\balpha\s*=",
            "error",
            "plot() does NOT support 'alpha=' parameter",
            "Remove alpha=, transparency not supported",
        ),
        # Invalid color hallucinations
        (
            r"color\.(purple|orange|pink|brown|cyan|magenta|gray|grey)\b",
            "error",
            "Invalid color - PyneCore only supports: green, red, blue, yellow, white, black",
            "Use only: color.green, color.red, color.blue, color.yellow, color.white, color.black",
        ),
        # Boolean operator hallucinations (using 'and'/'or' with Series)
        (
            r"\b(rsi|sma|ema|macd|close|open|high|low)\s*[<>=!]+\s*\d+\s+and\s+",
            "warning",
            "Using 'and' with Series comparisons - should use '&'",
            "Replace 'and' with '&': (condition1) & (condition2)",
        ),
        (
            r"\b(rsi|sma|ema|macd|close|open|high|low)\s*[<>=!]+\s*\d+\s+or\s+",
            "warning",
            "Using 'or' with Series comparisons - should use '|'",
            "Replace 'or' with '|': (condition1) | (condition2)",
        ),
        # plotshape() hallucinations (not commonly available)
        (
            r"plotshape\s*\(",
            "warning",
            "plotshape() may not be available in PyneCore",
            "Use plot() instead with boolean values",
        ),
        # plotarrow() hallucinations
        (
            r"plotarrow\s*\(",
            "warning",
            "plotarrow() may not be available in PyneCore",
            "Use plot() instead",
        ),
        # fill() hallucinations
        (
            r"\bfill\s*\(",
            "warning",
            "fill() may not be available in PyneCore",
            "Use plot() for individual series instead",
        ),
    ]

    # Required imports check
    REQUIRED_IMPORTS = [
        r"from pynecore import",
        r"@script\.(indicator|strategy)",
    ]

    def detect_hallucinations(self, code: str) -> List[HallucinationIssue]:
        """
        Detect all hallucinations in generated code.

        Args:
            code: The generated PyneCore code

        Returns:
            List of detected hallucination issues
        """
        issues = []

        # Check each line
        lines = code.split("\n")
        for line_num, line in enumerate(lines, 1):
            # Skip comments
            if line.strip().startswith("#"):
                continue

            # Check each forbidden pattern
            for pattern, severity, description, suggestion in self.FORBIDDEN_PATTERNS:
                if re.search(pattern, line, re.IGNORECASE):
                    issues.append(
                        HallucinationIssue(
                            pattern=pattern,
                            line_number=line_num,
                            line_content=line.strip(),
                            severity=severity,
                            description=description,
                            suggestion=suggestion,
                        )
                    )

        # Check for missing imports
        has_pynecore_import = bool(re.search(r"from pynecore import", code))

        if not has_pynecore_import:
            issues.append(
                HallucinationIssue(
                    pattern="missing_import",
                    line_number=0,
                    line_content="",
                    severity="error",
                    description="Missing PyneCore import",
                    suggestion="Add: from pynecore import Series, input, plot, color, script",
                )
            )

        # Check for @script decorator
        has_decorator = bool(re.search(r"@script\.(indicator|strategy)", code))

        if not has_decorator:
            issues.append(
                HallucinationIssue(
                    pattern="missing_decorator",
                    line_number=0,
                    line_content="",
                    severity="error",
                    description="Missing @script decorator",
                    suggestion='Add: @script.indicator(title="Strategy Name", overlay=True)',
                )
            )

        return issues

    def validate_code(self, code: str) -> Tuple[bool, List[HallucinationIssue]]:
        """
        Validate code and return success status with issues.

        Args:
            code: The generated PyneCore code

        Returns:
            Tuple of (is_valid, issues_found)
        """
        issues = self.detect_hallucinations(code)

        # Code is invalid if there are any error-level issues
        has_errors = any(issue.severity == "error" for issue in issues)
        is_valid = not has_errors

        return is_valid, issues

    def format_report(self, issues: List[HallucinationIssue]) -> str:
        """
        Format hallucination issues into a readable report.

        Args:
            issues: List of detected issues

        Returns:
            Formatted report string
        """
        if not issues:
            return "✅ No hallucinations detected - code is clean!"

        report = [
            f"\n{'='*80}",
            "🚨 HALLUCINATION DETECTION REPORT",
            f"{'='*80}",
            f"\nFound {len(issues)} issue(s):\n",
        ]

        errors = [i for i in issues if i.severity == "error"]
        warnings = [i for i in issues if i.severity == "warning"]

        if errors:
            report.append(f"\n🛑 ERRORS ({len(errors)}):")
            for issue in errors:
                report.append(f"\n  Line {issue.line_number}: {issue.description}")
                if issue.line_content:
                    report.append(f"  Code: {issue.line_content}")
                report.append(f"  💡 Fix: {issue.suggestion}")

        if warnings:
            report.append(f"\n⚠️  WARNINGS ({len(warnings)}):")
            for issue in warnings:
                report.append(f"\n  Line {issue.line_number}: {issue.description}")
                if issue.line_content:
                    report.append(f"  Code: {issue.line_content}")
                report.append(f"  💡 Suggestion: {issue.suggestion}")

        report.append(f"\n{'='*80}\n")

        return "\n".join(report)

    def get_statistics(self, issues: List[HallucinationIssue]) -> Dict[str, int]:
        """Get statistics about detected issues."""
        return {
            "total_issues": len(issues),
            "errors": sum(1 for i in issues if i.severity == "error"),
            "warnings": sum(1 for i in issues if i.severity == "warning"),
            "plot_issues": sum(1 for i in issues if "plot" in i.pattern),
            "color_issues": sum(1 for i in issues if "color" in i.pattern),
            "operator_issues": sum(1 for i in issues if "and" in i.pattern or "or" in i.pattern),
        }


# Convenience functions


def detect_hallucinations(code: str) -> List[HallucinationIssue]:
    """Quick function to detect hallucinations in code."""
    detector = HallucinationDetector()
    return detector.detect_hallucinations(code)


def validate_code(code: str) -> Tuple[bool, List[HallucinationIssue]]:
    """Quick function to validate code."""
    detector = HallucinationDetector()
    return detector.validate_code(code)


def format_report(issues: List[HallucinationIssue]) -> str:
    """Quick function to format report."""
    detector = HallucinationDetector()
    return detector.format_report(issues)


# Example usage
if __name__ == "__main__":
    # Test with hallucinated code
    test_code = """
from pynecore import Series, input, plot, color, script

@script.indicator(title="Test", overlay=True)
def main():
    rsi = close.rsi(14)
    sma = close.sma(20)

    # This has hallucinations
    buy = rsi < 30 and close > sma  # Wrong operator
    sell = rsi > 70 and close < sma  # Wrong operator

    # Invalid parameters
    plot(rsi, "RSI", color=color.purple, style=plot.Style.LINE, title="RSI")
    plot(buy, "Buy", color=color.green, linewidth=2)

    return {"buy": buy, "sell": sell}
"""

    print("🧪 Testing Hallucination Detector\n")

    detector = HallucinationDetector()
    is_valid, issues = detector.validate_code(test_code)

    print(f"Valid: {is_valid}")
    print(detector.format_report(issues))

    stats = detector.get_statistics(issues)
    print("📊 Statistics:")
    for key, value in stats.items():
        print(f"  {key}: {value}")
