-- ========================================
-- 迁移脚本：添加 DuckDB 多表分析支持
-- 版本：007
-- 日期：2026-01-09
-- 功能：为 Dataset 表添加 duckdb_path 字段
-- ========================================

-- 添加 duckdb_path 字段
ALTER TABLE datasets ADD COLUMN duckdb_path VARCHAR(500) NULL COMMENT 'DuckDB 数据库文件路径，用于多表分析';

-- 修改 datasource_id 为可空（DuckDB 数据集不需要传统数据源）
-- MySQL 语法
ALTER TABLE datasets MODIFY COLUMN datasource_id INT NULL;

-- PostgreSQL 语法（如果使用 PostgreSQL，注释掉上面的 MySQL 语句，使用下面的）
-- ALTER TABLE datasets ALTER COLUMN datasource_id DROP NOT NULL;

-- 添加索引以提高查询性能
CREATE INDEX idx_datasets_duckdb_path ON datasets(duckdb_path);

-- 添加注释
ALTER TABLE datasets MODIFY COLUMN duckdb_path VARCHAR(500) NULL COMMENT 'DuckDB 数据库文件路径，用于多表分析';
