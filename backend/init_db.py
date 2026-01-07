#!/usr/bin/env python3
"""
Universal BI 数据库初始化脚本
用途：创建数据库表结构并插入初始数据
"""

import sys
from pathlib import Path

# 添加项目路径
sys.path.append(str(Path(__file__).parent))

from app.db.session import engine
from app.models.base import Base
from app.models.metadata import DataSource, Dataset, Dashboard, DashboardCard
from app.core.security import get_password_hash
from sqlalchemy.orm import Session
from sqlalchemy import text


def init_database():
    """初始化数据库"""
    print("=" * 50)
    print("开始初始化 Universal BI 数据库...")
    print("=" * 50)
    
    try:
        # 创建所有表
        print("\n1. 创建数据库表结构...")
        Base.metadata.create_all(bind=engine)
        print("✓ 表结构创建成功")
        
        # 创建默认管理员账户
        print("\n2. 创建默认管理员账户...")
        with Session(engine) as session:
            # 检查是否已存在管理员
            result = session.execute(text("SELECT id FROM users WHERE username = 'admin'"))
            if result.fetchone():
                print("✓ 管理员账户已存在，跳过创建")
            else:
                # 插入管理员账户
                hashed_password = get_password_hash("admin123")
                session.execute(text("""
                    INSERT INTO users (username, email, hashed_password, full_name, is_superuser, is_active)
                    VALUES (:username, :email, :password, :fullname, :is_super, :is_active)
                """), {
                    "username": "admin",
                    "email": "admin@example.com",
                    "password": hashed_password,
                    "fullname": "系统管理员",
                    "is_super": True,
                    "is_active": True
                })
                session.commit()
                print("✓ 管理员账户创建成功")
        
        print("\n" + "=" * 50)
        print("数据库初始化完成！")
        print("=" * 50)
        print("\n默认管理员账户:")
        print("  用户名: admin")
        print("  密码: admin123")
        print("  ⚠️  请登录后及时修改密码！")
        print("\n访问地址:")
        print("  后端 API: http://localhost:8000")
        print("  API 文档: http://localhost:8000/docs")
        print("  前端页面: http://localhost:3000")
        print("=" * 50)
        
    except Exception as e:
        print(f"\n✗ 初始化失败: {str(e)}")
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    init_database()
