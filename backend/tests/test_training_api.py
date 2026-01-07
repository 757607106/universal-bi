#!/usr/bin/env python3
"""
测试训练进度 API 端点
"""
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from fastapi.testclient import TestClient
from app.main import app

client = TestClient(app)

def test_training_endpoints():
    """测试训练相关端点是否存在"""
    print("=" * 60)
    print("测试训练进度 API 端点")
    print("=" * 60)
    
    # 注意：这些测试需要有效的认证 token
    # 这里只测试端点是否存在（会返回 401 而不是 404）
    
    dataset_id = 1
    
    # 测试获取训练进度
    print(f"\n1. 测试 GET /datasets/{dataset_id}/training/progress")
    response = client.get(f"/api/v1/datasets/{dataset_id}/training/progress")
    print(f"   状态码: {response.status_code}")
    if response.status_code == 401:
        print("   ✓ 端点存在（需要认证）")
    elif response.status_code == 404:
        print("   ✗ 端点不存在")
    else:
        print(f"   响应: {response.json()}")
    
    # 测试获取训练日志
    print(f"\n2. 测试 GET /datasets/{dataset_id}/training/logs")
    response = client.get(f"/api/v1/datasets/{dataset_id}/training/logs?limit=50")
    print(f"   状态码: {response.status_code}")
    if response.status_code == 401:
        print("   ✓ 端点存在（需要认证）")
    elif response.status_code == 404:
        print("   ✗ 端点不存在")
    else:
        print(f"   响应: {response.json()}")
    
    # 测试暂停训练
    print(f"\n3. 测试 POST /datasets/{dataset_id}/training/pause")
    response = client.post(f"/api/v1/datasets/{dataset_id}/training/pause")
    print(f"   状态码: {response.status_code}")
    if response.status_code == 401:
        print("   ✓ 端点存在（需要认证）")
    elif response.status_code == 404:
        print("   ✗ 端点不存在")
    else:
        print(f"   响应: {response.json()}")
    
    # 测试删除训练数据
    print(f"\n4. 测试 DELETE /datasets/{dataset_id}/training")
    response = client.delete(f"/api/v1/datasets/{dataset_id}/training")
    print(f"   状态码: {response.status_code}")
    if response.status_code == 401:
        print("   ✓ 端点存在（需要认证）")
    elif response.status_code == 404:
        print("   ✗ 端点不存在")
    else:
        print(f"   响应: {response.json()}")
    
    print("\n" + "=" * 60)
    print("测试完成")
    print("=" * 60)
    print("\n说明：")
    print("- 状态码 401: 端点存在但需要认证（正常）")
    print("- 状态码 404: 端点不存在（需要检查路由）")
    print("- 其他状态码: 请查看响应内容")


if __name__ == "__main__":
    test_training_endpoints()
