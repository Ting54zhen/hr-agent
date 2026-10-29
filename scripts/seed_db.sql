USE hr;

CREATE TABLE IF NOT EXISTS employees (
  id INT PRIMARY KEY,
  name VARCHAR(50) NOT NULL,
  department VARCHAR(50) NOT NULL,
  manager_id INT,
  email VARCHAR(100),
  CONSTRAINT fk_employee_manager FOREIGN KEY (manager_id) REFERENCES employees(id)
);

CREATE TABLE IF NOT EXISTS users (
  employee_id INT PRIMARY KEY,
  password_hash VARCHAR(255) NOT NULL,
  is_active TINYINT(1) NOT NULL DEFAULT 1,
  created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
  last_login_at TIMESTAMP NULL DEFAULT NULL,
  CONSTRAINT fk_users_employee FOREIGN KEY (employee_id) REFERENCES employees(id)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

CREATE TABLE IF NOT EXISTS leave_balances (
  employee_id INT PRIMARY KEY,
  annual_total INT NOT NULL,
  annual_used INT NOT NULL DEFAULT 0,
  sick_total INT NOT NULL,
  sick_used INT NOT NULL DEFAULT 0,
  CONSTRAINT fk_leave_employee FOREIGN KEY (employee_id) REFERENCES employees(id),
  CONSTRAINT chk_leave_nonnegative CHECK (
    annual_total >= 0 AND annual_used >= 0 AND
    sick_total >= 0 AND sick_used >= 0
  )
);

CREATE TABLE IF NOT EXISTS attendance (
  id INT AUTO_INCREMENT PRIMARY KEY,
  employee_id INT NOT NULL,
  work_date DATE NOT NULL,
  status ENUM('normal','late','early_leave','absent','leave') NOT NULL,
  check_in TIME,
  check_out TIME,
  CONSTRAINT fk_attendance_employee FOREIGN KEY (employee_id) REFERENCES employees(id),
  UNIQUE KEY uk_employee_date (employee_id, work_date)
);

INSERT INTO employees (id, name, department, manager_id, email) VALUES
  (1001, '张三', '研发部', NULL, 'zhangsan@example.com'),
  (1002, '李四', '产品部', 1001, 'lisi@example.com'),
  (1003, '王五', 'HR 部', NULL, 'wangwu@example.com')
ON DUPLICATE KEY UPDATE
  name = VALUES(name), department = VALUES(department),
  manager_id = VALUES(manager_id), email = VALUES(email);

-- 演示账号初始密码均为 123456（PBKDF2-SHA256）。
-- 已有密码被修改后，重新执行本文件不会覆盖（INSERT IGNORE）。
INSERT IGNORE INTO users (employee_id, password_hash, is_active) VALUES
  (1001, 'pbkdf2_sha256$600000$I7wyVrmsCcuqwWdJAYkarA$9CPKHFPnx4zrr-SCwEhFxDDUZhy9A2SFpAiC2gVEagc', 1),
  (1002, 'pbkdf2_sha256$600000$BDXASmyXhVL8Ww5wQgA8Zg$2nx5f9TQuOLnNZxzloc3Y1DGxSC8tXmVecypNBM0CME', 1),
  (1003, 'pbkdf2_sha256$600000$AgzL0AI5qz5mMmDXJqzvMg$ao9aXCG-Voh1kX9Op9tIlpBUgCbJD-cj1ZGlRTf4IrE', 1);

INSERT INTO leave_balances (employee_id, annual_total, annual_used, sick_total, sick_used) VALUES
  (1001, 10, 3, 5, 4),
  (1002, 8, 8, 5, 0),
  (1003, 12, 1, 5, 1)
ON DUPLICATE KEY UPDATE
  annual_total = VALUES(annual_total), annual_used = VALUES(annual_used),
  sick_total = VALUES(sick_total), sick_used = VALUES(sick_used);

INSERT INTO attendance (employee_id, work_date, status, check_in, check_out) VALUES
  (1001, '2026-10-08', 'normal', '09:00:00', '18:00:00'),
  (1001, '2026-10-09', 'late', '09:35:00', '18:10:00'),
  (1001, '2026-10-10', 'normal', '08:55:00', '18:05:00'),
  (1002, '2026-10-08', 'normal', '09:00:00', '18:00:00'),
  (1002, '2026-10-09', 'leave', NULL, NULL),
  (1003, '2026-10-08', 'normal', '08:50:00', '17:55:00')
ON DUPLICATE KEY UPDATE
  status = VALUES(status), check_in = VALUES(check_in), check_out = VALUES(check_out);

CREATE TABLE IF NOT EXISTS leave_requests (
  id INT AUTO_INCREMENT PRIMARY KEY,
  employee_id INT NOT NULL,
  leave_type VARCHAR(20) NOT NULL,
  start_date DATE NOT NULL,
  end_date DATE NOT NULL,
  status ENUM('pending','approved','rejected') NOT NULL DEFAULT 'pending'
);

INSERT INTO leave_requests (employee_id, leave_type, start_date, end_date, status) VALUES
  (1001, 'annual', '2026-11-02', '2026-11-03', 'pending'),
  (1001, 'sick',   '2026-09-15', '2026-09-16', 'approved')
ON DUPLICATE KEY UPDATE status = VALUES(status);
