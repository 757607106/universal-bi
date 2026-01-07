# Schema Injection - 利用可视化建模增强 Vanna 训练

## 功能概述

**Schema Injection** 功能通过解析前端可视化建模中的连线数据（VueFlow edges），自动生成表关系的自然语言描述，并训练到 Vanna 向量库中。这使得 AI 能够理解表之间的 JOIN 关系，从而生成更准确的跨表查询 SQL。

## 核心价值

### 问题背景
在传统的 Vanna 训练中：
- 仅训练 DDL（表结构），缺少表关系信息
- AI 需要推测哪些表可以关联，容易出错
- 复杂的多表 JOIN 查询准确率较低

### 解决方案
通过可视化建模：
1. **用户可视化操作**：在画布上手动连接表之间的关系
2. **自动解析转换**：将连线数据转换为自然语言描述
3. **增强 AI 理解**：将关系描述训练到向量库
4. **提升查询准确率**：AI 生成 JOIN 查询时使用正确的关联条件

## 技术实现

### 1. 数据流程

```
用户操作 (VueFlow 画布连线)
        ↓
保存 modeling_config (包含 edges)
        ↓
检测 edges 变化
        ↓
解析 edges → 生成关系描述
        ↓
调用 Vanna train(documentation)
        ↓
向量库更新 → AI 增强
```

### 2. VueFlow Edge 数据结构

**前端 VueFlow 产生的 edge 格式**：
```json
{
  "id": "edge-1",
  "source": "node-users",       // 源节点 ID
  "target": "node-orders",      // 目标节点 ID
  "sourceHandle": "id",         // 源字段名
  "targetHandle": "user_id",    // 目标字段名
  "data": {                     // 扩展数据（可选但推荐）
    "sourceTable": "users",     // 源表名
    "targetTable": "orders",    // 目标表名
    "sourceField": "id",        // 源字段名
    "targetField": "user_id"    // 目标字段名
  }
}
```

### 3. 后端核心组件

#### 3.1 VannaManager.train_relationships()

**位置**：`backend/app/services/vanna_manager.py`

**功能**：批量训练表关系描述到 Vanna 向量库

**签名**：
```python
@staticmethod
def train_relationships(
    dataset_id: int, 
    relationships: list[str], 
    db_session: Session
)
```

**参数**：
- `dataset_id`: 数据集 ID
- `relationships`: 关系描述列表（自然语言）
- `db_session`: 数据库会话

**示例**：
```python
relationships = [
    "The table `users` can be joined with table `orders` on the condition `users`.`id` = `orders`.`user_id`.",
    "The table `orders` can be joined with table `users` on the condition `orders`.`user_id` = `users`.`id`."
]

VannaManager.train_relationships(
    dataset_id=1,
    relationships=relationships,
    db_session=db
)
```

#### 3.2 _train_relationships_from_edges()

**位置**：`backend/app/api/v1/endpoints/dataset.py`

**功能**：解析 VueFlow edges 并调用 train_relationships

**逻辑**：
1. 遍历每条 edge
2. 提取表名和字段名（优先从 `data` 读取，回退到 `source`/`target` 解析）
3. 生成双向关系描述（正向 + 反向）
4. 调用 VannaManager.train_relationships 训练

**双向关系示例**：
```python
# 正向关系
"The table `users` can be joined with table `orders` on the condition `users`.`id` = `orders`.`user_id`."

# 反向关系（自动生成）
"The table `orders` can be joined with table `users` on the condition `orders`.`user_id` = `users`.`id`."
```

#### 3.3 update_modeling_config 接口增强

**端点**：`PUT /datasets/{id}/modeling-config`

**新增参数**：
- `train_relationships: bool = False`  
  是否立即训练关系（默认 False）

**行为**：
- `train_relationships=False`: 仅保存配置，不训练
- `train_relationships=True`: 保存配置并立即训练 edges 中的关系

**请求示例**：
```bash
curl -X PUT "http://localhost:8000/datasets/1/modeling-config?train_relationships=true" \
  -H "Content-Type: application/json" \
  -d '{
    "nodes": [...],
    "edges": [
      {
        "id": "edge-1",
        "source": "node-users",
        "target": "node-orders",
        "sourceHandle": "id",
        "targetHandle": "user_id",
        "data": {
          "sourceTable": "users",
          "targetTable": "orders",
          "sourceField": "id",
          "targetField": "user_id"
        }
      }
    ]
  }'
```

