-- 迁移脚本：为 users 表添加超级管理员和软删除字段
-- 日期: 2026-01-06
-- 描述: 添加 is_superuser 和 is_deleted 字段以支持管理员功能

-- 1. 添加 is_superuser 字段（超级管理员标识）
ALTER TABLE users ADD COLUMN is_superuser BOOLEAN DEFAULT FALSE;

-- 2. 添加 is_deleted 字段（软删除标识）
ALTER TABLE users ADD COLUMN is_deleted BOOLEAN DEFAULT FALSE;

-- 3. 更新现有数据：确保所有现有用户的新字段都有默认值
UPDATE users SET is_superuser = FALSE WHERE is_superuser IS NULL;
UPDATE users SET is_deleted = FALSE WHERE is_deleted IS NULL;

-- 4. 可选：将某个用户设置为超级管理员（根据需要取消注释并修改邮箱）
-- UPDATE users SET is_superuser = TRUE WHERE email = 'admin@example.com';

-- 验证迁移结果
SELECT 'Migration completed successfully' AS status;
