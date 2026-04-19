# Title: LLM-based Static Analysis for Python Scripts

## 1. Input

**System Overview:**

This project implements an LLM-based static-analysis pipeline for Python code. The tool accepts a Python source file, sends the full source text to a large language model, and asks the model to report possible syntax errors, security vulnerabilities, runtime risks, and code-quality issues in a strict JSON format. The implementation reads source files from the local filesystem, invokes a Qwen-compatible API, normalize the returned JSON, stores the analysis result under a timestamped filename, and saves one proof-of-concept (PoC) script for each reported issue.

To evaluate the tool, we used three different inputs:

- `target/test1.py`: a small synthetic benchmark with intentionally injected defects.
- `target/test2.py`: a larger service-style benchmark containing security and reliability issues.
- `target/url.py`: a real parsing module adapted from `proxy.py`, used to evaluate generalizability on production-style code.

The experiments were executed on Windows PowerShell with Python 3.13. The LLM configuration was loaded from `.env`, while the project code handled source reading, response sanitization, result archival, and PoC persistence locally.

**Code Structure / Interfaces:**

| File / Component  | Main Interface                     | Role in the Experiment                                                                            |
| ----------------- | ---------------------------------- | ------------------------------------------------------------------------------------------------- |
| `main.py`         | `main()`                           | End-to-end entry point: resolve input path, load code, call LLM, parse JSON, save report and PoCs |
| `llm_client.py`   | `StaticAnalyzerLLM.analyze_code()` | Builds prompts and sends the static-analysis request to the Qwen-compatible API                   |
| `target/test1.py` | `process_data(filename, data)`     | Small benchmark with runtime, security, and code-quality defects                                  |
| `target/test2.py` | `ReportService` methods            | Larger benchmark with path handling, subprocess usage, `eval`, and file I/O                       |
| `target/url.py`   | `Url.from_bytes`, `Url._parse`     | Real parser module used to evaluate generalizability and false alarms                             |

## 2. Tool Artifact

**LLM Used:**

`qwen3.6-plus` via DashScope OpenAI-compatible endpoint `https://dashscope.aliyuncs.com/compatible-mode/v1`.

**Example Prompt:**

The final prompt used by the project is implemented in `llm_client.py`.

```text
System prompt:
You are a Static Code Analyzer. Analyze the provided Python code and detect:
(1) syntax errors, (2) security vulnerabilities,
(3) potential runtime errors, and (4) code quality issues.
Return ONLY valid JSON matching this exact schema and no additional text:
{
  "issues": [
    {
      "line": <line_number>,
      "type": "<issue_type>",
      "description": "<detailed description>",
      "severity": "<low/medium/high>",
      "recommendation": "<how to fix>",
      "category": "<e.g., Code Quality / Security>",
      "reference": "<URL to official docs/PEP8/CWE>",
      "proof_of_concept": "<A standalone python script string demonstrating this specific issue. If not applicable, return null.>"
    }
  ]
}.
Each issue must contain its own proof_of_concept so that there is a strict 1-to-1 relationship between the issue and its test case.
If a proof_of_concept is not applicable for a specific issue, return null for that field.

User prompt:
Analyze the following Python code and produce the strict JSON report.
Do not wrap the response in markdown fences.

{source_code}
```

The API call also enables `response_format={"type": "json_object"}` to make the output easier to parse automatically.

**Code:**

Representative benchmark snippets are shown below. The complete inputs are stored in `target/test1.py`, `target/test2.py`, and `target/url.py`.

```python
# target/test1.py
def process_data(filename, data):
    f = open(filename, "w")
    f.write(data)

    Print("Data written successfully")
    exec("print('Executing dynamic code')")

    try:
        result = 10 / 0
    except:
        pass

    return True
```

```python
# target/test2.py
class ReportService:
    def __init__(self, backup_root, hooks=[]):
        self.backup_root = backup_root
        self.hooks = hooks

    def load_report(self, report_name):
        report_path = Path(self.backup_root) / report_name
        return report_path.read_text(encoding="utf-8")

    def execute_hook(self, hook_code):
        return eval(hook_code)

    def export_report(self, report_name, shell_target):
        report_text = self.load_report(report_name)
        subprocess.run(f"echo {report_text} > {shell_target}", shell=True, check=True)
```

## 3. Generated Output

**Reported Alarms:**

The tool stores every analysis under `reported_alarms/analysis_report_<name>_<timestamp>.json`. Representative findings are listed below.

| Target     | Reported Issues | Representative Findings                                                                                                              |
| ---------- | --------------: | ------------------------------------------------------------------------------------------------------------------------------------ |
| `test1.py` |               5 | undefined `Print`, unclosed file, `exec`, division by zero, bare `except`                                                            |
| `test2.py` |               6 | mutable default argument, path traversal, `eval`, command injection, unclosed file, bare `except`                                    |
| `url.py`   |               6 | empty-input `IndexError`, credentials unpacking error, invalid port `ValueError`, UTF-8 decode risk, low-value code-quality warnings |

Example JSON excerpt from `analysis_report_test2_20260419_163521.json`:

```json
{
  "issues": [
    {
      "line": 14,
      "type": "Path Traversal",
      "severity": "high",
      "category": "Security",
      "description": "The `report_name` parameter is directly concatenated with `backup_root` without sanitization, allowing an attacker to read arbitrary files on the filesystem using sequences like `../../etc/passwd`."
    },
    {
      "line": 19,
      "type": "Arbitrary Code Execution",
      "severity": "high",
      "category": "Security",
      "description": "The `eval()` function executes arbitrary Python code from the `hook_code` string, which can lead to complete system compromise if the input is untrusted or user-controlled."
    }
  ]
}
```

