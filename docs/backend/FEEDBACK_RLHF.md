# ChatBI 反馈闭环机制（RLHF）

## 功能概述

ChatBI 实现了完整的**人类反馈强化学习（RLHF）机制**，允许用户通过点赞/点踩的方式帮助 AI 学习和改进 SQL 生成能力。这是提升 AI 准确率的**最强手段**。

## 核心价值

1. **正向反馈学习**：用户点赞正确结果，AI 立即将该问答对存入向量库
2. **负向反馈修正**：用户点踩错误结果并提供正确 SQL，AI 学习正确逻辑
3. **持续优化**：每次反馈都会提升未来相似问题的准确率
4. **零配置**：无需重新训练模型，实时生效

## 技术架构

### 1. 后端 API 实现

#### 接口定义
```
POST /api/v1/chat/feedback
```

#### 请求体
```python
class FeedbackRequest(BaseModel):
    dataset_id: int       # 数据集 ID
    question: str         # 用户原始问题
    sql: str              # rating=1 时为原始 SQL；rating=-1 时为修正后的 SQL
    rating: int           # 1 表示点赞，-1 表示点踩
```

#### 响应体
```python
class FeedbackResponse(BaseModel):
    success: bool         # 是否成功
    message: str          # 提示信息
```

#### 逻辑处理

**点赞（rating=1）**：
```python
if request.rating == 1:
    VannaManager.train_qa(
        dataset_id=request.dataset_id,
        question=request.question,
        sql=request.sql,  # 原始 SQL
        db_session=db
    )
    return "感谢反馈！AI 已记住这个查询逻辑。"
```

**点踩（rating=-1）**：
```python
elif request.rating == -1:
    VannaManager.train_qa(
        dataset_id=request.dataset_id,
        question=request.question,
        sql=request.sql,  # 用户修正后的 SQL
        db_session=db
    )
    return "感谢你的修正！AI 已学习了正确的 SQL。"
```

#### 权限控制
```python
# 验证数据集访问权限
ds_query = apply_ownership_filter(ds_query, Dataset, current_user)

# 额外检查：公共资源只有超级管理员可以训练
if dataset.owner_id is None and not current_user.is_superuser:
    raise HTTPException(status_code=403, detail="Cannot train public resources")
```

### 2. 前端交互实现

#### UI 组件位置
文件：`frontend/src/views/Chat/index.vue`

**反馈按钮**（位于每条 AI 回复下方）：
```vue
<div class="flex items-center gap-2 text-xs">
  <span class="text-xs text-gray-400">结果评价：</span>
  <div class="flex gap-2">
    <!-- 点赞按钮 -->
    <el-button
      size="small"
      :type="msg.feedbackGiven === 'like' ? 'success' : 'default'"
      :disabled="msg.feedbackGiven !== undefined"
      @click="handleLikeFeedback(msg, index)"
      circle
    >
      <el-icon><Select /></el-icon>
    </el-button>
    
    <!-- 点踩按钮 -->
    <el-button
      size="small"
      :type="msg.feedbackGiven === 'dislike' ? 'danger' : 'default'"
      :disabled="msg.feedbackGiven !== undefined"
      @click="handleDislikeFeedback(msg, index)"
      circle
    >
      <el-icon><CloseBold /></el-icon>
    </el-button>
  </div>
</div>
```

#### 点赞逻辑
```typescript
const handleLikeFeedback = async (msg: Message, index: number) => {
  if (!msg.sql || !msg.question || !msg.datasetId) {
    ElMessage.warning('无法提交反馈，缺少必要信息')
    return
  }
  
  submittingFeedback.value = true
  
  try {
    const response = await submitFeedback({
      dataset_id: msg.datasetId,
      question: msg.question,
      sql: msg.sql,  // 原始 SQL
      rating: 1
    })
    
    if (response.success) {
      ElMessage.success(response.message)
      messages.value[index].feedbackGiven = 'like'  // 标记为已反馈
    }
  } catch (error) {
    ElMessage.error('反馈提交失败')
  } finally {
    submittingFeedback.value = false
  }
}
```

