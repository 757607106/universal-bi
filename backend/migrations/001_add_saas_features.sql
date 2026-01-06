-- ===================================================================
-- SaaS 核心升级 - 数据模型与隔离机制迁移脚本
-- ===================================================================
-- 此脚本用于将现有数据库升级为多租户 SaaS 架构
-- 
-- 主要变更:
-- 1. User 模型新增 is_superuser, is_deleted 字段
-- 2. 所有业务模型新增 owner_id 字段（可为 NULL，表示公共资源）
-- 3. 现有数据的 owner_id 默认设为 1（假设 ID=1 是首个管理员）
-- ===================================================================

-- Step 1: 修改 users 表，新增超级管理员和软删除字段
ALTER TABLE users ADD COLUMN is_superuser BOOLEAN DEFAULT FALSE;
ALTER TABLE users ADD COLUMN is_deleted BOOLEAN DEFAULT FALSE;

-- 将第一个用户设置为超级管理员（可选，根据实际需求调整）
UPDATE users SET is_superuser = TRUE WHERE id = 1;

-- Step 2: 修改 datasources 表
-- datasources 表已有 owner_id，但需确保可为 NULL
ALTER TABLE datasources ALTER COLUMN owner_id DROP NOT NULL;

-- 将现有数据的 owner_id 设为 1（假设 ID=1 是首个管理员）
UPDATE datasources SET owner_id = 1 WHERE owner_id IS NULL;

-- Step 3: 修改 datasets 表
-- datasets 表已有 owner_id，但需确保可为 NULL
ALTER TABLE datasets ALTER COLUMN owner_id DROP NOT NULL;

-- 将现有数据的 owner_id 设为 1
UPDATE datasets SET owner_id = 1 WHERE owner_id IS NULL;

-- Step 4: 修改 dashboards 表，新增 owner_id 字段
ALTER TABLE dashboards ADD COLUMN owner_id INTEGER;
ALTER TABLE dashboards ADD CONSTRAINT fk_dashboards_owner FOREIGN KEY (owner_id) REFERENCES users(id);

-- 将现有看板的 owner_id 设为 1
UPDATE dashboards SET owner_id = 1 WHERE owner_id IS NULL;

-- Step 5: 修改 business_terms 表，新增 owner_id 字段
ALTER TABLE business_terms ADD COLUMN owner_id INTEGER;
ALTER TABLE business_terms ADD CONSTRAINT fk_business_terms_owner FOREIGN KEY (owner_id) REFERENCES users(id);

-- 将现有术语的 owner_id 设为 1
UPDATE business_terms SET owner_id = 1 WHERE owner_id IS NULL;

-- Step 6: 创建 chat_messages 表（如果不存在）
CREATE TABLE IF NOT EXISTS chat_messages (
    id SERIAL PRIMARY KEY,
    dataset_id INTEGER NOT NULL REFERENCES datasets(id) ON DELETE CASCADE,
    user_id INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    owner_id INTEGER REFERENCES users(id) ON DELETE SET NULL,
    question TEXT NOT NULL,
    answer TEXT,
    sql TEXT,
    chart_type VARCHAR(50),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- 创建索引以优化查询性能
CREATE INDEX idx_chat_messages_dataset_id ON chat_messages(dataset_id);
CREATE INDEX idx_chat_messages_user_id ON chat_messages(user_id);
CREATE INDEX idx_chat_messages_owner_id ON chat_messages(owner_id);
CREATE INDEX idx_chat_messages_created_at ON chat_messages(created_at);

-- ===================================================================
-- SQLite 版本（如果使用 SQLite）
-- ===================================================================
-- 注意：SQLite 不支持 ALTER COLUMN，需要使用更复杂的方式
-- 以下是 SQLite 兼容版本（保留供参考）

/*
-- SQLite 版本（仅在使用 SQLite 时使用）

-- Step 1: 修改 users 表
-- SQLite 需要创建新表并迁移数据
BEGIN TRANSACTION;

-- 创建备份表
CREATE TABLE users_backup AS SELECT * FROM users;

-- 删除旧表
DROP TABLE users;

-- 创建新表结构
CREATE TABLE users (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    email VARCHAR UNIQUE NOT NULL,
    hashed_password VARCHAR NOT NULL,
    full_name VARCHAR,
    is_active BOOLEAN DEFAULT 1,
    is_superuser BOOLEAN DEFAULT 0,
    is_deleted BOOLEAN DEFAULT 0,
    role VARCHAR DEFAULT 'user'
);

-- 恢复数据（添加默认值）
INSERT INTO users (id, email, hashed_password, full_name, is_active, role, is_superuser, is_deleted)
SELECT id, email, hashed_password, full_name, is_active, role, 0, 0 FROM users_backup;

-- 设置第一个用户为超级管理员
UPDATE users SET is_superuser = 1 WHERE id = 1;

-- 删除备份表
DROP TABLE users_backup;

COMMIT;

-- Step 2-5: 为其他表添加 owner_id（SQLite 方式类似）
-- ... 省略详细步骤，原理同上

-- Step 6: 创建 chat_messages 表（SQLite 版本）
CREATE TABLE IF NOT EXISTS chat_messages (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    dataset_id INTEGER NOT NULL,
    user_id INTEGER NOT NULL,
    owner_id INTEGER,
    question TEXT NOT NULL,
    answer TEXT,
    sql TEXT,
    chart_type VARCHAR(50),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (dataset_id) REFERENCES datasets(id) ON DELETE CASCADE,
    FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE,
    FOREIGN KEY (owner_id) REFERENCES users(id) ON DELETE SET NULL
);

-- 创建索引
CREATE INDEX idx_chat_messages_dataset_id ON chat_messages(dataset_id);
CREATE INDEX idx_chat_messages_user_id ON chat_messages(user_id);
CREATE INDEX idx_chat_messages_owner_id ON chat_messages(owner_id);
CREATE INDEX idx_chat_messages_created_at ON chat_messages(created_at);
*/

-- ===================================================================
-- 验证迁移结果（可选）
-- ===================================================================
-- 检查用户表结构
-- SELECT * FROM users LIMIT 5;

-- 检查各表的 owner_id 分布
-- SELECT 'datasources' as table_name, COUNT(*) as total, COUNT(owner_id) as with_owner FROM datasources
-- UNION ALL
-- SELECT 'datasets', COUNT(*), COUNT(owner_id) FROM datasets
-- UNION ALL
-- SELECT 'dashboards', COUNT(*), COUNT(owner_id) FROM dashboards
-- UNION ALL
-- SELECT 'business_terms', COUNT(*), COUNT(owner_id) FROM business_terms;
