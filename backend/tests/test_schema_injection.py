"""
测试 Schema Injection 功能（利用可视化建模连线训练表关系）

测试流程：
1. 模拟 VueFlow edges 数据
2. 调用 _train_relationships_from_edges 解析并训练
3. 验证训练结果
"""

import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.api.v1.endpoints.dataset import _train_relationships_from_edges
from app.db.session import SessionLocal

def test_train_relationships_from_edges():
    """测试从 edges 训练关系"""
    
    # 模拟 VueFlow edges 数据
    mock_edges = [
        {
            "id": "edge-1",
            "source": "node-users",
            "target": "node-orders",
            "sourceHandle": "id",
            "targetHandle": "user_id",
            "data": {
                "sourceTable": "users",
                "targetTable": "orders",
                "sourceField": "id",
                "targetField": "user_id"
            }
        },
        {
            "id": "edge-2",
            "source": "node-orders",
            "target": "node-products",
            "sourceHandle": "product_id",
            "targetHandle": "id",
            "data": {
                "sourceTable": "orders",
                "targetTable": "products",
                "sourceField": "product_id",
                "targetField": "id"
            }
        },
        {
            "id": "edge-3",
            "source": "node-orders",
            "target": "node-users",
            "sourceHandle": "customer_id",
            "targetHandle": "id",
            # 测试没有 data 字段的情况（回退到 source/target 解析）
        }
    ]
    
    print("=" * 70)
    print("测试 Schema Injection 功能")
    print("=" * 70)
    
    print(f"\n📊 模拟 VueFlow Edges ({len(mock_edges)} 条)：")
    for i, edge in enumerate(mock_edges, 1):
        print(f"  {i}. {edge['id']}:")
        if 'data' in edge and edge['data']:
            data = edge['data']
            print(f"     {data['sourceTable']}.{data['sourceField']} -> {data['targetTable']}.{data['targetField']}")
        else:
            print(f"     {edge['source']}.{edge.get('sourceHandle', '?')} -> {edge['target']}.{edge.get('targetHandle', '?')}")
    
    print("\n" + "=" * 70)
    print("开始解析并训练表关系...")
    print("=" * 70)
    
    # 创建数据库会话
    db = SessionLocal()
    
    try:
        # 假设数据集 ID 为 1（请替换为实际存在的数据集 ID）
        dataset_id = 1
        
        print(f"\n✅ 目标数据集 ID: {dataset_id}")
        print("\n预期生成的关系描述：")
        print("  1. users.id <-> orders.user_id (双向)")
        print("  2. orders.product_id <-> products.id (双向)")
        print("  3. orders.customer_id <-> users.id (双向，从 source/target 解析)")
        
        # 执行训练
        _train_relationships_from_edges(dataset_id, mock_edges, db)
        
        print("\n" + "=" * 70)
        print("✅ 训练完成！")
        print("=" * 70)
        print("\n提示：")
        print("  1. 检查日志确认训练的关系数量")
        print("  2. 尝试在 ChatBI 中提问跨表查询，如：")
        print("     - \"查询所有用户的订单数量\"")
        print("     - \"统计每个产品的销售额\"")
        print("  3. 观察生成的 SQL 是否包含正确的 JOIN 条件")
        
    except Exception as e:
        print(f"\n❌ 训练失败: {e}")
        import traceback
        traceback.print_exc()
    finally:
        db.close()

if __name__ == "__main__":
    test_train_relationships_from_edges()
