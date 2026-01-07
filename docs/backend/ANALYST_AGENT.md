# 分析师 Agent 功能实现文档

## 功能概述

在 ChatBI 流程中引入"分析师 Agent"功能，对查询到的数据进行自动化业务总结分析。该功能在用户提问并执行 SQL 查询后，**同步生成**业务洞察，无需额外请求。

## 核心特性

### 1. **数据压缩策略**
为避免将整个 DataFrame 发送给 LLM（造成 token 浪费和性能问题），系统采用智能数据压缩：

- **前 5 行数据**：使用 `df.head(5).to_markdown()` 生成 Markdown 表格
- **统计描述**：针对数值列使用 `df.describe().to_markdown()` 生成统计信息（均值、中位数、标准差等）
- **元信息**：列名列表和数据总量

### 2. **Prompt 设计**
采用两段式 Prompt 设计：

#### System Prompt（角色扮演）
```
你是一位资深的商业数据分析师，擅长从数据中挖掘洞察和趋势。
你的任务是基于用户的问题、SQL 查询逻辑和数据摘要，提供简洁的业务分析。

分析要求：
1. 使用 Markdown 格式输出
2. 重点关注数据趋势、异常值、关键发现
3. 用业务语言，避免技术术语
4. 篇幅控制在 150 字以内
5. 直接输出分析内容，不要添加"分析："等前缀
6. 使用中文
```

#### User Prompt（输入信息）
```
用户问题：{question}

SQL 查询逻辑：
```sql
{sql}
```

### 数据样本（前 5 行）
{数据 Markdown 表格}

### 统计描述（数值列）
{统计信息 Markdown 表格}

### 数据元信息
- 列名：col1, col2, col3
- 数据总量：100 行

请基于以上信息，提供业务洞察分析：
```

### 3. **同步集成**
- ✅ 在 `VannaManager.generate_result()` 中，SQL 执行成功后立即调用 `generate_data_insight()`
- ✅ 将生成的 insight 包含在 API 响应中，前端一次性获取所有数据
- ✅ 无需额外 HTTP 请求，减少延迟和复杂度

## 技术实现

### 后端修改

#### 1. Schema 更新 (`backend/app/schemas/chat.py`)
```python
class ChatResponse(BaseModel):
    sql: Optional[str] = None
    columns: Optional[List[str]] = None
    rows: Optional[List[Dict[str, Any]]] = None
    chart_type: str
    summary: Optional[str] = None
    answer_text: Optional[str] = None
    steps: Optional[List[str]] = None
    from_cache: Optional[bool] = False
    insight: Optional[str] = None  # 新增字段
```

#### 2. 核心服务方法 (`backend/app/services/vanna_manager.py`)

**新增方法：`generate_data_insight()`**
```python
@staticmethod
def generate_data_insight(question: str, sql: str, df: pd.DataFrame, dataset_id: int) -> str:
    """
    Generate AI-powered business insight as an analyst agent.
    Compresses data into a summary before sending to LLM to reduce token usage.
    
    Args:
        question: User's original question
        sql: SQL query that generated the data
        df: Query result DataFrame
        dataset_id: Dataset ID for Vanna instance
        
    Returns:
        str: AI-generated business insight (Markdown format, in Chinese)
    """
```

**集成到 `generate_result()`**
```python
# Execute SQL
df = pd.read_sql(cleaned_sql, engine)

# Generate Business Insight (Analyst Agent)
insight = None
if len(df) > 0:
    try:
        insight = VannaManager.generate_data_insight(
            question=question,
            sql=cleaned_sql,
            df=df,
            dataset_id=dataset_id
        )
    except Exception as insight_error:
        logger.warning(f"Failed to generate insight: {insight_error}")
        insight = None

# Return result with insight
result = {
    "sql": cleaned_sql,
    "columns": df.columns.tolist(),
    "rows": cleaned_rows,
    "chart_type": chart_type,
    "steps": execution_steps,
    "insight": insight  # 新增
}
```

#### 3. API 端点 (`backend/app/api/v1/endpoints/chat.py`)
无需修改，`ChatResponse` 自动包含 `insight` 字段。

### 前端修改

#### 1. TypeScript 接口更新 (`frontend/src/api/chat.ts`)
```typescript
export interface ChatResponse {
  answer_text?: string
  sql: string | null
  columns?: string[] | null
  rows?: any[] | null
  chart_type: string
  steps?: string[]
  from_cache?: boolean
  insight?: string  // 新增
}

export const sendChat = async (data: { dataset_id: number, question: string }) => {
  const responseData = await http.post('/chat/', data)
  return {
    // ... 其他字段
    insight: responseData.insight  // 传递 insight
  } as ChatResponse
}
```

