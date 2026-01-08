-- 数据库迁移脚本：添加会话管理和看板模板功能
-- 执行时间：2026-01-09
-- 注意：请按顺序执行，如果某条语句报错"Duplicate column"可以忽略

-- ============ 1. 创建 chat_sessions 表 ============
CREATE TABLE IF NOT EXISTS chat_sessions (
    id INT AUTO_INCREMENT PRIMARY KEY,
    title VARCHAR(255) DEFAULT '新会话',
    dataset_id INT NULL,
    owner_id INT NOT NULL,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    updated_at DATETIME DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    INDEX idx_owner_id (owner_id),
    INDEX idx_dataset_id (dataset_id),
    FOREIGN KEY (dataset_id) REFERENCES datasets(id) ON DELETE SET NULL,
    FOREIGN KEY (owner_id) REFERENCES users(id) ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- ============ 2. 修改 chat_messages 表 ============
-- 添加 session_id 字段（如果已存在会报错，可忽略）
ALTER TABLE chat_messages ADD COLUMN session_id INT NULL AFTER id;
ALTER TABLE chat_messages ADD INDEX idx_session_id (session_id);
ALTER TABLE chat_messages ADD FOREIGN KEY fk_session (session_id) REFERENCES chat_sessions(id) ON DELETE CASCADE;

-- 添加 role 字段（如果已存在会报错，可忽略）
ALTER TABLE chat_messages ADD COLUMN role VARCHAR(20) DEFAULT 'user' AFTER owner_id;

-- 添加 chart_data 字段（如果已存在会报错，可忽略）
ALTER TABLE chat_messages ADD COLUMN chart_data JSON NULL AFTER chart_type;

-- 添加 insight 字段（如果已存在会报错，可忽略）
ALTER TABLE chat_messages ADD COLUMN insight TEXT NULL AFTER chart_data;

-- ============ 3. 创建 dashboard_templates 表 ============
CREATE TABLE IF NOT EXISTS dashboard_templates (
    id INT AUTO_INCREMENT PRIMARY KEY,
    name VARCHAR(255) NOT NULL,
    description VARCHAR(500) NULL,
    source_dashboard_id INT NULL,
    config JSON NOT NULL,
    owner_id INT NOT NULL,
    is_public BOOLEAN DEFAULT FALSE,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    updated_at DATETIME DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    INDEX idx_owner_id (owner_id),
    INDEX idx_is_public (is_public),
    INDEX idx_name (name),
    FOREIGN KEY (source_dashboard_id) REFERENCES dashboards(id) ON DELETE SET NULL,
    FOREIGN KEY (owner_id) REFERENCES users(id) ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;
