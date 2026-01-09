# Universal BI - 完整安装部署指南（新手版）

本文档面向新手用户，提供从零开始的完整安装部署流程，包括所有依赖软件的安装。

---

## 📋 目录

- [系统要求](#系统要求)
- [第一部分：环境准备](#第一部分环境准备)
  - [1. 安装 Python 3.8+](#1-安装-python-38)
  - [2. 安装 Node.js 16+](#2-安装-nodejs-16)
  - [3. 安装 MySQL 数据库](#3-安装-mysql-数据库)
  - [4. 安装 Redis 缓存](#4-安装-redis-缓存)
- [第二部分：项目部署](#第二部分项目部署)
  - [5. 克隆项目代码](#5-克隆项目代码)
  - [6. 配置环境变量](#6-配置环境变量)
  - [7. 初始化数据库](#7-初始化数据库)
  - [8. 安装项目依赖](#8-安装项目依赖)
  - [9. 启动服务](#9-启动服务)
- [第三部分：验证与使用](#第三部分验证与使用)
- [常见问题排查](#常见问题排查)

---

## 系统要求

- **操作系统**: macOS / Linux / Windows 10+
- **内存**: 至少 4GB RAM（推荐 8GB+）
- **磁盘空间**: 至少 5GB 可用空间
- **网络**: 需要访问互联网（下载依赖、调用 AI API）

---

## 第一部分：环境准备

### 1. 安装 Python 3.8+

#### macOS

```bash
# 方法一：使用 Homebrew（推荐）
brew install python@3.12

# 验证安装
python3 --version
# 输出应为: Python 3.12.x
```

#### Linux (Ubuntu/Debian)

```bash
# 更新软件源
sudo apt update

# 安装 Python
sudo apt install python3 python3-pip python3-venv

# 验证安装
python3 --version
```

#### Windows

1. 访问 [Python 官网](https://www.python.org/downloads/)
2. 下载 Windows 安装包（3.8 或更高版本）
3. 运行安装程序，**勾选** "Add Python to PATH"
4. 打开命令提示符，验证安装：

```cmd
python --version
```

---

### 2. 安装 Node.js 16+

#### macOS

```bash
# 使用 Homebrew 安装
brew install node@18

# 验证安装
node --version   # 应输出 v18.x.x
npm --version    # 应输出 9.x.x
```

#### Linux (Ubuntu/Debian)

```bash
# 使用 NodeSource 官方源
curl -fsSL https://deb.nodesource.com/setup_18.x | sudo -E bash -
sudo apt-get install -y nodejs

# 验证安装
node --version
npm --version
```

#### Windows

1. 访问 [Node.js 官网](https://nodejs.org/)
2. 下载 LTS 版本（推荐 18.x）
3. 运行安装程序（默认选项即可）
4. 打开命令提示符，验证安装：

```cmd
node --version
npm --version
```

---

### 3. 安装 MySQL 数据库

#### macOS

```bash
# 使用 Homebrew 安装
brew install mysql

# 启动 MySQL 服务
brew services start mysql

# 首次安装后设置 root 密码
mysql_secure_installation
# 按提示操作：
# - 设置 root 密码（建议设置）
# - 移除匿名用户: Y
# - 禁止 root 远程登录: Y
# - 移除测试数据库: Y
# - 重新加载权限表: Y

# 登录 MySQL（如果未设置密码，直接回车）
mysql -u root -p
```

#### Linux (Ubuntu/Debian)

```bash
# 安装 MySQL Server
sudo apt update
sudo apt install mysql-server

# 启动 MySQL 服务
sudo systemctl start mysql
sudo systemctl enable mysql  # 设置开机自启

# 运行安全配置脚本
sudo mysql_secure_installation

# 登录 MySQL
sudo mysql -u root -p
```

#### Windows

1. 访问 [MySQL 官网](https://dev.mysql.com/downloads/installer/)
2. 下载 MySQL Installer（推荐使用 Web Installer）
3. 运行安装程序：
   - 选择 "Developer Default"
   - 设置 root 密码（请牢记！）
   - 保持其他选项默认
4. 安装完成后，打开 MySQL Command Line Client：

```cmd
# 输入刚才设置的 root 密码登录
```

#### 创建数据库

登录 MySQL 后，执行以下命令创建数据库：

```sql
-- 创建 Universal BI 数据库
CREATE DATABASE universal_bi 
CHARACTER SET utf8mb4 
COLLATE utf8mb4_unicode_ci;

-- 查看数据库
SHOW DATABASES;

-- 退出 MySQL
EXIT;
```

---

### 4. 安装 Redis 缓存

Redis 用于缓存查询结果，提升系统性能。

#### macOS

```bash
# 使用 Homebrew 安装
brew install redis

# 启动 Redis 服务
brew services start redis

# 验证 Redis 运行状态
redis-cli ping
# 应输出: PONG
```

#### Linux (Ubuntu/Debian)

```bash
# 安装 Redis
sudo apt update
sudo apt install redis-server

# 启动 Redis 服务
sudo systemctl start redis-server
sudo systemctl enable redis-server  # 设置开机自启

# 验证 Redis
redis-cli ping
# 应输出: PONG
```

#### Windows

1. 访问 [Redis Windows 版本](https://github.com/microsoftarchive/redis/releases)
2. 下载最新的 `.msi` 安装包
3. 运行安装程序（默认选项即可）
4. 打开命令提示符：

```cmd
# 启动 Redis 服务
redis-server

# 新开一个命令提示符窗口，验证
redis-cli ping
# 应输出: PONG
```

---

## 第二部分：项目部署

### 5. 克隆项目代码

```bash
# 克隆 GitHub 仓库（替换为你的实际仓库地址）
git clone https://github.com/yourusername/universal-bi.git

# 进入项目目录
cd universal-bi

# 查看项目结构
ls -la
```

如果未安装 Git：
- macOS: `brew install git`
- Linux: `sudo apt install git`
- Windows: 下载 [Git for Windows](https://git-scm.com/download/win)

---

### 6. 配置环境变量

#### 6.1 创建配置文件

```bash
# 复制环境变量模板
cp .env.example .env

# 使用文本编辑器打开 .env
# macOS/Linux: vi .env 或 nano .env
# Windows: notepad .env
```

#### 6.2 获取通义千问 API Key（必填）

1. 访问 [阿里云 DashScope 控制台](https://dashscope.console.aliyun.com/apiKey)
2. 登录阿里云账号（没有则注册）
3. 创建或复制 API Key（格式：`sk-xxxxxxxxxxxxxx`）

#### 6.3 编辑配置文件

打开 `.env` 文件，修改以下关键配置：

```env
# ========== 必填项 ==========

# 通义千问 API Key（必填！）
DASHSCOPE_API_KEY=sk-你的实际API密钥

# ========== 数据库配置 ==========

# MySQL 连接（根据你的实际配置修改）
SQLALCHEMY_DATABASE_URI=mysql+pymysql://root:你的MySQL密码@localhost:3306/universal_bi?charset=utf8mb4

# 示例：如果 MySQL root 密码为 123456
# SQLALCHEMY_DATABASE_URI=mysql+pymysql://root:123456@localhost:3306/universal_bi?charset=utf8mb4

# 如果没有设置 MySQL 密码，使用：
# SQLALCHEMY_DATABASE_URI=mysql+pymysql://root@localhost:3306/universal_bi?charset=utf8mb4

# ========== Redis 配置 ==========

# Redis 连接（如果未设置密码，保持默认即可）
REDIS_URL=redis://localhost:6379/0

# ========== 其他配置（可保持默认）==========

# JWT 密钥（生产环境建议修改）
SECRET_KEY=dev_secret_key_change_in_production_123456

# 开发模式
DEV=True
```

**保存文件后，验证配置：**

```bash
# 检查 API Key 是否正确配置
cat .env | grep DASHSCOPE_API_KEY

# 检查数据库配置
cat .env | grep SQLALCHEMY_DATABASE_URI
```

---

### 7. 初始化数据库

#### 7.1 创建数据库（如果第3步未创建）

```bash
# 登录 MySQL
mysql -u root -p

# 在 MySQL 中执行
CREATE DATABASE IF NOT EXISTS universal_bi CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;
EXIT;
```

#### 7.2 运行数据库迁移脚本

```bash
# 进入后端目录
cd backend

# 创建表结构
python init_db.py

# 如果提示找不到 Python，尝试：
# python3 init_db.py
```

**预期输出：**
```
✅ 数据库连接成功
✅ 创建表结构成功
✅ 插入初始管理员账号成功
用户名: admin
密码: admin123
```

---

### 8. 安装项目依赖

#### 8.1 安装后端依赖

```bash
# 确保在 backend 目录下
cd /path/to/universal-bi/backend

# 安装 Python 依赖（可能需要几分钟）
pip install -r requirements.txt

# 如果提示权限错误，使用：
# pip install --user -r requirements.txt

# macOS/Linux 推荐使用虚拟环境：
python3 -m venv venv
source venv/bin/activate  # Windows: venv\Scripts\activate
pip install -r requirements.txt
```

#### 8.2 安装前端依赖

```bash
# 进入前端目录
cd ../frontend

# 安装 Node.js 依赖（可能需要几分钟）
npm install

# 如果下载速度慢，可以使用淘宝镜像：
# npm install --registry=https://registry.npmmirror.com
```

---

### 9. 启动服务

#### 方法一：手动分别启动（推荐新手）

**终端窗口 1 - 启动后端：**

```bash
# 进入后端目录
cd /path/to/universal-bi/backend

# 启动 FastAPI 服务
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000

# 预期输出：
# INFO:     Uvicorn running on http://0.0.0.0:8000
# INFO:     Application startup complete.
```

**终端窗口 2 - 启动前端：**

```bash
# 打开新终端窗口
# 进入前端目录
cd /path/to/universal-bi/frontend

# 启动 Vite 开发服务器
npm run dev

# 预期输出：
# VITE ready in xxx ms
# ➜  Local:   http://localhost:3000/
```

#### 方法二：使用一键启动脚本

```bash
# 在项目根目录执行
cd /path/to/universal-bi

# macOS/Linux
bash setup.sh dev
bash start_dev.sh

# Windows
setup.bat dev
start_dev.bat
```

---

## 第三部分：验证与使用

### 1. 验证服务状态

打开浏览器，访问以下地址：

| 服务 | 地址 | 说明 |
|------|------|------|
| **前端页面** | http://localhost:3000 | 主界面 |
| **后端 API** | http://localhost:8000 | API 服务 |
| **API 文档** | http://localhost:8000/docs | Swagger 文档 |

### 2. 首次登录

1. 访问 http://localhost:3000
2. 使用初始管理员账号登录：
   - **用户名**: `admin`
   - **密码**: `admin123`
3. **登录后立即修改密码！**

### 3. 快速上手

#### 3.1 添加数据源

1. 点击左侧菜单「数据连接中心」
2. 点击「添加连接」
3. 填写数据库连接信息：
   ```
   名称: 我的MySQL
   类型: MySQL
   主机: localhost
   端口: 3306
   数据库: your_database
   用户名: root
   密码: your_password
   ```
4. 点击「测试连接」，成功后保存

#### 3.2 创建数据集

1. 点击「Dataset 管理」
2. 点击「新建 Dataset」
3. 选择刚才创建的数据源
4. 选择要分析的表（可多选）
5. 点击「开始训练」

   训练过程需要 1-5 分钟，系统会：
   - 提取表结构（DDL）
   - 生成示例查询
   - 训练 AI 模型

#### 3.3 开始对话查询

1. 点击「Chat BI」
2. 选择已训练的 Dataset
3. 输入自然语言问题，例如：
   - "查询所有用户"
   - "统计每月的销售额"
   - "找出销量最高的 10 个产品"
4. AI 自动生成 SQL 并执行
5. 结果以表格或图表展示

---

## 常见问题排查

### Q1: 后端启动失败 - 数据库连接错误

**错误信息：**
```
sqlalchemy.exc.OperationalError: (pymysql.err.OperationalError) 
(2003, "Can't connect to MySQL server")
```

**解决方法：**

1. **检查 MySQL 是否启动：**
   ```bash
   # macOS
   brew services list | grep mysql
   
   # Linux
   sudo systemctl status mysql
   
   # Windows
   # 打开「服务」查看 MySQL 服务状态
   ```

2. **检查连接配置：**
   ```bash
   cat .env | grep SQLALCHEMY_DATABASE_URI
   ```
   
   确保：
   - 主机地址正确（通常是 `localhost`）
   - 端口正确（MySQL 默认 3306）
   - 用户名和密码正确
   - 数据库 `universal_bi` 已创建

3. **测试 MySQL 连接：**
   ```bash
   mysql -h localhost -u root -p
   # 输入密码后能登录说明 MySQL 正常
   ```

---

### Q2: DASHSCOPE_API_KEY 错误

**错误信息：**
```
Error: Invalid API Key
```

**解决方法：**

1. 确认 API Key 格式正确（以 `sk-` 开头）
2. 检查 `.env` 文件配置：
   ```bash
   cat .env | grep DASHSCOPE_API_KEY
   ```
3. 重新获取 API Key：
   - 访问 https://dashscope.console.aliyun.com/apiKey
   - 创建新的 API Key
   - 更新 `.env` 文件
   - 重启后端服务

---

### Q3: Redis 连接失败

**错误信息：**
```
redis.exceptions.ConnectionError: Error connecting to Redis
```

**解决方法：**

1. **检查 Redis 是否启动：**
   ```bash
   # 测试连接
   redis-cli ping
   # 应输出: PONG
   
   # 如果失败，启动 Redis
   # macOS
   brew services start redis
   
   # Linux
   sudo systemctl start redis-server
   ```

2. **检查配置：**
   ```bash
   cat .env | grep REDIS_URL
   ```

3. **临时禁用 Redis（测试用）：**
   
   如果暂时无法解决 Redis 问题，系统会自动降级，不影响核心功能。

---

### Q4: 前端页面空白

**解决方法：**

1. **检查后端是否启动：**
   ```bash
   curl http://localhost:8000
   # 应返回: {"message": "Welcome to Universal BI API"}
   ```

2. **清理缓存重新构建：**
   ```bash
   cd frontend
   rm -rf node_modules dist
   npm install
   npm run dev
   ```

3. **检查浏览器控制台：**
   - 按 F12 打开开发者工具
   - 查看 Console 和 Network 标签是否有错误

---

### Q5: 训练失败

**可能原因：**
- 数据库连接中断
- 表结构复杂或包含特殊字符
- API Key 额度不足

**解决方法：**

1. 查看训练日志：
   - 在「Dataset 管理」页面点击「查看日志」
2. 检查表结构：
   - 确保表名和字段名使用英文
   - 避免使用 SQL 关键字
3. 重新训练：
   - 删除数据集
   - 重新创建并训练

---

### Q6: 查询结果不准确

**优化方法：**

1. **添加业务术语：**
   - 在「Dataset 管理」中添加业务术语
   - 示例：术语"活跃用户"，定义"最近30天有登录的用户"

2. **训练 QA 对：**
   ```bash
   cd backend
   python scripts/train_qa_fix.py
   ```

3. **使用更高级的模型：**
   - 修改 `.env` 中的 `QWEN_MODEL=qwen-max`

---

## 📚 下一步

恭喜！你已经成功部署 Universal BI。接下来可以：

- 📖 阅读[完整文档](README.md)
- 🎯 查看[功能特性](docs/general/4_feature_status.md)
- 🛠️ 了解[技术架构](docs/general/2_tech_stack.md)
- 💬 提问或反馈：[GitHub Issues](https://github.com/yourusername/universal-bi/issues)

---

## 🆘 获取帮助

如果遇到本文档未覆盖的问题：

- 📧 Email: support@universal-bi.com
- 💬 GitHub Issues: https://github.com/yourusername/universal-bi/issues
- 📖 官方文档: https://universal-bi.readthedocs.io

---

<div align="center">
⭐ 如果这个项目对你有帮助，请给一个 Star！
</div>