**响应示例**：
```json
{
  "message": "建模配置已保存，表关系已训练",
  "modeling_config": {...},
  "relationships_trained": true,
  "edges_count": 1
}
```

### 4. 边缘变化检测

系统会智能检测 edges 是否发生变化：
```python
old_edges = dataset.modeling_config.get('edges', [])
new_edges = config.get('edges', [])

# 比较数量和 ID
edges_changed = (
    len(old_edges) != len(new_edges) or
    old_edge_ids != new_edge_ids
)
```

## 使用场景

### 场景 1：保存建模配置（不立即训练）

**前端调用**：
```typescript
await updateModelingConfig(datasetId, {
  nodes: currentNodes,
  edges: currentEdges
})
// train_relationships 默认为 false，仅保存不训练
```

**适用场景**：
- 用户正在编辑建模，尚未完成
- 频繁保存布局，避免频繁调用 LLM

### 场景 2：完成建模并立即训练

**前端调用**：
```typescript
await updateModelingConfig(
  datasetId, 
  {
    nodes: currentNodes,
    edges: currentEdges
  },
  { train_relationships: true }  // 立即训练
)
```

**适用场景**：
- 用户点击"保存并训练"按钮
- 确认建模完成，需要增强 AI
- 与"开始训练"流程整合

### 场景 3：结合数据集训练流程

**推荐工作流**：
```
1. 选择表 (schema_config) 
2. 可视化建模 (modeling_config + edges) 
3. 点击"开始训练"
   ├─ 训练 DDL
   ├─ 训练业务术语
   └─ 训练表关系 (从 modeling_config.edges)
```

## 前端集成建议

### 1. 在建模页面添加"训练关系"按钮

```vue
<template>
  <el-button 
    @click="handleTrainRelationships" 
    :loading="trainingRelationships"
    type="primary"
  >
    训练表关系
  </el-button>
</template>

<script setup>
const handleTrainRelationships = async () => {
  trainingRelationships.value = true
  try {
    // 保存配置并训练关系
    const res = await updateModelingConfig(
      datasetId, 
      { nodes, edges },
      { train_relationships: true }
    )
    
    if (res.relationships_trained) {
      ElMessage.success(`已训练 ${res.edges_count} 条关系`)
    }
  } finally {
    trainingRelationships.value = false
  }
}
</script>
```

### 2. 在"开始训练"对话框中提示

```vue
<el-alert 
  type="info" 
  :closable="false"
  v-if="edges.length > 0"
>
  检测到 {{ edges.length }} 条表关系，训练时将自动包含
</el-alert>
```

### 3. 数据完整性确保

**在连线时保存完整数据**：
```typescript
const onConnect = (connection: Connection) => {
  // 获取源节点和目标节点的完整信息
  const sourceNode = findNode(connection.source)
  const targetNode = findNode(connection.target)
  
  const newEdge: Edge = {
    id: `edge-${Date.now()}`,
    source: connection.source,
    target: connection.target,
    sourceHandle: connection.sourceHandle,
    targetHandle: connection.targetHandle,
    data: {
      // 关键：保存表名和字段名
      sourceTable: sourceNode?.data?.tableName,
      targetTable: targetNode?.data?.tableName,
      sourceField: connection.sourceHandle,
      targetField: connection.targetHandle
    }
  }
  
  addEdges([newEdge])
}
```

## 测试验证

### 1. 单元测试

运行测试脚本：
```bash
cd backend
python tests/test_schema_injection.py
```

### 2. 集成测试

**步骤**：
1. 创建数据集并选择多个表
2. 进入可视化建模页面
3. 在画布上连接表（例如：users.id → orders.user_id）
4. 点击"保存并训练关系"
5. 进入 ChatBI 页面
6. 提问跨表查询：
   - "查询所有用户的订单数量"
   - "统计每个产品的销售额"
7. 验证生成的 SQL 包含正确的 JOIN 条件

### 3. 预期效果

