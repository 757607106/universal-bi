-- ========================================
-- 迁移脚本：添加 company 字段到 users 表
-- ========================================

-- 添加 company 字段（如果不存在）
ALTER TABLE users ADD COLUMN IF NOT EXISTS company VARCHAR(255) COMMENT '公司信息' AFTER full_name;

-- 如果上述语法不支持，使用以下方式（MySQL 8.0+）
-- SET @s = (SELECT IF(
--     (SELECT COUNT(*) FROM INFORMATION_SCHEMA.COLUMNS WHERE TABLE_NAME = 'users' AND COLUMN_NAME = 'company' AND TABLE_SCHEMA = DATABASE()) > 0,
--     'SELECT 1',
--     'ALTER TABLE users ADD COLUMN company VARCHAR(255) COMMENT "公司信息" AFTER full_name'
-- ));
-- PREPARE stmt FROM @s;
-- EXECUTE stmt;
-- DEALLOCATE PREPARE stmt;

SELECT 'Migration 004: Added company column to users table' AS migration_status;