#### 2. Message 接口更新 (`frontend/src/views/Chat/index.vue`)
```typescript
interface Message {
  // ... 其他字段
  insight?: string  // 分析师 Agent 的业务洞察
}
```

#### 3. UI 显示更新
**移除异步加载逻辑**，直接显示同步返回的 `insight`：

```vue
<!-- AI Insight Section (分析师 Agent) -->
<div v-if="msg.insight" class="bg-gradient-to-r from-blue-50/50 to-cyan-50/50 rounded-xl p-4">
  <div class="flex items-center gap-2 text-blue-600 mb-2">
    <el-icon class="text-lg"><DataAnalysis /></el-icon>
    <span class="text-xs font-semibold uppercase">智能分析</span>
  </div>
  <div class="text-sm text-gray-700 leading-relaxed whitespace-pre-wrap">
    {{ msg.insight }}
  </div>
</div>
```

## 使用示例

### 用户交互流程

1. **用户提问**：
   ```
   "统计本年度每月的销售额趋势"
   ```

2. **系统响应**：
   - 生成并执行 SQL
   - 返回图表数据
   - **同步生成业务洞察**：
     ```
     本年度销售额呈稳步上升趋势，从1月的12万增长至5月的16万，
     增幅达33.3%。其中，2-3月受季节性因素影响略有波动，
     但4-5月实现快速恢复并创新高。订单量也同步增长，
     表明市场需求旺盛。
     ```

3. **前端展示**：
   - 图表可视化（柱状图/折线图）
   - 业务洞察卡片（蓝色渐变背景，醒目展示）

## 优势与对比

### 对比旧实现（异步）

| 特性 | 旧实现（异步） | 新实现（同步） |
|------|--------------|--------------|
| **请求次数** | 2 次（先 SQL 查询，再请求总结） | 1 次（一次性返回） |
| **用户等待时间** | 长（先看图表，再等总结） | 短（同时展示） |
| **前端复杂度** | 高（需管理 loading 状态） | 低（直接渲染） |
| **性能开销** | 高（额外 HTTP 往返） | 低（后端一次性处理） |
| **失败处理** | 复杂（需独立错误处理） | 简单（统一错误处理） |

### 优势总结
✅ **更快的响应速度**：减少一次 HTTP 请求  
✅ **更简洁的代码**：前端无需异步管理  
✅ **更好的用户体验**：图表和分析同时呈现  
✅ **更低的 Token 成本**：数据压缩策略有效减少 LLM 输入  

## 测试

### 单元测试
运行测试脚本：
```bash
cd backend
python tests/test_analyst_agent.py
```

### 集成测试
1. 启动后端服务
2. 打开前端 Chat 页面
3. 选择数据集并提问
4. 验证：
   - ✅ 图表正常显示
   - ✅ 智能分析卡片出现
   - ✅ 分析内容合理且简洁

## 注意事项

1. **LLM 调用频率**：每次查询都会调用 LLM 生成 insight，请确保 API 额度充足
2. **数据量控制**：数据压缩策略已限制发送给 LLM 的数据量（最多 5 行 + 统计信息）
3. **错误处理**：即使 insight 生成失败，主查询结果仍正常返回
4. **长度限制**：insight 最长 300 字符，防止 LLM 输出过长

## 未来优化方向

1. **缓存机制**：相同查询的 insight 可缓存，减少重复调用
2. **流式输出**：支持 Server-Sent Events (SSE)，逐字输出分析
3. **多语言支持**：根据用户偏好生成英文/中文分析
4. **可配置性**：允许用户关闭 insight 功能或调整详细程度
5. **更智能的 Prompt**：根据数据特征（时序、分类、数值）动态调整 Prompt

## 相关文件

### 后端
- `backend/app/schemas/chat.py` - Schema 定义
- `backend/app/services/vanna_manager.py` - 核心逻辑
- `backend/app/api/v1/endpoints/chat.py` - API 端点
- `backend/tests/test_analyst_agent.py` - 测试脚本

### 前端
- `frontend/src/api/chat.ts` - API 接口定义
- `frontend/src/views/Chat/index.vue` - 聊天界面

## 总结

"分析师 Agent"功能成功将异步总结改为同步实现，通过数据压缩和优化的 Prompt 设计，在保证分析质量的同时大幅提升了性能和用户体验。该功能已完全集成到 ChatBI 流程，无缝支持现有功能。
