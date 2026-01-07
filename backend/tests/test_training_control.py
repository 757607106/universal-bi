#!/usr/bin/env python3
"""
测试训练进度更新和中断控制功能
"""
import sys
import os
import time
import asyncio

# Add parent directory to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from sqlalchemy.orm import Session
from app.db.session import SessionLocal
from app.models.metadata import Dataset, DataSource, TrainingLog, User
from app.services.vanna_manager import VannaManager, TrainingStoppedException
from app.core.security import encrypt_password


def test_training_progress():
    """测试训练进度更新"""
    print("=" * 60)
    print("测试 1: 训练进度更新")
    print("=" * 60)
    
    db: Session = SessionLocal()
    
    try:
        # 创建测试用户
        user = User(
            email="test_progress@example.com",
            hashed_password="test",
            full_name="Test Progress User",
            is_active=True
        )
        db.add(user)
        db.commit()
        db.refresh(user)
        
        # 创建测试数据源
        datasource = DataSource(
            name="test_progress_ds",
            type="mysql",
            host="localhost",
            port=3306,
            username="root",
            password_encrypted=encrypt_password(""),
            database_name="universal_bi",
            owner_id=user.id
        )
        db.add(datasource)
        db.commit()
        db.refresh(datasource)
        
        # 创建测试数据集
        dataset = Dataset(
            name="test_progress_dataset",
            datasource_id=datasource.id,
            collection_name="test_progress_collection",
            schema_config=["users"],  # 使用一个简单的表测试
            owner_id=user.id
        )
        db.add(dataset)
        db.commit()
        db.refresh(dataset)
        
        print(f"✓ 创建测试数据集 ID: {dataset.id}")
        print(f"  初始状态: {dataset.status}")
        print(f"  初始进度: {dataset.process_rate}%")
        
        # 启动训练
        print("\n开始训练...")
        VannaManager.train_dataset(dataset.id, ["users"], db)
        
        # 刷新数据集状态
        db.refresh(dataset)
        
        print(f"\n训练完成!")
        print(f"  最终状态: {dataset.status}")
        print(f"  最终进度: {dataset.process_rate}%")
        print(f"  最后训练时间: {dataset.last_train_at}")
        
        # 查看训练日志
        logs = db.query(TrainingLog).filter(
            TrainingLog.dataset_id == dataset.id
        ).order_by(TrainingLog.created_at).all()
        
        print(f"\n训练日志 ({len(logs)} 条):")
        for log in logs:
            print(f"  {log.created_at}: {log.content}")
        
        # 验证
        assert dataset.status == "completed"
        assert dataset.process_rate == 100
        assert len(logs) > 0
        
        print("\n✅ 进度更新测试通过")
        
        # 清理
        VannaManager.delete_collection(dataset.id)
        db.delete(dataset)
        db.delete(datasource)
        db.delete(user)
        db.commit()
        
    except Exception as e:
        print(f"\n❌ 测试失败: {e}")
        import traceback
        traceback.print_exc()
    finally:
        db.close()


