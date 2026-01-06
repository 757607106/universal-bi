# VannaManager 多轮推理增强功能文档

## 概述

本次增强为 `VannaManager.generate_result()` 方法添加了**多轮推理**和**中间 SQL 处理**能力，使系统能够智能处理模糊问题并进行自我反思。

## 核心功能

### 1. 中间 SQL 自动检测与执行 (Auto-Reflection)

当 AI 不确定某些列值时，会返回一个中间查询来探索数据：

**场景示例：**
```
用户问题："查询大客户数量"
第一轮 AI 响应："我不确定'大客户'的定义，让我先查询有哪些客户类型：
SELECT DISTINCT type FROM users;"
```

**系统行为：**
1. 检测到中间 SQL：`SELECT DISTINCT type FROM users`
2. 自动执行该查询，获取结果：`['VIP', 'Normal', 'Enterprise']`
3. 将结果反馈给 AI，进行第二轮生成
4. AI 基于实际数据生成最终 SQL：`SELECT COUNT(*) FROM users WHERE type = 'VIP'`

### 2. 澄清对话处理

当问题过于模糊且 AI 无法推断时，系统会返回澄清请求：

**场景示例：**
```
用户问题："统计订单"
AI 响应："我无法确定您想统计什么，是订单总数、金额还是按月分组？"
```

**返回格式：**
```python
{
    "sql": None,
    "data": None,
    "chart_type": "clarification",  # 新类型
    "answer_text": "AI 的澄清问题",
    "steps": ["解析问题", "检测到歧义", "请求澄清"]
}
```

### 3. 自愈机制集成

新增功能与现有的 SQL 自愈机制完全兼容：

**执行优先级：**
1. 第一轮：生成初始 SQL
2. 检测中间 SQL → 执行 → 第二轮生成
3. 检测澄清需求 → 返回澄清请求
4. 执行最终 SQL → 失败时进入自愈流程（最多 3 次尝试）

## 技术实现

### 新增辅助方法

#### `_extract_intermediate_sql(response: str) -> str`

**功能：** 从 LLM 响应中提取中间 SQL

**检测模式：**

1. **显式标记模式**
   - 关键词：`intermediate_sql`, `intermediate sql`
   - 示例：
     ```
     intermediate_sql:
     SELECT DISTINCT type FROM users;
     ```

2. **隐式模式**
   - 包含不确定关键词：不确定、不知道、unclear、uncertain
   - 同时包含 DISTINCT 查询（常见的探索性查询）
   - 示例：
     ```
     我不确定大客户的定义。让我先查询：
     SELECT DISTINCT type FROM customers;
     ```

**返回值：**
- 如果检测到中间 SQL → 返回清洗后的 SQL 字符串
- 否则 → 返回空字符串

---

#### `_is_clarification_request(response: str) -> bool`

**功能：** 判断 LLM 响应是否为澄清请求

**检测条件：**
- 包含澄清关键词（中英文支持）：
  - 中文：无法确定、不确定、请明确、请问、是指、没有找到
  - 英文：cannot determine, unclear, please clarify, not found
- 不包含完整的 SQL 查询，或 SQL 过短（< 50 字符）

**返回值：**
- `True`：响应是澄清请求
- `False`：响应包含有效 SQL

## 执行流程

