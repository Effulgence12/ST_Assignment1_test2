"""Main entry point for LLM-based static code analysis pipeline."""

from __future__ import annotations

import argparse
import json
from datetime import datetime
from pathlib import Path
from typing import Any

from llm_client import StaticAnalyzerLLM


TARGET_DIR: Path = Path("target")
REPORT_DIR: Path = Path("reported_alarms")
POC_DIR: Path = REPORT_DIR / "poc_cases"


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


def sanitize_code_snippet(raw_code: str) -> str:
    """Remove accidental markdown fences from a generated Python snippet.

    Args:
        raw_code: Raw code text returned by the LLM.

    Returns:
        Sanitized Python source code.
    """
    cleaned: str = raw_code.strip()

    # 单独清洗 PoC 代码块，避免模型返回 ```python 包裹时影响保存和执行。
    if cleaned.startswith("```"):
        cleaned = cleaned.strip("`").strip()
        if cleaned.lower().startswith("python"):
            cleaned = cleaned[6:].strip()

    return cleaned


def print_progress(message: str) -> None:
    """Print a concise progress hint for long-running analysis steps."""
    print(f"[进度] {message}", flush=True)


def parse_args() -> argparse.Namespace:
    """Parse command-line arguments for the analysis entry point."""
    parser = argparse.ArgumentParser(description="LLM 静态代码分析工具")
    parser.add_argument(
        "--input",
        dest="input_name",
        help="待分析代码文件名或路径；默认使用 target/test1.py",
    )
    return parser.parse_args()


def resolve_input_path(input_name: str | None) -> Path:
    """Resolve the input script path from a filename or path-like argument."""
    if input_name is None:
        return TARGET_DIR / "test1.py"

    raw_input: Path = Path(input_name)
    candidates: list[Path] = []

    if raw_input.is_absolute():
        candidates.append(raw_input)
    else:
        candidates.extend([raw_input, TARGET_DIR / raw_input])
        if raw_input.suffix == "":
            candidates.extend(
                [raw_input.with_suffix(".py"), TARGET_DIR / raw_input.with_suffix(".py")]
            )

    seen: set[Path] = set()
    unique_candidates: list[Path] = []
    for candidate in candidates:
        normalized: Path = candidate
        if normalized not in seen:
            seen.add(normalized)
            unique_candidates.append(normalized)

    for candidate in unique_candidates:
        if candidate.exists() and candidate.is_file():
            return candidate

    candidate_text: str = ", ".join(str(path) for path in unique_candidates)
    raise FileNotFoundError(f"Unable to locate input file. Checked: {candidate_text}")


def build_output_paths(input_path: Path) -> tuple[Path, Path]:
    """Build timestamped report and PoC output paths for one analysis run."""
    timestamp: str = datetime.now().strftime("%Y%m%d_%H%M%S")
    report_path: Path = REPORT_DIR / f"analysis_report_{input_path.stem}_{timestamp}.json"
    poc_output_dir: Path = POC_DIR / f"{input_path.stem}_{timestamp}"
    return report_path, poc_output_dir


def load_target_code(file_path: Path) -> str:
    """Read source code from target file.

    Args:
        file_path: Path to source code file.

    Returns:
        File content as UTF-8 text.
    """
    # 统一使用 UTF-8 读取，减少跨平台环境下的编码问题。
    return file_path.read_text(encoding="utf-8")


def save_report(report: dict[str, Any], output_path: Path) -> None:
    """Persist parsed analysis report to disk as indented JSON.

    Args:
        report: Parsed JSON report dictionary.
        output_path: Destination path for saved report.
    """
    # 使用缩进写入，便于人工审阅和版本管理。
    # 报告统一按时间编号保存，避免重复运行时覆盖旧结果。
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(json.dumps(report, indent=2, ensure_ascii=False), encoding="utf-8")


def save_issue_proof_of_concepts(report: dict[str, Any], output_dir: Path) -> list[Path]:
    """Save each valid issue-level proof of concept into a separate Python file.

    Args:
        report: Parsed analysis report dictionary.
        output_dir: Directory where PoC files should be written.

    Returns:
        A list of saved PoC file paths.
    """
    issues: list[dict[str, Any]] = report.get("issues", [])
    saved_files: list[Path] = []

    # 每次分析的 PoC 都放进独立子目录，避免根目录出现大量零散脚本。
    output_dir.mkdir(parents=True, exist_ok=True)
    for index, issue in enumerate(issues, start=1):
        proof_of_concept: Any = issue.get("proof_of_concept")
        if not isinstance(proof_of_concept, str):
            continue

        sanitized_code: str = sanitize_code_snippet(proof_of_concept)
        if not sanitized_code:
            continue

        output_path: Path = output_dir / f"poc_issue_{index}.py"
        output_path.write_text(f"{sanitized_code}\n", encoding="utf-8")
        saved_files.append(output_path)

    return saved_files


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
        category: Any = issue.get("category", "Uncategorized")
        reference: Any = issue.get("reference", "No reference provided")
        proof_of_concept: Any = issue.get("proof_of_concept")

        print(f"\nIssue {index}")
        print(f"  Line: {line}")
        print(f"  Type: {issue_type}")
        print(f"  Severity: {severity}")
        print(f"  Category: {category}")
        print(f"  Reference: {reference}")
        print(f"  Description: {description}")
        print(f"  Recommendation: {recommendation}")

        if isinstance(proof_of_concept, str) and sanitize_code_snippet(proof_of_concept):
            print("  Test Case (Proof of concept):")
            for code_line in sanitize_code_snippet(proof_of_concept).splitlines():
                print(f"    {code_line}")


def main() -> None:
    """Execute end-to-end static analysis workflow."""
    args: argparse.Namespace = parse_args()

    try:
        target_file: Path = resolve_input_path(args.input_name)
        report_file, poc_output_dir = build_output_paths(target_file)
        print_progress(f"已定位待分析文件: {target_file}")
        print_progress("正在读取源代码并准备请求大模型...")
        source_code: str = load_target_code(target_file)
    except FileNotFoundError:
        print(
            "Error: target file not found: "
            f"{args.input_name if args.input_name else TARGET_DIR / 'test1.py'}"
        )
        return

    try:
        analyzer: StaticAnalyzerLLM = StaticAnalyzerLLM()
        print_progress("大模型分析进行中，请稍候...")
        raw_response: str = analyzer.analyze_code(source_code)
        print_progress("模型响应已返回，正在解析并归档结果...")
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
    saved_poc_files: list[Path] = save_issue_proof_of_concepts(parsed_report, poc_output_dir)

    print(f"Analysis report saved to: {report_file.resolve()}")
    if saved_poc_files:
        print("Saved proof-of-concept files:")
        for file_path in saved_poc_files:
            print(f"  - {file_path.resolve()}")
    else:
        print("No valid proof-of-concept scripts were returned by the model.")

    print_issue_summary(parsed_report)


if __name__ == "__main__":
    main()
