# 🚀 多轮推理功能 - 快速启动指南

## 一键测试

### 1. 运行单元测试（推荐先执行）

```bash
cd /Users/pusonglin/PycharmProjects/universal-bi/backend
python3 test_multi_round.py
```

**预期输出：**
```
✅ 所有测试完成！
场景 1 - 显式标记: ✓
场景 2 - 隐式模式: ✓
场景 3 - 正常 SQL: ✓
...
```

### 2. 启动完整应用

**终端 1 - 启动后端：**
```bash
cd /Users/pusonglin/PycharmProjects/universal-bi/backend
uvicorn app.main:app --reload --log-level info
```

**终端 2 - 启动前端：**
```bash
cd /Users/pusonglin/PycharmProjects/universal-bi/frontend
npm run dev
```

### 3. 测试场景

访问前端：http://localhost:5173

#### 场景 A：多轮推理
1. 选择一个训练完成的数据集
2. 提问："查询大客户数量"
3. 观察：
   - 后端日志显示 "Detected intermediate SQL"
   - 前端执行步骤显示 "AI 进行了多轮推理 🧠"
   - 生成了正确的 SQL

#### 场景 B：澄清对话
1. 提问："统计订单"（故意模糊）
2. 观察：
   - 前端显示黄色澄清提示框 🟡
   - 内容："我无法确定您想统计什么..."
   - 提供了操作建议

#### 场景 C：SQL 自愈（已有功能）
1. 提问一个可能导致 SQL 错误的问题
2. 观察：
   - 执行步骤显示 "SQL 执行失败"
   - 显示 "AI 已修正 SQL"
   - 最终成功返回结果

---

## 查看日志

### 后端日志关键信息

```bash
# 查看完整日志
tail -f 后端运行的终端

# 关键日志标记
INFO: First round LLM response: ...          # 第一轮生成
INFO: Detected intermediate SQL: ...         # 检测到中间 SQL
INFO: Intermediate SQL returned values: ...  # 中间查询结果
INFO: Second round generated SQL: ...        # 第二轮生成
INFO: Clarification needed: ...              # 澄清请求
```

### 前端控制台

```javascript
// 打开浏览器开发者工具 (F12)
// 查看 Network 标签中的 /api/v1/chat/send 响应

{
  "sql": "SELECT ...",
  "chart_type": "table",  // 或 "clarification"
  "steps": [
    "第一轮：生成初始 SQL 响应",
    "检测到中间 SQL，启动多轮推理",
    "执行中间 SQL 成功，获取 3 行结果",
    ...
  ]
}
```

---

## 功能验证清单

- [ ] **单元测试通过**：`test_multi_round.py` 全部 ✓
- [ ] **中间 SQL 检测**：日志显示 "Detected intermediate SQL"
- [ ] **第二轮生成**：日志显示 "Second round generated SQL"
- [ ] **澄清对话 UI**：前端显示黄色提示框
- [ ] **执行步骤追踪**：前端可折叠查看详细步骤
- [ ] **自愈机制**：SQL 错误时自动修正

---

## 常见问题排查

### ❌ 测试失败："command not found: python"
**解决：** 使用 `python3` 代替 `python`

### ❌ 前端没有显示澄清对话
**检查：**
1. 后端返回的 `chart_type` 是否为 `"clarification"`
2. 前端是否正确导入 `QuestionFilled` 图标
3. 浏览器控制台是否有 Vue 组件错误

### ❌ 多轮推理没有触发
**可能原因：**
1. LLM 没有返回中间 SQL（调整检测关键词）
2. 中间 SQL 执行失败（查看后端日志）
3. 数据集没有包含相关术语（需要训练业务术语）

### ❌ 响应时间过长
**优化建议：**
1. 为中间查询添加 `LIMIT` 限制
2. 设置查询超时时间
3. 考虑缓存常见的中间查询结果

---

## 调试模式

### 启用详细日志

```bash
# 后端启动时添加环境变量
LOG_LEVEL=DEBUG uvicorn app.main:app --reload
```

### 查看执行步骤

在前端 Chat 界面，点击展开"查看执行步骤"折叠面板，查看完整的执行流程。

---

## 性能监控

### 响应时间对比

| 场景 | 原有流程 | 多轮推理 | 增加时间 |
|------|---------|---------|---------|
| 正常查询 | ~2s | ~2s | 0s |
| 中间 SQL | N/A | ~3-4s | +1-2s |
| 澄清对话 | 报错 | ~2s | 改善体验 |
| SQL 自愈 | ~4-6s | ~4-6s | 0s |

---

## 下一步

- [ ] 阅读详细文档：`MULTI_ROUND_REASONING.md`
- [ ] 查看实现总结：`IMPLEMENTATION_SUMMARY.md`
- [ ] 根据业务场景调整检测关键词
- [ ] 为中间查询添加安全限制
- [ ] 收集用户反馈，优化澄清对话内容

---

## 联系支持

遇到问题？检查以下资源：
1. 📖 技术文档：`MULTI_ROUND_REASONING.md`
2. 📋 实现总结：`IMPLEMENTATION_SUMMARY.md`
3. 🧪 单元测试：`test_multi_round.py`
4. 💻 核心代码：`app/services/vanna_manager.py`

---

**祝您使用愉快！** 🎉
