# Universal BI - 项目结构

## 📁 核心目录

```
universal-bi/
├── backend/              # 后端服务 (FastAPI + Python)
│   ├── app/             # 应用代码
│   │   ├── api/         # API路由
│   │   ├── core/        # 核心配置
│   │   ├── models/      # 数据模型
│   │   ├── schemas/     # Pydantic schemas
│   │   └── services/    # 业务逻辑
│   ├── migrations/      # 数据库迁移脚本
│   ├── tests/           # 测试脚本
│   ├── init_db.py       # 数据库初始化
│   └── requirements.txt # Python依赖
│
├── frontend/            # 前端应用 (Vue 3 + TypeScript)
│   ├── src/
│   │   ├── api/         # API调用
│   │   ├── components/  # 可复用组件
│   │   ├── views/       # 页面视图
│   │   ├── router/      # 路由配置
│   │   └── store/       # 状态管理
│   └── package.json     # NPM依赖
│
├── docs/                # 文档中心
│   ├── general/         # 通用文档
│   │   ├── 1_prd.md                # 产品需求
│   │   ├── 2_tech_stack.md         # 技术栈
│   │   ├── 3_project_structure.md  # 项目结构
│   │   └── 4_feature_status.md     # 功能状态
│   ├── backend/         # 后端文档
│   │   └── CHAT_INTERFACE_FIX.md   # 最新修复文档
│   ├── frontend/        # 前端文档
│   └── user/            # 用户文档
│
├── docker-compose.yml   # Docker编排
├── setup.sh            # Linux/Mac部署脚本
├── setup.bat           # Windows部署脚本
├── QUICKSTART.md       # 快速开始指南
└── README.md           # 项目说明
```

## 🚀 快速开始

### 方式1: 本地开发
```bash
# 后端
cd backend
pip install -r requirements.txt
python init_db.py
uvicorn app.main:app --reload

# 前端
cd frontend
npm install
npm run dev
```

### 方式2: Docker部署（推荐）
```bash
docker-compose up -d
```

## 📚 核心文档

| 文档 | 说明 |
|------|------|
| `QUICKSTART.md` | 快速开始指南 |
| `docs/general/4_feature_status.md` | 功能状态和最新更新 |
| `docs/backend/CHAT_INTERFACE_FIX.md` | 聊天接口修复详情 |
| `README.md` | 项目说明 |

## 🔑 默认账户

- 用户名：`admin`
- 密码：`admin123`
- ⚠️ 首次登录后请修改密码

## 📊 访问地址

- 前端：http://localhost:3000
- 后端API：http://localhost:8000
- API文档：http://localhost:8000/docs