**Test Case (Proof of concept):**

The final prompt asks the model to generate one PoC per issue. A successful example is the PoC generated for the `eval()` vulnerability in `test2.py`:

```python
hook_code = '__import__("os").system("echo pwned")'
result = eval(hook_code)
print(result)
```

When executed locally, this script printed `pwned`, confirming that the reported risk is reproducible.

## 4. Experimental Analysis

**4.1 False Alarms Analysis**

We first evaluated the analyzer on the two synthetic benchmarks whose defects were manually planted in advance. This gives us a controlled ground truth for precision and recall analysis.

| Target     |     Ground-Truth Defects | Reported Issues |  TP |  FP |  FN | Notes                                                      |
| ---------- | -----------------------: | --------------: | --: | --: | --: | ---------------------------------------------------------- |
| `test1.py` |                        5 |               5 |   5 |   0 |   0 | All planted issues were detected                           |
| `test2.py` |                        6 |               6 |   6 |   0 |   0 | All planted issues were detected after token-budget tuning |
| `url.py`   | not exhaustively labeled |               6 | N/A | N/A | N/A | Used mainly for realism and false-alarm discussion         |

On `test1.py`, the model correctly identified the unclosed file handle, undefined `Print`, use of `exec`, unconditional division by zero, and bare `except`. On `test2.py`, it correctly detected the mutable default argument, path traversal risk, arbitrary code execution via `eval`, command injection through `shell=True`, resource leak, and bare `except`.

The results on `url.py` were more nuanced. Several findings were clearly useful:

- accessing `raw[0]` without checking for empty input can raise `IndexError`
- unpacking `split_at[0].split(COLON)` can raise `ValueError`
- converting an invalid port string with `int(...)` can raise `ValueError`

However, the analyzer also produced weaker low-severity findings, such as the warning about using the magic number `47` and the warning about omitting port `0` in `__str__`. These findings are not entirely wrong, but they are much less actionable than the runtime issues. This suggests that the LLM has strong recall on curated benchmark code, but precision decreases on real modules where some reported issues are arguable or low value.

**4.2 Refining Prompts for improving accuracy**

To study prompt refinement, we compared two prompt versions on the same targets:

- **Baseline prompt:** only requested `line`, `type`, `description`, and `severity`.
- **Refined prompt:** required recommendations, categories, references, and a one-to-one PoC for each issue, plus a strict JSON schema.

| Dimension            | Baseline Prompt                                                            | Refined Prompt                                                |
| -------------------- | -------------------------------------------------------------------------- | ------------------------------------------------------------- |
| Output fields        | `line`, `type`, `description`, `severity`                                  | full schema with recommendation, category, reference, and PoC |
| PoC generation       | not available                                                              | available for most findings                                   |
| Type naming          | inconsistent (`code_quality`, `security_vulnerability`, lowercase phrases) | more standardized human-readable labels                       |
| Line localization    | less stable on `test2.py` and `url.py`                                     | more precise on the benchmark files                           |
| Automation readiness | limited                                                                    | directly usable by `main.py` for report and PoC archival      |

For example, on `test2.py` the baseline prompt reported the six defects, but line numbers drifted to `6/13/18/23/26/35`, type names mixed snake\_case with lowercase phrases, and no supporting artifacts were generated. The refined prompt reported the same six defects with clearer labels, explicit security/code-quality categories, remediation guidance, references, and executable PoCs.

Prompt refinement also exposed an engineering tradeoff. With the final prompt and the default `QWEN_MAX_TOKENS=1200`, the first `test2.py` run failed because the returned JSON was truncated, causing `JSONDecodeError`. After increasing the token budget to `2200`, the refined prompt completed successfully and produced a full six-issue report. Therefore, prompt refinement improved usefulness and structure, but it also increased output length and required parameter tuning for stability.

**4.3 Try more projects to improve generalizability**

We evaluated generalizability by applying the same tool to three targets with different characteristics:

- `test1.py`: tiny function with obvious planted defects
- `test2.py`: larger service-like script with file I/O, subprocess calls, and path handling
- `url.py`: real parser logic from an open-source codebase

The analyzer generalized well across these targets. On `test1.py`, it detected direct runtime and security risks. On `test2.py`, it successfully reasoned about higher-level vulnerabilities such as path traversal and shell injection, which require more semantic understanding than simple style checks. On `url.py`, it shifted naturally from classic security findings to parser edge cases and runtime robustness issues, indicating that the same prompt can adapt to different code domains.

At the same time, the realism of the target clearly affected output quality. The synthetic benchmarks yielded near-perfect results, while the real parser produced a mix of strong findings and low-priority observations. This indicates that the tool generalizes across project types, but its precision remains sensitive to code style, context, and whether the code is intentionally seeded with defects or taken from a mature codebase.

**4.4 Bug Reporting and Validation by the developers**

We manually executed representative PoCs generated by the refined prompt to validate whether the reported issues were reproducible.