```
┌─────────────────────────────────────────────────────────────────┐
│ 1. 用户提问："查询大客户数量"                                   │
└─────────────────────┬───────────────────────────────────────────┘
                      │
                      ▼
┌─────────────────────────────────────────────────────────────────┐
│ 2. 第一轮生成 (vn.generate_sql)                                 │
│    响应：包含中间 SQL 或澄清请求                                │
└─────────────────────┬───────────────────────────────────────────┘
                      │
                      ▼
            ┌─────────┴─────────┐
            │                   │
            ▼                   ▼
┌───────────────────┐   ┌─────────────────┐
│ 检测中间 SQL      │   │ 检测澄清请求     │
│ (_extract_...)    │   │ (_is_clarifi...) │
└────────┬──────────┘   └────────┬─────────┘
         │                       │
         ▼                       ▼
┌───────────────────┐   ┌─────────────────┐
│ 3. 执行中间查询    │   │ 4. 返回澄清对话  │
│ pd.read_sql()     │   │ chart_type=     │
│                   │   │ "clarification" │
└────────┬──────────┘   └─────────────────┘
         │
         ▼
┌───────────────────────────────────────────┐
│ 5. 第二轮生成                              │
│ Prompt: "原始问题 + 中间结果值"            │
│ 响应：SELECT ... WHERE type = 'VIP'       │
└────────┬──────────────────────────────────┘
         │
         ▼
┌───────────────────────────────────────────┐
│ 6. 执行最终 SQL (带自愈)                   │
│ - 尝试 1：执行 SQL                         │
│ - 失败？→ AI 修正 → 尝试 2                 │
│ - 失败？→ AI 再修正 → 尝试 3               │
└────────┬──────────────────────────────────┘
         │
         ▼
┌───────────────────────────────────────────┐
│ 7. 返回结果                                │
│ - sql, rows, columns                      │
│ - chart_type (table/bar/line)             │
│ - steps (执行步骤追踪)                     │
└───────────────────────────────────────────┘
```

## 使用示例

### 示例 1：自动处理中间 SQL

```python
# 用户提问
question = "查询大客户数量"

# 系统执行
result = await VannaManager.generate_result(
    dataset_id=1,
    question=question,
    db_session=session
)

# 执行步骤追踪
result["steps"] = [
    "第一轮：生成初始 SQL 响应",
    "检测到中间 SQL，启动多轮推理",
    "执行中间 SQL 成功，获取 3 行结果",
    "中间结果包含值: ['VIP', 'Normal', 'Enterprise']",
    "第二轮：基于中间结果生成最终 SQL",
    "SQL 执行成功 (尝试 1/3)"
]

# 最终结果
result["sql"] = "SELECT COUNT(*) FROM users WHERE type = 'VIP'"
result["rows"] = [{"count": 42}]
```

### 示例 2：澄清对话

```python
# 用户提问（过于模糊）
question = "统计订单"

# 系统返回
result = {
    "sql": None,
    "data": None,
    "chart_type": "clarification",
    "answer_text": "我无法确定您想统计什么，是订单总数、订单金额还是按月分组的订单统计？",
    "steps": ["第一轮：生成初始 SQL 响应", "AI 请求用户澄清问题"]
}
```

### 示例 3：SQL 自愈

```python
# 第一轮生成的 SQL 有语法错误
current_sql = "SELECT * FORM users"  # FORM 拼写错误

# 执行失败后，系统自动修正
result["steps"] = [
    "SQL 执行失败 (尝试 1): near 'FORM': syntax error",
    "尝试 AI 自动修复 SQL",
    "AI 已修正 SQL (尝试 2)",
    "SQL 执行成功 (尝试 2/3)"
]

# 修正后的 SQL
corrected_sql = "SELECT * FROM users"
```

## 配置参数

在 `generate_result` 方法中：

```python
max_retries = 2  # SQL 自愈最大重试次数（总共 3 次尝试）
```

## 前端集成建议

### 处理澄清对话

在前端 Chat 组件中添加对 `clarification` 类型的处理：

```typescript
// frontend/src/components/ChatBI.vue

if (response.chart_type === 'clarification') {
  // 显示 AI 的澄清问题
  messages.value.push({
    role: 'assistant',
    content: response.answer_text,
    type: 'clarification'
  });
  
  // 提示用户补充信息
  // 或者提供快捷选项（如果能从 answer_text 中解析）
}
```

### 显示执行步骤

