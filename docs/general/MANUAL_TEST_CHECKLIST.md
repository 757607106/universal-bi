# Universal BI - 手动测试验证清单

**版本**: v2.0  
**日期**: 2026-01-08  

---

## 🧪 测试前准备

### 1. 数据库迁移

```bash
cd /Users/pusonglin/PycharmProjects/universal-bi/backend
python3 run_migration.py migrations/005_add_computed_metrics.sql
```

### 2. 启动服务

```bash
# 启动后端
cd backend
uvicorn app.main:app --reload --port 8000

# 启动前端
cd frontend
npm run dev
```

### 3. 清理缓存（可选）

```bash
redis-cli FLUSHALL
```

---

## ✅ 功能测试清单

### 阶段一：即席分析 (Excel/CSV上传)

#### 测试1.1：Excel文件上传

**测试步骤**：
1. 打开浏览器访问 `http://localhost:3000`
2. 登录系统
3. 进入"数据集管理"页面
4. 点击"上传Excel/CSV"按钮
5. 选择一个测试Excel文件（<20MB, <50000行）
6. 等待上传完成

**预期结果**：
- ✅ 文件上传进度展示
- ✅ 上传成功提示
- ✅ 自动跳转到Chat页面
- ✅ Dataset列表中出现新数据集

**API测试**：
```bash
curl -X POST http://localhost:8000/api/v1/upload/file \
  -H "Authorization: Bearer YOUR_TOKEN" \
  -F "file=@test_data.xlsx"
```

---

#### 测试1.2：计算指标管理

**测试步骤**：
1. 在数据集卡片上点击"计算指标"按钮
2. 点击"新建指标"
3. 填写：
   - 指标名称：客单价
   - 计算公式：SUM(amount) / COUNT(DISTINCT user_id)
   - 业务口径：平均每个用户的消费金额
4. 点击"保存"
5. 查看指标列表

**预期结果**：
- ✅ 指标创建成功
- ✅ 列表中显示新指标
- ✅ 可以编辑和删除指标

**API测试**：
```bash
# 创建指标
curl -X POST http://localhost:8000/api/v1/datasets/1/metrics \
  -H "Authorization: Bearer YOUR_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "name": "客单价",
    "formula": "SUM(amount) / COUNT(DISTINCT user_id)",
    "description": "平均每个用户的消费金额"
  }'

# 查询指标列表
curl http://localhost:8000/api/v1/datasets/1/metrics \
  -H "Authorization: Bearer YOUR_TOKEN"
```

---

#### 测试1.3：数据集删除

**测试步骤**：
1. 找到一个上传的数据集
2. 点击"删除"按钮
3. 确认删除

**预期结果**：
- ✅ 数据集从列表消失
- ✅ 向量数据被删除
- ✅ 物理表被删除
- ✅ 关联的指标和术语被删除

**验证SQL**：
```sql
-- 检查物理表是否删除
SHOW TABLES LIKE 'upload_%';

-- 检查计算指标是否删除
SELECT * FROM computed_metrics WHERE dataset_id = <deleted_id>;
```

---

### 阶段二：智能分析

#### 测试2.1：统计分析和AI洞察

**测试步骤**：
1. 进入Chat页面
2. 选择一个数据集
3. 提问："查询最近30天的销售额趋势"
4. 等待结果返回
5. 查看返回的insight字段

**预期结果**：
- ✅ SQL正确生成
- ✅ 数据正确查询
- ✅ 返回统计分析（mean, std, cv等）
- ✅ 返回AI业务洞察（insight字段）
- ✅ 洞察包含趋势分析和关键发现

**API测试**：
```bash
curl -X POST http://localhost:8000/api/v1/chat \
  -H "Authorization: Bearer YOUR_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "dataset_id": 1,
    "question": "查询最近30天的销售额趋势",
    "use_cache": false
  }'
```

**检查响应**：
```json
{
  "sql": "SELECT ...",
  "columns": [...],
  "rows": [...],
  "chart_type": "line",
  "insight": "从数据来看，最近30天销售额呈现稳健增长...",
  "alternative_charts": ["bar", "area", "table"]
}
```

---

### 阶段三：智能图表推荐

#### 测试3.1：图表类型推荐

**测试用例集**：

**用例1：时间序列 → 折线图**
```bash
# 提问："查询每日销售额"
# 预期：chart_type = "line"
```

**用例2：占比构成 → 饼图**
```bash
# 提问："查询各城市销售额占比"
# 预期：chart_type = "pie"
```

**用例3：数量对比 → 柱状图**
```bash
# 提问："查询各城市销售额对比"（城市数>8）
# 预期：chart_type = "bar"
```

**用例4：明细数据 → 表格**
```bash
# 提问："查询订单明细"
# 预期：chart_type = "table"
```

**验证方法**：
- 检查API响应的`chart_type`字段
- 检查`alternative_charts`是否包含备选项

---

#### 测试3.2：多轮对话上下文