| Target / Issue                      | PoC Result                                                              | Validation Outcome                  |
| ----------------------------------- | ----------------------------------------------------------------------- | ----------------------------------- |
| `test1.py` undefined `Print`        | raised `NameError`                                                      | confirmed                           |
| `test1.py` `exec`                   | printed `compromised`                                                   | confirmed                           |
| `test1.py` division by zero         | raised `ZeroDivisionError`                                              | confirmed                           |
| `test1.py` bare `except`            | exception swallowed silently                                            | confirmed pattern                   |
| `test1.py` resource leak            | script ran but mainly demonstrated the risky pattern                    | partial                             |
| `test2.py` mutable default argument | printed `[1]`                                                           | confirmed                           |
| `test2.py` `eval`                   | printed `pwned`                                                         | confirmed                           |
| `test2.py` path traversal           | generated PoC failed to reach an external file                          | issue valid, PoC weak               |
| `test2.py` command injection        | payload used `;`, which is not an effective Windows `cmd.exe` separator | issue valid, PoC platform-dependent |

These results show that the analyzer can generate actionable PoCs for direct runtime failures and arbitrary code execution risks. However, PoC quality is not uniform. For environment-dependent vulnerabilities such as shell injection and path traversal, the model may identify the correct vulnerability class but generate an exploit script that is incomplete or not portable across operating systems. This is an important limitation for practical use.

## 5. Project Report

**5.1 Comparison to traditional non-AI-based technique, pros and cons**

As a traditional baseline, we ran `pylint` on the same benchmark files.

On `test1.py`, `pylint` successfully reported:

- `undefined-variable` for `Print`
- `exec-used`
- `bare-except`
- `consider-using-with` for file handling

However, it did **not** flag the unconditional `10 / 0` statement as a concrete runtime fault. It also produced several extra style-oriented messages, such as missing docstrings, trailing whitespace, unspecified encoding, and an unused variable warning.

On `test2.py`, `pylint` successfully reported:

- `dangerous-default-value`
- `eval-used`
- `bare-except`
- `consider-using-with`

But it did **not** report the path traversal risk or the command-injection risk caused by `shell=True` with string interpolation. Those issues require more semantic reasoning about untrusted input propagation than a standard rule-based linter usually performs.

On `url.py`, `pylint` first complained about relative imports because the file was analyzed outside its original package context. It also produced style and refactor messages such as `too-many-arguments` and `consider-using-f-string`. In contrast, the LLM-based analyzer discussed runtime edge cases inside the parsing logic itself. This highlights a key contextual difference: traditional tools are sensitive to packaging and configuration, while an LLM can reason directly over the source text even when the full project context is missing.

| Dimension          | LLM-based Analyzer                                                              | Pylint                                                                         |
| ------------------ | ------------------------------------------------------------------------------- | ------------------------------------------------------------------------------ |
| Security reasoning | Can infer path traversal, command injection, and `eval` risks                   | Good for explicit risky APIs, weaker for multi-step security reasoning         |
| Runtime reasoning  | Can discuss concrete failure scenarios such as empty input and division by zero | Stronger on syntactic/rule-based defects, weaker on semantic runtime reasoning |
| Output richness    | Description, severity, recommendation, reference, and PoC                       | Rule id, message, and location                                                 |
| Determinism        | Lower; may vary by prompt and token budget                                      | High; same code usually gives same diagnostics                                 |
| Noise profile      | Risk of weak or arguable warnings on real code                                  | Many style/configuration warnings, especially on default settings              |
| Setup sensitivity  | Requires model access and prompt tuning                                         | Requires correct environment/package context and tool configuration            |

In short, the LLM-based approach is better at semantic interpretation and richer reporting, while the traditional tool is more stable, deterministic, and cheaper to run repeatedly.

**5.2 Analytical report: limitations of AI and the ways to improve the tool**

The experiments revealed several limitations of the current LLM-based analyzer.

- **Output stability depends on prompt and token budget.** The refined prompt is far more useful than the baseline prompt, but it produced a truncated JSON response on `test2.py` when `QWEN_MAX_TOKENS=1200`. This means structured output must be paired with sufficient generation budget.
- **PoCs are not always environment-aware.** The generated command-injection PoC used a Unix-style separator (`;`) that did not demonstrate injection clearly under Windows `cmd.exe`.
- **False alarms increase on realistic code.** On `url.py`, the model mixed strong edge-case findings with weaker maintainability or style observations.
- **Line numbers can drift.** The baseline prompt in particular produced less precise line numbers than the refined version.
- **The system depends on external API availability.** We observed connection errors before rerunning the analyzer with network access, which means repeatability is partly tied to external service availability.

Several improvements are therefore recommended:

- keep the refined prompt, but tune `QWEN_MAX_TOKENS` according to file size
- add a lightweight pre-pass based on AST or regex rules to filter obvious issues before calling the LLM
- post-process findings to deduplicate overlapping alarms and downgrade low-value style comments
- add OS-aware PoC templates for Windows and Unix-like shells
- preserve richer metadata such as confidence scores and evidence spans
- compare repeated runs to measure response variance formally

These improvements would move the system from a useful course project prototype toward a more reliable engineering tool.

**5.3 Summary**

This project demonstrates that an LLM can be used as a practical static-analysis assistant for Python code. On the two controlled benchmark files, the analyzer detected all manually planted issues. On a more realistic open-source parsing module, it still identified several meaningful runtime edge cases, although some low-value warnings also appeared. Prompt refinement substantially improved the quality of the output by adding structured fields, remediation guidance, references, and executable PoCs, but it also required larger token budgets for stable execution. Compared with `pylint`, the LLM-based analyzer was better at contextual reasoning about security and runtime behavior, while the traditional tool remained more deterministic and easier to reproduce. Overall, the results support the usefulness of AI-assisted static analysis, while also showing that prompt design, output control, and validation are essential for dependable results.