#### 点踩逻辑（含 SQL 修正对话框）
```typescript
const handleDislikeFeedback = (msg: Message, index: number) => {
  if (!msg.sql || !msg.question || !msg.datasetId) {
    ElMessage.warning('无法提交反馈，缺少必要信息')
    return
  }
  
  // 打开 SQL 修正对话框
  currentFeedbackMessage.value = msg
  currentFeedbackMessageIndex.value = index
  correctedSql.value = msg.sql  // 预填充当前 SQL
  sqlCorrectionDialog.value = true
}

const handleSubmitCorrection = async () => {
  if (!correctedSql.value.trim()) {
    ElMessage.warning('请输入修正后的 SQL')
    return
  }
  
  submittingFeedback.value = true
  
  try {
    const response = await submitFeedback({
      dataset_id: currentFeedbackMessage.value.datasetId!,
      question: currentFeedbackMessage.value.question!,
      sql: correctedSql.value.trim(),  // 修正后的 SQL
      rating: -1
    })
    
    if (response.success) {
      ElMessage.success(response.message)
      messages.value[currentFeedbackMessageIndex.value].feedbackGiven = 'dislike'
      handleCancelCorrection()
    }
  } catch (error) {
    ElMessage.error('修正提交失败')
  } finally {
    submittingFeedback.value = false
  }
}
```

#### SQL 修正对话框
```vue
<el-dialog
  v-model="sqlCorrectionDialog"
  title="修正 SQL"
  width="700px"
>
  <div class="space-y-4">
    <div>
      <p class="text-sm text-slate-400 mb-2">请修改下方的 SQL 查询，然后提交给 AI 学习：</p>
      <el-input
        v-model="correctedSql"
        type="textarea"
        :rows="10"
        placeholder="输入正确的 SQL..."
        class="font-mono text-sm"
      />
    </div>
    <el-alert
      title="提示"
      type="info"
      :closable="false"
      show-icon
    >
      AI 会学习你提供的正确 SQL，下次遇到类似问题时会更准确。
    </el-alert>
  </div>
  
  <template #footer>
    <el-button @click="handleCancelCorrection">取消</el-button>
    <el-button type="primary" @click="handleSubmitCorrection" :loading="submittingFeedback">
      提交修正
    </el-button>
  </template>
</el-dialog>
```

### 3. Vanna 训练机制

#### VannaManager.train_qa 方法
```python
@staticmethod
def train_qa(dataset_id: int, question: str, sql: str, db_session: Session):
    """
    Train Vanna with a question-SQL pair.
    This is the most powerful training method for RLHF.
    """
    vn = VannaManager.get_legacy_vanna(dataset_id)
    
    # Train the Q-A pair
    vn.train(question=question, sql=sql)
    
    logger.info(f"Successfully trained Q-A pair for dataset {dataset_id}")
    
    # Clear cache after training
    cleared = VannaManager.clear_cache(dataset_id)
    if cleared >= 0:
        logger.info(f"Cleared {cleared} cached queries after training")
```

#### 训练后的效果
1. **向量存储**：问答对立即写入 ChromaDB 向量库
2. **语义检索**：未来相似问题会优先匹配训练过的正确答案
3. **缓存清理**：自动清理该数据集的所有查询缓存，确保新知识生效

## 使用场景

### 场景 1：AI 生成了正确的 SQL

**用户操作**：点击 👍 点赞按钮

**系统行为**：
1. 后端调用 `train_qa(question, sql)`
2. 将问答对存入向量库
3. 清理查询缓存
4. 提示"感谢反馈！AI 已记住这个查询逻辑。"

**结果**：下次遇到相同或相似问题时，AI 会直接生成正确的 SQL

### 场景 2：AI 生成的 SQL 有错误

**用户操作**：
1. 点击 👎 点踩按钮
2. 在弹出的对话框中修改 SQL
3. 点击"提交修正"

