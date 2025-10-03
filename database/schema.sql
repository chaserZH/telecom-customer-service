

-- 创建数据库
CREATE DATABASE IF NOT EXISTS telecom_chatbot DEFAULT CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;

USE telecom_chatbot;

-- 1. 套餐表
CREATE TABLE IF NOT EXISTS t_packages (
    id INT PRIMARY KEY AUTO_INCREMENT COMMENT '套餐ID',
    name VARCHAR(50) NOT NULL UNIQUE COMMENT '套餐名称',
    data_gb INT NOT NULL COMMENT '每月流量(GB)',
    voice_minutes INT DEFAULT 0 COMMENT '每月通话时长(分钟)',
    price DECIMAL(10,2) NOT NULL COMMENT '月费(元)',
    target_user VARCHAR(20) DEFAULT '无限制' COMMENT '适用人群',
    description TEXT COMMENT '套餐说明',
    status TINYINT DEFAULT 1 COMMENT '状态: 1=在售, 0=下架',
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    INDEX idx_price (price),
    INDEX idx_data (data_gb),
    INDEX idx_status (status)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='套餐信息表';

-- 2. 用户表
CREATE TABLE IF NOT EXISTS t_user (
    phone VARCHAR(11) PRIMARY KEY COMMENT '手机号',
    name VARCHAR(50) COMMENT '姓名',
    current_package_id INT COMMENT '当前套餐ID',
    package_start_date DATE COMMENT '套餐生效日期',
    monthly_usage_gb DECIMAL(10,2) DEFAULT 0 COMMENT '本月已用流量(GB)',
    monthly_usage_minutes INT DEFAULT 0 COMMENT '本月已用通话(分钟)',
    balance DECIMAL(10,2) DEFAULT 0 COMMENT '账户余额(元)',
    status TINYINT DEFAULT 1 COMMENT '状态: 1=正常, 0=停机',
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    FOREIGN KEY (current_package_id) REFERENCES packages(id),
    INDEX idx_package (current_package_id),
    INDEX idx_status (status)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='用户信息表';

-- 3. 对话记录表
CREATE TABLE IF NOT EXISTS t_conversations (
    id BIGINT PRIMARY KEY AUTO_INCREMENT,
    session_id VARCHAR(64) NOT NULL COMMENT '会话ID',
    phone VARCHAR(11) COMMENT '用户手机号',
    user_input TEXT NOT NULL COMMENT '用户输入',
    intent VARCHAR(50) COMMENT '识别的意图',
    function_name VARCHAR(50) COMMENT '调用的函数',
    parameters JSON COMMENT '函数参数',
    bot_response TEXT COMMENT '机器人回复',
    execution_time_ms INT COMMENT '执行耗时(毫秒)',
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    INDEX idx_session (session_id),
    INDEX idx_phone (phone),
    INDEX idx_created (created_at)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='对话记录表';
