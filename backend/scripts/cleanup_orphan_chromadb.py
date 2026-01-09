#!/usr/bin/env python3
"""
清理孤立的 ChromaDB Collection 文件

用途：
    删除数据集后，ChromaDB 文件夹可能残留。
    本脚本会检查 chroma_db 目录中的所有 collection，
    并删除数据库中不存在对应 dataset 的 collection。

使用方法：
    python scripts/cleanup_orphan_chromadb.py [--dry-run] [--confirm]
    
参数：
    --dry-run: 只显示要删除的内容，不实际删除
    --confirm: 跳过确认提示，直接执行删除
"""

import os
import sys
import argparse
import shutil
from pathlib import Path

# 添加项目根目录到 Python 路径
sys.path.insert(0, str(Path(__file__).parent.parent))

from app.db.session import SessionLocal
from app.models.metadata import Dataset
from app.core.config import settings
from app.core.logger import get_logger

logger = get_logger(__name__)


def get_all_dataset_collections(db_session) -> set[str]:
    """
    从数据库获取所有数据集的 collection_name
    
    Returns:
        set[str]: collection_name 集合
    """
    datasets = db_session.query(Dataset).all()
    return {ds.collection_name for ds in datasets if ds.collection_name}


def get_chromadb_collections(chroma_dir: str) -> dict[str, str]:
    """
    扫描 ChromaDB 目录，获取所有 collection
    
    Returns:
        dict[str, str]: {collection_name: collection_uuid_path}
    """
    chroma_path = Path(chroma_dir)
    
    if not chroma_path.exists():
        logger.warning(f"ChromaDB 目录不存在: {chroma_dir}")
        return {}
    
    # ChromaDB 使用 UUID 作为目录名
    collections = {}
    
    for uuid_dir in chroma_path.iterdir():
        if not uuid_dir.is_dir():
            continue
            
        # 检查是否为有效的 UUID 目录（36 字符，包含 4 个连字符）
        if len(uuid_dir.name) == 36 and uuid_dir.name.count('-') == 4:
            # ChromaDB 目录结构: chroma_db/{uuid}/
            # 需要读取 collection 元数据来获取 collection_name
            # 简化处理：假设目录名即为 collection 的标识
            collections[uuid_dir.name] = str(uuid_dir)
    
    return collections


def find_orphan_collections(
    db_collections: set[str], 
    chroma_collections: dict[str, str],
    db_session
) -> list[tuple[str, str]]:
    """
    查找孤立的 collection（chroma_db 中存在但数据库中不存在）
    
    Returns:
        list[tuple[str, str]]: [(uuid, path), ...]
    """
    orphans = []
    
    # 获取所有数据集的 ID（用于匹配 vec_ds_{id} 格式）
    datasets = db_session.query(Dataset.id, Dataset.collection_name).all()
    valid_ids = {ds.id for ds in datasets}
    
    for uuid, path in chroma_collections.items():
        # 检查该 UUID 是否对应某个数据集的 collection
        # 由于我们无法直接从 UUID 反推 collection_name，
        # 我们需要通过 ChromaDB 的 SQLite 数据库查询
        
        # 简化方案：如果 chroma_db 目录下的 UUID 目录不被任何数据集引用，
        # 我们认为它是孤立的
        
        # 读取 chroma.sqlite3 来匹配
        # 为了简化，我们先标记所有 UUID 目录，后续可以手动确认
        orphans.append((uuid, path))
    
    return orphans


def cleanup_orphans(orphans: list[tuple[str, str]], dry_run: bool = True):
    """
    清理孤立的 collection
    
    Args:
        orphans: [(uuid, path), ...]
        dry_run: 如果为 True，只打印不删除
    """
    if not orphans:
        logger.info("✅ 没有发现孤立的 ChromaDB collection")
        return
    
    logger.info(f"发现 {len(orphans)} 个可能的孤立 collection:")
    
    for uuid, path in orphans:
        logger.info(f"  - {uuid} ({path})")
    
    if dry_run:
        logger.info("\n🔍 Dry-run 模式：未执行实际删除")
        logger.info("如需删除，请使用: python scripts/cleanup_orphan_chromadb.py --confirm")
        return
    
    # 执行删除
    deleted_count = 0
    for uuid, path in orphans:
        try:
            shutil.rmtree(path)
            logger.info(f"✅ 已删除: {uuid}")
            deleted_count += 1
        except Exception as e:
            logger.error(f"❌ 删除失败 {uuid}: {e}")
    
    logger.info(f"\n✅ 清理完成，共删除 {deleted_count} 个 collection")


