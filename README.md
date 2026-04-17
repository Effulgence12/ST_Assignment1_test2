# LLM 静态代码分析工具

## 项目结构

```text
.
├─ target/                  # 待分析脚本目录
│  ├─ test1.py              # 基础示例
│  └─ test2.py              # 更复杂的示例
├─ reported_alarms/         # 按时间编号归档的分析结果
│  └─ poc_cases/            # 每次分析对应的 PoC 脚本目录
├─ llm_client.py            # 大模型调用与提示词封装
├─ main.py                  # 主程序入口
├─ requirements.txt         # 依赖列表
└─ .env / .env.example      # Qwen API 配置
```

## 环境准备

python 3.10

```powershell
pip install -r requirements.txt
```

复制`.env.example` 重命名为 `.env` 后，正确配置 apikey
`REQUEST_TIMEOUT_SECONDS` 建议设置为 `180`，复杂脚本分析时更稳。

## 使用方法

### 1. 分析默认脚本 `target/test1.py`

```powershell
conda run -n st-a1 python main.py
```

### 2. 指定待分析脚本

将需要分析的脚本复制到`traget/`
在运行 main 时提供--input 参数即可

```powershell
python main.py --input target/<文件名>.py
```

```powershell
conda run -n st-a1 python main.py --input target/<文件名>.py
```

## 输出结果

每次运行都会生成两类结果：

- `reported_alarms/analysis_report_<脚本名>_<时间戳>.json` json 格式分析报告
- `reported_alarms/poc_cases/<脚本名>_<时间戳>/poc_issue_<序号>.py` Poc 缺陷复现脚本

## 后续任务

(请对照 `report.md`以及作业要求`Assignment1.pdf` )

**A：负责报告第 4 章 (Experimental Analysis)**

- **任务：** 运行当前的 Python 脚本，完成实验数据的收集分析。
- **具体工作项：**
  1. 准备多组含有各类潜在错误的 Python 目标代码(复制进 target 然后测试)以测试工具的泛化能力（对应 4.3）。
  2. 执行多次代码扫描，人工比对 JSON 结果，统计误报率并记录典型误报案例（对应 4.1）。
  3. 运行自动生成的 PoC 脚本，验证漏洞是否成功复现（对应 4.4）。
  4. 记录修改 Prompt 前后的扫描数据差异，证明提示词优化的有效性（对应 4.2）。

**B：负责报告第 5 章 (Project Report)**

- **任务：** 运行脚本并分析，撰写与传统工具的对比分析与技术局限性总结。
- **具体工作项：**
  1. 搜集一些 Pylint(AI 推荐) (或其他静态代码分析工具) 的运行机制与典型报错案例，然后用脚本跑，对比结果。
  2. 将同一段目标代码分别交由静态工具检测和我们的大模型脚本进行分析，对比两者的错误识别类型、上下文理解能力及配置复杂度。
  3. 提炼并撰写基于大模型的静态分析工具的优缺点，完成报告第五章的理论论述。

**C：负责报告前置章节 (Section 1-3)、全篇整合与 PPT 制作**

- **任务：** 项目文档交付物组装与演示材料制作。
- **具体工作项：**
  1. 根据当前脚本，完成报告 1-3 节()。
  2. 汇总组员 A 和 B 的章节，统一全篇英文专业术语与排版格式。
  3. 提取全篇核心结论，制作 15 演示 PPT。
