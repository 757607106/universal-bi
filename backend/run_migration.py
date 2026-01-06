#!/usr/bin/env python3
"""
执行数据库迁移脚本
用于添加 is_superuser 和 is_deleted 字段到 users 表
"""

import sqlite3
import sys
from pathlib import Path

# 获取项目根目录
BACKEND_DIR = Path(__file__).parent
DB_PATH = BACKEND_DIR / "sql_app.db"
MIGRATION_FILE = BACKEND_DIR / "migrations" / "002_add_user_admin_fields.sql"

def run_migration():
    """执行数据库迁移"""
    
    # 检查数据库文件是否存在
    if not DB_PATH.exists():
        print(f"❌ 数据库文件不存在: {DB_PATH}")
        print("提示: 请先启动应用创建数据库")
        return False
    
    # 检查迁移文件是否存在
    if not MIGRATION_FILE.exists():
        print(f"❌ 迁移文件不存在: {MIGRATION_FILE}")
        return False
    
    print("=" * 60)
    print("开始执行数据库迁移...")
    print(f"数据库: {DB_PATH}")
    print(f"迁移文件: {MIGRATION_FILE}")
    print("=" * 60)
    
    try:
        # 连接数据库
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()
        
        # 读取迁移 SQL
        with open(MIGRATION_FILE, 'r', encoding='utf-8') as f:
            migration_sql = f.read()
        
        # 检查字段是否已经存在
        cursor.execute("PRAGMA table_info(users)")
        columns = [col[1] for col in cursor.fetchall()]
        
        print("\n当前 users 表的字段:")
        for col in columns:
            print(f"  - {col}")
        
        # 判断是否需要迁移
        needs_migration = False
        if 'is_superuser' not in columns:
            print("\n✓ 需要添加 is_superuser 字段")
            needs_migration = True
        else:
            print("\n⚠ is_superuser 字段已存在")
        
        if 'is_deleted' not in columns:
            print("✓ 需要添加 is_deleted 字段")
            needs_migration = True
        else:
            print("⚠ is_deleted 字段已存在")
        
        if not needs_migration:
            print("\n✅ 数据库已是最新状态，无需迁移")
            conn.close()
            return True
        
        # 执行迁移
        print("\n执行迁移 SQL...")
        
        # 手动逐条执行 SQL 语句
        print("\n[1/4] 添加 is_superuser 字段...")
        try:
            cursor.execute("ALTER TABLE users ADD COLUMN is_superuser BOOLEAN DEFAULT FALSE")
            print("✓ 成功")
        except sqlite3.OperationalError as e:
            if "duplicate column name" in str(e).lower():
                print("⚠ 字段已存在，跳过")
            else:
                raise
        
        print("\n[2/4] 添加 is_deleted 字段...")
        try:
            cursor.execute("ALTER TABLE users ADD COLUMN is_deleted BOOLEAN DEFAULT FALSE")
            print("✓ 成功")
        except sqlite3.OperationalError as e:
            if "duplicate column name" in str(e).lower():
                print("⚠ 字段已存在，跳过")
            else:
                raise
        
        print("\n[3/4] 更新 is_superuser 默认值...")
        try:
            cursor.execute("UPDATE users SET is_superuser = FALSE WHERE is_superuser IS NULL")
            print("✓ 成功")
        except sqlite3.OperationalError:
            print("⚠ 跳过")
        
        print("\n[4/4] 更新 is_deleted 默认值...")
        try:
            cursor.execute("UPDATE users SET is_deleted = FALSE WHERE is_deleted IS NULL")
            print("✓ 成功")
        except sqlite3.OperationalError:
            print("⚠ 跳过")
        
        # 提交事务
        conn.commit()
        
        # 验证迁移结果
        print("\n验证迁移结果...")
        cursor.execute("PRAGMA table_info(users)")
        columns_after = [col[1] for col in cursor.fetchall()]
        
        print("\n迁移后 users 表的字段:")
        for col in columns_after:
            print(f"  - {col}")
        
        # 检查新字段
        if 'is_superuser' in columns_after and 'is_deleted' in columns_after:
            print("\n✅ 迁移成功！is_superuser 和 is_deleted 字段已添加")
            
            # 显示现有用户数量
            cursor.execute("SELECT COUNT(*) FROM users")
            user_count = cursor.fetchone()[0]
            print(f"\n当前用户数: {user_count}")
            
            if user_count > 0:
                print("\n提示: 如需设置超级管理员，请执行:")
                print("  UPDATE users SET is_superuser = TRUE WHERE email = 'your@email.com';")
            
            return True
        else:
            print("\n❌ 迁移失败：字段未成功添加")
            return False
        
    except Exception as e:
        print(f"\n❌ 迁移失败: {e}")
        import traceback
        traceback.print_exc()
        return False
    
    finally:
        if conn:
            conn.close()

if __name__ == "__main__":
    success = run_migration()
    sys.exit(0 if success else 1)
