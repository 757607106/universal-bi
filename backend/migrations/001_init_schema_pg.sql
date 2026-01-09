-- ========================================
-- Universal BI 数据库初始化脚本 (PostgreSQL)
-- ========================================
-- 用途：在 PostgreSQL 中创建必要的表结构
-- 执行：docker-compose 启动时自动执行
-- ========================================

-- 创建数据源表
CREATE TABLE IF NOT EXISTS datasources (
    id SERIAL PRIMARY KEY,
    name VARCHAR(100) NOT NULL UNIQUE,
    db_type VARCHAR(20) NOT NULL,
    host VARCHAR(255) NOT NULL,
    port INTEGER NOT NULL,
    database_name VARCHAR(100) NOT NULL,
    username VARCHAR(100) NOT NULL,
    password VARCHAR(255) NOT NULL,
    owner_id INTEGER,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

COMMENT ON TABLE datasources IS '数据源配置表';
COMMENT ON COLUMN datasources.name IS '数据源名称';
COMMENT ON COLUMN datasources.db_type IS '数据库类型: mysql/postgresql';
COMMENT ON COLUMN datasources.host IS '主机地址';
COMMENT ON COLUMN datasources.port IS '端口号';
COMMENT ON COLUMN datasources.database_name IS '数据库名';
COMMENT ON COLUMN datasources.username IS '用户名';
COMMENT ON COLUMN datasources.password IS '密码（加密存储）';
COMMENT ON COLUMN datasources.owner_id IS '所有者ID';
COMMENT ON COLUMN datasources.created_at IS '创建时间';
COMMENT ON COLUMN datasources.updated_at IS '更新时间';

-- 创建数据集表
CREATE TABLE IF NOT EXISTS datasets (
    id SERIAL PRIMARY KEY,
    name VARCHAR(255) NOT NULL,
    datasource_id INTEGER,
    collection_name VARCHAR(255) UNIQUE,
    schema_config JSONB,
    status VARCHAR(50) DEFAULT 'pending',
    modeling_config JSONB,
    process_rate INTEGER DEFAULT 0,
    error_msg TEXT,
    last_train_at TIMESTAMP,
    duckdb_path VARCHAR(500),
    owner_id INTEGER,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (datasource_id) REFERENCES datasources(id) ON DELETE CASCADE
);

COMMENT ON TABLE datasets IS '数据集表';
COMMENT ON COLUMN datasets.name IS '数据集名称';
COMMENT ON COLUMN datasets.datasource_id IS '关联的数据源ID（DuckDB数据集可为NULL）';
COMMENT ON COLUMN datasets.collection_name IS 'Vanna collection名称';
COMMENT ON COLUMN datasets.schema_config IS '已选择的表列表（JSON格式）';
COMMENT ON COLUMN datasets.status IS '训练状态: pending, training, completed, failed, paused';
COMMENT ON COLUMN datasets.modeling_config IS '存储前端可视化建模的画布数据(nodes/edges)';
COMMENT ON COLUMN datasets.process_rate IS '训练进度百分比 0-100';
COMMENT ON COLUMN datasets.error_msg IS '错误信息';
COMMENT ON COLUMN datasets.last_train_at IS '最后训练时间';
COMMENT ON COLUMN datasets.duckdb_path IS 'DuckDB 数据库文件路径';
COMMENT ON COLUMN datasets.owner_id IS '所有者ID';

-- 创建仪表盘表
CREATE TABLE IF NOT EXISTS dashboards (
    id SERIAL PRIMARY KEY,
    name VARCHAR(100) NOT NULL,
    description TEXT,
    owner_id INTEGER,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

COMMENT ON TABLE dashboards IS '仪表盘表';
COMMENT ON COLUMN dashboards.name IS '仪表盘名称';
COMMENT ON COLUMN dashboards.description IS '描述';
COMMENT ON COLUMN dashboards.owner_id IS '所有者ID';

-- 创建业务术语表
CREATE TABLE IF NOT EXISTS business_terms (
    id SERIAL PRIMARY KEY,
    dataset_id INTEGER NOT NULL,
    term VARCHAR(255) NOT NULL,
    definition TEXT NOT NULL,
    owner_id INTEGER,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (dataset_id) REFERENCES datasets(id) ON DELETE CASCADE
);

COMMENT ON TABLE business_terms IS '业务术语表';
COMMENT ON COLUMN business_terms.dataset_id IS '关联的数据集ID';
COMMENT ON COLUMN business_terms.term IS '术语名称';
COMMENT ON COLUMN business_terms.definition IS '术语定义';
COMMENT ON COLUMN business_terms.owner_id IS '所有者ID';

-- 创建训练日志表
CREATE TABLE IF NOT EXISTS training_logs (
    id SERIAL PRIMARY KEY,
    dataset_id INTEGER NOT NULL,
    content TEXT NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (dataset_id) REFERENCES datasets(id) ON DELETE CASCADE
);

COMMENT ON TABLE training_logs IS '训练日志表';
COMMENT ON COLUMN training_logs.dataset_id IS '关联的数据集ID';
COMMENT ON COLUMN training_logs.content IS '日志内容';

-- 创建仪表盘卡片表
CREATE TABLE IF NOT EXISTS dashboard_cards (
    id SERIAL PRIMARY KEY,
    dashboard_id INTEGER NOT NULL,
    dataset_id INTEGER NOT NULL,
    title VARCHAR(200) NOT NULL,
    question TEXT NOT NULL,
    sql_query TEXT NOT NULL,
    chart_type VARCHAR(50) DEFAULT 'table',
    position_x INTEGER DEFAULT 0,
    position_y INTEGER DEFAULT 0,
    width INTEGER DEFAULT 6,
    height INTEGER DEFAULT 4,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (dashboard_id) REFERENCES dashboards(id) ON DELETE CASCADE,
    FOREIGN KEY (dataset_id) REFERENCES datasets(id) ON DELETE CASCADE
);

COMMENT ON TABLE dashboard_cards IS '仪表盘卡片表';
COMMENT ON COLUMN dashboard_cards.dashboard_id IS '所属仪表盘ID';
COMMENT ON COLUMN dashboard_cards.dataset_id IS '关联的数据集ID';
COMMENT ON COLUMN dashboard_cards.title IS '卡片标题';
COMMENT ON COLUMN dashboard_cards.question IS '原始问题';
COMMENT ON COLUMN dashboard_cards.sql_query IS 'SQL 查询语句';
COMMENT ON COLUMN dashboard_cards.chart_type IS '图表类型: table/bar/line/pie';

-- 创建用户表
CREATE TABLE IF NOT EXISTS users (
    id SERIAL PRIMARY KEY,
    username VARCHAR(50) NOT NULL UNIQUE,
    email VARCHAR(255) UNIQUE,
    hashed_password VARCHAR(255) NOT NULL,
    full_name VARCHAR(255),
    company VARCHAR(255),
    is_active BOOLEAN DEFAULT TRUE,
    is_superuser BOOLEAN DEFAULT FALSE,
    is_deleted BOOLEAN DEFAULT FALSE,
    role VARCHAR(50) DEFAULT 'user',
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

COMMENT ON TABLE users IS '用户表';
COMMENT ON COLUMN users.username IS '登录账号';
COMMENT ON COLUMN users.email IS '邮箱';
COMMENT ON COLUMN users.hashed_password IS '加密后的密码';
COMMENT ON COLUMN users.full_name IS '姓名';
COMMENT ON COLUMN users.company IS '公司信息';
COMMENT ON COLUMN users.is_active IS '是否激活';
COMMENT ON COLUMN users.is_superuser IS '是否超级管理员';
COMMENT ON COLUMN users.is_deleted IS '软删除标记';
COMMENT ON COLUMN users.role IS '用户角色';

-- 创建聊天会话表
CREATE TABLE IF NOT EXISTS chat_sessions (
    id SERIAL PRIMARY KEY,
    title VARCHAR(255) DEFAULT '新会话',
    dataset_id INTEGER,
    owner_id INTEGER NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (dataset_id) REFERENCES datasets(id) ON DELETE SET NULL,
    FOREIGN KEY (owner_id) REFERENCES users(id) ON DELETE CASCADE
);

COMMENT ON TABLE chat_sessions IS '会话模型';
COMMENT ON COLUMN chat_sessions.title IS '会话标题';
COMMENT ON COLUMN chat_sessions.dataset_id IS '关联的数据集（可选）';
COMMENT ON COLUMN chat_sessions.owner_id IS '会话所有者';

-- 创建聊天消息表
CREATE TABLE IF NOT EXISTS chat_messages (
    id SERIAL PRIMARY KEY,
    session_id INTEGER,
    dataset_id INTEGER NOT NULL,
    user_id INTEGER NOT NULL,
    owner_id INTEGER,
    role VARCHAR(20) DEFAULT 'user',
    question TEXT NOT NULL,
    answer TEXT,
    sql TEXT,
    chart_type VARCHAR(50),
    chart_data JSONB,
    insight TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (session_id) REFERENCES chat_sessions(id) ON DELETE SET NULL,
    FOREIGN KEY (dataset_id) REFERENCES datasets(id) ON DELETE CASCADE,
    FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE,
    FOREIGN KEY (owner_id) REFERENCES users(id) ON DELETE SET NULL
);

COMMENT ON TABLE chat_messages IS '聊天消息表';
COMMENT ON COLUMN chat_messages.session_id IS '关联会话';
COMMENT ON COLUMN chat_messages.role IS 'user/assistant';
COMMENT ON COLUMN chat_messages.question IS '用户问题';
COMMENT ON COLUMN chat_messages.answer IS 'AI回答';
COMMENT ON COLUMN chat_messages.sql IS 'SQL语句';
COMMENT ON COLUMN chat_messages.chart_type IS '图表类型';
COMMENT ON COLUMN chat_messages.chart_data IS '图表数据';
COMMENT ON COLUMN chat_messages.insight IS 'AI分析洞察';

-- 创建计算指标表
CREATE TABLE IF NOT EXISTS computed_metrics (
    id SERIAL PRIMARY KEY,
    dataset_id INTEGER NOT NULL,
    name VARCHAR(255) NOT NULL,
    formula TEXT NOT NULL,
    description TEXT,
    owner_id INTEGER,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (dataset_id) REFERENCES datasets(id) ON DELETE CASCADE,
    FOREIGN KEY (owner_id) REFERENCES users(id) ON DELETE SET NULL
);

COMMENT ON TABLE computed_metrics IS '计算指标表';
COMMENT ON COLUMN computed_metrics.dataset_id IS '关联的数据集ID';
COMMENT ON COLUMN computed_metrics.name IS '指标名称';
COMMENT ON COLUMN computed_metrics.formula IS 'SQL表达式';
COMMENT ON COLUMN computed_metrics.description IS '业务口径描述';

-- 创建数据表管理表
CREATE TABLE IF NOT EXISTS data_tables (
    id SERIAL PRIMARY KEY,
    name VARCHAR(255) NOT NULL,
    display_name VARCHAR(255),
    description TEXT,
    owner_id INTEGER NOT NULL,
    file_path VARCHAR(500) NOT NULL,
    file_type VARCHAR(20),
    file_size BIGINT,
    row_count INTEGER,
    column_count INTEGER,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (owner_id) REFERENCES users(id) ON DELETE CASCADE
);

COMMENT ON TABLE data_tables IS '数据表管理表';
COMMENT ON COLUMN data_tables.name IS '表名（唯一标识）';
COMMENT ON COLUMN data_tables.display_name IS '显示名称';
COMMENT ON COLUMN data_tables.file_path IS '文件存储路径';
COMMENT ON COLUMN data_tables.row_count IS '数据行数';

-- 创建仪表盘模板表
CREATE TABLE IF NOT EXISTS dashboard_templates (
    id SERIAL PRIMARY KEY,
    name VARCHAR(255) NOT NULL,
    description VARCHAR(500),
    source_dashboard_id INTEGER,
    config JSONB NOT NULL,
    owner_id INTEGER NOT NULL,
    is_public BOOLEAN DEFAULT FALSE,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (source_dashboard_id) REFERENCES dashboards(id) ON DELETE SET NULL,
    FOREIGN KEY (owner_id) REFERENCES users(id) ON DELETE CASCADE
);

COMMENT ON TABLE dashboard_templates IS '仪表盘模板表';
COMMENT ON COLUMN dashboard_templates.name IS '模板名称';
COMMENT ON COLUMN dashboard_templates.source_dashboard_id IS '来源看板（可选）';
COMMENT ON COLUMN dashboard_templates.config IS '卡片配置快照';
COMMENT ON COLUMN dashboard_templates.is_public IS '是否公开';

-- 创建索引
CREATE INDEX IF NOT EXISTS idx_datasource_owner ON datasources(owner_id);
CREATE INDEX IF NOT EXISTS idx_dataset_datasource ON datasets(datasource_id);
CREATE INDEX IF NOT EXISTS idx_dataset_owner ON datasets(owner_id);
CREATE INDEX IF NOT EXISTS idx_dataset_collection_name ON datasets(collection_name);
CREATE INDEX IF NOT EXISTS idx_business_term_dataset ON business_terms(dataset_id);
CREATE INDEX IF NOT EXISTS idx_business_term_owner ON business_terms(owner_id);
CREATE INDEX IF NOT EXISTS idx_training_log_dataset ON training_logs(dataset_id);
CREATE INDEX IF NOT EXISTS idx_training_log_created ON training_logs(created_at);
CREATE INDEX IF NOT EXISTS idx_dashboard_owner ON dashboards(owner_id);
CREATE INDEX IF NOT EXISTS idx_card_dashboard ON dashboard_cards(dashboard_id);
CREATE INDEX IF NOT EXISTS idx_card_dataset ON dashboard_cards(dataset_id);
CREATE INDEX IF NOT EXISTS idx_user_username ON users(username);
CREATE INDEX IF NOT EXISTS idx_user_email ON users(email);
CREATE INDEX IF NOT EXISTS idx_chat_session_owner ON chat_sessions(owner_id);
CREATE INDEX IF NOT EXISTS idx_chat_session_dataset ON chat_sessions(dataset_id);
CREATE INDEX IF NOT EXISTS idx_chat_message_session ON chat_messages(session_id);
CREATE INDEX IF NOT EXISTS idx_chat_message_dataset ON chat_messages(dataset_id);
CREATE INDEX IF NOT EXISTS idx_chat_message_user ON chat_messages(user_id);
CREATE INDEX IF NOT EXISTS idx_chat_message_owner ON chat_messages(owner_id);
CREATE INDEX IF NOT EXISTS idx_chat_message_created ON chat_messages(created_at);
CREATE INDEX IF NOT EXISTS idx_computed_metric_dataset ON computed_metrics(dataset_id);
CREATE INDEX IF NOT EXISTS idx_data_table_owner ON data_tables(owner_id);
CREATE INDEX IF NOT EXISTS idx_dashboard_template_owner ON dashboard_templates(owner_id);

-- 插入默认管理员账户（密码: admin123）
INSERT INTO users (username, email, hashed_password, full_name, company, is_superuser) 
VALUES ('admin', 'admin@example.com', '$2b$12$LQv3c1yqBWVHxkd0LHAkCOYz6TtxMQJqhN8/LewY5GyYmOTLYV8Ku', '系统管理员', 'Universal BI', TRUE)
ON CONFLICT (username) DO NOTHING;

-- 打印初始化信息
DO $$
BEGIN
    RAISE NOTICE '===========================================';
    RAISE NOTICE 'Universal BI 数据库初始化完成';
    RAISE NOTICE '===========================================';
    RAISE NOTICE '默认管理员账户:';
    RAISE NOTICE '  账号: admin';
    RAISE NOTICE '  密码: admin123';
    RAISE NOTICE '  请登录后及时修改密码！';
    RAISE NOTICE '===========================================';
END $$;
-- ========================================
-- Universal BI 数据库初始化脚本 (PostgreSQL)
-- ========================================
-- 用途：在 PostgreSQL 中创建必要的表结构
-- 执行：docker-compose 启动时自动执行
-- ========================================

-- 创建数据源表
CREATE TABLE IF NOT EXISTS datasources (
    id SERIAL PRIMARY KEY,
    name VARCHAR(100) NOT NULL UNIQUE,
    db_type VARCHAR(20) NOT NULL,
    host VARCHAR(255) NOT NULL,
    port INTEGER NOT NULL,
    database_name VARCHAR(100) NOT NULL,
    username VARCHAR(100) NOT NULL,
    password VARCHAR(255) NOT NULL,
    owner_id INTEGER,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

COMMENT ON TABLE datasources IS '数据源配置表';
COMMENT ON COLUMN datasources.name IS '数据源名称';
COMMENT ON COLUMN datasources.db_type IS '数据库类型: mysql/postgresql';
COMMENT ON COLUMN datasources.host IS '主机地址';
COMMENT ON COLUMN datasources.port IS '端口号';
COMMENT ON COLUMN datasources.database_name IS '数据库名';
COMMENT ON COLUMN datasources.username IS '用户名';
COMMENT ON COLUMN datasources.password IS '密码（加密存储）';
COMMENT ON COLUMN datasources.owner_id IS '所有者ID';
COMMENT ON COLUMN datasources.created_at IS '创建时间';
COMMENT ON COLUMN datasources.updated_at IS '更新时间';

-- 创建数据集表
CREATE TABLE IF NOT EXISTS datasets (
    id SERIAL PRIMARY KEY,
    name VARCHAR(255) NOT NULL,
    datasource_id INTEGER,
    collection_name VARCHAR(255) UNIQUE,
    schema_config JSONB,
    status VARCHAR(50) DEFAULT 'pending',
    modeling_config JSONB,
    process_rate INTEGER DEFAULT 0,
    error_msg TEXT,
    last_train_at TIMESTAMP,
    duckdb_path VARCHAR(500),
    owner_id INTEGER,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (datasource_id) REFERENCES datasources(id) ON DELETE CASCADE
);

COMMENT ON TABLE datasets IS '数据集表';
COMMENT ON COLUMN datasets.name IS '数据集名称';
COMMENT ON COLUMN datasets.datasource_id IS '关联的数据源ID（DuckDB数据集可为NULL）';
COMMENT ON COLUMN datasets.collection_name IS 'Vanna collection名称';
COMMENT ON COLUMN datasets.schema_config IS '已选择的表列表（JSON格式）';
COMMENT ON COLUMN datasets.status IS '训练状态: pending, training, completed, failed, paused';
COMMENT ON COLUMN datasets.modeling_config IS '存储前端可视化建模的画布数据(nodes/edges)';
COMMENT ON COLUMN datasets.process_rate IS '训练进度百分比 0-100';
COMMENT ON COLUMN datasets.error_msg IS '错误信息';
COMMENT ON COLUMN datasets.last_train_at IS '最后训练时间';
COMMENT ON COLUMN datasets.duckdb_path IS 'DuckDB 数据库文件路径';
COMMENT ON COLUMN datasets.owner_id IS '所有者ID';

-- 创建仪表盘表
CREATE TABLE IF NOT EXISTS dashboards (
    id SERIAL PRIMARY KEY,
    name VARCHAR(100) NOT NULL,
    description TEXT,
    owner_id INTEGER,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

COMMENT ON TABLE dashboards IS '仪表盘表';
COMMENT ON COLUMN dashboards.name IS '仪表盘名称';
COMMENT ON COLUMN dashboards.description IS '描述';
COMMENT ON COLUMN dashboards.owner_id IS '所有者ID';

-- 创建业务术语表
CREATE TABLE IF NOT EXISTS business_terms (
    id SERIAL PRIMARY KEY,
    dataset_id INTEGER NOT NULL,
    term VARCHAR(255) NOT NULL,
    definition TEXT NOT NULL,
    owner_id INTEGER,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (dataset_id) REFERENCES datasets(id) ON DELETE CASCADE
);

COMMENT ON TABLE business_terms IS '业务术语表';
COMMENT ON COLUMN business_terms.dataset_id IS '关联的数据集ID';
COMMENT ON COLUMN business_terms.term IS '术语名称';
COMMENT ON COLUMN business_terms.definition IS '术语定义';
COMMENT ON COLUMN business_terms.owner_id IS '所有者ID';

-- 创建训练日志表
CREATE TABLE IF NOT EXISTS training_logs (
    id SERIAL PRIMARY KEY,
    dataset_id INTEGER NOT NULL,
    content TEXT NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (dataset_id) REFERENCES datasets(id) ON DELETE CASCADE
);

COMMENT ON TABLE training_logs IS '训练日志表';
COMMENT ON COLUMN training_logs.dataset_id IS '关联的数据集ID';
COMMENT ON COLUMN training_logs.content IS '日志内容';

-- 创建仪表盘卡片表
CREATE TABLE IF NOT EXISTS dashboard_cards (
    id SERIAL PRIMARY KEY,
    dashboard_id INTEGER NOT NULL,
    dataset_id INTEGER NOT NULL,
    title VARCHAR(200) NOT NULL,
    question TEXT NOT NULL,
    sql_query TEXT NOT NULL,
    chart_type VARCHAR(50) DEFAULT 'table',
    position_x INTEGER DEFAULT 0,
    position_y INTEGER DEFAULT 0,
    width INTEGER DEFAULT 6,
    height INTEGER DEFAULT 4,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (dashboard_id) REFERENCES dashboards(id) ON DELETE CASCADE,
    FOREIGN KEY (dataset_id) REFERENCES datasets(id) ON DELETE CASCADE
);

COMMENT ON TABLE dashboard_cards IS '仪表盘卡片表';
COMMENT ON COLUMN dashboard_cards.dashboard_id IS '所属仪表盘ID';
COMMENT ON COLUMN dashboard_cards.dataset_id IS '关联的数据集ID';
COMMENT ON COLUMN dashboard_cards.title IS '卡片标题';
COMMENT ON COLUMN dashboard_cards.question IS '原始问题';
COMMENT ON COLUMN dashboard_cards.sql_query IS 'SQL 查询语句';
COMMENT ON COLUMN dashboard_cards.chart_type IS '图表类型: table/bar/line/pie';

-- 创建用户表
CREATE TABLE IF NOT EXISTS users (
    id SERIAL PRIMARY KEY,
    username VARCHAR(50) NOT NULL UNIQUE,
    email VARCHAR(255) UNIQUE,
    hashed_password VARCHAR(255) NOT NULL,
    full_name VARCHAR(255),
    company VARCHAR(255),
    is_active BOOLEAN DEFAULT TRUE,
    is_superuser BOOLEAN DEFAULT FALSE,
    is_deleted BOOLEAN DEFAULT FALSE,
    role VARCHAR(50) DEFAULT 'user',
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

COMMENT ON TABLE users IS '用户表';
COMMENT ON COLUMN users.username IS '登录账号';
COMMENT ON COLUMN users.email IS '邮箱';
COMMENT ON COLUMN users.hashed_password IS '加密后的密码';
COMMENT ON COLUMN users.full_name IS '姓名';
COMMENT ON COLUMN users.company IS '公司信息';
COMMENT ON COLUMN users.is_active IS '是否激活';
COMMENT ON COLUMN users.is_superuser IS '是否超级管理员';
COMMENT ON COLUMN users.is_deleted IS '软删除标记';
COMMENT ON COLUMN users.role IS '用户角色';

-- 创建聊天会话表
CREATE TABLE IF NOT EXISTS chat_sessions (
    id SERIAL PRIMARY KEY,
    title VARCHAR(255) DEFAULT '新会话',
    dataset_id INTEGER,
    owner_id INTEGER NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (dataset_id) REFERENCES datasets(id) ON DELETE SET NULL,
    FOREIGN KEY (owner_id) REFERENCES users(id) ON DELETE CASCADE
);

COMMENT ON TABLE chat_sessions IS '会话模型';
COMMENT ON COLUMN chat_sessions.title IS '会话标题';
COMMENT ON COLUMN chat_sessions.dataset_id IS '关联的数据集（可选）';
COMMENT ON COLUMN chat_sessions.owner_id IS '会话所有者';

-- 创建聊天消息表
CREATE TABLE IF NOT EXISTS chat_messages (
    id SERIAL PRIMARY KEY,
    session_id INTEGER,
    dataset_id INTEGER NOT NULL,
    user_id INTEGER NOT NULL,
    owner_id INTEGER,
    role VARCHAR(20) DEFAULT 'user',
    question TEXT NOT NULL,
    answer TEXT,
    sql TEXT,
    chart_type VARCHAR(50),
    chart_data JSONB,
    insight TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (session_id) REFERENCES chat_sessions(id) ON DELETE SET NULL,
    FOREIGN KEY (dataset_id) REFERENCES datasets(id) ON DELETE CASCADE,
    FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE,
    FOREIGN KEY (owner_id) REFERENCES users(id) ON DELETE SET NULL
);

COMMENT ON TABLE chat_messages IS '聊天消息表';
COMMENT ON COLUMN chat_messages.session_id IS '关联会话';
COMMENT ON COLUMN chat_messages.role IS 'user/assistant';
COMMENT ON COLUMN chat_messages.question IS '用户问题';
COMMENT ON COLUMN chat_messages.answer IS 'AI回答';
COMMENT ON COLUMN chat_messages.sql IS 'SQL语句';
COMMENT ON COLUMN chat_messages.chart_type IS '图表类型';
COMMENT ON COLUMN chat_messages.chart_data IS '图表数据';
COMMENT ON COLUMN chat_messages.insight IS 'AI分析洞察';

-- 创建计算指标表
CREATE TABLE IF NOT EXISTS computed_metrics (
    id SERIAL PRIMARY KEY,
    dataset_id INTEGER NOT NULL,
    name VARCHAR(255) NOT NULL,
    formula TEXT NOT NULL,
    description TEXT,
    owner_id INTEGER,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (dataset_id) REFERENCES datasets(id) ON DELETE CASCADE,
    FOREIGN KEY (owner_id) REFERENCES users(id) ON DELETE SET NULL
);

COMMENT ON TABLE computed_metrics IS '计算指标表';
COMMENT ON COLUMN computed_metrics.dataset_id IS '关联的数据集ID';
COMMENT ON COLUMN computed_metrics.name IS '指标名称';
COMMENT ON COLUMN computed_metrics.formula IS 'SQL表达式';
COMMENT ON COLUMN computed_metrics.description IS '业务口径描述';

-- 创建数据表管理表
CREATE TABLE IF NOT EXISTS data_tables (
    id SERIAL PRIMARY KEY,
    name VARCHAR(255) NOT NULL,
    display_name VARCHAR(255),
    description TEXT,
    owner_id INTEGER NOT NULL,
    file_path VARCHAR(500) NOT NULL,
    file_type VARCHAR(20),
    file_size BIGINT,
    row_count INTEGER,
    column_count INTEGER,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (owner_id) REFERENCES users(id) ON DELETE CASCADE
);

COMMENT ON TABLE data_tables IS '数据表管理表';
COMMENT ON COLUMN data_tables.name IS '表名（唯一标识）';
COMMENT ON COLUMN data_tables.display_name IS '显示名称';
COMMENT ON COLUMN data_tables.file_path IS '文件存储路径';
COMMENT ON COLUMN data_tables.row_count IS '数据行数';

-- 创建仪表盘模板表
CREATE TABLE IF NOT EXISTS dashboard_templates (
    id SERIAL PRIMARY KEY,
    name VARCHAR(255) NOT NULL,
    description VARCHAR(500),
    source_dashboard_id INTEGER,
    config JSONB NOT NULL,
    owner_id INTEGER NOT NULL,
    is_public BOOLEAN DEFAULT FALSE,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (source_dashboard_id) REFERENCES dashboards(id) ON DELETE SET NULL,
    FOREIGN KEY (owner_id) REFERENCES users(id) ON DELETE CASCADE
);

COMMENT ON TABLE dashboard_templates IS '仪表盘模板表';
COMMENT ON COLUMN dashboard_templates.name IS '模板名称';
COMMENT ON COLUMN dashboard_templates.source_dashboard_id IS '来源看板（可选）';
COMMENT ON COLUMN dashboard_templates.config IS '卡片配置快照';
COMMENT ON COLUMN dashboard_templates.is_public IS '是否公开';

-- 创建索引
CREATE INDEX IF NOT EXISTS idx_datasource_owner ON datasources(owner_id);
CREATE INDEX IF NOT EXISTS idx_dataset_datasource ON datasets(datasource_id);
CREATE INDEX IF NOT EXISTS idx_dataset_owner ON datasets(owner_id);
CREATE INDEX IF NOT EXISTS idx_dataset_collection_name ON datasets(collection_name);
CREATE INDEX IF NOT EXISTS idx_business_term_dataset ON business_terms(dataset_id);
CREATE INDEX IF NOT EXISTS idx_business_term_owner ON business_terms(owner_id);
CREATE INDEX IF NOT EXISTS idx_training_log_dataset ON training_logs(dataset_id);
CREATE INDEX IF NOT EXISTS idx_training_log_created ON training_logs(created_at);
CREATE INDEX IF NOT EXISTS idx_dashboard_owner ON dashboards(owner_id);
CREATE INDEX IF NOT EXISTS idx_card_dashboard ON dashboard_cards(dashboard_id);
CREATE INDEX IF NOT EXISTS idx_card_dataset ON dashboard_cards(dataset_id);
CREATE INDEX IF NOT EXISTS idx_user_username ON users(username);
CREATE INDEX IF NOT EXISTS idx_user_email ON users(email);
CREATE INDEX IF NOT EXISTS idx_chat_session_owner ON chat_sessions(owner_id);
CREATE INDEX IF NOT EXISTS idx_chat_session_dataset ON chat_sessions(dataset_id);
CREATE INDEX IF NOT EXISTS idx_chat_message_session ON chat_messages(session_id);
CREATE INDEX IF NOT EXISTS idx_chat_message_dataset ON chat_messages(dataset_id);
CREATE INDEX IF NOT EXISTS idx_chat_message_user ON chat_messages(user_id);
CREATE INDEX IF NOT EXISTS idx_chat_message_owner ON chat_messages(owner_id);
CREATE INDEX IF NOT EXISTS idx_chat_message_created ON chat_messages(created_at);
CREATE INDEX IF NOT EXISTS idx_computed_metric_dataset ON computed_metrics(dataset_id);
CREATE INDEX IF NOT EXISTS idx_data_table_owner ON data_tables(owner_id);
CREATE INDEX IF NOT EXISTS idx_dashboard_template_owner ON dashboard_templates(owner_id);

-- 插入默认管理员账户（密码: admin123）
INSERT INTO users (username, email, hashed_password, full_name, company, is_superuser) 
VALUES ('admin', 'admin@example.com', '$2b$12$LQv3c1yqBWVHxkd0LHAkCOYz6TtxMQJqhN8/LewY5GyYmOTLYV8Ku', '系统管理员', 'Universal BI', TRUE)
ON CONFLICT (username) DO NOTHING;

-- 打印初始化信息
DO $$
BEGIN
    RAISE NOTICE '===========================================';
    RAISE NOTICE 'Universal BI 数据库初始化完成';
    RAISE NOTICE '===========================================';
    RAISE NOTICE '默认管理员账户:';
    RAISE NOTICE '  账号: admin';
    RAISE NOTICE '  密码: admin123';
    RAISE NOTICE '  请登录后及时修改密码！';
    RAISE NOTICE '===========================================';
END $$;
