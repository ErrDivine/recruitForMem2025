-- 南京大学招生助手系统数据库建表脚本
-- 创建数据库
CREATE DATABASE IF NOT EXISTS nju_recruitment CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;
USE nju_recruitment;

-- 1. 专业信息表
CREATE TABLE majors (
    id INT AUTO_INCREMENT PRIMARY KEY,
    major_code VARCHAR(20) UNIQUE NOT NULL COMMENT '专业代码',
    major_name VARCHAR(100) NOT NULL COMMENT '专业名称',
    category ENUM('理科', '文科', '综合') NOT NULL DEFAULT '综合' COMMENT '专业类别',
    quota INT DEFAULT 0 COMMENT '招生名额',
    description TEXT COMMENT '专业描述',
    is_active BOOLEAN DEFAULT TRUE COMMENT '是否启用',
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP
) COMMENT '专业信息表';

-- 2. 学生信息表
CREATE TABLE students (
    id INT AUTO_INCREMENT PRIMARY KEY,
    student_id VARCHAR(20) UNIQUE COMMENT '学生编号',
    name VARCHAR(50) NOT NULL COMMENT '考生姓名',
    high_school VARCHAR(100) COMMENT '考生高中学校名',
    category BOOLEAN NOT NULL COMMENT '考生类别：0-文科生，1-理科生',
    total_score DECIMAL(6,2) DEFAULT 0.00 COMMENT '考生高考总分',
    chinese_score DECIMAL(6,2) DEFAULT 0.00 COMMENT '考生高考语文分数',
    math_score DECIMAL(6,2) DEFAULT 0.00 COMMENT '考生高考数学分数',
    overall_rank INT DEFAULT 0 COMMENT '考生省排名',
    sfp_university VARCHAR(100) COMMENT '考生强基学校（如果没有就是空字符串）',
    tele_student VARCHAR(20) COMMENT '考生自己联系电话',
    tele_parent VARCHAR(20) COMMENT '考生家长联系电话',
    transferable BOOLEAN DEFAULT FALSE COMMENT '考生是否服从调剂',
    level INT DEFAULT 0 COMMENT '考生意向等级，0-100分',
    admission_status ENUM('未处理', '已录取', '已滑档', '调剂中') DEFAULT '未处理' COMMENT '录取状态',
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    INDEX idx_category (category),
    INDEX idx_total_score (total_score),
    INDEX idx_overall_rank (overall_rank),
    INDEX idx_admission_status (admission_status)
) COMMENT '学生信息表';

-- 3. 工作人员基础表
CREATE TABLE crew_base (
    id INT AUTO_INCREMENT PRIMARY KEY,
    name VARCHAR(50) NOT NULL COMMENT '工作人员名字',
    account VARCHAR(50) UNIQUE NOT NULL COMMENT '工作人员账号',
    password VARCHAR(255) NOT NULL COMMENT '账号密码（加密）',
    email VARCHAR(100) COMMENT '工作人员邮箱',
    color VARCHAR(20) COMMENT '颜色标识',
    is_active BOOLEAN DEFAULT TRUE COMMENT '是否启用',
    last_login TIMESTAMP NULL COMMENT '最后登录时间',
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    INDEX idx_account (account)
) COMMENT '工作人员基础表';

-- 4. 普通工作人员表
CREATE TABLE crew_members (
    id INT AUTO_INCREMENT PRIMARY KEY,
    crew_base_id INT NOT NULL UNIQUE,
    -- 将来可能添加的特有字段
    member_level INT DEFAULT 1 COMMENT '成员等级',
    supervisor_id INT COMMENT '上级主管ID',
    FOREIGN KEY (crew_base_id) REFERENCES crew_base(id) ON DELETE CASCADE,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP
) COMMENT '普通工作人员表';

-- 5. 工作人员负责人表
CREATE TABLE crew_leaders (
    id INT AUTO_INCREMENT PRIMARY KEY,
    crew_base_id INT NOT NULL UNIQUE,
    -- 将来可能添加的特有字段
    department VARCHAR(100) COMMENT '负责部门',
    authority_level INT DEFAULT 1 COMMENT '权限等级',
    FOREIGN KEY (crew_base_id) REFERENCES crew_base(id) ON DELETE CASCADE,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP
) COMMENT '工作人员负责人表';

-- 6. 学生意向专业关联表
CREATE TABLE student_intended_majors (
    id INT AUTO_INCREMENT PRIMARY KEY,
    student_id INT NOT NULL,
    major_name VARCHAR(100) NOT NULL COMMENT '专业名（字符串）',
    priority INT NOT NULL COMMENT '志愿优先级，数字越小优先级越高',
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (student_id) REFERENCES students(id) ON DELETE CASCADE,
    UNIQUE KEY uk_student_major_priority (student_id, major_name, priority),
    INDEX idx_student_id (student_id),
    INDEX idx_priority (priority)
) COMMENT '学生意向专业关联表 - 专业名字符串列表';

-- 7. 学生承诺专业关联表
CREATE TABLE student_promise_majors (
    id INT AUTO_INCREMENT PRIMARY KEY,
    student_id INT NOT NULL,
    major_name VARCHAR(100) NOT NULL COMMENT '招生组对考生的承诺专业名',
    priority INT NOT NULL COMMENT '承诺优先级',
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (student_id) REFERENCES students(id) ON DELETE CASCADE,
    UNIQUE KEY uk_student_promise_priority (student_id, major_name, priority),
    INDEX idx_student_id (student_id)
) COMMENT '学生承诺专业关联表 - 招生组承诺专业列表';

