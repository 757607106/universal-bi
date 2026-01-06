#!/usr/bin/env python3
"""
设置用户为超级管理员
"""

import sqlite3
import sys
from pathlib import Path

BACKEND_DIR = Path(__file__).parent
DB_PATH = BACKEND_DIR / "sql_app.db"

def set_superuser(email: str):
    """设置指定邮箱的用户为超级管理员"""
    
    try:
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()
        
        # 检查用户是否存在
        cursor.execute("SELECT id, email, is_superuser FROM users WHERE email = ?", (email,))
        user = cursor.fetchone()
        
        if not user:
            print(f"❌ 用户不存在: {email}")
            return False
        
        user_id, user_email, is_superuser = user
        
        if is_superuser:
            print(f"✓ 用户 {email} 已经是超级管理员")
            return True
        
        # 设置为超级管理员
        cursor.execute("UPDATE users SET is_superuser = TRUE WHERE email = ?", (email,))
        conn.commit()
        
        print(f"✅ 成功将用户 {email} (ID: {user_id}) 设置为超级管理员")
        return True
        
    except Exception as e:
        print(f"❌ 操作失败: {e}")
        return False
    finally:
        if conn:
            conn.close()

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("用法: python3 set_superuser.py <email>")
        print("示例: python3 set_superuser.py admin@example.com")
        sys.exit(1)
    
    email = sys.argv[1]
    success = set_superuser(email)
    sys.exit(0 if success else 1)
