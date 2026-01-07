"""
测试 ChatBI 反馈闭环机制（RLHF）

功能测试：
1. 点赞正确的 SQL
2. 点踩并提供修正的 SQL
3. 训练后验证效果
"""

import requests
import json
import time

# 配置
BASE_URL = "http://localhost:8000/api/v1"
DATASET_ID = 1  # 替换为你的数据集 ID

# 获取 Token（需要先登录）
def get_token(username: str = "admin@example.com", password: str = "admin123"):
    """登录获取 Token"""
    response = requests.post(
        f"{BASE_URL}/auth/login",
        data={
            "username": username,
            "password": password
        }
    )
    
    if response.status_code == 200:
        token = response.json()["access_token"]
        print(f"✅ 登录成功，Token: {token[:20]}...")
        return token
    else:
        print(f"❌ 登录失败: {response.text}")
        return None


def submit_like_feedback(token: str, dataset_id: int, question: str, sql: str):
    """测试点赞功能"""
    print(f"\n📝 测试点赞功能...")
    print(f"   问题: {question}")
    print(f"   SQL: {sql}")
    
    response = requests.post(
        f"{BASE_URL}/chat/feedback",
        headers={
            "Authorization": f"Bearer {token}",
            "Content-Type": "application/json"
        },
        json={
            "dataset_id": dataset_id,
            "question": question,
            "sql": sql,
            "rating": 1
        }
    )
    
    if response.status_code == 200:
        result = response.json()
        print(f"✅ 点赞成功: {result['message']}")
        return True
    else:
        print(f"❌ 点赞失败: {response.text}")
        return False


def submit_dislike_feedback(token: str, dataset_id: int, question: str, corrected_sql: str):
    """测试点踩修正功能"""
    print(f"\n📝 测试点踩修正功能...")
    print(f"   问题: {question}")
    print(f"   修正后的 SQL: {corrected_sql}")
    
    response = requests.post(
        f"{BASE_URL}/chat/feedback",
        headers={
            "Authorization": f"Bearer {token}",
            "Content-Type": "application/json"
        },
        json={
            "dataset_id": dataset_id,
            "question": question,
            "sql": corrected_sql,  # 这里是修正后的 SQL
            "rating": -1
        }
    )
    
    if response.status_code == 200:
        result = response.json()
        print(f"✅ 修正成功: {result['message']}")
        return True
    else:
        print(f"❌ 修正失败: {response.text}")
        return False


def test_chat_and_feedback(token: str, dataset_id: int, question: str):
    """测试完整流程：提问 -> 反馈"""
    print(f"\n🤖 测试完整流程: {question}")
    
    # 1. 发送聊天请求
    print("   步骤 1: 发送问题...")
    response = requests.post(
        f"{BASE_URL}/chat/",
        headers={
            "Authorization": f"Bearer {token}",
            "Content-Type": "application/json"
        },
        json={
            "dataset_id": dataset_id,
            "question": question
        }
    )
    
    if response.status_code != 200:
        print(f"❌ 聊天请求失败: {response.text}")
        return False
    
    result = response.json()
    sql = result.get("sql")
    
    if not sql:
        print(f"⚠️  AI 未生成 SQL（可能是澄清请求）: {result.get('answer_text', 'No answer')}")
        return False
    
    print(f"✅ AI 生成 SQL: {sql}")
    
    # 2. 提交点赞反馈
    print("   步骤 2: 提交点赞反馈...")
    submit_like_feedback(token, dataset_id, question, sql)
    
    return True


def test_training_effect(token: str, dataset_id: int):
    """测试训练效果：训练前后对比"""
    print(f"\n🧪 测试训练效果...")
    
    question = "查询用户总数"
    correct_sql = "SELECT COUNT(*) as user_count FROM users"
    
    # 1. 提交正确的问答对训练
    print("   步骤 1: 提交训练数据...")
    if not submit_like_feedback(token, dataset_id, question, correct_sql):
        print("⚠️  训练失败，无法继续测试")
        return False
    
    # 等待训练生效（缓存清理）
    print("   等待 2 秒让训练生效...")
    time.sleep(2)
    
    # 2. 再次提问，验证是否生成相似的 SQL
    print(f"   步骤 2: 再次提问验证效果...")
    response = requests.post(
        f"{BASE_URL}/chat/",
        headers={
            "Authorization": f"Bearer {token}",
            "Content-Type": "application/json"
        },
        json={
            "dataset_id": dataset_id,
            "question": question
        }
    )
    
    if response.status_code != 200:
        print(f"❌ 验证失败: {response.text}")
        return False
    
    result = response.json()
    generated_sql = result.get("sql")
    
    print(f"   训练目标 SQL: {correct_sql}")
    print(f"   训练后生成 SQL: {generated_sql}")
    
    if generated_sql and "COUNT(*)" in generated_sql.upper() and "users" in generated_sql.lower():
        print("✅ 训练效果验证成功！生成的 SQL 与训练数据相似。")
        return True
    else:
        print("⚠️  训练效果不明显，可能需要多次训练或检查缓存清理。")
        return False


def main():
    print("=" * 60)
    print("ChatBI 反馈闭环机制（RLHF）测试")
    print("=" * 60)
    
    # 1. 登录获取 Token
    token = get_token()
    if not token:
        print("\n❌ 无法获取 Token，测试终止")
        return
    
    # 2. 测试点赞功能
    print("\n" + "=" * 60)
    print("测试 1: 点赞正确的 SQL")
    print("=" * 60)
    submit_like_feedback(
        token=token,
        dataset_id=DATASET_ID,
        question="查询订单总数",
        sql="SELECT COUNT(*) as total FROM orders"
    )
    
    # 3. 测试点踩修正功能
    print("\n" + "=" * 60)
    print("测试 2: 点踩并提供修正 SQL")
    print("=" * 60)
    submit_dislike_feedback(
        token=token,
        dataset_id=DATASET_ID,
        question="查询最近 7 天的订单",
        corrected_sql="SELECT * FROM orders WHERE created_at >= DATE_SUB(NOW(), INTERVAL 7 DAY)"
    )
    
    # 4. 测试完整流程
    print("\n" + "=" * 60)
    print("测试 3: 完整流程（提问 + 反馈）")
    print("=" * 60)
    test_chat_and_feedback(
        token=token,
        dataset_id=DATASET_ID,
        question="显示所有产品"
    )
    
    # 5. 测试训练效果
    print("\n" + "=" * 60)
    print("测试 4: 训练效果验证")
    print("=" * 60)
    test_training_effect(token, DATASET_ID)
    
    print("\n" + "=" * 60)
    print("测试完成")
    print("=" * 60)


if __name__ == "__main__":
    main()