-- 8. 学生负责人关联表
CREATE TABLE student_due_chargers (
    id INT AUTO_INCREMENT PRIMARY KEY,
    student_id INT NOT NULL,
    crew_base_id INT NOT NULL COMMENT '负责人ID（可以是member或leader）',
    assigned_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    is_primary BOOLEAN DEFAULT FALSE COMMENT '是否为主要负责人',
    FOREIGN KEY (student_id) REFERENCES students(id) ON DELETE CASCADE,
    FOREIGN KEY (crew_base_id) REFERENCES crew_base(id) ON DELETE CASCADE,
    UNIQUE KEY uk_student_crew (student_id, crew_base_id),
    INDEX idx_student_id (student_id),
    INDEX idx_crew_base_id (crew_base_id)
) COMMENT '学生负责人关联表';

-- 9. 学生沟通记录表
CREATE TABLE student_records (
    id INT AUTO_INCREMENT PRIMARY KEY,
    student_id INT NOT NULL,
    contact_time TIMESTAMP NOT NULL COMMENT '联系时间',
    contact_person VARCHAR(50) NOT NULL COMMENT '联系人',
    content_summary TEXT NOT NULL COMMENT '沟通内容摘要',
    record_type ENUM('咨询', '面试', '录取', '调剂', '其他') NOT NULL DEFAULT '其他' COMMENT '记录类型',
    operator_id INT COMMENT '操作人员ID',
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (student_id) REFERENCES students(id) ON DELETE CASCADE,
    FOREIGN KEY (operator_id) REFERENCES crew_base(id) ON DELETE SET NULL,
    INDEX idx_student_id (student_id),
    INDEX idx_contact_time (contact_time),
    INDEX idx_record_type (record_type)
) COMMENT '学生沟通记录表 - 格式：[联系时间,联系人]->沟通内容摘要';

-- 10. 工作人员联系学生列表
CREATE TABLE crew_worklist (
    id INT AUTO_INCREMENT PRIMARY KEY,
    crew_base_id INT NOT NULL,
    student_name VARCHAR(50) NOT NULL COMMENT '需要联系的考生名字',
    priority ENUM('低', '中', '高', '紧急') DEFAULT '中' COMMENT '优先级',
    status ENUM('待处理', '进行中', '已完成', '已取消') DEFAULT '待处理' COMMENT '状态',
    notes TEXT COMMENT '备注信息',
    due_date DATE COMMENT '截止日期',
    completed_at TIMESTAMP NULL COMMENT '完成时间',
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    FOREIGN KEY (crew_base_id) REFERENCES crew_base(id) ON DELETE CASCADE,
    INDEX idx_crew_base_id (crew_base_id),
    INDEX idx_student_name (student_name),
    INDEX idx_status (status),
    INDEX idx_priority (priority)
) COMMENT '工作人员联系学生列表 - 由考生名字组成的列表';

-- 11. 工作文件表 - 支持网页文件访问
CREATE TABLE crew_work_files (
    id INT AUTO_INCREMENT PRIMARY KEY,
    crew_base_id INT NOT NULL,
    file_name VARCHAR(255) NOT NULL COMMENT '文件显示名称',
    file_original_name VARCHAR(255) NOT NULL COMMENT '原始文件名',
    file_path VARCHAR(500) NOT NULL COMMENT '服务器文件存储路径',
    file_url VARCHAR(500) COMMENT '文件访问URL（用于网页打开）',
    file_size BIGINT DEFAULT 0 COMMENT '文件大小（字节）',
    file_type VARCHAR(50) COMMENT '文件类型/扩展名',
    mime_type VARCHAR(100) COMMENT 'MIME类型（用于浏览器识别）',
    description TEXT COMMENT '文件描述',
    access_permission ENUM('private', 'crew_only', 'public') DEFAULT 'private' COMMENT '访问权限',
    is_viewable_online BOOLEAN DEFAULT TRUE COMMENT '是否可在线查看',
    download_count INT DEFAULT 0 COMMENT '下载次数',
    last_accessed TIMESTAMP NULL COMMENT '最后访问时间',
    upload_time TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (crew_base_id) REFERENCES crew_base(id) ON DELETE CASCADE,
    INDEX idx_crew_base_id (crew_base_id),
    INDEX idx_file_type (file_type),
    INDEX idx_access_permission (access_permission),
    INDEX idx_upload_time (upload_time)
) COMMENT '工作文件表 - 支持网页文件访问和在线查看';

-- 创建默认管理员账户（密码需要在应用中加密）
INSERT INTO crew_base (name, account, password, email, color) VALUES 
('系统管理员', 'admin', 'admin123', 'admin@nju.edu.cn', '#007AFF');

-- 将管理员设置为负责人
INSERT INTO crew_leaders (crew_base_id, department, authority_level) VALUES 
(1, '系统管理', 10);

-- 添加crew_members表的外键约束（在所有表创建完成后）
ALTER TABLE crew_members 
ADD CONSTRAINT fk_crew_members_supervisor 
FOREIGN KEY (supervisor_id) REFERENCES crew_leaders(id) ON DELETE SET NULL;

-- 插入一些示例专业数据
INSERT INTO majors (major_code, major_name, category, quota, description) VALUES
('001', '人文科学试验班', '文科', 30, '人文社科类综合培养'),
('002', '汉语言文学', '文科', 25, '中国语言文学专业'),
('003', '英语', '文科', 20, '英语语言文学专业'),
('004', '德语(德语法学实验班)', '文科', 15, '德语与法学交叉培养'),
('101', '理科试验班类（数理科学类）', '理科', 40, '数学物理类基础学科'),
('102', '理科试验班类（化学与生命科学类）', '理科', 35, '化学生物类基础学科'),
('103', '计算机科学与技术', '理科', 50, '计算机科学技术专业'),
('104', '软件工程', '理科', 45, '软件工程专业'); 