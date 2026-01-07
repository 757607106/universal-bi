# Universal BI - 快速开始指南

欢迎使用 Universal BI！本指南将帮助你在 5 分钟内完成部署。

## 🎯 部署方式选择

### 推荐：Docker Compose（最简单）

适合：
- ✅ 生产环境部署
- ✅ 快速体验和测试
- ✅ 不想手动配置依赖

### 开发模式（手动安装）

适合：
- ✅ 本地开发和调试
- ✅ 需要修改源代码
- ✅ 不想使用 Docker

---

## 🐳 Docker Compose 部署（推荐）

### 第一步：准备工作

```bash
# 确保已安装 Docker 和 Docker Compose
docker --version
docker-compose --version

# 如未安装，参考：
# macOS: https://docs.docker.com/desktop/install/mac-install/
# Linux: https://docs.docker.com/engine/install/
```

### 第二步：克隆项目

```bash
git clone https://github.com/757607106/universal-bi.git
cd universal-bi
```

### 第三步：配置环境变量

```bash
# 复制环境变量模板
cp .env.example .env

# 编辑 .env 文件
vi .env  # 或使用任意编辑器
```

**必须配置以下内容：**

```env
# 通义千问 API Key（必填）
# 获取地址：https://dashscope.console.aliyun.com/apiKey
DASHSCOPE_API_KEY=sk-your-actual-api-key-here

# 数据库密码（建议修改）
MYSQL_ROOT_PASSWORD=your_secure_password
POSTGRES_PASSWORD=your_secure_password
```

### 第四步：启动服务

```bash
# 一键启动所有服务
docker-compose up -d

# 查看启动日志
docker-compose logs -f
```

等待 1-2 分钟，所有服务启动完成。

### 第五步：访问系统

打开浏览器访问：

- 🌐 **前端页面**：http://localhost:3000
- 📚 **API 文档**：http://localhost:8000/docs
- 👤 **默认账户**：用户名 `admin`，密码 `admin123`

---

## 💻 开发模式部署

### 第一步：准备环境

```bash
# 确保已安装以下软件：
python3 --version  # Python 3.8+
node --version     # Node.js 16+
mysql --version    # MySQL 5.7+ 或 PostgreSQL 12+
redis-cli --version  # Redis 5.0+
```

### 第二步：快速部署

```bash
# 克隆项目
git clone https://github.com/757607106/universal-bi.git
cd universal-bi

# 执行一键部署脚本
bash setup.sh dev
```

脚本将自动：
1. ✅ 安装后端 Python 依赖
2. ✅ 安装前端 Node.js 依赖
3. ✅ 创建 .env 配置文件
4. ✅ 生成启动脚本

### 第三步：配置 API Key

```bash
# 编辑 .env 文件
vi .env

# 设置通义千问 API Key
DASHSCOPE_API_KEY=sk-your-actual-api-key-here
```

### 第四步：初始化数据库

```bash
cd backend
python init_db.py
```

### 第五步：启动服务

```bash
# 使用生成的启动脚本
bash start_dev.sh

# 或者手动分别启动：
# 后端：cd backend && uvicorn app.main:app --reload
# 前端：cd frontend && npm run dev
```

---

## ✅ 验证部署

### 1. 检查服务状态

**Docker 模式：**
```bash
docker-compose ps
```

**开发模式：**
```bash
# 检查后端
curl http://localhost:8000/api/v1/health

# 检查前端
curl http://localhost:3000
```

### 2. 登录系统

- 访问：http://localhost:3000
- 用户名：`admin`
- 密码：`admin123`

**⚠️ 首次登录后请立即修改密码！**

### 3. 测试功能

1. **添加数据源**
   - 进入「数据连接中心」
   - 点击「添加连接」
   - 配置你的数据库连接

2. **创建 Dataset**
   - 进入「Dataset 管理」
   - 创建新 Dataset
   - 选择表并训练

3. **开始对话**
   - 进入「Chat BI」
   - 选择 Dataset
   - 用自然语言提问

---

## 🐞 常见问题

### Q1: 后端启动失败，提示数据库连接错误

**解决方法：**

```bash
# Docker 模式：检查 MySQL 容器
docker-compose ps mysql
docker-compose logs mysql

# 开发模式：检查 MySQL 服务
mysql -h localhost -u root -p

# 检查 .env 配置
cat .env | grep SQLALCHEMY_DATABASE_URI
```

### Q2: DASHSCOPE_API_KEY 错误

**解决方法：**

1. 访问 https://dashscope.console.aliyun.com/apiKey
2. 创建或复制 API Key
3. 确保 .env 中正确配置：
   ```env
   DASHSCOPE_API_KEY=sk-xxxxxxxxxxxxxxxx
   ```
4. 重启服务

### Q3: Redis 连接失败

**解决方法：**

```bash
# Docker 模式
docker-compose ps redis
docker-compose restart redis

# 开发模式
redis-cli ping
# 如果失败，启动 Redis：
redis-server
```

### Q4: 前端页面空白或 404

**解决方法：**

```bash
# 检查后端是否正常
curl http://localhost:8000/api/v1/health

# 清理缓存重新构建
cd frontend
rm -rf node_modules dist
npm install
npm run dev
```

---

## 📚 下一步

- 📖 阅读[完整文档](../README.md)
- 🎯 查看[功能特性](../docs/general/4_feature_status.md)
- 🛠️ 了解[技术架构](../docs/general/2_tech_stack.md)
- 💬 提问或反馈：[GitHub Issues](https://github.com/757607106/universal-bi/issues)

---

## 🆘 需要帮助？

- 📧 Email: support@universal-bi.com
- 💬 GitHub Issues: https://github.com/757607106/universal-bi/issues
- 📖 文档中心: https://universal-bi.readthedocs.io

---

<div align="center">
⭐ 如果这个项目对你有帮助，请给一个 Star！
</div>
