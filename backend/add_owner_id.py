#!/usr/bin/env python3
"""
为所有需要权限隔离的表添加 owner_id 字段
"""

import sqlite3
from pathlib import Path

BACKEND_DIR = Path(__file__).parent
DB_PATH = BACKEND_DIR / "sql_app.db"

# 需要添加 owner_id 的表
TABLES = ["datasources", "datasets", "dashboards", "business_terms", "chat_messages"]

def add_owner_id_columns():
    """为所有表添加 owner_id 字段"""
    
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    
    print("=" * 60)
    print("开始为表添加 owner_id 字段...")
    print("=" * 60)
    
    try:
        for table in TABLES:
            print(f"\n处理表: {table}")
            
            # 检查表是否存在
            cursor.execute(
                "SELECT name FROM sqlite_master WHERE type='table' AND name=?", 
                (table,)
            )
            if not cursor.fetchone():
                print(f"  ⚠ 表 {table} 不存在，跳过")
                continue
            
            # 检查字段是否已存在
            cursor.execute(f"PRAGMA table_info({table})")
            columns = [col[1] for col in cursor.fetchall()]
            
            if 'owner_id' in columns:
                print(f"  ✓ owner_id 字段已存在")
            else:
                print(f"  + 添加 owner_id 字段...")
                cursor.execute(
                    f"ALTER TABLE {table} ADD COLUMN owner_id INTEGER"
                )
                print(f"  ✓ 成功")
        
        conn.commit()
        print("\n" + "=" * 60)
        print("✅ 所有表的 owner_id 字段已添加完成")
        print("=" * 60)
        
        # 显示每个表的字段
        print("\n验证结果:")
        for table in TABLES:
            cursor.execute(
                "SELECT name FROM sqlite_master WHERE type='table' AND name=?", 
                (table,)
            )
            if cursor.fetchone():
                cursor.execute(f"PRAGMA table_info({table})")
                columns = [col[1] for col in cursor.fetchall()]
                has_owner = "✓" if "owner_id" in columns else "✗"
                print(f"  {has_owner} {table}: {len(columns)} 个字段")
        
        return True
        
    except Exception as e:
        print(f"\n❌ 操作失败: {e}")
        import traceback
        traceback.print_exc()
        return False
    finally:
        conn.close()

if __name__ == "__main__":
    import sys
    success = add_owner_id_columns()
    sys.exit(0 if success else 1)
