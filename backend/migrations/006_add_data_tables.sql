-- ========================================
-- Universal BI 数据表管理功能迁移脚本
-- ========================================
-- 版本：006
-- 创建时间：2026-01-08
-- 功能：新增文件夹、数据表、字段配置表
-- ========================================

-- 创建文件夹表
CREATE TABLE IF NOT EXISTS folders (
    id INTEGER PRIMARY KEY AUTO_INCREMENT,
    name VARCHAR(255) NOT NULL COMMENT '文件夹名称',
    parent_id INTEGER COMMENT '父文件夹ID（支持嵌套）',
    owner_id INTEGER COMMENT '所有者ID',
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP COMMENT '创建时间',
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP COMMENT '更新时间',
    FOREIGN KEY (parent_id) REFERENCES folders(id) ON DELETE CASCADE,
    FOREIGN KEY (owner_id) REFERENCES users(id) ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='文件夹表';

-- 创建数据表元数据表
CREATE TABLE IF NOT EXISTS data_tables (
    id INTEGER PRIMARY KEY AUTO_INCREMENT,
    display_name VARCHAR(255) NOT NULL COMMENT '显示名称',
    physical_table_name VARCHAR(255) NOT NULL COMMENT '物理表名',
    datasource_id INTEGER NOT NULL COMMENT '数据源ID',
    folder_id INTEGER COMMENT '所属文件夹ID',
    description TEXT COMMENT '表备注',
    creation_method VARCHAR(50) NOT NULL COMMENT '建表方式: excel_upload, datasource_table',
    status VARCHAR(50) DEFAULT 'active' COMMENT '状态: active, archived',
    row_count INTEGER DEFAULT 0 COMMENT '行数',
    column_count INTEGER DEFAULT 0 COMMENT '列数',
    owner_id INTEGER COMMENT '创建人ID',
    modifier_id INTEGER COMMENT '修改人ID',
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP COMMENT '创建时间',
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP COMMENT '更新时间',
    FOREIGN KEY (datasource_id) REFERENCES datasources(id) ON DELETE CASCADE,
    FOREIGN KEY (folder_id) REFERENCES folders(id) ON DELETE SET NULL,
    FOREIGN KEY (owner_id) REFERENCES users(id) ON DELETE CASCADE,
    FOREIGN KEY (modifier_id) REFERENCES users(id) ON DELETE SET NULL
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='数据表元数据表';

-- 创建表字段配置表
CREATE TABLE IF NOT EXISTS table_fields (
    id INTEGER PRIMARY KEY AUTO_INCREMENT,
    data_table_id INTEGER NOT NULL COMMENT '数据表ID',
    field_name VARCHAR(255) NOT NULL COMMENT '字段值（物理字段名）',
    field_display_name VARCHAR(255) NOT NULL COMMENT '字段中文名',
    field_type VARCHAR(50) NOT NULL COMMENT '字段类型: text, number, datetime, geo',
    date_format VARCHAR(50) COMMENT '时间格式（如YYYY-MM-DD）',
    null_display VARCHAR(50) DEFAULT '—' COMMENT '空值展示',
    description TEXT COMMENT '字段备注',
    is_selected BOOLEAN DEFAULT TRUE COMMENT '是否选中',
    sort_order INTEGER DEFAULT 0 COMMENT '排序顺序',
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP COMMENT '创建时间',
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP COMMENT '更新时间',
    FOREIGN KEY (data_table_id) REFERENCES data_tables(id) ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='表字段配置表';

-- 创建索引
CREATE INDEX idx_folder_owner ON folders(owner_id);
CREATE INDEX idx_folder_parent ON folders(parent_id);
CREATE INDEX idx_data_table_owner ON data_tables(owner_id);
CREATE INDEX idx_data_table_datasource ON data_tables(datasource_id);
CREATE INDEX idx_data_table_folder ON data_tables(folder_id);
CREATE INDEX idx_data_table_physical_name ON data_tables(physical_table_name);
CREATE INDEX idx_table_field_data_table ON table_fields(data_table_id);
CREATE INDEX idx_table_field_sort ON table_fields(sort_order);

-- 打印迁移信息
SELECT '===========================================';
SELECT '数据表管理功能迁移完成';
SELECT '新增表: folders, data_tables, table_fields';
SELECT '===========================================';
