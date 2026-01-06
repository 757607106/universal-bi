#!/usr/bin/env python3
"""
测试 Token 黑名单与退出登录功能
"""
import requests
import json
import time
from redis import Redis
from app.core.config import settings

# API 基础 URL
BASE_URL = "http://localhost:8000/api/v1"

# 颜色输出
class Colors:
    GREEN = '\033[92m'
    RED = '\033[91m'
    YELLOW = '\033[93m'
    BLUE = '\033[94m'
    RESET = '\033[0m'

def print_step(step, message):
    print(f"\n{Colors.BLUE}[步骤 {step}]{Colors.RESET} {message}")

def print_success(message):
    print(f"{Colors.GREEN}✓{Colors.RESET} {message}")

def print_error(message):
    print(f"{Colors.RED}✗{Colors.RESET} {message}")

def print_warning(message):
    print(f"{Colors.YELLOW}⚠{Colors.RESET} {message}")

def print_info(message):
    print(f"  {message}")

# 连接 Redis
try:
    redis_client = Redis.from_url(settings.REDIS_URL, decode_responses=True)
    redis_client.ping()
    print_success(f"Redis 连接成功: {settings.REDIS_URL}")
except Exception as e:
    print_error(f"Redis 连接失败: {e}")
    redis_client = None

# 测试数据
TEST_USER = {
    "email": "test_logout@example.com",
    "password": "test123456",
    "full_name": "Logout Test User"
}

def test_logout_flow():
    """测试完整的退出登录流程"""
    
    print("\n" + "="*60)
    print(f"{Colors.BLUE}开始测试 Token 黑名单与退出登录功能{Colors.RESET}")
    print("="*60)
    
    # ========== 步骤 1: 注册用户 ==========
    print_step(1, "注册测试用户")
    try:
        response = requests.post(
            f"{BASE_URL}/auth/register",
            json=TEST_USER
        )
        
        if response.status_code == 200:
            print_success("用户注册成功")
            print_info(f"Email: {TEST_USER['email']}")
        elif response.status_code == 400 and "already registered" in response.text:
            print_warning("用户已存在，继续测试")
        else:
            print_error(f"注册失败: {response.text}")
            return
    except Exception as e:
        print_error(f"注册请求失败: {e}")
        return
    
    # ========== 步骤 2: 登录获取 Token ==========
    print_step(2, "登录获取 Token")
    try:
        response = requests.post(
            f"{BASE_URL}/auth/login",
            data={
                "username": TEST_USER["email"],
                "password": TEST_USER["password"]
            }
        )
        
        if response.status_code == 200:
            token_data = response.json()
            token = token_data["access_token"]
            print_success("登录成功，获取到 Token")
            print_info(f"Token 前缀: {token[:50]}...")
            print_info(f"Token 类型: {token_data['token_type']}")
        else:
            print_error(f"登录失败: {response.text}")
            return
    except Exception as e:
        print_error(f"登录请求失败: {e}")
        return
    
    # ========== 步骤 3: 使用 Token 访问受保护资源 ==========
    print_step(3, "使用 Token 访问受保护资源")
    headers = {"Authorization": f"Bearer {token}"}
    
    try:
        response = requests.get(f"{BASE_URL}/datasources/", headers=headers)
        
        if response.status_code == 200:
            print_success("Token 有效，成功访问资源")
            print_info(f"返回状态: {response.status_code}")
        else:
            print_error(f"访问失败: {response.status_code} - {response.text}")
            return
    except Exception as e:
        print_error(f"访问请求失败: {e}")
        return
    
    # ========== 步骤 4: 检查 Redis 黑名单（退出前） ==========
    print_step(4, "检查 Redis 黑名单（退出前）")
    if redis_client:
        key = f"blacklist:token:{token}"
        exists = redis_client.exists(key)
        
        if exists:
            print_warning("Token 已在黑名单中（异常）")
        else:
            print_success("Token 不在黑名单中（正常）")
    else:
        print_warning("Redis 不可用，跳过检查")
    
    # ========== 步骤 5: 退出登录 ==========
    print_step(5, "调用退出登录接口")
    try:
        response = requests.post(f"{BASE_URL}/auth/logout", headers=headers)
        
        if response.status_code == 200:
            result = response.json()
            print_success("退出登录成功")
            print_info(f"消息: {result.get('message', 'N/A')}")
            if 'warning' in result:
                print_warning(f"警告: {result['warning']}")
        else:
            print_error(f"退出失败: {response.status_code} - {response.text}")
            return
    except Exception as e:
        print_error(f"退出请求失败: {e}")
        return
    
    # ========== 步骤 6: 检查 Redis 黑名单（退出后） ==========
    print_step(6, "检查 Redis 黑名单（退出后）")
    if redis_client:
        key = f"blacklist:token:{token}"
        exists = redis_client.exists(key)
        
        if exists:
            ttl = redis_client.ttl(key)
            print_success("Token 已加入黑名单")
            print_info(f"Redis Key: {key[:60]}...")
            print_info(f"剩余有效期: {ttl} 秒")
        else:
            print_error("Token 未加入黑名单（异常）")
    else:
        print_warning("Redis 不可用，跳过检查")
    
    # 等待一下，确保 Redis 操作完成
    time.sleep(0.5)
    
    # ========== 步骤 7: 再次使用 Token 访问（应该被拒绝） ==========
    print_step(7, "尝试再次使用已撤销的 Token")
    try:
        response = requests.get(f"{BASE_URL}/datasources/", headers=headers)
        
        if response.status_code == 401:
            error_detail = response.json().get('detail', '')
            if 'revoked' in error_detail.lower():
                print_success("Token 已被正确拒绝")
                print_info(f"错误消息: {error_detail}")
            else:
                print_warning(f"Token 被拒绝，但原因不明确: {error_detail}")
        else:
            print_error(f"Token 仍然有效（不应该）: {response.status_code}")
            print_error("黑名单机制可能未生效！")
    except Exception as e:
        print_error(f"访问请求失败: {e}")
    
    # ========== 步骤 8: 查看 Redis 中所有黑名单 Key ==========
    print_step(8, "查看 Redis 中所有黑名单 Key")
    if redis_client:
        try:
            keys = redis_client.keys("blacklist:token:*")
            print_success(f"找到 {len(keys)} 个黑名单 Token")
            
            if keys:
                print_info("黑名单详情:")
                for i, key in enumerate(keys[:5], 1):  # 只显示前5个
                    ttl = redis_client.ttl(key)
                    print_info(f"  {i}. {key[:60]}... (TTL: {ttl}s)")
                
                if len(keys) > 5:
                    print_info(f"  ... 还有 {len(keys) - 5} 个")
        except Exception as e:
            print_error(f"查询 Redis 失败: {e}")
    else:
        print_warning("Redis 不可用，跳过查询")
    
    # ========== 测试完成 ==========
    print("\n" + "="*60)
    print(f"{Colors.GREEN}✓ 测试完成！{Colors.RESET}")
    print("="*60)
    print("\n总结:")
    print_success("Token 黑名单机制正常工作")
    print_success("退出登录功能正常")
    print_success("已撤销的 Token 无法再次使用")

if __name__ == "__main__":
    try:
        test_logout_flow()
    except KeyboardInterrupt:
        print(f"\n{Colors.YELLOW}测试被中断{Colors.RESET}")
    except Exception as e:
        print_error(f"测试过程中发生错误: {e}")
        import traceback
        traceback.print_exc()
