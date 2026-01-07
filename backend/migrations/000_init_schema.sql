-- ========================================
-- Universal BI 数据库初始化脚本
-- ========================================
-- 用途：在 MySQL/PostgreSQL 中创建必要的表结构
-- 执行：docker-compose 启动时自动执行
-- ========================================

-- 创建数据源表
CREATE TABLE IF NOT EXISTS datasources (
    id INTEGER PRIMARY KEY AUTO_INCREMENT,
    name VARCHAR(100) NOT NULL UNIQUE COMMENT '数据源名称',
    db_type VARCHAR(20) NOT NULL COMMENT '数据库类型: mysql/postgresql',
    host VARCHAR(255) NOT NULL COMMENT '主机地址',
    port INTEGER NOT NULL COMMENT '端口号',
    database_name VARCHAR(100) NOT NULL COMMENT '数据库名',
    username VARCHAR(100) NOT NULL COMMENT '用户名',
    password VARCHAR(255) NOT NULL COMMENT '密码（加密存储）',
    owner_id INTEGER COMMENT '所有者ID',
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP COMMENT '创建时间',
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP COMMENT '更新时间'
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='数据源配置表';

-- 创建数据集表
CREATE TABLE IF NOT EXISTS datasets (
    id INTEGER PRIMARY KEY AUTO_INCREMENT,
    name VARCHAR(255) NOT NULL COMMENT '数据集名称',
    datasource_id INTEGER NOT NULL COMMENT '关联的数据源ID',
    collection_name VARCHAR(255) UNIQUE COMMENT 'Vanna collection名称',
    schema_config JSON COMMENT '已选择的表列表（JSON格式）',
    status VARCHAR(50) DEFAULT 'pending' COMMENT '训练状态: pending, training, completed, failed, paused',
    modeling_config JSON COMMENT '存储前端可视化建模的画布数据(nodes/edges)',
    process_rate INTEGER DEFAULT 0 COMMENT '训练进度百分比 0-100',
    error_msg TEXT COMMENT '错误信息',
    last_train_at DATETIME COMMENT '最后训练时间',
    owner_id INTEGER COMMENT '所有者ID',
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP COMMENT '创建时间',
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP COMMENT '更新时间',
    FOREIGN KEY (datasource_id) REFERENCES datasources(id) ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='数据集表';

-- 创建仪表盘表
CREATE TABLE IF NOT EXISTS dashboards (
    id INTEGER PRIMARY KEY AUTO_INCREMENT,
    name VARCHAR(100) NOT NULL COMMENT '仪表盘名称',
    description TEXT COMMENT '描述',
    owner_id INTEGER COMMENT '所有者ID',
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP COMMENT '创建时间',
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP COMMENT '更新时间'
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='仪表盘表';

-- 创建业务术语表
CREATE TABLE IF NOT EXISTS business_terms (
    id INTEGER PRIMARY KEY AUTO_INCREMENT,
    dataset_id INTEGER NOT NULL COMMENT '关联的数据集ID',
    term VARCHAR(255) NOT NULL COMMENT '术语名称',
    definition TEXT NOT NULL COMMENT '术语定义',
    owner_id INTEGER COMMENT '所有者ID',
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP COMMENT '创建时间',
    FOREIGN KEY (dataset_id) REFERENCES datasets(id) ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='业务术语表';

-- 创建训练日志表
CREATE TABLE IF NOT EXISTS training_logs (
    id INTEGER PRIMARY KEY AUTO_INCREMENT,
    dataset_id INTEGER NOT NULL COMMENT '关联的数据集ID',
    content TEXT NOT NULL COMMENT '日志内容',
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP COMMENT '创建时间',
    FOREIGN KEY (dataset_id) REFERENCES datasets(id) ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='训练日志表';

-- 创建仪表盘卡片表
CREATE TABLE IF NOT EXISTS dashboard_cards (
    id INTEGER PRIMARY KEY AUTO_INCREMENT,
    dashboard_id INTEGER NOT NULL COMMENT '所属仪表盘ID',
    dataset_id INTEGER NOT NULL COMMENT '关联的数据集ID',
    title VARCHAR(200) NOT NULL COMMENT '卡片标题',
    question TEXT NOT NULL COMMENT '原始问题',
    sql_query TEXT NOT NULL COMMENT 'SQL 查询语句',
    chart_type VARCHAR(50) DEFAULT 'table' COMMENT '图表类型: table/bar/line/pie',
    position_x INTEGER DEFAULT 0 COMMENT 'X 坐标位置',
    position_y INTEGER DEFAULT 0 COMMENT 'Y 坐标位置',
    width INTEGER DEFAULT 6 COMMENT '宽度（栅格列数）',
    height INTEGER DEFAULT 4 COMMENT '高度（栅格行数）',
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP COMMENT '创建时间',
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP COMMENT '更新时间',
    FOREIGN KEY (dashboard_id) REFERENCES dashboards(id) ON DELETE CASCADE,
    FOREIGN KEY (dataset_id) REFERENCES datasets(id) ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='仪表盘卡片表';

-- 创建用户表
CREATE TABLE IF NOT EXISTS users (
    id INTEGER PRIMARY KEY AUTO_INCREMENT,
    username VARCHAR(50) NOT NULL UNIQUE COMMENT '登录账号',
    email VARCHAR(255) UNIQUE COMMENT '邮箱',
    hashed_password VARCHAR(255) NOT NULL COMMENT '加密后的密码',
    full_name VARCHAR(255) COMMENT '姓名',
    company VARCHAR(255) COMMENT '公司信息',
    is_active BOOLEAN DEFAULT TRUE COMMENT '是否激活',
    is_superuser BOOLEAN DEFAULT FALSE COMMENT '是否超级管理员',
    is_deleted BOOLEAN DEFAULT FALSE COMMENT '软删除标记',
    role VARCHAR(50) DEFAULT 'user' COMMENT '用户角色',
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP COMMENT '创建时间',
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP COMMENT '更新时间'
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='用户表';

-- 创建聊天消息表
CREATE TABLE IF NOT EXISTS chat_messages (
    id INTEGER PRIMARY KEY AUTO_INCREMENT,
    dataset_id INTEGER NOT NULL COMMENT '关联的数据集ID',
    user_id INTEGER NOT NULL COMMENT '用户ID',
    owner_id INTEGER COMMENT '所有者ID',
    question TEXT NOT NULL COMMENT '用户问题',
    answer TEXT COMMENT 'AI回答',
    sql TEXT COMMENT 'SQL语句',
    chart_type VARCHAR(50) COMMENT '图表类型',
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP COMMENT '创建时间',
    FOREIGN KEY (dataset_id) REFERENCES datasets(id) ON DELETE CASCADE,
    FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE,
    FOREIGN KEY (owner_id) REFERENCES users(id) ON DELETE SET NULL
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='聊天消息表';

-- 创建索引
CREATE INDEX idx_datasource_owner ON datasources(owner_id);
CREATE INDEX idx_dataset_datasource ON datasets(datasource_id);
CREATE INDEX idx_dataset_owner ON datasets(owner_id);
CREATE INDEX idx_dataset_collection_name ON datasets(collection_name);
CREATE INDEX idx_business_term_dataset ON business_terms(dataset_id);
CREATE INDEX idx_business_term_owner ON business_terms(owner_id);
CREATE INDEX idx_training_log_dataset ON training_logs(dataset_id);
CREATE INDEX idx_training_log_created ON training_logs(created_at);
CREATE INDEX idx_dashboard_owner ON dashboards(owner_id);
CREATE INDEX idx_card_dashboard ON dashboard_cards(dashboard_id);
CREATE INDEX idx_card_dataset ON dashboard_cards(dataset_id);
CREATE INDEX idx_user_username ON users(username);
CREATE INDEX idx_user_email ON users(email);
CREATE INDEX idx_chat_message_dataset ON chat_messages(dataset_id);
CREATE INDEX idx_chat_message_user ON chat_messages(user_id);
CREATE INDEX idx_chat_message_owner ON chat_messages(owner_id);
CREATE INDEX idx_chat_message_created ON chat_messages(created_at);

-- 插入默认管理员账户（密码: admin123）
INSERT IGNORE INTO users (username, email, hashed_password, full_name, company, is_superuser) 
VALUES ('admin', 'admin@example.com', '$2b$12$LQv3c1yqBWVHxkd0LHAkCOYz6TtxMQJqhN8/LewY5GyYmOTLYV8Ku', '系统管理员', 'Universal BI', TRUE);

-- 打印初始化信息
SELECT '===========================================';
SELECT 'Universal BI 数据库初始化完成';
SELECT '===========================================';
SELECT '默认管理员账户:';
SELECT '  账号: admin';
SELECT '  密码: admin123';
SELECT '  请登录后及时修改密码！';
SELECT '===========================================';
