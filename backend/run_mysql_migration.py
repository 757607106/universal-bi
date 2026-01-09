#!/usr/bin/env python3
"""
执行 MySQL 数据库迁移脚本
支持运行 migrations 目录下的 SQL 文件
"""

import sys
import pymysql
from pathlib import Path
from urllib.parse import urlparse

# 获取项目根目录
BACKEND_DIR = Path(__file__).parent
sys.path.insert(0, str(BACKEND_DIR))

# 导入配置
from app.core.config import settings

def parse_mysql_uri(uri: str):
    """解析 MySQL 连接字符串"""
    # 移除 mysql+pymysql:// 前缀
    if uri.startswith("mysql+pymysql://"):
        uri = uri.replace("mysql+pymysql://", "mysql://")
    
    parsed = urlparse(uri)
    
    # 解析查询参数
    params = {}
    if parsed.query:
        for param in parsed.query.split('&'):
            if '=' in param:
                key, value = param.split('=', 1)
                params[key] = value
    
    return {
        'host': parsed.hostname or 'localhost',
        'port': parsed.port or 3306,
        'user': parsed.username or 'root',
        'password': parsed.password or '',
        'database': parsed.path.lstrip('/').split('?')[0] if parsed.path else 'universal_bi',
        'charset': params.get('charset', 'utf8mb4')
    }

def run_migration(migration_file: str = None):
    """执行数据库迁移"""
    
    # 如果未指定迁移文件，默认使用 007_add_duckdb_support.sql
    if not migration_file:
        migration_file = "007_add_duckdb_support.sql"
    
    MIGRATION_FILE = BACKEND_DIR / "migrations" / migration_file
    
    # 检查迁移文件是否存在
    if not MIGRATION_FILE.exists():
        print(f"❌ 迁移文件不存在: {MIGRATION_FILE}")
        return False
    
    print("=" * 80)
    print("开始执行 MySQL 数据库迁移...")
    print(f"迁移文件: {MIGRATION_FILE}")
    print("=" * 80)
    
    # 解析数据库连接信息
    db_config = parse_mysql_uri(settings.SQLALCHEMY_DATABASE_URI)
    
    print(f"\n数据库配置:")
    print(f"  主机: {db_config['host']}:{db_config['port']}")
    print(f"  数据库: {db_config['database']}")
    print(f"  用户: {db_config['user']}")
    print(f"  字符集: {db_config['charset']}")
    
    conn = None
    try:
        # 连接 MySQL 数据库
        print("\n正在连接数据库...")
        conn = pymysql.connect(
            host=db_config['host'],
            port=db_config['port'],
            user=db_config['user'],
            password=db_config['password'],
            database=db_config['database'],
            charset=db_config['charset'],
            autocommit=False
        )
        cursor = conn.cursor()
        print("✓ 数据库连接成功")
        
        # 检查 datasets 表是否存在 duckdb_path 字段
        print("\n检查 datasets 表当前结构...")
        cursor.execute("SHOW COLUMNS FROM datasets")
        columns = [col[0] for col in cursor.fetchall()]
        
        print(f"\n当前 datasets 表的字段 (共 {len(columns)} 个):")
        for col in columns:
            print(f"  - {col}")
        
        # 判断是否需要迁移
        needs_migration = False
        if 'duckdb_path' not in columns:
            print("\n✓ 需要添加 duckdb_path 字段")
            needs_migration = True
        else:
            print("\n⚠ duckdb_path 字段已存在，无需迁移")
        
        if not needs_migration:
            print("\n✅ 数据库已是最新状态，无需迁移")
            return True
        
        # 读取并执行迁移 SQL
        print("\n执行迁移 SQL...")
        with open(MIGRATION_FILE, 'r', encoding='utf-8') as f:
            migration_sql = f.read()
        
        # 分割 SQL 语句（按分号分隔）
        sql_statements = []
        for statement in migration_sql.split(';'):
            # 移除注释行（支持 -- 和 # 注释）
            lines = []
            for line in statement.split('\n'):
                line = line.strip()
                # 跳过注释行和空行
                if line and not line.startswith('--') and not line.startswith('#'):
                    lines.append(line)
            
            # 重新组合有效的 SQL 行
            clean_statement = ' '.join(lines).strip()
            if clean_statement:
                sql_statements.append(clean_statement)
        
        print(f"\n找到 {len(sql_statements)} 条 SQL 语句")
        
        # 逐条执行 SQL
        for i, sql in enumerate(sql_statements, 1):
            try:
                # 显示简化的 SQL（前50个字符）
                sql_preview = sql[:50].replace('\n', ' ') + ('...' if len(sql) > 50 else '')
                print(f"\n[{i}/{len(sql_statements)}] 执行: {sql_preview}")
                
                cursor.execute(sql)
                print(f"✓ 成功")
            except pymysql.err.OperationalError as e:
                error_msg = str(e)
                # 如果是字段已存在或索引已存在，则跳过
                if "Duplicate column name" in error_msg or "Duplicate key name" in error_msg:
                    print(f"⚠ 已存在，跳过")
                else:
                    print(f"❌ 失败: {error_msg}")
                    raise
            except Exception as e:
                print(f"❌ 失败: {e}")
                raise
        
        # 提交事务
        print("\n提交事务...")
        conn.commit()
        print("✓ 事务已提交")
        
        # 验证迁移结果
        print("\n验证迁移结果...")
        cursor.execute("SHOW COLUMNS FROM datasets")
        columns_after = [col[0] for col in cursor.fetchall()]
        
        print(f"\n迁移后 datasets 表的字段 (共 {len(columns_after)} 个):")
        for col in columns_after:
            print(f"  - {col}")
        
        # 检查新字段
        if 'duckdb_path' in columns_after:
            print("\n✅ 迁移成功！duckdb_path 字段已添加")
            
            # 显示现有 Dataset 数量
            cursor.execute("SELECT COUNT(*) FROM datasets")
            dataset_count = cursor.fetchone()[0]
            print(f"\n当前数据集数: {dataset_count}")
            
            return True
        else:
            print("\n❌ 迁移失败：duckdb_path 字段未成功添加")
            return False
        
    except pymysql.err.OperationalError as e:
        print(f"\n❌ 数据库连接失败: {e}")
        print("\n请检查:")
        print("  1. MySQL 服务是否已启动")
        print("  2. 数据库连接配置是否正确 (.env 文件)")
        print("  3. 数据库用户是否有足够权限")
        return False
    except Exception as e:
        print(f"\n❌ 迁移失败: {e}")
        import traceback
        traceback.print_exc()
        if conn:
            print("\n回滚事务...")
            conn.rollback()
            print("✓ 已回滚")
        return False
    finally:
        if conn:
            conn.close()
            print("\n数据库连接已关闭")

if __name__ == "__main__":
    # 支持命令行参数指定迁移文件
    migration_file = sys.argv[1] if len(sys.argv) > 1 else None
    success = run_migration(migration_file)
    
    if success:
        print("\n" + "=" * 80)
        print("🎉 数据库迁移完成！")
        print("=" * 80)
    else:
        print("\n" + "=" * 80)
        print("❌ 数据库迁移失败，请检查错误信息")
        print("=" * 80)
    
    sys.exit(0 if success else 1)