## 6. Appendix: Full Artifacts

This appendix is intentionally verbose so that the report can still serve as a self-contained submission artifact even if the raw repository is not reviewed together with the PDF.

### 6.1 Exact Final Prompt Used in the Repository

```text
System prompt:
You are a Static Code Analyzer. Analyze the provided Python code and detect:
(1) syntax errors, (2) security vulnerabilities,
(3) potential runtime errors, and (4) code quality issues.
Return ONLY valid JSON matching this exact schema and no additional text:
{
  "issues": [
    {
      "line": <line_number>,
      "type": "<issue_type>",
      "description": "<detailed description>",
      "severity": "<low/medium/high>",
      "recommendation": "<how to fix>",
      "category": "<e.g., Code Quality / Security>",
      "reference": "<URL to official docs/PEP8/CWE>",
      "proof_of_concept": "<A standalone python script string demonstrating this specific issue. If not applicable, return null.>"
    }
  ]
}.
Each issue must contain its own proof_of_concept so that there is a strict 1-to-1 relationship between the issue and its test case.
If a proof_of_concept is not applicable for a specific issue, return null for that field.

User prompt:
Analyze the following Python code and produce the strict JSON report.
Do not wrap the response in markdown fences.

{source_code}
```

### 6.2 Exact Baseline Prompt Used for the Prompt-Refinement Experiment

```text
System prompt:
You are a Static Code Analyzer. Analyze the provided Python code and detect
syntax errors, security vulnerabilities, potential runtime errors, and code
quality issues. Return only valid JSON in this format and no extra text:
{
  "issues": [
    {
      "line": <line_number>,
      "type": "<issue_type>",
      "description": "<detailed description>",
      "severity": "<low/medium/high>"
    }
  ]
}.

User prompt:
Analyze the following Python code and produce the JSON report.

{source_code}
```

### 6.3 Full Input Source Code: `target/test1.py`

```python
def process_data(filename, data):
    
    f = open(filename, "w")
    f.write(data)

    Print("Data written successfully")

    exec("print('Executing dynamic code')")

    try:
        result = 10 / 0
    except:
        pass

    return True
```

### 6.4 Full Input Source Code: `target/test2.py`

```python
import json
import subprocess
from pathlib import Path


class ReportService:
    def __init__(self, backup_root, hooks=[]):
        # 问题 1：可变默认参数会在不同实例之间共享状态。
        self.backup_root = backup_root
        self.hooks = hooks

    def load_report(self, report_name):
        # 问题 2：未校验输入路径，可能触发路径遍历读取任意文件。
        report_path = Path(self.backup_root) / report_name
        return report_path.read_text(encoding="utf-8")

    def execute_hook(self, hook_code):
        # 问题 3：直接 eval 动态字符串，存在代码执行风险。
        return eval(hook_code)

    def export_report(self, report_name, shell_target):
        report_text = self.load_report(report_name)
        # 问题 4：shell=True 且拼接命令字符串，存在命令注入风险。
        subprocess.run(f"echo {report_text} > {shell_target}", shell=True, check=True)

    def save_summary(self, summary_path, payload):
        summary_file = open(summary_path, "w", encoding="utf-8")
        summary_file.write(json.dumps(payload, ensure_ascii=False))
        # 问题 5：文件打开后未关闭。

    def run(self, report_name, shell_target, hook_code):
        try:
            hook_result = self.execute_hook(hook_code)
            self.export_report(report_name, shell_target)
            self.save_summary("summary.json", {"hook": hook_result})
        except:
            # 问题 6：裸 except 会吞掉关键异常，增加排错难度。
            pass


def bootstrap():
    service = ReportService("./reports")
    service.run("weekly.txt", "out.txt", "__import__('os').getcwd()")
```

### 6.5 Full Input Source Code: `target/url.py`

