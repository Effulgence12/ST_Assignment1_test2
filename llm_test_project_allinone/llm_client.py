"""Client module for communicating with a Qwen-compatible OpenAI API endpoint."""

from __future__ import annotations

import os
from pathlib import Path
from typing import Any

from openai import OpenAI


def _load_dotenv(dotenv_path: Path = Path(".env")) -> None:
    """Load simple KEY=VALUE pairs from a .env file into process environment.

    Notes:
        - This project intentionally avoids extra dependencies.
        - Existing environment variables will not be overwritten.

    Args:
        dotenv_path: Path to the .env file.
    """
    # 如果本地没有 .env 文件，则直接回退到系统环境变量。
    if not dotenv_path.exists():
        return

    # 逐行读取 .env，并仅处理简单的 KEY=VALUE 配置。
    for raw_line in dotenv_path.read_text(encoding="utf-8").splitlines():
        line: str = raw_line.strip()

        # 跳过空行和注释行，避免污染配置。
        if not line or line.startswith("#"):
            continue
        if "=" not in line:
            continue

        key, value = line.split("=", 1)
        key = key.strip()
        value = value.strip().strip('"').strip("'")

        # 已存在的环境变量优先级更高，这里不做覆盖。
        if key and key not in os.environ:
            os.environ[key] = value


def _normalize_base_url(base_url: str) -> str:
    """Normalize a Qwen-compatible base URL for the OpenAI SDK."""
    normalized: str = base_url.strip().rstrip("/")

    if normalized.endswith("/chat/completions"):
        normalized = normalized[: -len("/chat/completions")]

    return normalized


def _read_float_env(name: str, default: float) -> float:
    """Read a float environment variable with validation."""
    raw_value: str | None = os.getenv(name)
    if raw_value is None:
        return default

    try:
        return float(raw_value)
    except ValueError as exc:
        raise ValueError(f"Environment variable {name} must be a float.") from exc


def _read_int_env(name: str, default: int) -> int:
    """Read an integer environment variable with validation."""
    raw_value: str | None = os.getenv(name)
    if raw_value is None:
        return default

    try:
        return int(raw_value)
    except ValueError as exc:
        raise ValueError(f"Environment variable {name} must be an integer.") from exc


class StaticAnalyzerLLM:
    """LLM-driven static analyzer that submits source code and expects strict JSON output."""

    def __init__(self, model: str | None = None) -> None:
        """Initialize analyzer with API credentials from environment variables.

        Args:
            model: Optional explicit model name. If omitted, reads QWEN_MODEL.

        Raises:
            ValueError: If required environment variables are missing.
        """
        # 优先从项目根目录读取 .env，同时兼容外部注入的环境变量。
        _load_dotenv()

        api_key: str | None = os.getenv("QWEN_API_KEY")
        base_url: str | None = os.getenv("QWEN_BASE_URL")
        env_model: str = os.getenv("QWEN_MODEL", "qwen-max")

        if not api_key:
            raise ValueError("Environment variable QWEN_API_KEY is required.")
        if not base_url:
            raise ValueError("Environment variable QWEN_BASE_URL is required.")

        # 配置项统一在此收口，便于后续调试不同模型和超参数。
        self._model: str = model or env_model
        self._temperature: float = _read_float_env("QWEN_TEMPERATURE", 0.0)
        self._max_tokens: int = _read_int_env("QWEN_MAX_TOKENS", 1200)
        timeout_seconds: float = _read_float_env("REQUEST_TIMEOUT_SECONDS", 90.0)
        max_retries: int = _read_int_env("REQUEST_MAX_RETRIES", 2)
        self._client: OpenAI = OpenAI(
            api_key=api_key,
            base_url=_normalize_base_url(base_url),
            timeout=timeout_seconds,
            max_retries=max_retries,
        )

    def _build_messages(self, source_code: str) -> list[dict[str, str]]:
        """Construct system and user messages for static code analysis.

        Args:
            source_code: The source code text to be analyzed.

        Returns:
            A list of chat messages formatted for the OpenAI-compatible API.
        """
        # 用严格 schema 约束模型输出，确保每个 issue 都绑定自己的 PoC。
        system_prompt: str = (
            "You are a Static Code Analyzer. Analyze the provided Python code and detect: "
            "(1) syntax errors, (2) security vulnerabilities, "
            "(3) potential runtime errors, and (4) code quality issues. "
            "Return ONLY valid JSON matching this exact schema and no additional text: "
            "{\n"
            "  \"issues\": [\n"
            "    {\n"
            "      \"line\": <line_number>,\n"
            "      \"type\": \"<issue_type>\",\n"
            "      \"description\": \"<detailed description>\",\n"
            "      \"severity\": \"<low/medium/high>\",\n"
            "      \"recommendation\": \"<how to fix>\",\n"
            "      \"category\": \"<e.g., Code Quality / Security>\",\n"
            "      \"reference\": \"<URL to official docs/PEP8/CWE>\",\n"
            "      \"proof_of_concept\": \"<A standalone python script string demonstrating this specific issue. If not applicable, return null.>\"\n"
            "    }\n"
            "  ]\n"
            "}. "
            "Each issue must contain its own proof_of_concept so that there is a strict 1-to-1 relationship between the issue and its test case. "
            "If a proof_of_concept is not applicable for a specific issue, return null for that field."
        )

        user_prompt: str = (
            "Analyze the following Python code and produce the strict JSON report.\n"
            "Do not wrap the response in markdown fences.\n\n"
            f"{source_code}"
        )

        return [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt},
        ]

    def analyze_code(self, source_code: str) -> str:
        """Submit source code for analysis and return raw model response text.

        Args:
            source_code: Python source code to evaluate.

        Returns:
            Raw textual response from model, expected to be strict JSON.

        Raises:
            RuntimeError: If API response does not contain textual content.
        """
        # 保留 json_object 模式，尽量让返回结构稳定且易于解析。
        response: Any = self._client.chat.completions.create(
            model=self._model,
            messages=self._build_messages(source_code),
            temperature=self._temperature,
            max_tokens=self._max_tokens,
            response_format={"type": "json_object"},
        )

        content: str | None = response.choices[0].message.content
        if not content:
            raise RuntimeError("The model response did not include content.")

        return content
