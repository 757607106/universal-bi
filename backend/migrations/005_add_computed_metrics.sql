-- 添加计算指标表
-- 用于存储业务指标的计算公式和语义描述

CREATE TABLE IF NOT EXISTS computed_metrics (
    id INT AUTO_INCREMENT PRIMARY KEY,
    dataset_id INT NOT NULL,
    name VARCHAR(255) NOT NULL COMMENT '指标名称',
    formula TEXT NOT NULL COMMENT 'SQL计算公式',
    description TEXT COMMENT '业务口径描述',
    owner_id INT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    
    INDEX idx_dataset_id (dataset_id),
    INDEX idx_name (name),
    
    FOREIGN KEY (dataset_id) REFERENCES datasets(id) ON DELETE CASCADE,
    FOREIGN KEY (owner_id) REFERENCES users(id) ON DELETE SET NULL
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='计算指标表';