```python
# -*- coding: utf-8 -*-
"""
    proxy.py
    ~~~~~~~~
    Fast, Lightweight, Pluggable, TLS interception capable proxy server focused on
    Network monitoring, controls & Application development, testing, debugging.

    :copyright: (c) 2013-present by Abhinav Singh and contributors.
    :license: BSD, see LICENSE for more details.

    .. spelling::

       http
       url
"""
from typing import List, Tuple, Optional

from .exception import HttpProtocolException
from ..common.utils import text_
from ..common.constants import AT, COLON, SLASH, DEFAULT_ALLOWED_URL_SCHEMES


class Url:
    """``urllib.urlparse`` doesn't work for proxy.py, so we wrote a simple URL.

    Currently, URL only implements what is necessary for HttpParser to work.
    """

    def __init__(
            self,
            scheme: Optional[bytes] = None,
            username: Optional[bytes] = None,
            password: Optional[bytes] = None,
            hostname: Optional[bytes] = None,
            port: Optional[int] = None,
            remainder: Optional[bytes] = None,
    ) -> None:
        self.scheme: Optional[bytes] = scheme
        self.username: Optional[bytes] = username
        self.password: Optional[bytes] = password
        self.hostname: Optional[bytes] = hostname
        self.port: Optional[int] = port
        self.remainder: Optional[bytes] = remainder

    @property
    def has_credentials(self) -> bool:
        """Returns true if both username and password components are present."""
        return self.username is not None and self.password is not None

    def __str__(self) -> str:
        url = ''
        if self.scheme:
            url += '{0}://'.format(text_(self.scheme))
        if self.hostname:
            url += text_(self.hostname)
        if self.port:
            url += ':{0}'.format(self.port)
        if self.remainder:
            url += text_(self.remainder)
        return url

    @classmethod
    def from_bytes(cls, raw: bytes, allowed_url_schemes: Optional[List[bytes]] = None) -> 'Url':
        """A URL within proxy.py core can have several styles,
        because proxy.py supports both proxy and web server use cases.

        Example:
        For a Web server, url is like ``/`` or ``/get`` or ``/get?key=value``
        For a HTTPS connect tunnel, url is like ``httpbin.org:443``
        For a HTTP proxy request, url is like ``http://httpbin.org/get``

        proxy.py internally never expects a https scheme in the request line.
        But `Url` class provides support for parsing any scheme present in the URLs.
        e.g. ftp, icap etc.

        If a url with no scheme is parsed, e.g. ``//host/abc.js``, then scheme
        defaults to `http`.

        Further:
        1) URL may contain unicode characters
        2) URL may contain IPv4 and IPv6 format addresses instead of domain names
        """
        # SLASH == 47, check if URL starts with single slash but not double slash
        starts_with_single_slash = raw[0] == 47
        starts_with_double_slash = starts_with_single_slash and \
            len(raw) >= 2 and \
            raw[1] == 47
        if starts_with_single_slash and \
                not starts_with_double_slash:
            return cls(remainder=raw)
        scheme = None
        rest = None
        if not starts_with_double_slash:
            # Find scheme
            parts = raw.split(b'://', 1)
            if len(parts) == 2:
                scheme = parts[0]
                rest = parts[1]
                if scheme not in (allowed_url_schemes or DEFAULT_ALLOWED_URL_SCHEMES):
                    raise HttpProtocolException(
                        'Invalid scheme received in the request line %r' % raw,
                    )
        else:
            rest = raw[len(SLASH + SLASH):]
        if scheme is not None or starts_with_double_slash:
            assert rest is not None
            parts = rest.split(SLASH, 1)
            username, password, host, port = Url._parse(parts[0])
            return cls(
                scheme=scheme if not starts_with_double_slash else b'http',
                username=username,
                password=password,
                hostname=host,
                port=port,
                remainder=None if len(parts) == 1 else (
                    SLASH + parts[1]
                ),
            )
        username, password, host, port = Url._parse(raw)
        return cls(username=username, password=password, hostname=host, port=port)

    @staticmethod
    def _parse(raw: bytes) -> Tuple[
            Optional[bytes],
            Optional[bytes],
            bytes,
            Optional[int],
    ]:
        split_at = raw.split(AT, 1)
        username, password = None, None
        if len(split_at) == 2:
            username, password = split_at[0].split(COLON)
        parts = split_at[-1].split(COLON, 2)
        num_parts = len(parts)
        port: Optional[int] = None
        # No port found
        if num_parts == 1:
            return username, password, parts[0], None
        # Host and port found
        if num_parts == 2:
            return username, password, COLON.join(parts[:-1]), int(parts[-1])
        # More than a single COLON i.e. IPv6 scenario
        try:
            # Try to resolve last part as an int port
            last_token = parts[-1].split(COLON)
            port = int(last_token[-1])
            host = COLON.join(parts[:-1]) + COLON + \
                COLON.join(last_token[:-1])
        except ValueError:
            # If unable to convert last part into port,
            # treat entire data as host
            host, port = raw, None
        # patch up invalid ipv6 scenario
        rhost = host.decode('utf-8')
        if COLON.decode('utf-8') in rhost and \
                rhost[0] != '[' and \
                rhost[-1] != ']':
            host = b'[' + host + b']'
        return username, password, host, port
```

### 6.6 Full Refined JSON Output: `test1`

