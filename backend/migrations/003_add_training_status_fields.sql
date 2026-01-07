-- Migration: 003_add_training_status_fields.sql
-- Description: 添加训练状态管理和可视化建模存档字段
-- Date: 2026-01-07

-- =====================================================
-- 1. 修改 datasets 表，添加新字段
-- =====================================================

-- 重命名 training_status 为 status (如果存在旧字段)
-- MySQL 语法
ALTER TABLE datasets CHANGE COLUMN training_status status VARCHAR(50) DEFAULT 'pending' COMMENT 'pending, training, completed, failed, paused';

-- 重命名 last_trained_at 为 last_train_at (如果存在旧字段)
ALTER TABLE datasets CHANGE COLUMN last_trained_at last_train_at DATETIME NULL;

-- 添加 modeling_config 字段
ALTER TABLE datasets ADD COLUMN modeling_config JSON NULL COMMENT '存储前端可视化建模的画布数据(nodes/edges)';

-- 添加 process_rate 字段
ALTER TABLE datasets ADD COLUMN process_rate INT DEFAULT 0 COMMENT '训练进度百分比 0-100';

-- 添加 error_msg 字段
ALTER TABLE datasets ADD COLUMN error_msg TEXT NULL;

-- =====================================================
-- 2. 创建 training_logs 表
-- =====================================================

CREATE TABLE IF NOT EXISTS training_logs (
    id INT AUTO_INCREMENT PRIMARY KEY,
    dataset_id INT NOT NULL,
    content TEXT NOT NULL COMMENT '日志内容',
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    
    INDEX idx_training_logs_dataset_id (dataset_id),
    INDEX idx_training_logs_created_at (created_at),
    
    CONSTRAINT fk_training_logs_dataset 
        FOREIGN KEY (dataset_id) REFERENCES datasets(id) ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci COMMENT='训练日志表';

-- =====================================================
-- PostgreSQL 语法 (如果使用 PostgreSQL)
-- =====================================================

-- ALTER TABLE datasets RENAME COLUMN training_status TO status;
-- ALTER TABLE datasets RENAME COLUMN last_trained_at TO last_train_at;
-- ALTER TABLE datasets ADD COLUMN IF NOT EXISTS modeling_config JSONB;
-- ALTER TABLE datasets ADD COLUMN IF NOT EXISTS process_rate INTEGER DEFAULT 0;
-- ALTER TABLE datasets ADD COLUMN IF NOT EXISTS error_msg TEXT;

-- CREATE TABLE IF NOT EXISTS training_logs (
--     id SERIAL PRIMARY KEY,
--     dataset_id INTEGER NOT NULL REFERENCES datasets(id) ON DELETE CASCADE,
--     content TEXT NOT NULL,
--     created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
-- );
-- CREATE INDEX IF NOT EXISTS idx_training_logs_dataset_id ON training_logs(dataset_id);
-- CREATE INDEX IF NOT EXISTS idx_training_logs_created_at ON training_logs(created_at);
