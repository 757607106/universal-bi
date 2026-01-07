"""
测试分析师 Agent 功能
用于验证同步生成业务洞察的功能
"""
import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import pandas as pd
from app.services.vanna_manager import VannaManager

def test_generate_data_insight():
    """测试 generate_data_insight 方法"""
    
    # 创建示例数据
    df = pd.DataFrame({
        'month': ['2024-01', '2024-02', '2024-03', '2024-04', '2024-05'],
        'sales': [120000, 135000, 128000, 145000, 160000],
        'orders': [450, 480, 460, 510, 550]
    })
    
    question = "统计近5个月的销售额趋势"
    sql = "SELECT month, SUM(amount) as sales, COUNT(*) as orders FROM orders GROUP BY month ORDER BY month DESC LIMIT 5"
    dataset_id = 1  # 请替换为实际的数据集ID
    
    print("=" * 60)
    print("测试数据：")
    print(df)
    print("\n用户问题：", question)
    print("\nSQL 查询：", sql)
    print("=" * 60)
    
    try:
        insight = VannaManager.generate_data_insight(
            question=question,
            sql=sql,
            df=df,
            dataset_id=dataset_id
        )
        
        print("\n✅ 业务洞察生成成功：")
        print("-" * 60)
        print(insight)
        print("-" * 60)
        
    except Exception as e:
        print(f"\n❌ 业务洞察生成失败：{e}")

if __name__ == "__main__":
    test_generate_data_insight()
