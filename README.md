# Universal BI - AI 驱动的自然语言数据分析平台

<div align="center">

**通过自然语言与数据库对话，让数据分析变得简单**

[![Python](https://img.shields.io/badge/Python-3.8+-blue.svg)](https://www.python.org/)
[![FastAPI](https://img.shields.io/badge/FastAPI-0.100+-green.svg)](https://fastapi.tiangolo.com/)
[![Vue.js](https://img.shields.io/badge/Vue.js-3.0+-brightgreen.svg)](https://vuejs.org/)
[![License](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)

</div>

## 📖 项目简介

Universal BI 是一个基于 AI 的智能数据分析平台，用户只需用自然语言提问，系统就能自动生成 SQL 查询、执行并返回可视化结果。

### ✨ 核心特性

- 🤖 **AI SQL 生成**：使用 Vanna AI + Qwen-Max 模型，自动将自然语言转换为 SQL
- 📊 **智能可视化**：根据查询结果自动推荐最佳图表类型（柱状图、折线图、表格等）
- 🔌 **多数据源支持**：支持 MySQL、PostgreSQL 等主流数据库
- 📦 **Dataset 管理**：可视化构建和训练数据集，提升 AI 准确率
- 📈 **仪表盘功能**：保存查询结果为卡片，构建个性化数据驾驶舱
- 🎨 **现代化 UI**：基于 Element Plus + Tailwind CSS 的美观界面
- 🌙 **主题切换**：支持亮色/暗色主题

## 🏗️ 技术架构

### 后端技术栈

- **Web 框架**：FastAPI（Python 3.8+）
- **AI 引擎**：Vanna AI（Legacy API + Qwen-Max）
- **向量数据库**：PostgreSQL + pgvector
- **ORM**：SQLAlchemy
- **数据库支持**：PostgreSQL（主数据库 + 向量存储）
- **缓存**：Redis
- **分析引擎**：DuckDB（用于多表分析）

### 前端技术栈

- **框架**：Vue 3 + TypeScript
- **构建工具**：Vite
- **UI 组件库**：Element Plus
- **CSS 框架**：Tailwind CSS
- **图表库**：ECharts
- **路由**：Vue Router

## 🚀 快速开始

### 环境要求

- Python 3.8+
- Node.js 16+
- PostgreSQL 12+ (with pgvector extension)
- Redis 5.0+（用于缓存）
- Docker & Docker Compose（可选，推荐）

### 方式一：一键部署（推荐）

使用自动化部署脚本，支持开发模式和 Docker 模式：

#### 开发模式（本地运行）

```bash
# 1. 克隆项目
git clone https://github.com/757607106/universal-bi.git
cd universal-bi

# 2. 执行一键部署脚本
bash setup.sh dev

# 3. 编辑 .env 配置文件（重要！）
vi .env
# 必须配置 DASHSCOPE_API_KEY

# 4. 启动服务
bash start_dev.sh
```

#### Docker 模式（容器化部署）

```bash
# 1. 克隆项目
git clone https://github.com/757607106/universal-bi.git
cd universal-bi

# 2. 执行 Docker 部署
bash setup.sh docker

# 3. 编辑 .env 配置文件（重要！）
vi .env
# 必须配置 DASHSCOPE_API_KEY

# 4. 启动服务
docker-compose up -d

# 查看日志
docker-compose logs -f
```

### 方式二：手动部署

#### 后端启动

1. **克隆项目**

```bash
git clone https://github.com/757607106/universal-bi.git
cd universal-bi
```

2. **配置环境变量**

```bash
# 复制环境变量模板
cp .env.example .env

# 编辑 .env 文件，至少配置以下项：
# - DASHSCOPE_API_KEY（必填）
# - SQLALCHEMY_DATABASE_URI（数据库连接）
# - REDIS_URL（Redis 连接）
vi .env
```

3. **安装 Python 依赖**

```bash
cd backend
pip install -r requirements.txt
```

4. **初始化数据库**

```bash
# 创建数据库表并插入初始数据
python init_db.py
```

5. **启动后端服务**

```bash
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

后端服务将运行在 `http://localhost:8000`

#### 前端启动

1. **安装依赖**

```bash
cd frontend
npm install
```

2. **启动开发服务器**

```bash
npm run dev
```

前端服务将运行在 `http://localhost:3000`

### 访问地址

部署完成后，访问以下地址：

- 🌐 **前端页面**：http://localhost:3000
- 🔧 **后端 API**：http://localhost:8000
- 📚 **API 文档**：http://localhost:8000/docs
- 👤 **默认管理员**：用户名 `admin`，密码 `admin123`（请登录后立即修改）

### 环境配置说明

#### 必填配置

```env
# 通义千问 API Key（必填）
# 获取地址：https://dashscope.console.aliyun.com/apiKey
DASHSCOPE_API_KEY=sk-xxxxxxxxxxxxxxxxxxxxxxxxxx
```

#### 数据库配置（可选）

```env
# PostgreSQL（统一主数据库，同时支持向量存储）
SQLALCHEMY_DATABASE_URI=postgresql://postgres:password@localhost:5432/universal_bi
PG_HOST=localhost
PG_PORT=5432
PG_DB=universal_bi
PG_USER=postgres
PG_PASSWORD=password
VECTOR_STORE_TYPE=pgvector
```

#### Redis 配置（可选）

```env
# Redis 缓存服务
REDIS_URL=redis://localhost:6379/0
# 如果设置了密码：
REDIS_URL=redis://:password@localhost:6379/0
```

## 📚 使用指南

### 1. 添加数据源

访问「数据连接中心」，点击「添加连接」，配置数据库连接信息：

- 数据源名称
- 数据库类型（MySQL/PostgreSQL）
- 主机地址、端口
- 数据库名、用户名、密码

### 2. 创建 Dataset

在「Dataset 管理」页面：

1. 点击「新建 Dataset」
2. 选择数据源
3. 选择需要训练的表（支持多选）
4. 点击「开始训练」，系统会自动提取 DDL 并训练 AI 模型

### 3. 开始对话查询

在「Chat BI」页面：

1. 选择已训练的 Dataset
2. 用自然语言提问，例如：
   - "查询上个月的销售额"
   - "统计每个产品的销量"
   - "按月统计订单数"
3. 系统自动生成 SQL 并执行
4. 结果以表格或图表形式展示

### 4. 保存到仪表盘

- 点击查询结果右侧的「保存到看板」按钮
- 选择或创建仪表盘
- 查询卡片会保存到仪表盘，支持一键刷新数据

## 🔧 QA 训练优化

为了提高 AI 生成 SQL 的准确率，可以使用 QA 对（Question-SQL Pair）进行训练：

```bash
cd backend
python scripts/train_qa_fix.py
```

编辑 `train_qa_fix.py` 中的 `qa_pairs` 列表，添加常见问题和对应的标准 SQL。

## 🐳 Docker 常用命令

```bash
# 启动所有服务
docker-compose up -d

# 停止所有服务
docker-compose down

# 重启服务
docker-compose restart

# 查看服务状态
docker-compose ps

# 查看实时日志
docker-compose logs -f

# 查看特定服务日志
docker-compose logs -f backend

# 重新构建并启动
docker-compose up -d --build

# 进入容器执行命令
docker exec -it universal-bi-backend bash

# 清理所有数据（谨慎！）
docker-compose down -v
```

## 🐞 故障排查

### 1. 后端启动失败

**问题**：数据库连接失败

```bash
# 检查数据库服务是否启动
docker-compose ps mysql
# 或
mysql -h localhost -u root -p

# 检查 .env 中的数据库连接配置
cat .env | grep SQLALCHEMY_DATABASE_URI
```

**问题**：DASHSCOPE_API_KEY 未配置

```bash
# 确认 API Key 已配置
cat .env | grep DASHSCOPE_API_KEY

# 获取 API Key：https://dashscope.console.aliyun.com/apiKey
```

### 2. Docker 容器启动失败

```bash
# 查看容器状态
docker-compose ps

# 查看错误日志
docker-compose logs backend
docker-compose logs mysql

# 重启服务
docker-compose restart

# 完全重新部署
docker-compose down
docker-compose up -d --build
```

### 3. Redis 连接问题

```bash
# 检查 Redis 服务
redis-cli ping
# 或 Docker 环境：
docker-compose exec redis redis-cli ping

# 检查 Redis 连接配置
cat .env | grep REDIS_URL
```

### 4. 前端访问 404

**问题**：前端页面刷新后 404

解决：确认 Vue Router 配置为 `history` 模式，且后端支持 SPA 路由

### 5. 性能问题

```bash
# 检查系统资源
docker stats

# 清理 Docker 缓存
docker system prune -a

# 清理 ChromaDB 向量数据（谨慎！）
rm -rf backend/chroma_db
```

## 📝 更新日志

### v0.2.0 (2026-01)

- ✅ 新增一键部署脚本
- ✅ 支持 Docker Compose 部署
- ✅ 添加 Redis 缓存支持
- ✅ 完善环境配置管理
- ✅ 数据库自动初始化

### v0.1.0 (2025-12)

- ✅ 基本功能实现
- ✅ Chat BI 自然语言查询
- ✅ Dataset 管理和训练
- ✅ Dashboard 看板功能

## 📂 项目结构

```
universal-bi/
├── backend/                 # 后端代码
│   ├── app/
│   │   ├── api/v1/         # API 端点
│   │   │   └── endpoints/
│   │   │       ├── chat.py          # Chat BI 接口
│   │   │       ├── dataset.py       # Dataset 管理
│   │   │       ├── datasource.py    # 数据源管理
│   │   │       └── dashboard.py     # 仪表盘管理
│   │   ├── core/           # 核心配置
│   │   │   ├── config.py            # 系统配置
│   │   │   └── security.py
│   │   ├── models/         # 数据模型
│   │   │   ├── base.py
│   │   │   └── metadata.py          # 数据源、Dataset、Dashboard 模型
│   │   ├── schemas/        # Pydantic Schema
│   │   ├── services/       # 业务逻辑
│   │   │   ├── vanna_manager.py     # Vanna AI 核心服务
│   │   │   └── db_inspector.py      # 数据库元数据检查
│   │   └── main.py         # FastAPI 应用入口
│   ├── scripts/            # 工具脚本
│   │   ├── train_qa_fix.py          # QA 训练脚本
│   │   └── generate_fake_data.py    # 生成测试数据
│   └── requirements.txt    # Python 依赖
├── frontend/               # 前端代码
│   ├── src/
│   │   ├── api/           # API 调用封装
│   │   ├── components/    # Vue 组件
│   │   │   ├── ChatBI.vue
│   │   │   ├── DatasetBuilder.vue
│   │   │   ├── Dashboard.vue
│   │   │   └── Charts/
│   │   ├── views/         # 页面视图
│   │   │   ├── Chat/      # Chat BI 页面
│   │   │   └── Dataset/   # Dataset 管理页面
│   │   ├── router/        # 路由配置
│   │   └── main.ts
│   └── package.json       # NPM 依赖
├── docs/                  # 文档
│   ├── 1_prd.md           # 产品需求文档
│   ├── 2_tech_stack.md    # 技术选型文档
│   └── 3_project_structure.md
└── README.md              # 项目说明
```

## 🎯 核心功能模块

### Chat BI - 自然语言查询

- 输入问题 → AI 生成 SQL → 执行 → 可视化
- 支持历史对话记录
- 一键保存查询到仪表盘

### Dataset Builder - 数据集管理

- 可视化选择表进行训练
- 实时训练进度展示
- 支持数据预览和 SQL 查看

### Dashboard - 数据驾驶舱

- 网格布局展示多个查询卡片
- 支持创建、编辑、删除仪表盘
- 卡片支持刷新、删除操作

## 🔑 关键技术亮点

### 1. Vanna AI Legacy API 集成

使用 Vanna Legacy API 替代 Vanna 2.0 Agent Memory，确保 QA 训练数据能够被正确检索和使用：

```python
class VannaLegacy(ChromaDB_VectorStore, OpenAI_Chat):
    def __init__(self, config=None):
        ChromaDB_VectorStore.__init__(self, config=config)
        self.client = OpenAIClient(
            api_key=config.get('api_key'),
            base_url='https://dashscope.aliyuncs.com/compatible-mode/v1'
        )
```

### 2. Qwen-Max 模型

经过测试，`qwen-max` 相比 `qwen-turbo` 在严格遵守 prompt 方面表现更好，能够稳定返回纯 SQL 而非引导性回答。

### 3. SQLAlchemy Eager Loading

使用 `selectinload` 预加载关联对象，避免 N+1 查询和 lazy loading 问题：

```python
stmt = select(Dataset).options(selectinload(Dataset.datasource))
```

## 🐛 已知问题与解决方案

### 表名前缀问题

**问题**：AI 可能忽略表名前缀（如 `dim_`、`fact_`）

**解决方案**：
1. 在 system prompt 中明确强调使用完整表名
2. 通过 QA 训练提供标准示例
3. 使用 `qwen-max` 模型提高准确率

## 🤝 贡献指南

欢迎提交 Issue 和 Pull Request！

## 📄 开源协议

MIT License

## 👥 作者

[@757607106](https://github.com/757607106)

## 🙏 致谢

- [Vanna AI](https://vanna.ai/) - AI SQL 生成引擎
- [FastAPI](https://fastapi.tiangolo.com/) - 现代化 Python Web 框架
- [Vue.js](https://vuejs.org/) - 渐进式 JavaScript 框架
- [Element Plus](https://element-plus.org/) - Vue 3 组件库
- [通义千问](https://tongyi.aliyun.com/) - 大语言模型支持

---

<div align="center">
⭐ 如果这个项目对你有帮助，请给一个 Star！
</div>
