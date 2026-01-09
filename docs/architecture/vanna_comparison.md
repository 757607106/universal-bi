# Vanna 逻辑框架对比分析报告

**日期**: 2026-01-10  
**版本**: Universal BI v1.0

## 1. 核心结论
**"形似而神不似，逻辑一致但架构不同。"**

当前项目的实现逻辑与 Vanna 官方推荐的**核心训练策略（RAG 思想）**高度一致，但在**代码架构**上使用的是 Vanna 0.x (Legacy) 的模式，而非最新的 Vanna 2.0 Agent 架构。

这一架构选择在当前阶段是合理的，因为它提供了更强的直接控制力和稳定性，且完全能够满足 Text-to-SQL 的核心需求。

---

## 2. 架构层面的差距 (Architecture Gap)
**差距评估：较大 (Architectural Shift)**

| 维度 | 官方 Vanna 2.0+ (Agent) | 当前项目 (Legacy Wrapper) |
| :--- | :--- | :--- |
| **核心对象** | `VannaAgent` (Stateful, Tools-based) | `VannaLegacyPGVector` (继承自 `VannaBase`) |
| **上下文管理** | **User-Aware**: 原生支持用户隔离和权限上下文，Request 级隔离 | **Instance-Based**: 通过 `VannaInstanceManager` 为每个 dataset_id 创建独立单例来实现隔离 |
| **工具调用** | **Tools System**: 注册式工具 (SQL, Python, API)，LLM 自主决定调用 | **Method Call**: 代码显式调用 `vn.generate_sql()`, `vn.train()` 等方法 |
| **输出模式** | **Dual-Output**: 同时返回 LLM 友好的数据和前端友好的 UI 组件 | **Service Layer**: 后端处理数据后返回 JSON，前端负责渲染 |

**评价**：
当前项目实际上是**用 Vanna 0.x 的核心能力构建了一套自己的 Service 层**。虽然没有使用 Vanna 2.0 的 Agent 框架，但通过 `dataset_id` 隔离实例的方式，已经实现了类似的多租户隔离效果。

---

## 3. 训练流程的差距 (Training Flow Gap)
**差距评估：极小（且当前项目在工程化上更优）**

官方推荐的训练“三板斧”是：**DDL (表结构)** + **Documentation (文档)** + **SQL (问答对)**。当前项目不仅完整实现了这一流程，还增加了**前置增强步骤**。

### 详细流程对比

#### A. DDL 训练 (Schema)
*   ✅ **一致性**: 都通过 `vn.train(ddl=...)` 注入表结构。
*   🚀 **项目增强**: 
    *   实现了 `DuckDB` (本地文件) 和 `SQLAlchemy` (远程库) 双引擎支持。
    *   `DBInspector` 自动提取 DDL，无需人工干预。

#### B. 文档训练 (Documentation)
*   ✅ **一致性**: 都通过 `vn.train(documentation=...)` 注入业务知识。
*   🚀 **项目增强**:
    *   **自动关系分析 (`RelationshipAnalyzer`)**: 在训练前自动分析表外键和数据重合度，生成高质量的“表关系描述文档”喂给 LLM。这是官方 Quick Start 中没有的高级特性。
    *   **业务术语库**: 独立的 `BusinessTerm` 模块，管理特定术语并自动同步训练。

#### C. SQL 问答对训练 (QA Pairs)
*   ✅ **一致性**: 都通过 `vn.train(question=..., sql=...)` 注入 Golden SQL。
*   🚀 **项目增强**:
    *   **冷启动优化**: 在训练阶段自动为核心表生成 `SELECT *`, `COUNT`, `GROUP BY` 等基础 SQL 对，让模型“未问先知”。
    *   **反馈闭环**: 实现了 QA 训练接口，支持将用户修正后的 SQL 回流训练。

---

## 4. 建议与规划

### A. 现状评估
目前基于 `VannaService` + `PGVector` 的架构非常成熟且稳定。
*   **优势**: 对 Prompt、上下文组装、SQL 执行过程有完全的控制权（如 `sql_generator.py` 中的中间推理和重试逻辑）。
*   **劣势**: 无法直接享受 Vanna 2.0 生态中的非 SQL 工具（如 Python 代码沙箱、API 调用工具）。

### B. 演进建议
**不需要立即重构到 Vanna 2.0**，除非业务场景扩展到“非数据库查询”领域（如执行 Python 脚本绘图）。

**推荐的微调方向**:
1.  **Prompt 模板化**: 目前 Prompt 可能硬编码在 `base.py` 或 `sql_generator.py` 中，建议抽离为独立的 Prompt 模板文件，便于 A/B 测试不同模型（Qwen vs GPT-4）。
2.  **思维链增强 (CoT)**: 借鉴 Vanna 2.0 的思想，在 `SqlGenerator` 中显式增加一步“生成中间推理步骤”，强制 LLM 在生成 SQL 前先输出分析逻辑，可显著提高复杂查询准确率。
