#!/usr/bin/env python3
"""
监控 Redis 黑名单 Key 的使用情况
"""
import time
import sys
from redis import Redis
from app.core.config import settings
from datetime import datetime

# 颜色输出
class Colors:
    GREEN = '\033[92m'
    RED = '\033[91m'
    YELLOW = '\033[93m'
    BLUE = '\033[94m'
    CYAN = '\033[96m'
    RESET = '\033[0m'

def clear_screen():
    """清屏"""
    print("\033[H\033[J", end="")

def format_size(size_bytes):
    """格式化字节大小"""
    for unit in ['B', 'KB', 'MB', 'GB']:
        if size_bytes < 1024.0:
            return f"{size_bytes:.2f} {unit}"
        size_bytes /= 1024.0
    return f"{size_bytes:.2f} TB"

def monitor_redis_blacklist(interval=2):
    """
    监控 Redis 黑名单
    
    Args:
        interval: 刷新间隔（秒）
    """
    print(f"{Colors.BLUE}正在连接 Redis...{Colors.RESET}")
    
    try:
        redis_client = Redis.from_url(settings.REDIS_URL, decode_responses=True)
        redis_client.ping()
        print(f"{Colors.GREEN}✓ Redis 连接成功: {settings.REDIS_URL}{Colors.RESET}\n")
    except Exception as e:
        print(f"{Colors.RED}✗ Redis 连接失败: {e}{Colors.RESET}")
        sys.exit(1)
    
    print(f"{Colors.YELLOW}提示: 按 Ctrl+C 退出监控{Colors.RESET}\n")
    time.sleep(1)
    
    iteration = 0
    
    try:
        while True:
            iteration += 1
            clear_screen()
            
            # 标题
            now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            print("=" * 80)
            print(f"{Colors.CYAN}Redis Token 黑名单监控{Colors.RESET}".center(90))
            print(f"更新时间: {now} | 刷新次数: {iteration}".center(80))
            print("=" * 80)
            print()
            
            # Redis 服务器信息
            try:
                info = redis_client.info("server")
                memory = redis_client.info("memory")
                
                print(f"{Colors.BLUE}【Redis 服务器信息】{Colors.RESET}")
                print(f"  版本: {info.get('redis_version', 'N/A')}")
                print(f"  端口: {info.get('tcp_port', 'N/A')}")
                print(f"  运行时间: {info.get('uptime_in_days', 0)} 天")
                print(f"  内存使用: {format_size(memory.get('used_memory', 0))}")
                print()
            except Exception as e:
                print(f"{Colors.RED}✗ 获取服务器信息失败: {e}{Colors.RESET}\n")
            
            # 黑名单统计
            try:
                blacklist_keys = redis_client.keys("blacklist:token:*")
                cache_keys = redis_client.keys("bi:cache:*")
                
                print(f"{Colors.BLUE}【Key 统计】{Colors.RESET}")
                print(f"  Token 黑名单: {Colors.YELLOW}{len(blacklist_keys)}{Colors.RESET} 个")
                print(f"  查询缓存: {Colors.YELLOW}{len(cache_keys)}{Colors.RESET} 个")
                print()
                
                # 黑名单详情
                if blacklist_keys:
                    print(f"{Colors.BLUE}【黑名单详情】{Colors.RESET}")
                    print(f"  {'序号':<6} {'Token 前缀':<50} {'剩余时间 (秒)':<15} {'状态':<10}")
                    print(f"  {'-'*6} {'-'*50} {'-'*15} {'-'*10}")
                    
                    for i, key in enumerate(blacklist_keys[:20], 1):  # 最多显示20个
                        try:
                            # 获取 TTL
                            ttl = redis_client.ttl(key)
                            
                            # 提取 token（去掉前缀）
                            token = key.replace("blacklist:token:", "")
                            token_preview = token[:47] + "..." if len(token) > 50 else token
                            
                            # 状态指示
                            if ttl > 3600:
                                status = f"{Colors.GREEN}长期{Colors.RESET}"
                            elif ttl > 300:
                                status = f"{Colors.YELLOW}中期{Colors.RESET}"
                            elif ttl > 0:
                                status = f"{Colors.RED}即将到期{Colors.RESET}"
                            else:
                                status = f"{Colors.RED}已过期{Colors.RESET}"
                            
                            print(f"  {i:<6} {token_preview:<50} {ttl:<15} {status:<10}")
                        except Exception as e:
                            print(f"  {i:<6} {key[:50]:<50} {'错误':<15} {str(e)[:10]}")
                    
                    if len(blacklist_keys) > 20:
                        print(f"\n  {Colors.YELLOW}... 还有 {len(blacklist_keys) - 20} 个黑名单 Token{Colors.RESET}")
                else:
                    print(f"{Colors.GREEN}【黑名单详情】{Colors.RESET}")
                    print(f"  {Colors.YELLOW}暂无 Token 在黑名单中{Colors.RESET}")
                
                print()
                
                # 缓存统计（简要）
                if cache_keys:
                    print(f"{Colors.BLUE}【缓存统计】{Colors.RESET}")
                    
                    # 统计不同数据集的缓存
                    dataset_cache = {}
                    for key in cache_keys:
                        # 格式: bi:cache:{dataset_id}:{hash}
                        parts = key.split(":")
                        if len(parts) >= 3:
                            dataset_id = parts[2]
                            dataset_cache[dataset_id] = dataset_cache.get(dataset_id, 0) + 1
                    
                    print(f"  数据集缓存分布:")
                    for dataset_id, count in sorted(dataset_cache.items())[:10]:
                        print(f"    Dataset {dataset_id}: {count} 个缓存")
                    
                    if len(dataset_cache) > 10:
                        print(f"    ... 还有 {len(dataset_cache) - 10} 个数据集")
                
            except Exception as e:
                print(f"{Colors.RED}✗ 获取黑名单信息失败: {e}{Colors.RESET}")
            
            # 底部提示
            print()
            print("=" * 80)
            print(f"{Colors.YELLOW}按 Ctrl+C 退出监控 | 刷新间隔: {interval} 秒{Colors.RESET}".center(90))
            print("=" * 80)
            
            # 等待
            time.sleep(interval)
            
    except KeyboardInterrupt:
        print(f"\n\n{Colors.YELLOW}监控已停止{Colors.RESET}")
    except Exception as e:
        print(f"\n\n{Colors.RED}监控过程中发生错误: {e}{Colors.RESET}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    # 从命令行参数获取刷新间隔
    interval = 2
    if len(sys.argv) > 1:
        try:
            interval = int(sys.argv[1])
        except ValueError:
            print(f"{Colors.RED}无效的刷新间隔，使用默认值 2 秒{Colors.RESET}")
    
    monitor_redis_blacklist(interval)
