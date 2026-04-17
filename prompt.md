You are an expert Python Software Engineer. Your task is to build an automated LLM-based Static Code Analysis tool using the Qwen API.

I need a complete, runnable Python project that reads a target source code file, sends it to the Qwen LLM with a specific prompt, parses the returned structured JSON report, and saves the analysis results locally.

Please generate the complete codebase with the following file structure and specifications:

### 1. File Structure Requirement

Create the following files in the workspace:

1. `target_code.py` (The buggy source code to be analyzed)
2. `llm_client.py` (Handles Qwen API communication and prompt construction)
3. `main.py` (The main orchestrator that coordinates the reading, API calling, parsing, and saving)
4. `requirements.txt` (Dependencies: openai)

### 2. Specific Implementation Details

#### File: target_code.py

Write the following buggy Python function into this file. It contains typical static flaws (resource leaks, undefined variables, security issues, and bare exceptions) which the LLM must detect:

```python
def process_data(filename, data):
    # Issue 1: Resource management leak (file not closed)
    f = open(filename, 'w')
    f.write(data)

    # Issue 2: Undefined variable / typo
    Print("Data written successfully")

    # Issue 3: Security vulnerability
    exec("print('Executing dynamic code')")

    # Issue 4: Potential runtime error and bad practice
    try:
        result = 10 / 0
    except:
        pass

    return True
```
#### File: llm_client.py
Implement a class StaticAnalyzerLLM.

- It must use the openai Python package to call the Qwen API. Assume a generic OpenAI-compatible endpoint. Fetch QWEN_API_KEY and QWEN_BASE_URL from environment variables.

- Prompt Engineering Requirement: The system prompt must instruct the LLM to act as a Static Code Analyzer. It must detect: 1. Syntax errors 2. Security vulnerabilities 3. Potential runtime errors 4. Code quality issues.

- Strict Output Format Constraint: The LLM's output must be strictly constrained to the following JSON structure. It must NOT output any markdown blocks outside this JSON.

```json
{
  "issues": [
    {
      "line": <line_number>,
      "type": "<issue_type>",
      "description": "<detailed description>",
      "severity": "<low/medium/high>",
      "recommendation": "<how to fix>"
    }
  ],
  "proof_of_concept": "<code>"
}
```
Note: proof_of_concept should contain a short Python script demonstrating how one of the severe vulnerabilities (e.g., the resource leak or exec) could be exploited or cause a failure.

#### File: main.py
Implement the complete pipeline:

Read the content of target_code.py.

Initialize StaticAnalyzerLLM and pass the source code to it.

Call the analysis method. Ensure robust error handling (e.g., JSON decoding errors if the LLM output is malformed).

Save the parsed JSON response locally to a file named analysis_report.json.

Print a clear, formatted summary of the discovered issues to the console.

### 3. Engineering Constraints
Ensure strict typing (using the typing module) and clear docstrings for all classes and methods.

Maintain professional and academic rigor in variable naming and print statements. Do not use overly casual language.

Ensure the JSON parsing logic securely strips any accidental markdown formatting (like ````json) before calling json.loads()`.

Please output the content for all required files immediately so I can execute the pipeline.