def main():
    parser = argparse.ArgumentParser(description="清理孤立的 ChromaDB collection")
    parser.add_argument(
        "--dry-run", 
        action="store_true", 
        help="只显示要删除的内容，不实际删除（默认）"
    )
    parser.add_argument(
        "--confirm", 
        action="store_true", 
        help="跳过确认提示，直接执行删除"
    )
    
    args = parser.parse_args()
    
    # 默认为 dry-run 模式
    dry_run = not args.confirm
    
    logger.info("=" * 60)
    logger.info("ChromaDB 孤立文件清理工具")
    logger.info("=" * 60)
    logger.info(f"ChromaDB 目录: {settings.CHROMA_PERSIST_DIR}")
    logger.info(f"模式: {'Dry-run (预览)' if dry_run else '实际删除'}")
    logger.info("=" * 60)
    
    # 1. 连接数据库
    db = SessionLocal()
    try:
        # 2. 获取数据库中的所有 collection
        db_collections = get_all_dataset_collections(db)
        logger.info(f"数据库中有 {len(db_collections)} 个数据集 collection")
        
        # 3. 扫描 ChromaDB 目录
        chroma_collections = get_chromadb_collections(settings.CHROMA_PERSIST_DIR)
        logger.info(f"ChromaDB 目录中有 {len(chroma_collections)} 个 collection 文件夹")
        
        # 4. 找出孤立的 collection
        # 注意：由于 ChromaDB 使用 UUID 作为目录名，我们需要更智能的匹配
        # 这里我们使用一个简化的策略：
        # 读取 chroma.sqlite3 数据库来获取 collection_name 和 UUID 的映射
        
        import sqlite3
        sqlite_path = os.path.join(settings.CHROMA_PERSIST_DIR, "chroma.sqlite3")
        
        if not os.path.exists(sqlite_path):
            logger.error(f"ChromaDB SQLite 文件不存在: {sqlite_path}")
            return
        
        conn = sqlite3.connect(sqlite_path)
        cursor = conn.cursor()
        
        # 查询所有 collection
        cursor.execute("SELECT name, id FROM collections")
        chromadb_records = cursor.fetchall()
        conn.close()
        
        logger.info(f"ChromaDB SQLite 中有 {len(chromadb_records)} 条 collection 记录")
        
        # 查找孤立的 collection
        orphans = []
        for coll_name, coll_uuid in chromadb_records:
            if coll_name not in db_collections:
                # 找到对应的目录路径
                coll_path = os.path.join(settings.CHROMA_PERSIST_DIR, coll_uuid)
                if os.path.exists(coll_path):
                    orphans.append((coll_name, coll_uuid, coll_path))
        
        # 5. 清理孤立的 collection
        if orphans:
            logger.info(f"\n发现 {len(orphans)} 个孤立的 collection:")
            for name, uuid, path in orphans:
                logger.info(f"  - {name} (UUID: {uuid})")
            
            if dry_run:
                logger.info("\n🔍 Dry-run 模式：未执行实际删除")
                logger.info("如需删除，请使用: python scripts/cleanup_orphan_chromadb.py --confirm")
            else:
                # 确认删除
                print("\n⚠️  警告：即将删除以上 collection！")
                response = input("确认删除吗？(yes/no): ")
                
                if response.lower() == "yes":
                    deleted_count = 0
                    for name, uuid, path in orphans:
                        try:
                            # 从 SQLite 中删除记录
                            conn = sqlite3.connect(sqlite_path)
                            cursor = conn.cursor()
                            cursor.execute("DELETE FROM collections WHERE id = ?", (uuid,))
                            conn.commit()
                            conn.close()
                            
                            # 删除文件夹
                            if os.path.exists(path):
                                shutil.rmtree(path)
                            
                            logger.info(f"✅ 已删除: {name} (UUID: {uuid})")
                            deleted_count += 1
                        except Exception as e:
                            logger.error(f"❌ 删除失败 {name}: {e}")
                    
                    logger.info(f"\n✅ 清理完成，共删除 {deleted_count} 个 collection")
                else:
                    logger.info("❌ 已取消删除")
        else:
            logger.info("\n✅ 没有发现孤立的 ChromaDB collection")
    
    finally:
        db.close()


if __name__ == "__main__":
    main()
