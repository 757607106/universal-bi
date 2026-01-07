#!/bin/bash

# ========================================
# Universal BI 一键部署脚本
# ========================================
# 功能：自动检查环境、安装依赖、配置服务
# 支持：macOS、Linux（Ubuntu/Debian/CentOS）
# 使用：bash setup.sh [dev|docker]
# ========================================

set -e  # 遇到错误立即退出

# 颜色输出
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# 日志函数
log_info() {
    echo -e "${BLUE}[INFO]${NC} $1"
}

log_success() {
    echo -e "${GREEN}[SUCCESS]${NC} $1"
}

log_warning() {
    echo -e "${YELLOW}[WARNING]${NC} $1"
}

log_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

# 打印 Logo
print_logo() {
    cat << "EOF"
 _   _       _                          _   ____ ___ 
| | | |_ __ (_)_   _____ _ __ ___  __ _| | | __ )_ _|
| | | | '_ \| \ \ / / _ \ '__/ __|/ _` | | |  _ \| | 
| |_| | | | | |\ V /  __/ |  \__ \ (_| | | | |_) | | 
 \___/|_| |_|_| \_/ \___|_|  |___/\__,_|_| |____/___|
                                                      
      AI 驱动的自然语言数据分析平台
EOF
    echo ""
}

# 检测操作系统
detect_os() {
    if [[ "$OSTYPE" == "darwin"* ]]; then
        OS="macos"
        log_info "检测到操作系统: macOS"
    elif [[ "$OSTYPE" == "linux-gnu"* ]]; then
        if [ -f /etc/os-release ]; then
            . /etc/os-release
            OS=$ID
            log_info "检测到操作系统: $NAME"
        else
            OS="linux"
            log_info "检测到操作系统: Linux"
        fi
    else
        log_error "不支持的操作系统: $OSTYPE"
        exit 1
    fi
}

# 检查命令是否存在
check_command() {
    if command -v $1 &> /dev/null; then
        log_success "$1 已安装: $(command -v $1)"
        return 0
    else
        log_warning "$1 未安装"
        return 1
    fi
}

# 安装 Python
install_python() {
    if check_command python3; then
        PYTHON_VERSION=$(python3 --version | cut -d " " -f 2)
        log_info "Python 版本: $PYTHON_VERSION"
        return
    fi
    
    log_info "开始安装 Python 3..."
    if [[ "$OS" == "macos" ]]; then
        brew install python@3.10
    elif [[ "$OS" == "ubuntu" ]] || [[ "$OS" == "debian" ]]; then
        sudo apt-get update
        sudo apt-get install -y python3 python3-pip python3-venv
    elif [[ "$OS" == "centos" ]] || [[ "$OS" == "rhel" ]]; then
        sudo yum install -y python3 python3-pip
    fi
    log_success "Python 安装完成"
}

# 安装 Node.js
install_nodejs() {
    if check_command node; then
        NODE_VERSION=$(node --version)
        log_info "Node.js 版本: $NODE_VERSION"
        return
    fi
    
    log_info "开始安装 Node.js..."
    if [[ "$OS" == "macos" ]]; then
        brew install node@18
    elif [[ "$OS" == "ubuntu" ]] || [[ "$OS" == "debian" ]]; then
        curl -fsSL https://deb.nodesource.com/setup_18.x | sudo -E bash -
        sudo apt-get install -y nodejs
    elif [[ "$OS" == "centos" ]] || [[ "$OS" == "rhel" ]]; then
        curl -fsSL https://rpm.nodesource.com/setup_18.x | sudo bash -
        sudo yum install -y nodejs
    fi
    log_success "Node.js 安装完成"
}

# 安装 Docker
install_docker() {
    if check_command docker; then
        DOCKER_VERSION=$(docker --version)
        log_info "Docker 版本: $DOCKER_VERSION"
        return
    fi
    
    log_info "开始安装 Docker..."
    if [[ "$OS" == "macos" ]]; then
        log_warning "请手动安装 Docker Desktop: https://www.docker.com/products/docker-desktop"
        exit 1
    elif [[ "$OS" == "ubuntu" ]] || [[ "$OS" == "debian" ]]; then
        curl -fsSL https://get.docker.com | sh
        sudo usermod -aG docker $USER
    elif [[ "$OS" == "centos" ]] || [[ "$OS" == "rhel" ]]; then
        sudo yum install -y docker
        sudo systemctl start docker
        sudo systemctl enable docker
        sudo usermod -aG docker $USER
    fi
    log_success "Docker 安装完成"
    log_warning "请重新登录以使 Docker 组权限生效"
}

# 配置环境变量
setup_env() {
    if [ ! -f .env ]; then
        log_info "创建 .env 配置文件..."
        cp .env.example .env
        log_success ".env 文件已创建"
        
        echo ""
        log_warning "重要：请编辑 .env 文件，配置以下必填项："
        echo "  1. DASHSCOPE_API_KEY (通义千问 API Key)"
        echo "  2. 数据库连接信息（如需修改）"
        echo ""
        read -p "是否现在编辑 .env 文件? (y/n) " -n 1 -r
        echo
        if [[ $REPLY =~ ^[Yy]$ ]]; then
            ${EDITOR:-vi} .env
        fi
    else
        log_info ".env 文件已存在，跳过创建"
    fi
}

# 开发模式部署
setup_dev() {
    log_info "========== 开发模式部署 =========="
    
    # 安装依赖
    install_python
    install_nodejs
    
    # 配置环境变量
    setup_env
    
    # 安装后端依赖
    log_info "安装后端 Python 依赖..."
    cd backend
    if [ ! -d "venv" ]; then
        python3 -m venv venv
    fi
    source venv/bin/activate
    pip install -r requirements.txt -i https://mirrors.aliyun.com/pypi/simple/
    cd ..
    log_success "后端依赖安装完成"
    
    # 安装前端依赖
    log_info "安装前端 Node.js 依赖..."
    cd frontend
    npm install --registry=https://registry.npmmirror.com
    cd ..
    log_success "前端依赖安装完成"
    
    # 创建启动脚本
    cat > start_dev.sh << 'SCRIPT'
#!/bin/bash
echo "启动 Universal BI 开发服务..."

# 启动后端
cd backend
source venv/bin/activate
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000 &
BACKEND_PID=$!
cd ..

# 启动前端
cd frontend
npm run dev &
FRONTEND_PID=$!
cd ..

echo "后端服务运行在: http://localhost:8000"
echo "前端服务运行在: http://localhost:3000"
echo "API 文档: http://localhost:8000/docs"
echo ""
echo "按 Ctrl+C 停止所有服务"

# 等待中断信号
trap "kill $BACKEND_PID $FRONTEND_PID; exit" INT TERM
wait
SCRIPT
    chmod +x start_dev.sh
    
    echo ""
    log_success "========== 开发环境配置完成 =========="
    echo ""
    log_info "启动开发服务:"
    echo "  bash start_dev.sh"
    echo ""
    log_info "或者分别启动:"
    echo "  后端: cd backend && source venv/bin/activate && uvicorn app.main:app --reload"
    echo "  前端: cd frontend && npm run dev"
    echo ""
}

# Docker 模式部署
setup_docker() {
    log_info "========== Docker 模式部署 =========="
    
    # 安装 Docker
    install_docker
    
    # 配置环境变量
    setup_env
    
    # 检查 Docker Compose
    if ! check_command docker-compose; then
        log_warning "docker-compose 未安装，尝试使用 docker compose"
        DOCKER_COMPOSE="docker compose"
    else
        DOCKER_COMPOSE="docker-compose"
    fi
    
    # 构建并启动服务
    log_info "构建 Docker 镜像..."
    $DOCKER_COMPOSE build
    
    log_info "启动 Docker 服务..."
    $DOCKER_COMPOSE up -d
    
    # 等待服务启动
    log_info "等待服务启动..."
    sleep 10
    
    # 检查服务状态
    $DOCKER_COMPOSE ps
    
    echo ""
    log_success "========== Docker 部署完成 =========="
    echo ""
    log_info "服务访问地址:"
    echo "  前端: http://localhost:3000"
    echo "  后端: http://localhost:8000"
    echo "  API 文档: http://localhost:8000/docs"
    echo ""
    log_info "常用命令:"
    echo "  查看日志: $DOCKER_COMPOSE logs -f"
    echo "  重启服务: $DOCKER_COMPOSE restart"
    echo "  停止服务: $DOCKER_COMPOSE down"
    echo "  查看状态: $DOCKER_COMPOSE ps"
    echo ""
}

# 主函数
main() {
    print_logo
    detect_os
    
    # 获取部署模式
    MODE=${1:-dev}
    
    case $MODE in
        dev)
            setup_dev
            ;;
        docker)
            setup_docker
            ;;
        *)
            log_error "无效的部署模式: $MODE"
            echo "使用方法: bash setup.sh [dev|docker]"
            echo "  dev    - 开发模式（本地安装依赖）"
            echo "  docker - Docker 模式（容器化部署）"
            exit 1
            ;;
    esac
    
    log_success "部署完成！"
}

# 执行主函数
main "$@"
