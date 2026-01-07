"""
测试新增字段功能
- Dataset 模型的训练状态管理字段
- TrainingLog 模型
"""
import pytest
from datetime import datetime
from sqlalchemy.orm import Session
from app.db.session import SessionLocal
from app.models.metadata import Dataset, DataSource, TrainingLog, User
from app.schemas.dataset import DatasetResponse, TrainingLogResponse, DatasetUpdateStatus


def test_dataset_new_fields():
    """测试 Dataset 新字段"""
    db: Session = SessionLocal()
    
    try:
        # 创建测试用户
        user = User(
            email="test_fields@example.com",
            hashed_password="test",
            full_name="Test User"
        )
        db.add(user)
        db.commit()
        db.refresh(user)
        
        # 创建测试数据源
        datasource = DataSource(
            name="test_ds_fields",
            type="mysql",
            host="localhost",
            port=3306,
            username="root",
            password_encrypted="test",
            database_name="test",
            owner_id=user.id
        )
        db.add(datasource)
        db.commit()
        db.refresh(datasource)
        
        # 创建 Dataset 并测试新字段
        dataset = Dataset(
            name="test_dataset_fields",
            datasource_id=datasource.id,
            collection_name="test_collection_fields",
            schema_config=["table1", "table2"],
            status="training",
            modeling_config={"nodes": [{"id": "1", "name": "table1"}], "edges": []},
            process_rate=50,
            error_msg=None,
            last_train_at=datetime.utcnow(),
            owner_id=user.id
        )
        db.add(dataset)
        db.commit()
        db.refresh(dataset)
        
        # 验证字段
        assert dataset.status == "training"
        assert dataset.process_rate == 50
        assert dataset.modeling_config is not None
        assert dataset.modeling_config["nodes"][0]["id"] == "1"
        assert dataset.last_train_at is not None
        
        print("✓ Dataset new fields test passed")
        
        # 测试状态更新
        dataset.status = "completed"
        dataset.process_rate = 100
        db.commit()
        db.refresh(dataset)
        
        assert dataset.status == "completed"
        assert dataset.process_rate == 100
        
        print("✓ Dataset status update test passed")
        
        # 清理
        db.delete(dataset)
        db.delete(datasource)
        db.delete(user)
        db.commit()
        
    finally:
        db.close()


def test_training_log_model():
    """测试 TrainingLog 模型"""
    db: Session = SessionLocal()
    
    try:
        # 创建测试用户
        user = User(
            email="test_log@example.com",
            hashed_password="test",
            full_name="Test User"
        )
        db.add(user)
        db.commit()
        db.refresh(user)
        
        # 创建测试数据源
        datasource = DataSource(
            name="test_ds_log",
            type="mysql",
            host="localhost",
            port=3306,
            username="root",
            password_encrypted="test",
            database_name="test",
            owner_id=user.id
        )
        db.add(datasource)
        db.commit()
        db.refresh(datasource)
        
        # 创建 Dataset
        dataset = Dataset(
            name="test_dataset_log",
            datasource_id=datasource.id,
            collection_name="test_collection_log",
            owner_id=user.id
        )
        db.add(dataset)
        db.commit()
        db.refresh(dataset)
        
        # 创建 TrainingLog
        log1 = TrainingLog(
            dataset_id=dataset.id,
            content="Training started"
        )
        log2 = TrainingLog(
            dataset_id=dataset.id,
            content="Processing table1"
        )
        db.add_all([log1, log2])
        db.commit()
        
        # 查询日志
        logs = db.query(TrainingLog).filter(TrainingLog.dataset_id == dataset.id).all()
        assert len(logs) == 2
        assert logs[0].content == "Training started"
        assert logs[1].content == "Processing table1"
        assert logs[0].created_at is not None
        
        print("✓ TrainingLog model test passed")
        
        # 测试级联删除
        db.delete(dataset)
        db.commit()
        
        logs_after_delete = db.query(TrainingLog).filter(TrainingLog.dataset_id == dataset.id).all()
        assert len(logs_after_delete) == 0
        
        print("✓ TrainingLog cascade delete test passed")
        
        # 清理
        db.delete(datasource)
        db.delete(user)
        db.commit()
        
    finally:
        db.close()


def test_schema_validation():
    """测试 Schema 验证"""
    from pydantic import ValidationError
    
    # 测试 DatasetResponse
    ds = DatasetResponse(
        id=1,
        name="test",
        datasource_id=1,
        status="pending",
        process_rate=0,
        modeling_config={"nodes": [], "edges": []},
        error_msg=None,
        last_train_at=None
    )
    
    assert ds.status == "pending"
    assert ds.process_rate == 0
    assert ds.modeling_config is not None
    
    print("✓ DatasetResponse schema test passed")
    
    # 测试 TrainingLogResponse
    log = TrainingLogResponse(
        id=1,
        dataset_id=1,
        content="Test log",
        created_at=datetime.now()
    )
    
    assert log.content == "Test log"
    assert log.created_at is not None
    
    print("✓ TrainingLogResponse schema test passed")
    
    # 测试 DatasetUpdateStatus
    update = DatasetUpdateStatus(
        status="completed",
        process_rate=100,
        error_msg=None
    )
    
    assert update.status == "completed"
    assert update.process_rate == 100
    
    print("✓ DatasetUpdateStatus schema test passed")


if __name__ == "__main__":
    print("Running new fields tests...\n")
    test_dataset_new_fields()
    test_training_log_model()
    test_schema_validation()
    print("\n=== All Tests Passed ===")
