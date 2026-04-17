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
    # 如果没有 .env 文件，直接返回，允许通过系统环境变量注入配置。
    if not dotenv_path.exists():
        return

    # 逐行读取 .env，并解析成环境变量。
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

        # 不覆盖已存在的环境变量，保证外部注入优先级更高。
        if key and key not in os.environ:
            os.environ[key] = value


class StaticAnalyzerLLM:
    """LLM-driven static analyzer that submits source code and expects strict JSON output."""

    def __init__(self, model: str | None = None) -> None:
        """Initialize analyzer with API credentials from environment variables.

        Args:
            model: Optional explicit model name. If omitted, reads QWEN_MODEL.

        Raises:
            ValueError: If required environment variables are missing.
        """
        # 优先读取 .env（如存在），同时兼容外部环境变量配置。
        _load_dotenv()

        api_key: str | None = os.getenv("QWEN_API_KEY")
        base_url: str | None = os.getenv("QWEN_BASE_URL")
        env_model: str = os.getenv("QWEN_MODEL", "qwen-max")

        if not api_key:
            raise ValueError("Environment variable QWEN_API_KEY is required.")
        if not base_url:
            raise ValueError("Environment variable QWEN_BASE_URL is required.")

        # 模型优先级为显式传参 > 环境变量 > 默认值。
        self._model: str = model or env_model
        self._client: OpenAI = OpenAI(api_key=api_key, base_url=base_url)

    def _build_messages(self, source_code: str) -> list[dict[str, str]]:
        """Construct system and user messages for static code analysis.

        Args:
            source_code: The source code text to be analyzed.

        Returns:
            A list of chat messages formatted for the OpenAI-compatible API.
        """
        # 系统提示词中强制约束输出为 JSON，降低解析失败概率。
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
            "      \"recommendation\": \"<how to fix>\"\n"
            "    }\n"
            "  ],\n"
            "  \"proof_of_concept\": \"<code>\"\n"
            "}. "
            "The proof_of_concept must be a short Python script that demonstrates how one severe vulnerability could be exploited or could fail in execution."
        )

        user_prompt: str = (
            "Analyze the following Python code and produce the strict JSON report:\n\n"
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
        # 温度设为 0，尽量提升输出结构稳定性。
        response: Any = self._client.chat.completions.create(
            model=self._model,
            messages=self._build_messages(source_code),
            temperature=0,
        )

        content: str | None = response.choices[0].message.content
        if not content:
            raise RuntimeError("The model response did not include content.")

        return content