def test_training_interrupt():
    """测试训练中断控制"""
    print("\n" + "=" * 60)
    print("测试 2: 训练中断控制")
    print("=" * 60)
    
    db: Session = SessionLocal()
    
    try:
        # 创建测试用户
        user = User(
            email="test_interrupt@example.com",
            hashed_password="test",
            full_name="Test Interrupt User",
            is_active=True
        )
        db.add(user)
        db.commit()
        db.refresh(user)
        
        # 创建测试数据源
        datasource = DataSource(
            name="test_interrupt_ds",
            type="mysql",
            host="localhost",
            port=3306,
            username="root",
            password_encrypted=encrypt_password(""),
            database_name="universal_bi",
            owner_id=user.id
        )
        db.add(datasource)
        db.commit()
        db.refresh(datasource)
        
        # 创建测试数据集
        dataset = Dataset(
            name="test_interrupt_dataset",
            datasource_id=datasource.id,
            collection_name="test_interrupt_collection",
            schema_config=["users", "datasources", "datasets"],  # 多个表
            owner_id=user.id
        )
        db.add(dataset)
        db.commit()
        db.refresh(dataset)
        
        print(f"✓ 创建测试数据集 ID: {dataset.id}")
        
        # 启动训练（在另一个线程中）
        import threading
        
        def train_in_background():
            db_bg = SessionLocal()
            try:
                VannaManager.train_dataset(dataset.id, ["users", "datasources", "datasets"], db_bg)
            finally:
                db_bg.close()
        
        train_thread = threading.Thread(target=train_in_background)
        train_thread.start()
        
        # 等待训练开始
        time.sleep(2)
        
        # 模拟用户中断
        print("\n模拟用户中断训练...")
        db.refresh(dataset)
        print(f"  当前进度: {dataset.process_rate}%")
        
        dataset.status = "paused"
        db.commit()
        print("  状态已设置为 'paused'")
        
        # 等待训练线程结束
        train_thread.join(timeout=10)
        
        # 刷新数据集状态
        db.refresh(dataset)
        
        print(f"\n训练中断结果:")
        print(f"  最终状态: {dataset.status}")
        print(f"  最终进度: {dataset.process_rate}%")
        print(f"  错误信息: {dataset.error_msg}")
        
        # 查看训练日志
        logs = db.query(TrainingLog).filter(
            TrainingLog.dataset_id == dataset.id
        ).order_by(TrainingLog.created_at).all()
        
        print(f"\n训练日志 ({len(logs)} 条):")
        for log in logs[-5:]:  # 显示最后5条
            print(f"  {log.created_at}: {log.content}")
        
        # 验证
        assert dataset.status == "paused"
        assert dataset.process_rate < 100
        assert "中断" in dataset.error_msg or dataset.error_msg is None
        
        print("\n✅ 中断控制测试通过")
        
        # 清理
        VannaManager.delete_collection(dataset.id)
        db.delete(dataset)
        db.delete(datasource)
        db.delete(user)
        db.commit()
        
    except Exception as e:
        print(f"\n❌ 测试失败: {e}")
        import traceback
        traceback.print_exc()
    finally:
        db.close()


def test_delete_collection():
    """测试删除 collection"""
    print("\n" + "=" * 60)
    print("测试 3: 删除 Collection")
    print("=" * 60)
    
    db: Session = SessionLocal()
    
    try:
        # 创建测试用户
        user = User(
            email="test_delete@example.com",
            hashed_password="test",
            full_name="Test Delete User",
            is_active=True
        )
        db.add(user)
        db.commit()
        db.refresh(user)
        
        # 创建测试数据源
        datasource = DataSource(
            name="test_delete_ds",
            type="mysql",
            host="localhost",
            port=3306,
            username="root",
            password_encrypted=encrypt_password(""),
            database_name="universal_bi",
            owner_id=user.id
        )
        db.add(datasource)
        db.commit()
        db.refresh(datasource)
        
        # 创建测试数据集
        dataset = Dataset(
            name="test_delete_dataset",
            datasource_id=datasource.id,
            collection_name="test_delete_collection",
            schema_config=["users"],
            owner_id=user.id
        )
        db.add(dataset)
        db.commit()
        db.refresh(dataset)
        
        dataset_id = dataset.id
        print(f"✓ 创建测试数据集 ID: {dataset_id}")
        
        # 训练以创建 collection
        print("\n训练数据集以创建 collection...")
        VannaManager.train_dataset(dataset_id, ["users"], db)
        
        print("✓ 训练完成")
        
        # 删除 collection
        print("\n删除 collection...")
        success = VannaManager.delete_collection(dataset_id)
        
        if success:
            print("✓ Collection 删除成功")
        else:
            print("✗ Collection 删除失败")
        
        # 验证缓存已清理
        collection_name = f"vec_ds_{dataset_id}"
        assert collection_name not in VannaManager._chroma_clients
        assert collection_name not in VannaManager._agent_instances
        print("✓ 缓存已清理")
        
        print("\n✅ 删除 Collection 测试通过")
        
        # 清理数据库
        db.delete(dataset)
        db.delete(datasource)
        db.delete(user)
        db.commit()
        
    except Exception as e:
        print(f"\n❌ 测试失败: {e}")
        import traceback
        traceback.print_exc()
    finally:
        db.close()


def main():
    """运行所有测试"""
    print("\n" + "=" * 60)
    print("训练进度和中断控制功能测试")
    print("=" * 60)
    print("\n⚠️  注意：这些测试会创建和删除数据，请在测试环境运行")
    print("按 Enter 继续...")
    input()
    
    # 运行测试
    test_training_progress()
    test_training_interrupt()
    test_delete_collection()
    
    print("\n" + "=" * 60)
    print("所有测试完成")
    print("=" * 60)


if __name__ == "__main__":
    main()
