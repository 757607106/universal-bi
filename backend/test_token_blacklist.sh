#!/bin/bash
# Token 黑名单测试与监控快速启动脚本

echo "=================================="
echo "Token 黑名单测试与监控工具"
echo "=================================="
echo ""
echo "请选择操作："
echo "1. 启动后端服务"
echo "2. 测试退出登录功能"
echo "3. 监控 Redis 黑名单"
echo "4. 查看 Redis 当前状态"
echo "5. 清空所有黑名单"
echo "6. 退出"
echo ""
read -p "请输入选项 (1-6): " choice

case $choice in
    1)
        echo ""
        echo "正在启动后端服务..."
        echo "访问地址: http://localhost:8000"
        echo "API 文档: http://localhost:8000/docs"
        echo ""
        uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
        ;;
    2)
        echo ""
        echo "开始测试退出登录功能..."
        echo "注意：请确保后端服务已启动！"
        echo ""
        read -p "按 Enter 继续..."
        python3 test_logout.py
        ;;
    3)
        echo ""
        echo "启动 Redis 黑名单监控..."
        echo "提示：按 Ctrl+C 退出监控"
        echo ""
        sleep 2
        python3 monitor_redis.py
        ;;
    4)
        echo ""
        echo "=== Redis 服务状态 ==="
        redis-cli ping && echo "✓ Redis 正在运行" || echo "✗ Redis 未运行"
        echo ""
        echo "=== Redis 服务器信息 ==="
        redis-cli INFO server | grep -E "redis_version|tcp_port|uptime"
        echo ""
        echo "=== 黑名单统计 ==="
        blacklist_count=$(redis-cli KEYS "blacklist:token:*" | wc -l)
        echo "Token 黑名单数量: $blacklist_count"
        echo ""
        echo "=== 缓存统计 ==="
        cache_count=$(redis-cli KEYS "bi:cache:*" | wc -l)
        echo "查询缓存数量: $cache_count"
        echo ""
        ;;
    5)
        echo ""
        echo "警告：将清空所有 Token 黑名单！"
        read -p "确认清空？(y/N): " confirm
        if [ "$confirm" = "y" ] || [ "$confirm" = "Y" ]; then
            count=$(redis-cli KEYS "blacklist:token:*" | wc -l)
            if [ "$count" -gt 0 ]; then
                redis-cli KEYS "blacklist:token:*" | xargs redis-cli DEL
                echo "✓ 已清空 $count 个黑名单 Token"
            else
                echo "黑名单为空，无需清理"
            fi
        else
            echo "操作已取消"
        fi
        echo ""
        ;;
    6)
        echo ""
        echo "再见！"
        exit 0
        ;;
    *)
        echo ""
        echo "无效的选项"
        exit 1
        ;;
esac
