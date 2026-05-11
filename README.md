# File Agent Flowchart Generator

## 1. Project Overview

File Agent Flowchart Generator is a local Agent-style tool that converts natural-language process descriptions into structured flowchart data and Mermaid flowcharts.

The project started as a simple natural-language-to-Mermaid generator and has evolved into a multi-stage Agent pipeline. It can process user input, extract key concepts, decompose workflow structure, route the flow type, generate structured flowchart data, repair common structural errors, validate the result, and output Mermaid diagrams.

The current project focuses on **process flowchart generation**, including:

- Linear workflows
- Branch workflows
- Multi-step workflows
- Workflow descriptions with decisions, retries, returns, and validations

The project does **not** aim to generate hardware topology diagrams, system architecture diagrams, or complex technical infographics.

---

## 2. Current Scope

### Supported

The current version supports:

- Natural-language process descriptions
- Direct terminal input
- `.txt` and `.md` document input
- Linear process flow generation
- Branch process flow generation
- Multi-flow segmentation
- Research Agent concept extraction
- Decomposition Agent workflow decomposition
- Router-based flow type detection
- Mermaid flowchart generation
- SVG output generation
- Code-level repair for known Agent pipeline flow issues
- Built-in regression testing module

### Not Supported

The current version does not focus on:

- Hardware topology diagrams
- Module connection diagrams
- System architecture diagrams
- Power / communication / control network diagrams
- Complex visual infographics requiring precise layout control

For these inputs, the system may not generate meaningful process flowcharts.

---

## 3. Current Pipeline

The current pipeline is:

```text
User Input / Document Input
        ↓
Input Reader
        ↓
Flow Segmenter
        ↓
Research Agent
        ↓
Decomposition Agent
        ↓
Router
   ↓              ↓
Linear Flow       Branch Flow
Extractor         Extractor
        ↓
Repair / Validation
        ↓
Mermaid Generator
        ↓
Mermaid / SVG Output
```

---

## 4. Main Components

### 4.1 Input Reader

Handles input from:

- Manual terminal input
- `.txt` files
- `.md` files

### 4.2 Flow Segmenter

Detects whether the input contains one workflow or multiple workflow segments.

If multiple segments are detected, the system processes them one by one.

### 4.3 Research Agent

Extracts key concepts from the input, such as:

- Inputs
- Processes
- Modules
- Decisions
- Outputs

The Research Agent provides structured context for later stages.

### 4.4 Decomposition Agent

Decomposes the workflow into:

- Modules
- Decisions
- Flows
- Dependencies

The Decomposition Agent helps the Router and later repair logic better understand the workflow structure.

### 4.5 Router

The Router determines whether the workflow should be handled as:

- `linear`
- `branch`

The current Router uses:

- Original user input
- Decomposition Agent flow conditions
- Agent context where necessary

The Router is intentionally conservative to avoid incorrectly treating simple linear workflows as branch workflows.

### 4.6 Linear Flow Extractor

Handles simple linear workflows and converts them into structured flowchart data.

### 4.7 Branch Flow Extractor

Handles workflows with decisions, conditions, retries, returns, success/failure paths, and approval-style branches.

### 4.8 Repair Modules

The system includes code-level repair functions to fix known structural issues after flow extraction.

Current repair logic includes:

- Loop / return edge repair
- Agent pipeline edge repair
- Repair for missing Mermaid generation step in Agent pipeline flows
- Repair for broken links between extractor nodes and Mermaid rendering checks

### 4.9 Validator

The validator checks whether branch flow structures contain serious structural problems, such as:

- Isolated nodes
- Decision nodes with insufficient exits
- Invalid edge references
- Broken main flow structure

Warnings may still appear for natural terminal nodes such as:

- Unsupported-flow messages
- Save-output nodes

These warnings are not always fatal.

---

## 5. Folder Structure

Current project structure is similar to:

