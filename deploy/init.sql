-- Vue FastAPI Admin full initialization script for MySQL 8.0.
-- Run this script only against a new database.
-- Initial login: admin / 123456. Change the password immediately after login.

SET NAMES utf8mb4;
SET time_zone = '+08:00';

CREATE DATABASE IF NOT EXISTS `vue_fastapi_admin`
    CHARACTER SET utf8mb4
    COLLATE utf8mb4_unicode_ci;
USE `vue_fastapi_admin`;

CREATE TABLE `api` (
    `id` BIGINT NOT NULL AUTO_INCREMENT,
    `created_at` DATETIME(6) NOT NULL DEFAULT CURRENT_TIMESTAMP(6),
    `updated_at` DATETIME(6) NOT NULL DEFAULT CURRENT_TIMESTAMP(6) ON UPDATE CURRENT_TIMESTAMP(6),
    `path` VARCHAR(100) NOT NULL COMMENT 'API路径',
    `method` VARCHAR(6) NOT NULL COMMENT '请求方法',
    `summary` VARCHAR(500) NOT NULL COMMENT '请求简介',
    `tags` VARCHAR(100) NOT NULL COMMENT 'API标签',
    PRIMARY KEY (`id`),
    UNIQUE KEY `uid_api_method_path` (`method`, `path`),
    KEY `idx_api_created_at` (`created_at`),
    KEY `idx_api_updated_at` (`updated_at`),
    KEY `idx_api_path` (`path`),
    KEY `idx_api_method` (`method`),
    KEY `idx_api_summary` (`summary`),
    KEY `idx_api_tags` (`tags`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

CREATE TABLE `auditlog` (
    `id` BIGINT NOT NULL AUTO_INCREMENT,
    `created_at` DATETIME(6) NOT NULL DEFAULT CURRENT_TIMESTAMP(6),
    `updated_at` DATETIME(6) NOT NULL DEFAULT CURRENT_TIMESTAMP(6) ON UPDATE CURRENT_TIMESTAMP(6),
    `user_id` INT NOT NULL COMMENT '用户ID',
    `username` VARCHAR(64) NOT NULL DEFAULT '' COMMENT '用户名称',
    `module` VARCHAR(64) NOT NULL DEFAULT '' COMMENT '功能模块',
    `summary` VARCHAR(128) NOT NULL DEFAULT '' COMMENT '请求描述',
    `method` VARCHAR(10) NOT NULL DEFAULT '' COMMENT '请求方法',
    `path` VARCHAR(255) NOT NULL DEFAULT '' COMMENT '请求路径',
    `status` INT NOT NULL DEFAULT -1 COMMENT '状态码',
    `response_time` INT NOT NULL DEFAULT 0 COMMENT '响应时间(单位ms)',
    `request_args` JSON NULL COMMENT '请求参数',
    `response_body` JSON NULL COMMENT '返回数据',
    PRIMARY KEY (`id`),
    KEY `idx_auditlog_created_at` (`created_at`),
    KEY `idx_auditlog_updated_at` (`updated_at`),
    KEY `idx_auditlog_user_id` (`user_id`),
    KEY `idx_auditlog_username` (`username`),
    KEY `idx_auditlog_module` (`module`),
    KEY `idx_auditlog_summary` (`summary`),
    KEY `idx_auditlog_method` (`method`),
    KEY `idx_auditlog_path` (`path`),
    KEY `idx_auditlog_status` (`status`),
    KEY `idx_auditlog_response_time` (`response_time`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

CREATE TABLE `dept` (
    `id` BIGINT NOT NULL AUTO_INCREMENT,
    `created_at` DATETIME(6) NOT NULL DEFAULT CURRENT_TIMESTAMP(6),
    `updated_at` DATETIME(6) NOT NULL DEFAULT CURRENT_TIMESTAMP(6) ON UPDATE CURRENT_TIMESTAMP(6),
    `name` VARCHAR(20) NOT NULL COMMENT '部门名称',
    `desc` VARCHAR(500) NULL COMMENT '备注',
    `is_deleted` BOOL NOT NULL DEFAULT 0 COMMENT '软删除标记',
    `order` INT NOT NULL DEFAULT 0 COMMENT '排序',
    `parent_id` INT NOT NULL DEFAULT 0 COMMENT '父部门ID',
    PRIMARY KEY (`id`),
    UNIQUE KEY `uid_dept_name` (`name`),
    KEY `idx_dept_created_at` (`created_at`),
    KEY `idx_dept_updated_at` (`updated_at`),
    KEY `idx_dept_is_deleted` (`is_deleted`),
    KEY `idx_dept_order` (`order`),
    KEY `idx_dept_parent_id` (`parent_id`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

CREATE TABLE `deptclosure` (
    `id` BIGINT NOT NULL AUTO_INCREMENT,
    `created_at` DATETIME(6) NOT NULL DEFAULT CURRENT_TIMESTAMP(6),
    `updated_at` DATETIME(6) NOT NULL DEFAULT CURRENT_TIMESTAMP(6) ON UPDATE CURRENT_TIMESTAMP(6),
    `ancestor` INT NOT NULL COMMENT '父代',
    `descendant` INT NOT NULL COMMENT '子代',
    `level` INT NOT NULL DEFAULT 0 COMMENT '深度',
    PRIMARY KEY (`id`),
    UNIQUE KEY `uid_deptclosure_ancestor_descendant` (`ancestor`, `descendant`),
    KEY `idx_deptclosure_created_at` (`created_at`),
    KEY `idx_deptclosure_updated_at` (`updated_at`),
    KEY `idx_deptclosure_ancestor` (`ancestor`),
    KEY `idx_deptclosure_descendant` (`descendant`),
    KEY `idx_deptclosure_level` (`level`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

CREATE TABLE `menu` (
    `id` BIGINT NOT NULL AUTO_INCREMENT,
    `created_at` DATETIME(6) NOT NULL DEFAULT CURRENT_TIMESTAMP(6),
    `updated_at` DATETIME(6) NOT NULL DEFAULT CURRENT_TIMESTAMP(6) ON UPDATE CURRENT_TIMESTAMP(6),
    `name` VARCHAR(20) NOT NULL COMMENT '菜单名称',
    `remark` JSON NULL COMMENT '保留字段',
    `menu_type` VARCHAR(7) NULL COMMENT '菜单类型',
    `icon` VARCHAR(100) NULL COMMENT '菜单图标',
    `path` VARCHAR(100) NOT NULL COMMENT '菜单路径',
    `order` INT NOT NULL DEFAULT 0 COMMENT '排序',
    `parent_id` INT NOT NULL DEFAULT 0 COMMENT '父菜单ID',
    `is_hidden` BOOL NOT NULL DEFAULT 0 COMMENT '是否隐藏',
    `component` VARCHAR(100) NOT NULL COMMENT '组件',
    `keepalive` BOOL NOT NULL DEFAULT 1 COMMENT '存活',
    `redirect` VARCHAR(100) NULL COMMENT '重定向',
    PRIMARY KEY (`id`),
    UNIQUE KEY `uid_menu_parent_path` (`parent_id`, `path`),
    KEY `idx_menu_created_at` (`created_at`),
    KEY `idx_menu_updated_at` (`updated_at`),
    KEY `idx_menu_name` (`name`),
    KEY `idx_menu_path` (`path`),
    KEY `idx_menu_order` (`order`),
    KEY `idx_menu_parent_id` (`parent_id`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

CREATE TABLE `role` (
    `id` BIGINT NOT NULL AUTO_INCREMENT,
    `created_at` DATETIME(6) NOT NULL DEFAULT CURRENT_TIMESTAMP(6),
    `updated_at` DATETIME(6) NOT NULL DEFAULT CURRENT_TIMESTAMP(6) ON UPDATE CURRENT_TIMESTAMP(6),
    `name` VARCHAR(20) NOT NULL COMMENT '角色名称',
    `desc` VARCHAR(500) NULL COMMENT '角色描述',
    PRIMARY KEY (`id`),
    UNIQUE KEY `uid_role_name` (`name`),
    KEY `idx_role_created_at` (`created_at`),
    KEY `idx_role_updated_at` (`updated_at`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

CREATE TABLE `user` (
    `id` BIGINT NOT NULL AUTO_INCREMENT,
    `created_at` DATETIME(6) NOT NULL DEFAULT CURRENT_TIMESTAMP(6),
    `updated_at` DATETIME(6) NOT NULL DEFAULT CURRENT_TIMESTAMP(6) ON UPDATE CURRENT_TIMESTAMP(6),
    `username` VARCHAR(20) NOT NULL COMMENT '用户名称',
    `alias` VARCHAR(30) NULL COMMENT '姓名',
    `email` VARCHAR(255) NOT NULL COMMENT '邮箱',
    `phone` VARCHAR(20) NULL COMMENT '电话',
    `password` VARCHAR(128) NULL COMMENT '密码',
    `is_active` BOOL NOT NULL DEFAULT 1 COMMENT '是否激活',
    `is_superuser` BOOL NOT NULL DEFAULT 0 COMMENT '是否为超级管理员',
    `last_login` DATETIME(6) NULL COMMENT '最后登录时间',
    `dept_id` INT NULL COMMENT '部门ID',
    PRIMARY KEY (`id`),
    UNIQUE KEY `uid_user_username` (`username`),
    UNIQUE KEY `uid_user_email` (`email`),
    KEY `idx_user_created_at` (`created_at`),
    KEY `idx_user_updated_at` (`updated_at`),
    KEY `idx_user_alias` (`alias`),
    KEY `idx_user_phone` (`phone`),
    KEY `idx_user_is_active` (`is_active`),
    KEY `idx_user_is_superuser` (`is_superuser`),
    KEY `idx_user_last_login` (`last_login`),
    KEY `idx_user_dept_id` (`dept_id`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

CREATE TABLE `wifi_external_call_log` (
    `id` BIGINT NOT NULL AUTO_INCREMENT,
    `created_at` DATETIME(6) NOT NULL DEFAULT CURRENT_TIMESTAMP(6),
    `updated_at` DATETIME(6) NOT NULL DEFAULT CURRENT_TIMESTAMP(6) ON UPDATE CURRENT_TIMESTAMP(6),
    `trace_id` VARCHAR(64) NOT NULL,
    `auth_tx_id_hash` VARCHAR(64) NULL,
    `system_name` VARCHAR(32) NOT NULL,
    `api_name` VARCHAR(128) NOT NULL,
    `method` VARCHAR(10) NOT NULL,
    `result_code` VARCHAR(32) NULL,
    `success` BOOL NOT NULL,
    `duration_ms` INT NOT NULL,
    `error_message_masked` VARCHAR(512) NULL,
    PRIMARY KEY (`id`),
    KEY `idx_wifi_external_created_at` (`created_at`),
    KEY `idx_wifi_external_updated_at` (`updated_at`),
    KEY `idx_wifi_external_trace_id` (`trace_id`),
    KEY `idx_wifi_external_auth_tx_id_hash` (`auth_tx_id_hash`),
    KEY `idx_wifi_external_system_name` (`system_name`),
    KEY `idx_wifi_external_api_name` (`api_name`),
    KEY `idx_wifi_external_result_code` (`result_code`),
    KEY `idx_wifi_external_success` (`success`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

CREATE TABLE `role_menu` (
    `role_id` BIGINT NOT NULL,
    `menu_id` BIGINT NOT NULL,
    UNIQUE KEY `uid_role_menu` (`role_id`, `menu_id`),
    CONSTRAINT `fk_role_menu_role` FOREIGN KEY (`role_id`) REFERENCES `role` (`id`) ON DELETE CASCADE,
    CONSTRAINT `fk_role_menu_menu` FOREIGN KEY (`menu_id`) REFERENCES `menu` (`id`) ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

CREATE TABLE `role_api` (
    `role_id` BIGINT NOT NULL,
    `api_id` BIGINT NOT NULL,
    UNIQUE KEY `uid_role_api` (`role_id`, `api_id`),
    CONSTRAINT `fk_role_api_role` FOREIGN KEY (`role_id`) REFERENCES `role` (`id`) ON DELETE CASCADE,
    CONSTRAINT `fk_role_api_api` FOREIGN KEY (`api_id`) REFERENCES `api` (`id`) ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

CREATE TABLE `user_role` (
    `user_id` BIGINT NOT NULL,
    `role_id` BIGINT NOT NULL,
    UNIQUE KEY `uid_user_role` (`user_id`, `role_id`),
    CONSTRAINT `fk_user_role_user` FOREIGN KEY (`user_id`) REFERENCES `user` (`id`) ON DELETE CASCADE,
    CONSTRAINT `fk_user_role_role` FOREIGN KEY (`role_id`) REFERENCES `role` (`id`) ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

START TRANSACTION;

INSERT INTO `api` (`id`, `method`, `path`, `summary`, `tags`) VALUES
    (1, 'GET', '/api/v1/base/userinfo', '查看用户信息', '基础模块'),
    (2, 'GET', '/api/v1/base/usermenu', '查看用户菜单', '基础模块'),
    (3, 'GET', '/api/v1/base/userapi', '查看用户API', '基础模块'),
    (4, 'POST', '/api/v1/base/update_password', '修改密码', '基础模块'),
    (5, 'GET', '/api/v1/user/list', '查看用户列表', '用户模块'),
    (6, 'GET', '/api/v1/user/get', '查看用户', '用户模块'),
    (7, 'POST', '/api/v1/user/create', '创建用户', '用户模块'),
    (8, 'POST', '/api/v1/user/update', '更新用户', '用户模块'),
    (9, 'DELETE', '/api/v1/user/delete', '删除用户', '用户模块'),
    (10, 'POST', '/api/v1/user/reset_password', '重置密码', '用户模块'),
    (11, 'GET', '/api/v1/role/list', '查看角色列表', '角色模块'),
    (12, 'GET', '/api/v1/role/get', '查看角色', '角色模块'),
    (13, 'POST', '/api/v1/role/create', '创建角色', '角色模块'),
    (14, 'POST', '/api/v1/role/update', '更新角色', '角色模块'),
    (15, 'DELETE', '/api/v1/role/delete', '删除角色', '角色模块'),
    (16, 'GET', '/api/v1/role/authorized', '查看角色权限', '角色模块'),
    (17, 'POST', '/api/v1/role/authorized', '更新角色权限', '角色模块'),
    (18, 'GET', '/api/v1/menu/list', '查看菜单列表', '菜单模块'),
    (19, 'GET', '/api/v1/menu/get', '查看菜单', '菜单模块'),
    (20, 'POST', '/api/v1/menu/create', '创建菜单', '菜单模块'),
    (21, 'POST', '/api/v1/menu/update', '更新菜单', '菜单模块'),
    (22, 'DELETE', '/api/v1/menu/delete', '删除菜单', '菜单模块'),
    (23, 'GET', '/api/v1/api/list', '查看API列表', 'API模块'),
    (24, 'GET', '/api/v1/api/get', '查看Api', 'API模块'),
    (25, 'POST', '/api/v1/api/create', '创建Api', 'API模块'),
    (26, 'POST', '/api/v1/api/update', '更新Api', 'API模块'),
    (27, 'DELETE', '/api/v1/api/delete', '删除Api', 'API模块'),
    (28, 'POST', '/api/v1/api/refresh', '刷新API列表', 'API模块'),
    (29, 'GET', '/api/v1/dept/list', '查看部门列表', '部门模块'),
    (30, 'GET', '/api/v1/dept/get', '查看部门', '部门模块'),
    (31, 'POST', '/api/v1/dept/create', '创建部门', '部门模块'),
    (32, 'POST', '/api/v1/dept/update', '更新部门', '部门模块'),
    (33, 'DELETE', '/api/v1/dept/delete', '删除部门', '部门模块'),
    (34, 'GET', '/api/v1/auditlog/list', '查看操作日志', '审计日志模块'),
    (35, 'GET', '/api/v1/dashboard/health', '查询外部服务健康状态', 'WiFi运维'),
    (36, 'GET', '/api/v1/dashboard/statistics', '查询 WiFi 每日认证统计', 'WiFi运维'),
    (37, 'GET', '/api/v1/dashboard/online-users', '查询 NCE 实时在线用户', 'WiFi运维'),
    (38, 'POST', '/api/v1/dashboard/radius-logs', '查询 NCE RADIUS 准入日志', 'WiFi运维'),
    (39, 'GET', '/api/v1/runtime-config/summary', '查询脱敏运行配置摘要', 'WiFi运维');

INSERT INTO `menu`
    (`id`, `name`, `menu_type`, `icon`, `path`, `order`, `parent_id`, `is_hidden`, `component`, `keepalive`, `redirect`)
VALUES
    (1, '系统管理', 'catalog', 'carbon:gui-management', '/system', 1, 0, 0, 'Layout', 0, '/system/user'),
    (2, '用户管理', 'menu', 'material-symbols:person-outline-rounded', 'user', 1, 1, 0, '/system/user', 0, NULL),
    (3, '角色管理', 'menu', 'carbon:user-role', 'role', 2, 1, 0, '/system/role', 0, NULL),
    (4, '菜单管理', 'menu', 'material-symbols:list-alt-outline', 'menu', 3, 1, 0, '/system/menu', 0, NULL),
    (5, 'API管理', 'menu', 'ant-design:api-outlined', 'api', 4, 1, 0, '/system/api', 0, NULL),
    (6, '部门管理', 'menu', 'mingcute:department-line', 'dept', 5, 1, 0, '/system/dept', 0, NULL),
    (7, '审计日志', 'menu', 'ph:clipboard-text-bold', 'auditlog', 6, 1, 0, '/system/auditlog', 0, NULL),
    (8, '一级菜单', 'menu', 'material-symbols:featured-play-list-outline', '/top-menu', 2, 0, 0, '/top-menu', 0, ''),
    (9, 'WiFi运营', 'catalog', 'ph:wifi-high-bold', '/wifi-operations', 10, 0, 0, 'Layout', 0, '/wifi/statistics'),
    (10, '认证统计', 'menu', 'ph:chart-line-up-bold', '/wifi/statistics', 1, 9, 0, '/wifi/statistics', 0, ''),
    (11, '在线用户', 'menu', 'ph:devices-bold', '/wifi/online-users', 2, 9, 0, '/wifi/online-users', 0, ''),
    (12, 'WiFi日志', 'catalog', 'ph:list-magnifying-glass-bold', '/wifi-logs', 11, 0, 0, 'Layout', 0, '/wifi/radius-logs'),
    (13, '准入日志', 'menu', 'ph:clipboard-text-bold', '/wifi/radius-logs', 1, 12, 0, '/wifi/radius-logs', 0, ''),
    (14, 'WiFi运维', 'catalog', 'ph:activity-bold', '/wifi-maintenance', 12, 0, 0, 'Layout', 0, '/wifi/health'),
    (15, '外部服务状态', 'menu', 'ph:heartbeat-bold', '/wifi/health', 1, 14, 0, '/wifi/health', 0, ''),
    (16, '运行配置摘要', 'menu', 'ph:sliders-horizontal-bold', '/wifi/runtime-config', 2, 14, 0, '/wifi/runtime-config', 0, '');

INSERT INTO `role` (`id`, `name`, `desc`) VALUES
    (1, '管理员', '管理员角色'),
    (2, '普通用户', '普通用户角色');

INSERT INTO `user`
    (`id`, `username`, `alias`, `email`, `password`, `is_active`, `is_superuser`)
VALUES
    (1, 'admin', '管理员', 'admin@example.invalid',
     '$argon2id$v=19$m=65536,t=3,p=4$r9Uaw9i715oz5pwTQmjtnQ$20WPhPX1GTDk6jqpZ5vQFnKjDjlosB7F+ht5qDeZb+U',
     1, 1);

INSERT INTO `role_menu` (`role_id`, `menu_id`)
SELECT 1, `id` FROM `menu`;

INSERT INTO `role_api` (`role_id`, `api_id`)
SELECT 1, `id` FROM `api`;

INSERT INTO `role_api` (`role_id`, `api_id`)
SELECT 2, `id` FROM `api` WHERE `tags` = '基础模块';

COMMIT;