```json
{
  "issues": [
    {
      "line": 6,
      "type": "Runtime Error",
      "description": "The function 'Print' is not defined in Python. Python is case-sensitive and the correct built-in function is 'print'. This will raise a NameError at runtime.",
      "severity": "high",
      "recommendation": "Change 'Print' to 'print'.",
      "category": "Code Quality",
      "reference": "https://docs.python.org/3/library/functions.html#print",
      "proof_of_concept": "def test():\n    Print('This will raise a NameError')\ntest()"
    },
    {
      "line": 3,
      "type": "Resource Leak",
      "description": "The file opened with open() is never explicitly closed. This can lead to resource exhaustion and potential data loss if the buffer is not flushed before the program exits.",
      "severity": "medium",
      "recommendation": "Use a context manager (with statement) to ensure the file is automatically closed: with open(filename, 'w') as f:",
      "category": "Code Quality",
      "reference": "https://docs.python.org/3/tutorial/inputoutput.html#reading-and-writing-files",
      "proof_of_concept": "import os\nf = open('test_leak.txt', 'w')\nf.write('data')\n# File descriptor remains open until garbage collection or program exit"
    },
    {
      "line": 8,
      "type": "Security Vulnerability",
      "description": "The use of exec() allows execution of arbitrary Python code. Even with a static string here, it represents a severe security anti-pattern that can lead to code injection if the input becomes dynamic.",
      "severity": "high",
      "recommendation": "Remove exec() entirely. Use standard function calls or safe evaluation methods if dynamic behavior is required.",
      "category": "Security",
      "reference": "https://cwe.mitre.org/data/definitions/94.html",
      "proof_of_concept": "user_input = \"__import__('os').system('echo compromised')\"\nexec(user_input)"
    },
    {
      "line": 11,
      "type": "Runtime Error",
      "description": "Division by zero (10 / 0) will unconditionally raise a ZeroDivisionError. While currently caught, it indicates flawed logic or placeholder code that will fail if the exception handling is modified.",
      "severity": "medium",
      "recommendation": "Ensure the divisor is never zero, or implement proper validation before performing the division.",
      "category": "Code Quality",
      "reference": "https://docs.python.org/3/library/exceptions.html#ZeroDivisionError",
      "proof_of_concept": "result = 10 / 0"
    },
    {
      "line": 12,
      "type": "Code Quality",
      "description": "Using a bare except: clause catches all exceptions, including system-exiting exceptions like SystemExit and KeyboardInterrupt. This suppresses critical errors and makes debugging difficult.",
      "severity": "medium",
      "recommendation": "Catch specific exceptions instead, e.g., except ZeroDivisionError:.",
      "category": "Code Quality",
      "reference": "https://peps.python.org/pep-0008/#programming-recommendations",
      "proof_of_concept": "try:\n    raise KeyboardInterrupt('User interrupted')\nexcept:\n    pass # Silently swallows KeyboardInterrupt"
    }
  ]
}
```

### 6.7 Full Refined JSON Output: `test2`

```json
{
  "issues": [
    {
      "line": 7,
      "type": "Mutable Default Argument",
      "description": "Using a mutable list `[]` as a default argument causes it to be instantiated once at function definition time and shared across all instances of the class, leading to unexpected state persistence and cross-instance data leakage.",
      "severity": "medium",
      "recommendation": "Change the default to `None` and initialize inside the method: `self.hooks = hooks if hooks is not None else []`.",
      "category": "Code Quality",
      "reference": "https://docs.python.org/3/tutorial/controlflow.html#default-argument-values",
      "proof_of_concept": "class Test:\n    def __init__(self, items=[]):\n        self.items = items\na = Test()\nb = Test()\na.items.append(1)\nprint(b.items)"
    },
    {
      "line": 14,
      "type": "Path Traversal",
      "description": "The `report_name` parameter is directly concatenated with `backup_root` without sanitization, allowing an attacker to read arbitrary files on the filesystem using sequences like `../../etc/passwd`.",
      "severity": "high",
      "recommendation": "Validate that the resolved path starts with `backup_root` using `Path.resolve().is_relative_to(Path(backup_root).resolve())` before reading.",
      "category": "Security",
      "reference": "https://cwe.mitre.org/data/definitions/22.html",
      "proof_of_concept": "from pathlib import Path\nimport os\nos.makedirs('safe_dir', exist_ok=True)\nwith open('safe_dir/secret.txt', 'w') as f: f.write('secret')\nroot = 'safe_dir'\nmalicious = '../secret.txt'\npath = Path(root) / malicious\nprint(path.read_text())"
    },
    {
      "line": 19,
      "type": "Arbitrary Code Execution",
      "description": "The `eval()` function executes arbitrary Python code from the `hook_code` string, which can lead to complete system compromise if the input is untrusted or user-controlled.",
      "severity": "high",
      "recommendation": "Avoid `eval()`. Use `ast.literal_eval()` for safe parsing of literals, or implement a strict allowlist/sandbox for hook execution.",
      "category": "Security",
      "reference": "https://cwe.mitre.org/data/definitions/94.html",
      "proof_of_concept": "hook_code = '__import__(\"os\").system(\"echo pwned\")'\nresult = eval(hook_code)\nprint(result)"
    },
    {
      "line": 24,
      "type": "Command Injection",
      "description": "Using `shell=True` with f-string interpolation in `subprocess.run` allows an attacker to inject arbitrary shell commands via `report_text` or `shell_target`.",
      "severity": "high",
      "recommendation": "Pass arguments as a list without `shell=True`, or use `shlex.quote()` if shell execution is strictly necessary.",
      "category": "Security",
      "reference": "https://cwe.mitre.org/data/definitions/78.html",
      "proof_of_concept": "import subprocess\nreport_text = 'test; echo INJECTED'\nshell_target = 'out.txt'\nsubprocess.run(f'echo {report_text} > {shell_target}', shell=True, check=True)"
    },
    {
      "line": 27,
      "type": "Resource Leak",
      "description": "The file opened with `open()` is never explicitly closed, which can lead to file descriptor exhaustion and potential data loss if the buffer isn't flushed before program termination.",
      "severity": "medium",
      "recommendation": "Use a context manager (`with open(...) as f:`) to ensure the file is properly closed and flushed after writing.",
      "category": "Code Quality",
      "reference": "https://docs.python.org/3/tutorial/inputoutput.html#reading-and-writing-files",
      "proof_of_concept": "import os\nf = open('leak_test.txt', 'w')\nf.write('data')\nprint(os.path.exists('leak_test.txt'))\nf.close()\nos.remove('leak_test.txt')"
    },
    {
      "line": 36,
      "type": "Bare Except Clause",
      "description": "A bare `except:` catches all exceptions including `SystemExit`, `KeyboardInterrupt`, and `GeneratorExit`, making debugging difficult and potentially hiding critical runtime errors.",
      "severity": "medium",
      "recommendation": "Catch specific exceptions like `except Exception as e:` and log the error, or re-raise it.",
      "category": "Code Quality",
      "reference": "https://peps.python.org/pep-0008/#programming-recommendations",
      "proof_of_concept": "try:\n    raise ValueError('Critical error')\nexcept:\n    pass"
    }
  ]
}
```