```vue
<template>
  <div v-if="showSteps" class="execution-steps">
    <h4>执行步骤：</h4>
    <ul>
      <li v-for="(step, i) in result.steps" :key="i">
        {{ step }}
      </li>
    </ul>
  </div>
</template>
```

## 日志与调试

系统会在以下关键点记录日志：

```python
# 第一轮生成
logger.info(f"First round LLM response: {llm_response}")

# 检测到中间 SQL
logger.info(f"Detected intermediate SQL: {intermediate_sql}")

# 中间查询结果
logger.info(f"Intermediate SQL returned values: {values_list}")

# 第二轮生成
logger.info(f"Second round generated SQL: {current_sql}")

# 澄清请求
logger.info(f"Clarification needed: {llm_response}")
```

查看日志：
```bash
cd backend
uvicorn app.main:app --reload --log-level info
```

## 性能考虑

### 时间复杂度
- **无中间 SQL**：1 次 LLM 调用 + 1 次 SQL 执行（原有流程）
- **有中间 SQL**：2 次 LLM 调用 + 2 次 SQL 执行
- **自愈模式**：最多额外 2 次 LLM 调用（修正）

### 优化建议
1. 为中间查询设置超时（避免慢查询）
2. 缓存常见的中间查询结果（如 `DISTINCT type`）
3. 限制中间查询返回的行数（避免过大结果集）

## 测试验证

运行单元测试：
```bash
cd backend
python3 test_multi_round.py
```

测试覆盖：
- ✅ 中间 SQL 提取（显式 & 隐式模式）
- ✅ 澄清请求识别
- ✅ SQL 清洗
- ✅ 完整工作流程

## 常见问题

### Q1: 中间 SQL 执行失败怎么办？

**A**: 系统会捕获异常并回退到原始响应：
```python
except Exception as e:
    logger.warning(f"Intermediate SQL execution failed: {e}")
    execution_steps.append(f"中间 SQL 执行失败: {str(e)}")
    # 回退：使用原始响应作为最终 SQL
    current_sql = VannaManager._clean_sql(llm_response)
```

### Q2: 如何调整中间 SQL 检测的敏感度？

**A**: 修改 `_extract_intermediate_sql` 中的关键词列表：
```python
uncertainty_keywords = [
    '不确定', '不知道', 'uncertain', 'unclear',
    '是指', '是不是', '可能', 'might be', 'could be',
    '需要澄清'  # 添加更多关键词
]
```

### Q3: 多轮推理会影响响应速度吗？

**A**: 是的，但影响可控：
- 无中间 SQL：响应时间不变
- 有中间 SQL：增加约 1-2 秒（1 次额外 LLM 调用 + 1 次简单 SQL）
- 前端可显示 "正在深入思考..." 的加载提示

## 未来增强

### 计划中的功能
1. **多次中间查询**：支持 3 轮以上的推理
2. **智能缓存**：缓存中间查询结果，避免重复执行
3. **上下文学习**：从历史澄清对话中学习用户偏好
4. **主动推荐**：基于中间结果，主动推荐可能的查询方向

## 相关文件

- 核心实现：[backend/app/services/vanna_manager.py](file:///Users/pusonglin/PycharmProjects/universal-bi/backend/app/services/vanna_manager.py)
- 单元测试：[backend/test_multi_round.py](file:///Users/pusonglin/PycharmProjects/universal-bi/backend/test_multi_round.py)
- API 端点：[backend/app/api/v1/endpoints/chat.py](file:///Users/pusonglin/PycharmProjects/universal-bi/backend/app/api/v1/endpoints/chat.py)

## 总结

多轮推理功能使 Universal-BI 具备了"三思而后行"的能力：
1. **先探索**：通过中间 SQL 了解数据结构
2. **再推理**：基于实际数据生成精确查询
3. **善沟通**：遇到歧义时主动请求澄清
4. **会自愈**：执行失败时自动修正

这大大提升了系统处理模糊问题的能力，减少了用户需要明确指定查询条件的负担。