**系统行为**：
1. 后端调用 `train_qa(question, corrected_sql)`
2. 将问题和修正后的 SQL 存入向量库
3. 清理查询缓存
4. 提示"感谢你的修正！AI 已学习了正确的 SQL。"

**结果**：AI 学习到了正确的逻辑，避免重复犯错

### 场景 3：点踩但不提供修正 SQL

**用户操作**：
1. 点击 👎 点踩按钮
2. 直接关闭对话框（不修改 SQL）

**系统行为**：
- 不调用训练接口
- 不存储任何数据
- 仅作为用户满意度的被动记录

**结果**：AI 不会学习到任何内容（需要修正 SQL 才能触发训练）

## 高级特性

### 1. 防止重复反馈
```typescript
interface Message {
  feedbackGiven?: 'like' | 'dislike'  // 反馈状态
}

// 按钮禁用逻辑
:disabled="msg.feedbackGiven !== undefined"
```

**效果**：用户反馈后，按钮变为禁用状态，防止重复提交

### 2. 权限控制
```python
# 公共资源只有超级管理员可以训练
if dataset.owner_id is None and not current_user.is_superuser:
    raise HTTPException(status_code=403, detail="Cannot train public resources")
```

**效果**：
- 私有数据集：所有者可以训练
- 公共数据集：只有超级管理员可以训练（防止污染）

### 3. 自动缓存清理
```python
# 训练后自动清理缓存
cleared = VannaManager.clear_cache(dataset_id)
```

**效果**：确保新训练的知识立即生效，不会被旧缓存覆盖

## 最佳实践

### 1. 鼓励用户反馈

**在聊天界面增加引导性提示**：
```
"如果答案准确，请点击 👍 帮助 AI 学习；
 如果有错误，请点击 👎 并提供正确的 SQL。"
```

### 2. 分阶段收集反馈

**初期（数据集刚创建）**：
- 积极邀请用户反馈
- 重点关注高频问题
- 优先训练核心业务场景

**成熟期（数据集已训练充分）**：
- 仅在出现新问题时反馈
- 关注边缘案例和特殊场景

### 3. 定期分析反馈数据

**建议指标**：
- 点赞率（Like Rate）
- 点踩修正率（Correction Rate）
- 训练前后准确率对比

### 4. 避免训练噪音数据

**高质量反馈**：
- ✅ SQL 语法正确
- ✅ 逻辑符合业务需求
- ✅ 性能可接受

**低质量反馈**：
- ❌ SQL 语法错误
- ❌ 逻辑不符合实际业务
- ❌ 过度复杂或不通用

## 技术细节

### 1. 训练数据存储结构

Vanna 使用 ChromaDB 向量库存储训练数据：

```
Collection: training-plan-{dataset_id}
Document Structure:
{
  "id": "qa-{uuid}",
  "question": "最近 7 天的销售额是多少？",
  "content": "SELECT SUM(amount) FROM orders WHERE date >= DATE_SUB(NOW(), INTERVAL 7 DAY)",
  "training_data_type": "sql"
}
```

### 2. 语义检索机制

当用户提问时，Vanna 会：
1. 将问题转换为向量
2. 在向量库中搜索相似问题（Top-K）
3. 优先使用已训练的 SQL 作为参考
4. 结合 DDL 和文档生成最终 SQL

### 3. 缓存清理策略

```python
# Redis 缓存 Key 格式
cache_key = f"vanna_cache:dataset_{dataset_id}:question_{hash(question)}"

# 清理逻辑
def clear_cache(dataset_id: int) -> int:
    pattern = f"vanna_cache:dataset_{dataset_id}:*"
    keys = redis_client.keys(pattern)
    if keys:
        return redis_client.delete(*keys)
    return 0
```

**清理时机**：
- 用户提交反馈后
- 训练新的表结构后
- 更新建模配置后

## 测试验证

### 1. 测试点赞功能