**测试步骤**：
1. 第一轮："查询上个月的销售额"
2. 记录对话历史
3. 第二轮："按城市拆分"（省略主语）
4. 携带历史发送请求

**预期结果**：
- ✅ 后端自动将"按城市拆分"重写为"查询上个月的销售额，按城市拆分"
- ✅ SQL正确生成
- ✅ 返回分城市的销售额

**API测试**：
```bash
curl -X POST http://localhost:8000/api/v1/chat \
  -H "Authorization: Bearer YOUR_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "dataset_id": 1,
    "question": "按城市拆分",
    "use_cache": false,
    "conversation_history": [
      {"role": "user", "content": "查询上个月的销售额"},
      {"role": "assistant", "content": "总销售额100万元"}
    ]
  }'
```

**检查日志**：
```
# 应该能看到类似日志
Query rewritten: original="按城市拆分", rewritten="查询上个月的销售额，按城市拆分"
```

---

### 阶段四：数据导出

#### 测试4.1：Excel导出

**测试步骤**：
1. 在Chat页面执行查询获取结果
2. 记录返回的columns和rows
3. 调用导出API

**API测试**：
```bash
curl -X POST http://localhost:8000/api/v1/chat/export/excel \
  -H "Authorization: Bearer YOUR_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "dataset_id": 1,
    "question": "查询销售数据",
    "columns": ["date", "sales", "profit"],
    "rows": [
      {"date": "2024-01-01", "sales": 1000, "profit": 200},
      {"date": "2024-01-02", "sales": 1200, "profit": 250}
    ]
  }' \
  --output test_export.xlsx
```

**预期结果**：
- ✅ 文件下载成功
- ✅ 文件可以用Excel打开
- ✅ 数据完整
- ✅ 中文正常显示
- ✅ 列宽自动调整

---

#### 测试4.2：CSV导出

**API测试**：
```bash
curl -X POST http://localhost:8000/api/v1/chat/export/csv \
  -H "Authorization: Bearer YOUR_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "dataset_id": 1,
    "question": "查询销售数据",
    "columns": ["date", "sales"],
    "rows": [
      {"date": "2024-01-01", "sales": 1000}
    ]
  }' \
  --output test_export.csv
```

**预期结果**：
- ✅ 文件下载成功
- ✅ 文件可以用Excel/文本编辑器打开
- ✅ 中文正常显示（UTF-8 BOM）

---

## 🔍 数据库验证

### 检查新表

```sql
-- 计算指标表
SELECT * FROM computed_metrics;

-- 上传的物理表
SHOW TABLES LIKE 'upload_%';

-- 查看某个上传表的结构
DESCRIBE upload_1_test_20260108143025;
```

---

## 📊 性能测试

### 1. 统计分析性能

```python
import time
import pandas as pd
from app.services.stats_analyzer import StatsAnalyzer

df = pd.DataFrame({
    'sales': range(1000),
    'profit': range(1000)
})

start = time.time()
stats = StatsAnalyzer.analyze(df, "test")
elapsed = time.time() - start

print(f"分析耗时: {elapsed:.3f}秒")
# 预期：< 1秒
```

### 2. 图表推荐性能

```python
import time
from app.services.chart_recommender import ChartRecommender

start = time.time()
chart_type = ChartRecommender.recommend(df, "test")
elapsed = time.time() - start

print(f"推荐耗时: {elapsed:.3f}秒")
# 预期：< 0.1秒
```

### 3. 查询重写性能

```python
import time
from app.services.query_rewriter import QueryRewriter

history = [
    {"role": "user", "content": "查询销售额"},
    {"role": "assistant", "content": "结果"}
]

start = time.time()
rewritten = QueryRewriter.rewrite_query("按城市拆分", history)
elapsed = time.time() - start

print(f"重写耗时: {elapsed:.3f}秒")
# 预期：< 2秒
```

---

## ✅ 测试结果记录

| 功能 | 测试结果 | 备注 |
|------|---------|------|
| Excel上传 | ⬜ 通过 / ❌ 失败 |  |
| 计算指标 | ⬜ 通过 / ❌ 失败 |  |
| 数据集删除 | ⬜ 通过 / ❌ 失败 |  |
| 统计分析 | ⬜ 通过 / ❌ 失败 |  |
| AI洞察 | ⬜ 通过 / ❌ 失败 |  |
| 图表推荐 | ⬜ 通过 / ❌ 失败 |  |
| 查询重写 | ⬜ 通过 / ❌ 失败 |  |
| Excel导出 | ⬜ 通过 / ❌ 失败 |  |
| CSV导出 | ⬜ 通过 / ❌ 失败 |  |

---

## 🐛 问题记录

| 问题描述 | 严重程度 | 状态 | 解决方案 |
|---------|---------|------|---------|
|  |  |  |  |

---

## 📝 测试结论

- [ ] 所有核心功能正常
- [ ] 性能满足要求
- [ ] 无严重Bug
- [ ] 可以发布

**测试人**: _____________  
**测试日期**: _____________  
**签名**: _____________