### 6.8 Full Refined JSON Output: `url`

```json
{
  "issues": [
    {
      "line": 78,
      "type": "Potential Runtime Error",
      "description": "Accessing raw[0] without checking if raw is empty will raise an IndexError when an empty byte string is passed to from_bytes.",
      "severity": "high",
      "recommendation": "Add a guard clause at the start of the method: if not raw: raise ValueError('Empty URL') or use raw.startswith(b'/') instead of direct indexing.",
      "category": "Runtime Error",
      "reference": "https://docs.python.org/3/library/stdtypes.html#common-sequence-operations",
      "proof_of_concept": "def test_index_error():\n    raw = b''\n    try:\n        _ = raw[0] == 47\n    except IndexError as e:\n        print(f'Caught IndexError: {e}')\ntest_index_error()"
    },
    {
      "line": 128,
      "type": "Potential Runtime Error",
      "description": "split_at[0].split(COLON) may return a list with only one element if no colon is present in the userinfo part, causing a ValueError during tuple unpacking into username and password.",
      "severity": "high",
      "recommendation": "Use split(COLON, 1) and check the length, or assign with a default: user_pass = split_at[0].split(COLON, 1); username = user_pass[0]; password = user_pass[1] if len(user_pass) > 1 else None.",
      "category": "Runtime Error",
      "reference": "https://docs.python.org/3/tutorial/datastructures.html#tuples-and-sequences",
      "proof_of_concept": "def test_unpack_error():\n    data = b'user'\n    try:\n        username, password = data.split(b':')\n    except ValueError as e:\n        print(f'Caught ValueError: {e}')\ntest_unpack_error()"
    },
    {
      "line": 135,
      "type": "Potential Runtime Error",
      "description": "int(parts[-1]) is called without exception handling. If the port segment contains non-numeric characters, it raises an unhandled ValueError.",
      "severity": "medium",
      "recommendation": "Wrap the conversion in a try-except block or validate that the string consists of digits before conversion.",
      "category": "Runtime Error",
      "reference": "https://docs.python.org/3/library/functions.html#int",
      "proof_of_concept": "def test_int_error():\n    port_str = b'abc'\n    try:\n        _ = int(port_str)\n    except ValueError as e:\n        print(f'Caught ValueError: {e}')\ntest_int_error()"
    },
    {
      "line": 148,
      "type": "Potential Runtime Error",
      "description": "host.decode('utf-8') assumes the host bytes are valid UTF-8. Invalid byte sequences will raise UnicodeDecodeError.",
      "severity": "medium",
      "recommendation": "Use host.decode('utf-8', errors='replace') or catch UnicodeDecodeError and handle it gracefully.",
      "category": "Runtime Error",
      "reference": "https://docs.python.org/3/library/stdtypes.html#bytes.decode",
      "proof_of_concept": "def test_decode_error():\n    invalid_bytes = b'\\xff\\xfe'\n    try:\n        _ = invalid_bytes.decode('utf-8')\n    except UnicodeDecodeError as e:\n        print(f'Caught UnicodeDecodeError: {e}')\ntest_decode_error()"
    },
    {
      "line": 51,
      "type": "Code Quality",
      "description": "Using if self.port: evaluates to False when self.port is 0, omitting the port from the string representation even though port 0 is technically valid.",
      "severity": "low",
      "recommendation": "Change the condition to if self.port is not None: to correctly handle port 0.",
      "category": "Code Quality",
      "reference": "https://peps.python.org/pep-0008/#programming-recommendations",
      "proof_of_concept": "def test_port_zero():\n    port = 0\n    url = 'example.com'\n    if port:\n        url += f':{port}'\n    print(f'Result with truthy check: {url}')\n    if port is not None:\n        url += f':{port}'\n    print(f'Result with None check: {url}')\ntest_port_zero()"
    },
    {
      "line": 78,
      "type": "Code Quality",
      "description": "The magic number 47 is used to check for a forward slash. This reduces code readability and maintainability.",
      "severity": "low",
      "recommendation": "Replace 47 with ord('/') or SLASH[0] to make the intent explicit.",
      "category": "Code Quality",
      "reference": "https://peps.python.org/pep-0008/#other-recommendations",
      "proof_of_concept": null
    }
  ]
}
```

### 6.9 Full Baseline JSON Output: `test1`

```json
{
  "issues": [
    {
      "line": 3,
      "type": "Resource Leak",
      "description": "File opened with open() is never closed. This can lead to resource exhaustion. Use a 'with' statement to ensure automatic cleanup.",
      "severity": "medium"
    },
    {
      "line": 6,
      "type": "Runtime Error",
      "description": "Built-in function 'print' is incorrectly capitalized as 'Print', which will raise a NameError at runtime.",
      "severity": "high"
    },
    {
      "line": 8,
      "type": "Security Vulnerability",
      "description": "Use of exec() is highly discouraged as it can execute arbitrary code. Even with hardcoded strings, it poses a security risk and violates safe coding practices.",
      "severity": "high"
    },
    {
      "line": 11,
      "type": "Runtime Error",
      "description": "Division by zero will unconditionally raise a ZeroDivisionError at runtime.",
      "severity": "high"
    },
    {
      "line": 12,
      "type": "Code Quality",
      "description": "Bare except clause catches all exceptions, including system-exiting ones like SystemExit and KeyboardInterrupt. Always specify the exact exception type to catch.",
      "severity": "medium"
    }
  ]
}
```

