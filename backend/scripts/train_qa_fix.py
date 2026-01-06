#!/usr/bin/env python3
"""
QA 训练脚本 - 修正 AI 表名幻觉问题

通过提供 Question-SQL 对，教会 Vanna 在遇到“销售”相关问题时使用正确的表名 (fact_orders)
"""
import sys
import os
import asyncio

# Disable CoreML to avoid ONNXRuntime issues on macOS
os.environ['ONNX_DISABLE_COREML'] = '1'
os.environ['TOKENIZERS_PARALLELISM'] = 'false'

# Add parent directory to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from sqlalchemy.orm import Session
from app.db.session import SessionLocal
from app.models.metadata import Dataset
from app.services.vanna_manager import VannaManager
from app.core.config import settings
from vanna.core import ToolContext
from vanna.core.user import User
import uuid

# Import Legacy Vanna for training
from vanna.legacy.openai import OpenAI_Chat
from vanna.legacy.chromadb import ChromaDB_VectorStore


class VannaLegacy(ChromaDB_VectorStore, OpenAI_Chat):
    """
    Legacy Vanna class for training with question-SQL pairs
    """
    def __init__(self, config=None):
        ChromaDB_VectorStore.__init__(self, config=config)
        OpenAI_Chat.__init__(self, config=config)


async def train_qa_pairs(dataset_id: int, db_session: Session):
    """
    异步版本（未使用）
    """
    pass


def train_qa_pairs_sync(dataset_id: int, db_session: Session):
    """
    使用 QA 对训练 Vanna，修正表名幻觉问题
    使用 Legacy API 的 train() 方法
    """
    print(f"🚀 开始 QA 训练，Dataset ID: {dataset_id}")
    
    # 1. 验证数据集存在
    dataset = db_session.query(Dataset).filter(Dataset.id == dataset_id).first()
    if not dataset:
        print(f"❌ 错误: 找不到 Dataset {dataset_id}")
        return False
    
    print(f"✓ 数据集: {dataset.name}")
    
    # 2. 初始化 Legacy Vanna (使用与 VannaManager 相同的配置)
    print("✓ 初始化 Vanna Legacy API...")
    collection_name = f"vec_ds_{dataset_id}"
    
    vn = VannaLegacy(config={
        'api_key': settings.DASHSCOPE_API_KEY,
        'model': settings.QWEN_MODEL,
        'path': './chroma_db',
        'n_results': 10,
        'client': 'persistent',
        'collection_name': collection_name
    })
    
    # 3. 准备 QA 训练数据 - 使用更强的格式
    qa_pairs = [
        {
            "question": "查询上个月销售额",
            "sql": "SELECT SUM(total_amount) AS sales FROM fact_orders WHERE order_date >= DATE_SUB(CURDATE(), INTERVAL 1 MONTH)"
        },
        {
            "question": "上个月的销售额是多少",
            "sql": "SELECT SUM(total_amount) AS total_sales FROM fact_orders WHERE order_date >= DATE_SUB(CURDATE(), INTERVAL 1 MONTH)"
        },
        {
            "question": "销售趋势",
            "sql": "SELECT DATE_FORMAT(order_date, '%Y-%m') as month, SUM(total_amount) as sales FROM fact_orders GROUP BY month ORDER BY month"
        },
        {
            "question": "按月统计销售额",
            "sql": "SELECT DATE_FORMAT(order_date, '%Y-%m') as month, SUM(total_amount) as monthly_sales FROM fact_orders GROUP BY month ORDER BY month"
        },
        {
            "question": "统计每个产品的销量",
            "sql": "SELECT p.product_name, SUM(o.quantity) as total_quantity FROM fact_orders o JOIN dim_products p ON o.product_id = p.product_id GROUP BY p.product_name ORDER BY total_quantity DESC"
        },
        {
            "question": "哪个产品销量最高",
            "sql": "SELECT p.product_name, SUM(o.quantity) as total_quantity FROM fact_orders o JOIN dim_products p ON o.product_id = p.product_id GROUP BY p.product_name ORDER BY total_quantity DESC LIMIT 1"
        },
        {
            "question": "按产品分类统计销售额",
            "sql": "SELECT p.category, SUM(o.total_amount) as category_sales FROM fact_orders o JOIN dim_products p ON o.product_id = p.product_id GROUP BY p.category ORDER BY category_sales DESC"
        },
        {
            "question": "统计订单数量",
            "sql": "SELECT COUNT(*) as order_count FROM fact_orders"
        },
        {
            "question": "今天的订单数",
            "sql": "SELECT COUNT(*) as today_orders FROM fact_orders WHERE DATE(order_date) = CURDATE()"
        },
        {
            "question": "按用户统计订单数",
            "sql": "SELECT u.username, COUNT(o.order_id) as order_count FROM fact_orders o JOIN dim_users u ON o.user_id = u.user_id GROUP BY u.username ORDER BY order_count DESC"
        }
    ]
    
    # 4. 使用 Legacy API 的 train() 方法训练 QA 对
    print(f"\n📚 开始训练 {len(qa_pairs)} 个 QA 对...")
    success_count = 0
    
    for i, qa in enumerate(qa_pairs, 1):
        try:
            # 使用 Legacy API 的 train() 方法
            vn.train(
                question=qa['question'],
                sql=qa['sql']
            )
            
            print(f"  ✓ [{i}/{len(qa_pairs)}] {qa['question']}")
            success_count += 1
            
        except Exception as e:
            print(f"  ✗ [{i}/{len(qa_pairs)}] {qa['question']}: {str(e)}")
    
    print(f"\n✅ QA 训练完成！成功: {success_count}/{len(qa_pairs)}")
    return True


def main():
    """
    主函数
    """
    print("=" * 60)
    print("QA 训练脚本 - 修正 AI 表名幻觉")
    print("=" * 60)
    
    # 创建数据库会话
    db = SessionLocal()
    
    try:
        # 查找 "电商销售分析" 数据集
        dataset = db.query(Dataset).filter(
            Dataset.name.like("%电商%")
        ).first()
        
        if not dataset:
            print("❌ 找不到电商相关数据集")
            print("提示: 请检查数据库中是否存在包含'电商'的数据集名称")
            return
        
        dataset_id = dataset.id
        print(f"\n找到数据集: {dataset.name} (ID: {dataset_id})")
        
        # 执行同步训练（Legacy API 不需要 async）
        success = train_qa_pairs_sync(dataset_id, db)
        
        if success:
            print("\n" + "=" * 60)
            print("🎉 训练成功！AI 现在应该能正确识别销售相关查询了")
            print("=" * 60)
            print("\n建议测试问题:")
            print("  - '上个月的销售额是多少'")
            print("  - '按产品统计销量'")
            print("  - '销售趋势分析'")
        
    except Exception as e:
        print(f"\n❌ 训练失败: {str(e)}")
        import traceback
        traceback.print_exc()
    
    finally:
        db.close()


if __name__ == "__main__":
    main()
