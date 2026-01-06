"""
测试管理员功能的脚本

需要先创建一个超级管理员用户：
UPDATE users SET is_superuser = TRUE WHERE email = 'admin@example.com';
"""

import requests
import json

BASE_URL = "http://localhost:8000/api/v1"

def test_admin_features():
    """测试管理员功能"""
    
    # 1. 登录获取 token
    print("=" * 50)
    print("1. 测试登录")
    login_data = {
        "username": "admin@example.com",  # 替换为你的超级管理员邮箱
        "password": "password123"  # 替换为你的密码
    }
    
    response = requests.post(
        f"{BASE_URL}/auth/login",
        data=login_data,
        headers={"Content-Type": "application/x-www-form-urlencoded"}
    )
    
    if response.status_code != 200:
        print(f"❌ 登录失败: {response.status_code}")
        print(response.text)
        return
    
    token = response.json()["access_token"]
    print(f"✅ 登录成功，Token: {token[:20]}...")
    
    headers = {"Authorization": f"Bearer {token}"}
    
    # 2. 获取当前用户信息
    print("\n" + "=" * 50)
    print("2. 测试获取当前用户信息 (GET /auth/me)")
    response = requests.get(f"{BASE_URL}/auth/me", headers=headers)
    
    if response.status_code == 200:
        user_info = response.json()
        print(f"✅ 成功获取用户信息:")
        print(f"   - Email: {user_info['email']}")
        print(f"   - 昵称: {user_info.get('full_name', 'N/A')}")
        print(f"   - 超级管理员: {user_info['is_superuser']}")
        print(f"   - 激活状态: {user_info['is_active']}")
        
        if not user_info['is_superuser']:
            print("❌ 当前用户不是超级管理员，无法测试管理员功能")
            return
    else:
        print(f"❌ 获取用户信息失败: {response.status_code}")
        print(response.text)
        return
    
    # 3. 获取用户列表
    print("\n" + "=" * 50)
    print("3. 测试获取用户列表 (GET /admin/users)")
    response = requests.get(
        f"{BASE_URL}/admin/users",
        headers=headers,
        params={"page": 1, "page_size": 10}
    )
    
    if response.status_code == 200:
        data = response.json()
        print(f"✅ 成功获取用户列表:")
        print(f"   - 总用户数: {data['total']}")
        print(f"   - 当前页: {data['page']}")
        print(f"   - 每页数量: {data['page_size']}")
        print(f"   - 用户列表:")
        for user in data['users'][:3]:  # 只显示前3个
            print(f"     * ID:{user['id']} - {user['email']} - {'超管' if user['is_superuser'] else '普通用户'}")
    else:
        print(f"❌ 获取用户列表失败: {response.status_code}")
        print(response.text)
    
    # 4. 测试搜索用户
    print("\n" + "=" * 50)
    print("4. 测试搜索用户 (GET /admin/users?search=admin)")
    response = requests.get(
        f"{BASE_URL}/admin/users",
        headers=headers,
        params={"page": 1, "page_size": 10, "search": "admin"}
    )
    
    if response.status_code == 200:
        data = response.json()
        print(f"✅ 搜索成功，找到 {data['total']} 个用户")
    else:
        print(f"❌ 搜索失败: {response.status_code}")
    
    # 5. 测试退出登录
    print("\n" + "=" * 50)
    print("5. 测试退出登录 (POST /auth/logout)")
    response = requests.post(f"{BASE_URL}/auth/logout", headers=headers)
    
    if response.status_code == 200:
        print(f"✅ 退出登录成功:")
        print(f"   {response.json()}")
    else:
        print(f"❌ 退出登录失败: {response.status_code}")
        print(response.text)
    
    # 6. 验证 Token 已失效
    print("\n" + "=" * 50)
    print("6. 验证 Token 是否已失效")
    response = requests.get(f"{BASE_URL}/auth/me", headers=headers)
    
    if response.status_code == 401:
        print("✅ Token 已成功加入黑名单，无法再次使用")
    else:
        print(f"❌ Token 仍然有效，状态码: {response.status_code}")
    
    print("\n" + "=" * 50)
    print("测试完成！")

if __name__ == "__main__":
    try:
        test_admin_features()
    except Exception as e:
        print(f"❌ 测试出错: {e}")
        import traceback
        traceback.print_exc()