```bash
curl -X POST http://localhost:8000/api/v1/chat/feedback \
  -H "Authorization: Bearer YOUR_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "dataset_id": 1,
    "question": "查询用户总数",
    "sql": "SELECT COUNT(*) as total FROM users",
    "rating": 1
  }'
```

**预期响应**：
```json
{
  "success": true,
  "message": "感谢反馈！AI 已记住这个查询逻辑。"
}
```

### 2. 测试点踩修正功能

```bash
curl -X POST http://localhost:8000/api/v1/chat/feedback \
  -H "Authorization: Bearer YOUR_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "dataset_id": 1,
    "question": "查询最近 7 天的订单",
    "sql": "SELECT * FROM orders WHERE created_at >= DATE_SUB(NOW(), INTERVAL 7 DAY)",
    "rating": -1
  }'
```

**预期响应**：
```json
{
  "success": true,
  "message": "感谢你的修正！AI 已学习了正确的 SQL。"
}
```

### 3. 验证训练效果

```python
# 在训练前后分别测试相同问题
question = "查询用户总数"

# 训练前
sql_before = vn.generate_sql(question)

# 提交反馈训练
vn.train(question=question, sql="SELECT COUNT(*) as total FROM users")

# 训练后
sql_after = vn.generate_sql(question)

# 对比结果
assert sql_before != sql_after or sql_after == "SELECT COUNT(*) as total FROM users"
```

## 故障排查

### 问题 1：反馈提交失败

**症状**：点击反馈按钮后提示"反馈提交失败"

**可能原因**：
1. 缺少必要字段（sql, question, datasetId）
2. 数据集访问权限不足
3. 公共数据集但用户不是超级管理员

**解决方案**：
```typescript
// 前端添加更详细的错误提示
catch (error: any) {
  const errorMsg = error.response?.data?.detail || '反馈提交失败'
  ElMessage.error(errorMsg)
  console.error('Feedback error:', error)
}
```

### 问题 2：训练后效果不明显

**症状**：提交反馈后，再次提问仍生成错误 SQL

**可能原因**：
1. 缓存未清理
2. 训练数据被其他更相似的错误数据覆盖
3. 问题表述差异较大

**解决方案**：
1. 手动清理缓存：`redis-cli KEYS "vanna_cache:dataset_1:*" | xargs redis-cli DEL`
2. 多次训练相同问答对提升权重
3. 使用更通用的问题表述进行训练

### 问题 3：SQL 修正对话框不显示

**症状**：点击 👎 按钮没有反应

**可能原因**：
1. `sqlCorrectionDialog` 状态未正确绑定
2. 消息缺少必要字段

**解决方案**：
```typescript
// 添加调试日志
const handleDislikeFeedback = (msg: Message, index: number) => {
  console.log('Dislike feedback:', msg)
  if (!msg.sql || !msg.question || !msg.datasetId) {
    console.error('Missing required fields:', { sql: msg.sql, question: msg.question, datasetId: msg.datasetId })
    ElMessage.warning('无法提交反馈，缺少必要信息')
    return
  }
  // ...
}
```

## 未来优化方向

1. **反馈统计面板**：展示点赞率、点踩率等指标
2. **批量训练**：支持批量导入问答对
3. **训练历史**：记录所有训练记录，支持回滚
4. **智能推荐修正**：AI 自动建议可能的正确 SQL
5. **A/B 测试**：对比训练前后的准确率提升
6. **协同学习**：公共数据集的反馈在团队内共享

## 总结

ChatBI 的反馈闭环机制（RLHF）是提升 SQL 生成准确率的**核心功能**。通过简单的点赞/点踩交互，用户可以持续优化 AI 的表现，实现：

1. ✅ **零配置学习**：无需重新训练模型，实时生效
2. ✅ **精准提升**：针对具体业务场景优化
3. ✅ **持续改进**：随着使用增加，准确率不断提高
4. ✅ **用户主导**：用户掌握 AI 的学习方向

建议在项目上线初期**积极引导用户反馈**，快速积累高质量训练数据，提升用户体验和 AI 准确率。
