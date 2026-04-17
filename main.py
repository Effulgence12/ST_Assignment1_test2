"""Main entry point for LLM-based static code analysis pipeline."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from llm_client import StaticAnalyzerLLM


def sanitize_llm_json(raw_response: str) -> str:
    """Remove common markdown wrappers and isolate JSON content safely.

    Args:
        raw_response: Raw text produced by the LLM.

    Returns:
        A cleaned string intended for JSON decoding.
    """
    cleaned: str = raw_response.strip()

    # 兼容模型偶发输出 ```json ... ``` 包裹的场景。
    if cleaned.startswith("```"):
        cleaned = cleaned.strip("`").strip()
        if cleaned.lower().startswith("json"):
            cleaned = cleaned[4:].strip()

    # 提取首尾大括号之间内容，减少前后噪声导致的解析错误。
    start_index: int = cleaned.find("{")
    end_index: int = cleaned.rfind("}")

    if start_index != -1 and end_index != -1 and end_index >= start_index:
        return cleaned[start_index : end_index + 1]

    return cleaned


def load_target_code(file_path: Path) -> str:
    """Read source code from target file.

    Args:
        file_path: Path to source code file.

    Returns:
        File content as UTF-8 text.
    """
    # 统一采用 UTF-8 读取，避免跨平台编码问题。
    return file_path.read_text(encoding="utf-8")


def save_report(report: dict[str, Any], output_path: Path) -> None:
    """Persist parsed analysis report to disk as indented JSON.

    Args:
        report: Parsed JSON report dictionary.
        output_path: Destination path for saved report.
    """
    # 使用缩进写入，便于人工审阅和版本管理。
    output_path.write_text(json.dumps(report, indent=2, ensure_ascii=False), encoding="utf-8")


def print_issue_summary(report: dict[str, Any]) -> None:
    """Print a clear summary of discovered issues to console.

    Args:
        report: Parsed analysis report dictionary.
    """
    issues: list[dict[str, Any]] = report.get("issues", [])
    print("\nStatic Code Analysis Summary")
    print("=" * 32)
    print(f"Total issues detected: {len(issues)}")

    if not issues:
        print("No issues were identified by the model.")
        return

    # 逐条输出，便于快速定位行号、类型、严重级别与修复建议。
    for index, issue in enumerate(issues, start=1):
        line: Any = issue.get("line", "N/A")
        issue_type: Any = issue.get("type", "Unknown")
        severity: Any = issue.get("severity", "Unknown")
        description: Any = issue.get("description", "No description provided")
        recommendation: Any = issue.get("recommendation", "No recommendation provided")

        print(f"\nIssue {index}")
        print(f"  Line: {line}")
        print(f"  Type: {issue_type}")
        print(f"  Severity: {severity}")
        print(f"  Description: {description}")
        print(f"  Recommendation: {recommendation}")


def main() -> None:
    """Execute end-to-end static analysis workflow."""
    target_file: Path = Path("target_code.py")
    report_file: Path = Path("analysis_report.json")

    try:
        source_code: str = load_target_code(target_file)
    except FileNotFoundError:
        print(f"Error: target file not found: {target_file}")
        return

    try:
        analyzer: StaticAnalyzerLLM = StaticAnalyzerLLM()
        raw_response: str = analyzer.analyze_code(source_code)
        sanitized_response: str = sanitize_llm_json(raw_response)
        parsed_report: dict[str, Any] = json.loads(sanitized_response)
    except json.JSONDecodeError as exc:
        print("Error: failed to decode model response as JSON.")
        print(f"Decoder message: {exc}")
        print("Raw model response follows:")
        print(raw_response if "raw_response" in locals() else "<no response captured>")
        return
    except Exception as exc:  # noqa: BLE001
        print(f"Unexpected error during analysis: {exc}")
        return

    save_report(parsed_report, report_file)
    print(f"Analysis report saved to: {report_file.resolve()}")
    print_issue_summary(parsed_report)


if __name__ == "__main__":
    main()