```text
file_agent/
│
├── agents/
│   ├── research_agent.py
│   └── decomposition_agent.py
│
├── builders/
│   └── flowchart_builder.py
│
├── ingest/
│   ├── document_loader.py
│   └── input_reader.py
│
├── models/
│   ├── branch_flow_spec.py
│   ├── concept_spec.py
│   ├── decomposition_spec.py
│   └── flow_segment_spec.py
│
├── processors/
│   ├── flow_segmenter.py
│   ├── linear_rule_extractor.py
│   └── role_normalizer.py
│
├── prompts/
│   ├── flowchart/
│   │   └── branch_flow.md
│   ├── research/
│   │   └── extract_concepts.md
│   └── decomposition/
│       └── decompose.md
│
├── routers/
│   └── flow_router.py
│
├── tests/
│   ├── builtin_cases.py
│   ├── assertions.py
│   ├── regression_runner.py
│   └── __init__.py
│
├── utils/
│   ├── prompt_loader.py
│   ├── loop_repairs.py
│   └── agent_pipeline_repairs.py
│
├── validators/
│   └── branch_validator.py
│
├── branch_flow_extractor.py
├── main.py
└── README.md
```

---

## 6. How to Run

Run the main program:

```bash
python main.py
```

The program supports different input modes.

Example menu:

```text
请选择输入方式：
1. 手动输入流程描述
2. 从 .txt / .md 文档读取
```

If the built-in self-test module is connected to `main.py`, the menu may also include:

```text
3. 运行内置回归测试
```

---

## 7. Manual Input Example

Example input:

```text
用户上传文件。
系统检查文件格式是否支持。
如果文件格式支持，则调用文件解析模块。
如果文件格式不支持，则提示用户重新上传文件。
文件解析完成后，系统输出解析结果。
流程结束。
END
```

Expected flow type:

```text
branch
```

Expected main structure:

```text
用户上传文件
↓
文件格式是否支持？
├─ 支持 → 调用文件解析模块 → 输出解析结果
└─ 不支持 → 提示用户重新上传文件 → 返回上传步骤
```

---

## 8. File Input Mode

You can also provide a `.txt` or `.md` file containing workflow descriptions.

Example:

```text
tests/test_cases/mixed_regression_test.txt
```

Then choose option `2` in the terminal and enter the file path.

---

## 9. Built-in Regression Testing

The project includes a built-in regression testing module.

Current testing files:

```text
tests/builtin_cases.py
tests/assertions.py
tests/regression_runner.py
```

### 9.1 `builtin_cases.py`

Defines built-in test cases, including:

- Chinese linear workflow
- Chinese simple branch workflow
- Chinese branch workflow with return edges
- English simple branch workflow
- English login branch workflow
- Agent pipeline workflow

Each test case can define:

```text
name
input_text
expected_flow_type
must_have_node_texts
must_have_edge_labels
must_have_edges
```

### 9.2 `assertions.py`

Provides assertion functions to check:

- Required node texts
- Required edge labels
- Required source-target edges

The assertions use relaxed text matching to reduce false failures caused by minor wording differences.

### 9.3 `regression_runner.py`

Runs the built-in test cases through the current Agent pipeline.

It checks:

- Whether Router output matches expected flow type
- Whether serious branch validation errors occur
- Whether required nodes, edge labels, and edges exist

Run the self-test module with:

```bash
python -m tests.regression_runner
```

Expected output format:

```text
======================================================================
开始运行内置回归测试
======================================================================

[1/6] TEST1 中文线性流程：订单提交
PASS

[2/6] TEST2 中文简单分支流程：文件上传
PASS

...

======================================================================
内置回归测试完成
通过: 6/6
失败: 0/6
======================================================================
```

---

## 10. Current Regression Test Status

The built-in regression test module currently passes all 6 test cases.

Current result:

```text
Passed: 6/6
Failed: 0/6
Status: PASS_WITH_WARNING
```

The remaining warning is caused by a terminal unsupported-flow node:

```text
节点 O（提示暂不支持该流程类型）没有出边，可能提前中断
```

This warning is currently acceptable because the unsupported-flow message can naturally act as a terminal branch. It does not indicate a serious structural failure.

Current test coverage:

