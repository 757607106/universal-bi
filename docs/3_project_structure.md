# 项目目录结构说明

本文档描述了 Universal BI 项目的当前目录结构及其主要职责。

## 根目录结构

```text
universal-bi/
├── backend/                # 后端项目 (FastAPI)
├── frontend/               # 前端项目 (Vue 3 + Vite)
├── docs/                   # 项目文档
├── figma_source/           # Figma 生成的原始 React 代码 (参考用)
└── requirements.txt        # Python 依赖列表
```

## 后端结构 (`backend/app/`)

后端采用 FastAPI 框架，遵循典型的分层架构。

```text
backend/app/
├── api/
│   └── v1/
│       └── endpoints/      # API 路由处理函数
│           └── datasource.py # 数据源管理接口 (CRUD, 测试连接)
├── core/                   # 核心配置
│   ├── config.py           # 环境变量与应用配置
│   └── security.py         # 安全相关 (密码加密等)
├── db/                     # 数据库相关
│   └── session.py          # 数据库会话管理
├── models/                 # SQLAlchemy ORM 模型 (映射数据库表)
│   ├── base.py             # 模型基类
│   └── metadata.py         # 元数据模型 (如 DataSource)
├── schemas/                # Pydantic 数据验证模型 (用于 API 输入/输出)
│   └── datasource.py       # 数据源相关的 Schema
├── services/               # 业务逻辑服务层
│   └── db_inspector.py     # 数据库反射与连接测试服务
└── main.py                 # 应用入口，注册路由与中间件
```

## 前端结构 (`frontend/src/`)

前端采用 Vue 3 (Composition API) + TypeScript + Element Plus + Tailwind CSS。

```text
frontend/src/
├── api/                    # API 接口封装
│   └── datasource.ts       # 数据源管理 API (Axios 请求)
├── components/             # Vue 组件
│   ├── AddConnectionDialog.vue  # 添加/编辑连接弹窗
│   ├── ConnectionCard.vue       # 数据源连接卡片
│   ├── DataConnectionHub.vue    # 数据连接管理主页面
│   ├── DeleteConfirmDialog.vue  # 删除确认弹窗
│   ├── ChatBI.vue               # 智能对话 BI 组件
│   ├── Dashboard.vue            # 仪表盘组件
│   ├── DatasetBuilder.vue       # 数据集构建器
│   ├── SQLViewDialog.vue        # SQL 查看弹窗
│   ├── ThemeToggle.vue          # 主题切换组件
│   └── TrainingProgressDialog.vue # 训练进度弹窗
├── composables/            # 组合式函数 (Hooks)
│   └── useTheme.ts         # 主题管理逻辑
├── App.vue                 # 根组件 (包含布局与路由逻辑)
├── main.ts                 # 入口文件 (挂载 Vue, 引入样式)
└── style.css               # 全局样式 (Tailwind 指令)
```

## 关键文件说明

- **backend/app/main.py**: 后端启动入口，负责初始化 FastAPI 应用和数据库表结构。
- **backend/app/services/db_inspector.py**: 核心服务类，用于处理不同数据库类型的连接测试和 Engine 创建。
- **frontend/src/api/datasource.ts**: 前端与后端数据源接口的通信桥梁，定义了类型接口。
- **frontend/src/components/DataConnectionHub.vue**: 数据源管理的核心页面，集成了列表展示、新增、编辑、删除等功能的入口。
