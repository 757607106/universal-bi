# 训练进度管理和中断控制功能指南

## 概述

VannaManager 已升级支持异步训练、实时进度更新和中断控制功能。

## 新增功能

### 1. 自定义异常 - TrainingStoppedException

用于标识训练被用户中断的情况。

```python
from app.services.vanna_manager import TrainingStoppedException
```

### 2. 训练进度分阶段管理

训练过程分为 4 个主要阶段，每个阶段都会更新进度并检查中断：

| 阶段 | 进度范围 | 描述 |
|------|---------|------|
| Step 1 | 0-10% | 初始化、检查数据库连接、提取 DDL |
| Step 2 | 10-40% | 训练 DDL 到 Vanna |
| Step 3 | 40-80% | 训练文档/业务术语 |
| Step 4 | 80-100% | 生成并训练示例 SQLQA 对 |

### 3. 实时进度更新

训练过程中会实时更新以下字段：

- `status`: 训练状态 (pending/training/completed/failed/paused)
- `process_rate`: 训练进度百分比 (0-100)
- `error_msg`: 错误信息（如果失败）
- `last_train_at`: 最后训练时间

### 4. 训练日志记录

每个检查点都会创建 `TrainingLog` 记录：

```python
from app.models.metadata import TrainingLog

# 查询训练日志
logs = db.query(TrainingLog).filter(
    TrainingLog.dataset_id == dataset_id
).order_by(TrainingLog.created_at).all()
```

## 使用方法

### 启动训练

```python
from app.services.vanna_manager import VannaManager
from app.db.session import SessionLocal

db = SessionLocal()
dataset_id = 1
table_names = ["users", "orders", "products"]

# 启动训练（会自动处理进度更新）
VannaManager.train_dataset(dataset_id, table_names, db)
```

### 监控训练进度

```python
from app.models.metadata import Dataset

# 查询当前进度
dataset = db.query(Dataset).filter(Dataset.id == dataset_id).first()

print(f"状态: {dataset.status}")
print(f"进度: {dataset.process_rate}%")
print(f"错误: {dataset.error_msg}")
```

### 中断训练

前端/API 可以通过修改数据集状态来中断训练：

```python
# 设置状态为 paused
dataset = db.query(Dataset).filter(Dataset.id == dataset_id).first()
dataset.status = "paused"
db.commit()

# 训练线程会在下一个检查点检测到状态变化并停止
```

### 删除训练数据（清理 Collection）

```python
# 删除 Vanna/ChromaDB 中的 collection
success = VannaManager.delete_collection(dataset_id)

if success:
    print("Collection 删除成功")
```

## API 端点示例

### 查询训练进度

```python
@router.get("/datasets/{id}/training/progress")
def get_training_progress(
    id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """获取训练进度"""
    dataset = db.query(Dataset).filter(Dataset.id == id).first()
    
    if not dataset:
        raise HTTPException(status_code=404, detail="Dataset not found")
    
    return {
        "status": dataset.status,
        "process_rate": dataset.process_rate,
        "error_msg": dataset.error_msg,
        "last_train_at": dataset.last_train_at
    }
```

### 获取训练日志

```python
@router.get("/datasets/{id}/training/logs")
def get_training_logs(
    id: int,
    limit: int = 50,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """获取训练日志"""
    logs = db.query(TrainingLog).filter(
        TrainingLog.dataset_id == id
    ).order_by(TrainingLog.created_at.desc()).limit(limit).all()
    
    return [
        {
            "id": log.id,
            "content": log.content,
            "created_at": log.created_at
        }
        for log in logs
    ]
```

### 暂停训练

```python
@router.post("/datasets/{id}/training/pause")
def pause_training(
    id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """暂停训练"""
    dataset = db.query(Dataset).filter(Dataset.id == id).first()
    
    if not dataset:
        raise HTTPException(status_code=404, detail="Dataset not found")
    
    if dataset.status != "training":
        raise HTTPException(status_code=400, detail="Dataset is not training")
    
    dataset.status = "paused"
    db.commit()
    
    return {"message": "训练暂停请求已发送"}
```

### 删除训练数据

```python
@router.delete("/datasets/{id}/training")
def delete_training_data(
    id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """删除训练数据（清理 Collection）"""
    success = VannaManager.delete_collection(id)
    
    if success:
        return {"message": "训练数据已清理"}
    else:
        raise HTTPException(status_code=500, detail="清理训练数据失败")
```

## 检查点逻辑

`_checkpoint_and_check_interrupt` 方法在每个关键步骤执行：

1. **更新进度**：将 `process_rate` 更新到数据库
2. **记录日志**：创建 `TrainingLog` 记录
3. **检查中断**：查询最新的 `status`，如果为 `paused` 则抛出异常

## 错误处理

训练过程中的错误会被捕获并记录：

- **TrainingStoppedException**：用户中断，状态保持为 `paused`
- **其他异常**：训练失败，状态设置为 `failed`，错误信息写入 `error_msg`

## 注意事项

1. **数据库会话**：确保传入的 `db_session` 在训练过程中保持有效
2. **并发控制**：同一数据集同时只能有一个训练任务
3. **中断延迟**：中断不是立即生效，而是在下一个检查点时检测到
4. **进度精度**：进度是估算值，可能不完全精确

## 测试

运行测试脚本：

```bash
python3 tests/test_training_control.py
```

测试覆盖：
- ✅ 训练进度更新
- ✅ 训练中断控制
- ✅ Collection 删除

## 前端集成建议

### 进度条显示

```vue
<template>
  <el-progress 
    :percentage="dataset.process_rate" 
    :status="getProgressStatus(dataset.status)"
  />
  <div class="status-text">
    {{ getStatusText(dataset.status) }}
  </div>
</template>

<script setup lang="ts">
const getProgressStatus = (status: string) => {
  switch (status) {
    case 'completed': return 'success'
    case 'failed': return 'exception'
    case 'paused': return 'warning'
    default: return undefined
  }
}

const getStatusText = (status: string) => {
  const statusMap = {
    'pending': '等待训练',
    'training': '训练中...',
    'completed': '训练完成',
    'failed': '训练失败',
    'paused': '已暂停'
  }
  return statusMap[status] || status
}
</script>
```

### 实时更新

```typescript
// 轮询获取训练进度
const pollTrainingProgress = async (datasetId: number) => {
  const interval = setInterval(async () => {
    const response = await api.get(`/datasets/${datasetId}/training/progress`)
    
    // 更新进度
    dataset.value.status = response.status
    dataset.value.process_rate = response.process_rate
    
    // 训练结束，停止轮询
    if (['completed', 'failed', 'paused'].includes(response.status)) {
      clearInterval(interval)
    }
  }, 2000) // 每 2 秒更新一次
}
```

### 暂停按钮

```vue
<el-button 
  v-if="dataset.status === 'training'"
  @click="pauseTraining(dataset.id)"
  type="warning"
>
  暂停训练
</el-button>
```

## 性能优化

1. **批量检查点**：避免过于频繁的数据库写入
2. **异步日志**：考虑使用消息队列记录日志
3. **缓存清理**：训练完成后自动清理相关缓存

## 未来扩展

- [ ] 支持训练恢复（从暂停状态继续）
- [ ] 支持训练取消（vs 暂停）
- [ ] 训练任务队列管理
- [ ] 更细粒度的进度报告
- [ ] WebSocket 实时推送进度