**训练前**：
```sql
-- AI 可能生成错误的 JOIN
SELECT u.name, COUNT(*) 
FROM users u, orders o
WHERE u.id = o.order_id  -- 错误的关联字段
GROUP BY u.name
```

**训练后**：
```sql
-- AI 使用正确的 JOIN 条件
SELECT u.name, COUNT(*) as order_count
FROM users u
LEFT JOIN orders o ON u.id = o.user_id  -- 正确的关联
GROUP BY u.name
```

## 性能考虑

### 1. 训练频率控制

**避免频繁训练**：
- 仅在用户显式点击"保存并训练"时触发
- 默认 `train_relationships=False`
- 与"开始训练"流程整合，一次性训练所有内容

### 2. 增量训练

**当前实现**：
- 每次训练会重新训练所有 edges
- 旧的关系描述仍保留在向量库中（累积）

**未来优化方向**：
- 差异检测：仅训练新增的 edges
- 关系去重：删除旧的关系描述再添加新的

### 3. 缓存清理

训练关系后会自动清理查询缓存：
```python
cleared = VannaManager.clear_cache(dataset_id)
logger.info(f"Cleared {cleared} cached queries after training relationships")
```

## 最佳实践

### 1. 建模规范

**连线命名规范**：
- 主键 → 外键（推荐）
- 保持字段名一致性（如 `user_id` 指向 `users.id`）

**数据完整性**：
- 确保 edge 的 `data` 字段包含完整信息
- 避免仅依赖 `source`/`target` 解析

### 2. 训练时机

**推荐流程**：
```
1. 选择表 → 保存
2. 可视化建模 → 保存（不训练）
3. 添加业务术语 → 保存
4. 点击"开始训练" → 一次性训练所有内容（包括关系）
```

### 3. 日志监控

查看训练日志：
```bash
# 查看后端日志
tail -f backend/logs/app.log | grep "relationship"

# 预期输出
Training 6 relationships for dataset 1
Trained relationship 1/6: The table `users` can be joined with...
Successfully trained 6 relationships for dataset 1
Cleared 3 cached queries after training relationships
```

## 常见问题

### Q1: 为什么有些 edges 没有被训练？

**原因**：
- edge 缺少必要字段（表名或字段名为空）
- edge 的 `data` 字段不完整且无法从 `source`/`target` 解析

**解决方案**：
- 检查日志中的警告信息
- 确保连线时保存完整的 `data` 字段

### Q2: 训练后 AI 仍然生成错误的 JOIN？

**可能原因**：
1. 向量检索未命中（相似度不够）
2. 关系描述与用户问题语义差距大
3. 需要更多的示例查询

**改进方法**：
- 增加业务术语训练
- 手动添加示例 SQL（包含 JOIN）
- 调整 prompt 强调使用已知关系

### Q3: 如何删除旧的关系训练数据？

**当前方案**：
- Vanna Legacy API 不支持删除特定训练数据
- 只能删除整个 collection（`DELETE /datasets/{id}/training`）

**替代方案**：
- 重新训练数据集（会覆盖旧数据）
- 迁移到 Vanna 2.0 Agent（支持更精细的数据管理）

## 未来优化方向

1. **智能关系推荐**：基于字段名和类型自动建议关系
2. **关系验证**：检查 JOIN 条件是否在实际数据中有效
3. **关系强度标注**：标记主从关系、一对多等
4. **可视化反馈**：在画布上显示哪些关系已训练
5. **批量导入导出**：支持关系配置的导入导出

## 相关文件

**后端**：
- `backend/app/services/vanna_manager.py` - train_relationships 方法
- `backend/app/api/v1/endpoints/dataset.py` - update_modeling_config 接口
- `backend/tests/test_schema_injection.py` - 单元测试

**前端**（待实现）：
- `frontend/src/views/Dataset/modeling/index.vue` - 建模页面
- `frontend/src/api/dataset.ts` - API 调用

## 总结

Schema Injection 功能通过可视化建模与 AI 训练的结合，显著提升了跨表查询的准确率。用户只需在画布上简单连线，系统就能自动将表关系转化为 AI 可理解的知识，实现了"所见即所得"的智能增强。