| Test | Purpose | Expected Router Result | Current Status |
|---|---|---|---|
| TEST1 | Chinese linear order workflow | linear | PASS |
| TEST2 | Chinese file upload branch workflow | branch | PASS |
| TEST3 | Chinese login workflow with return edges | branch | PASS |
| TEST4 | English simple file upload branch workflow | branch | PASS |
| TEST5 | English simple login branch workflow | branch | PASS |
| TEST6 | Agent pipeline workflow | branch | PASS_WITH_WARNING |

English tests currently focus mainly on whether English branch input can be recognized as branch.

The current system may translate English input into Chinese nodes during flowchart generation. Therefore, English output language preservation is not yet guaranteed.

---

## 11. Current Limitations

The current version still has several limitations:

1. English input can be understood to some extent, but output may be translated into Chinese.
2. Complex branch workflows may still require repair after extraction.
3. Mermaid layout may become visually messy for complex graphs with many return edges.
4. Some terminal nodes may trigger validator warnings even when they are acceptable endpoints.
5. Prompt rules are functional but still verbose.
6. The system is designed for process flowcharts, not system topology diagrams.
7. Built-in regression tests are now integrated, but the test cases should continue to expand gradually.

---

## 12. Development Workflow

Recommended workflow:

```bash
git checkout main
git pull origin main
git checkout -b feature-new-task
```

After making changes:

```bash
git status
git diff
```

Run syntax checks:

```bash
python -m py_compile main.py
python -m py_compile routers/flow_router.py
python -m py_compile utils/agent_pipeline_repairs.py
python -m py_compile tests/builtin_cases.py
python -m py_compile tests/assertions.py
python -m py_compile tests/regression_runner.py
```

Run built-in regression tests:

```bash
python -m tests.regression_runner
```

Then commit only the intended files:

```bash
git add main.py routers/flow_router.py utils/agent_pipeline_repairs.py tests/builtin_cases.py tests/assertions.py tests/regression_runner.py
git commit -m "your commit message"
```

Avoid using:

```bash
git add .
```

unless you are sure no generated files are included.

---

## 13. Generated Files

The system may generate files under:

```text
artifacts/
diagrams/
```

These are runtime outputs and should usually not be committed.

Recommended `.gitignore` entries:

```gitignore
artifacts/
diagrams/
__pycache__/
*.pyc
```

If these folders have already been tracked by Git, remove them from Git tracking while keeping local files:

```bash
git rm -r --cached artifacts diagrams
```

Then commit the `.gitignore` update.

---

## 14. Git Commands

View current status:

```bash
git status
```

View recent commits:

```bash
git log --oneline -5
```

View staged files:

```bash
git diff --staged --name-only
```

Unstage files:

```bash
git restore --staged <file_or_folder>
```

Restore generated runtime outputs:

```bash
git restore artifacts/
git restore diagrams/
```

Clean untracked files after previewing:

```bash
git clean -fdn
git clean -fd
```

---

## 15. Recommended Next Improvements

Recommended future improvements:

1. Refine validator rules to allow valid terminal nodes without warnings.
2. Add `main.py` option for running built-in tests directly.
3. Add stricter semantic validation for branch flows.
4. Add a start/end cleanup repair module.
5. Improve English input support and output language consistency.
6. Refactor Prompt rules only after regression tests remain stable.
7. Add more regression cases for approval workflows, retry workflows, and multi-flow inputs.

---

## 16. Project Status


```text
Core pipeline: working
Research Agent: integrated
Decomposition Agent: integrated
Router: uses Agent context
Branch repair: integrated
Agent pipeline repair: working for TEST6-style flows
Built-in regression tests: integrated and passing 6/6
Topology generation: out of scope
```

Current regression result:

```text
Passed: 6/6
Failed: 0/6
Remaining warning: unsupported-flow terminal node has no outgoing edge
```

This warning is acceptable at the current stage because unsupported-flow messages can act as natural terminal nodes.

The current development focus is:

```text
Stabilize regression testing
Reduce Router misclassification
Improve repair and validation reliability
Avoid Prompt over-expansion
Expand test coverage gradually
```
## CLI User Experience

The current CLI supports:
- Manual workflow input
- `.txt` / `.md` file input
- Built-in regression testing
- Return-to-menu behavior
- Friendly file path and file type validation
- Final output summary after generation