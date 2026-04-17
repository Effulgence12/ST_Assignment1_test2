# Title: LLM-based Static Analysis

## 1. Input
**System Overview:**
[在此处简要描述被测试目标代码的背景、运行环境及核心功能。]

**Code Structure / Interfaces:**
[在此处列出被测试模块的主要函数或接口说明。可使用表格呈现。]

## 2. Tool Artifact
**LLM Used:** [例如：Qwen 3.6 Plus via Aliyun API]

**Example Prompt:**
[在此处粘贴 `llm_client.py` 中最终定稿的 system_prompt 和 user_prompt 模板]

**Code:**
[在此处提供 target_code.py 的源代码文本]

## 3. Generated Output
**Reported Alarms:**
[在此处粘贴解析后的 analysis_report.json 核心内容，展示模型发现的缺陷列表]

**Test Case (Proof of concept):**
[在此处展示针对某一高危漏洞生成的、独立可运行的 PoC 验证脚本]

## 4. Experimental Analysis
**4.1 False Alarms Analysis**
[记录并分析模型输出中的误报（把正确代码判错）与漏报情况。]

**4.2 Refining Prompts for improving accuracy**
[对比记录：初始 Prompt 的分析结果 vs 加入特定约束后的 Prompt 分析结果，展示准确率的提升过程。]

**4.3 Try more projects to improve generalizability**
[展示使用同一套工具分析另一段不同逻辑的 Python 代码的结果，验证工具通用性。]

**4.4 Bug Reporting and Validation by the developers**
[说明 PoC 脚本的执行结果，验证指出的 Bug 是否真实会导致程序异常。]

## 5. Project Report
**5.1 Comparison to traditional non-AI-based technique, pros and cons**
[与 Pylint 等传统静态分析工具在准确度、运行速度、规则死板程度等维度的量化及定性对比。]

**5.2 Analytical report: limitations of AI and the ways to improve the tool**
[总结 AI 产生幻觉或不稳定输出的原因，以及在工程实践中采取的规避手段。]

**5.3 Summary**
[项目整体总结。]