### 6.10 Full Baseline JSON Output: `test2`

```json
{
  "issues": [
    {
      "line": 6,
      "type": "code_quality",
      "description": "Mutable default argument 'hooks=[]' is evaluated once at function definition and shared across all instances, leading to unexpected state sharing and potential bugs.",
      "severity": "medium"
    },
    {
      "line": 13,
      "type": "security_vulnerability",
      "description": "Path traversal vulnerability: 'report_name' is concatenated directly without sanitization, allowing an attacker to read arbitrary files outside the intended backup_root directory.",
      "severity": "high"
    },
    {
      "line": 18,
      "type": "security_vulnerability",
      "description": "Use of 'eval()' on untrusted input allows arbitrary code execution. This is a critical security risk; use safer alternatives like ast.literal_eval or explicit function dispatch.",
      "severity": "high"
    },
    {
      "line": 23,
      "type": "security_vulnerability",
      "description": "Command injection vulnerability: 'shell=True' combined with f-string interpolation of untrusted variables ('report_text', 'shell_target') allows execution of arbitrary shell commands.",
      "severity": "high"
    },
    {
      "line": 26,
      "type": "resource_leak",
      "description": "File opened without a context manager ('with' statement). If an exception occurs during the write operation, the file handle will leak. Use 'with open(...) as f:' to ensure proper closure.",
      "severity": "medium"
    },
    {
      "line": 35,
      "type": "code_quality",
      "description": "Bare 'except:' clause catches all exceptions including SystemExit and KeyboardInterrupt, swallowing critical errors and making debugging difficult. Always specify explicit exception types.",
      "severity": "medium"
    }
  ]
}
```

### 6.11 Full Baseline JSON Output: `url`

```json
{
  "issues": [
    {
      "line": 62,
      "type": "potential runtime error",
      "description": "Accessing raw[0] without checking if raw is empty will raise an IndexError if an empty byte string is passed to from_bytes.",
      "severity": "high"
    },
    {
      "line": 110,
      "type": "potential runtime error",
      "description": "Unpacking split_at[0].split(COLON) into two variables assumes exactly one colon is present. If there are zero or multiple colons in the credentials part, a ValueError will be raised.",
      "severity": "medium"
    },
    {
      "line": 119,
      "type": "potential runtime error",
      "description": "Calling int(parts[-1]) without a try-except block will raise a ValueError if the port segment contains non-numeric characters.",
      "severity": "medium"
    },
    {
      "line": 132,
      "type": "potential runtime error",
      "description": "Decoding host bytes to UTF-8 without error handling may raise a UnicodeDecodeError if the host contains invalid UTF-8 sequences.",
      "severity": "medium"
    },
    {
      "line": 134,
      "type": "potential runtime error",
      "description": "Accessing rhost[0] and rhost[-1] without checking if rhost is non-empty will raise an IndexError if the decoded host string is empty.",
      "severity": "low"
    },
    {
      "line": 133,
      "type": "code quality issue",
      "description": "COLON.decode('utf-8') is called repeatedly inside a conditional check. It is more efficient to decode it once or use a string literal ':'.",
      "severity": "low"
    }
  ]
}
```

### 6.12 Full Generated PoCs Used in Validation: `test1.py`

```python
# poc_issue_1.py
def test():
    Print('This will raise a NameError')
test()
```

```python
# poc_issue_2.py
import os
f = open('test_leak.txt', 'w')
f.write('data')
# File descriptor remains open until garbage collection or program exit
```

```python
# poc_issue_3.py
user_input = "__import__('os').system('echo compromised')"
exec(user_input)
```

```python
# poc_issue_4.py
result = 10 / 0
```

```python
# poc_issue_5.py
try:
    raise KeyboardInterrupt('User interrupted')
except:
    pass # Silently swallows KeyboardInterrupt
```

### 6.13 Full Generated PoCs Used in Validation: `test2.py`

```python
# poc_issue_1.py
class Test:
    def __init__(self, items=[]):
        self.items = items
a = Test()
b = Test()
a.items.append(1)
print(b.items)
```

```python
# poc_issue_2.py
from pathlib import Path
import os
os.makedirs('safe_dir', exist_ok=True)
with open('safe_dir/secret.txt', 'w') as f: f.write('secret')
root = 'safe_dir'
malicious = '../secret.txt'
path = Path(root) / malicious
print(path.read_text())
```

```python
# poc_issue_3.py
hook_code = '__import__("os").system("echo pwned")'
result = eval(hook_code)
print(result)
```

```python
# poc_issue_4.py
import subprocess
report_text = 'test; echo INJECTED'
shell_target = 'out.txt'
subprocess.run(f'echo {report_text} > {shell_target}', shell=True, check=True)
```

```python
# poc_issue_5.py
import os
f = open('leak_test.txt', 'w')
f.write('data')
print(os.path.exists('leak_test.txt'))
f.close()
os.remove('leak_test.txt')
```

```python
# poc_issue_6.py
try:
    raise ValueError('Critical error')
except:
    pass
```

