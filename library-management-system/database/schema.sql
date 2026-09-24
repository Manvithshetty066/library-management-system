-- ============================================================
-- POLICY DRIVEN LIBRARY MANAGEMENT SYSTEM
-- Database Schema
-- ============================================================

CREATE DATABASE IF NOT EXISTS library_db;
USE library_db;

-- ============================================================
-- USER CATEGORY TABLE
-- ============================================================
CREATE TABLE IF NOT EXISTS user_category (
    category_id   INT AUTO_INCREMENT PRIMARY KEY,
    category_name VARCHAR(100) NOT NULL
);

-- ============================================================
-- BOOK CATEGORY TABLE
-- ============================================================
CREATE TABLE IF NOT EXISTS book_category (
    category_id   INT AUTO_INCREMENT PRIMARY KEY,
    category_name VARCHAR(100) NOT NULL
);

-- ============================================================
-- ADMIN TABLE
-- ============================================================
CREATE TABLE IF NOT EXISTS admin (
    admin_id  INT AUTO_INCREMENT PRIMARY KEY,
    username  VARCHAR(100) NOT NULL UNIQUE,
    password  VARCHAR(255) NOT NULL
);

-- ============================================================
-- USER TABLE
-- ============================================================
CREATE TABLE IF NOT EXISTS user (
    user_id     INT AUTO_INCREMENT PRIMARY KEY,
    name        VARCHAR(150) NOT NULL,
    email       VARCHAR(150),
    phone       VARCHAR(20),
    category_id INT,
    FOREIGN KEY (category_id) REFERENCES user_category(category_id)
);

-- ============================================================
-- LOGIN_USER TABLE
-- ============================================================
CREATE TABLE IF NOT EXISTS login_user (
    login_id  INT AUTO_INCREMENT PRIMARY KEY,
    user_id   INT NOT NULL,
    username  VARCHAR(100) NOT NULL UNIQUE,
    password  VARCHAR(255) NOT NULL,
    role      VARCHAR(20) DEFAULT 'user',
    FOREIGN KEY (user_id) REFERENCES user(user_id)
);

-- ============================================================
-- BOOK TABLE
-- ============================================================
CREATE TABLE IF NOT EXISTS book (
    book_id             INT AUTO_INCREMENT PRIMARY KEY,
    title               VARCHAR(255) NOT NULL,
    author              VARCHAR(150),
    isbn                VARCHAR(50),
    category_id         INT,
    availability_status VARCHAR(20) DEFAULT 'Available',
    FOREIGN KEY (category_id) REFERENCES book_category(category_id)
);

-- ============================================================
-- POLICY TABLE
-- ============================================================
CREATE TABLE IF NOT EXISTS policy (
    policy_id        INT AUTO_INCREMENT PRIMARY KEY,
    user_category_id INT NOT NULL,
    book_category_id INT NOT NULL,
    borrow_days      INT NOT NULL DEFAULT 14,
    fine_per_day     DECIMAL(10,2) NOT NULL DEFAULT 2.00,
    FOREIGN KEY (user_category_id) REFERENCES user_category(category_id),
    FOREIGN KEY (book_category_id) REFERENCES book_category(category_id)
);

-- ============================================================
-- REQUEST TABLE
-- ============================================================
CREATE TABLE IF NOT EXISTS request (
    request_id   INT AUTO_INCREMENT PRIMARY KEY,
    user_id      INT NOT NULL,
    book_id      INT NOT NULL,
    request_date DATE NOT NULL,
    status       VARCHAR(20) DEFAULT 'Pending',
    FOREIGN KEY (user_id) REFERENCES user(user_id),
    FOREIGN KEY (book_id) REFERENCES book(book_id)
);

-- ============================================================
-- TRANSACTION TABLE
-- ============================================================
CREATE TABLE IF NOT EXISTS transaction (
    transaction_id INT AUTO_INCREMENT PRIMARY KEY,
    user_id        INT NOT NULL,
    book_id        INT NOT NULL,
    issue_date     DATE,
    due_date       DATE,
    return_date    DATE,
    status         VARCHAR(20) DEFAULT 'Issued',
    FOREIGN KEY (user_id) REFERENCES user(user_id),
    FOREIGN KEY (book_id) REFERENCES book(book_id)
);

-- ============================================================
-- FINE TABLE
-- ============================================================
CREATE TABLE IF NOT EXISTS fine (
    fine_id        INT AUTO_INCREMENT PRIMARY KEY,
    transaction_id INT NOT NULL,
    amount         DECIMAL(10,2),
    paid_status    VARCHAR(20) DEFAULT 'Unpaid',
    FOREIGN KEY (transaction_id) REFERENCES transaction(transaction_id)
);

-- ============================================================
-- NOTIFICATION TABLE
-- ============================================================
CREATE TABLE IF NOT EXISTS notification (
    notification_id INT AUTO_INCREMENT PRIMARY KEY,
    user_id         INT NOT NULL,
    message         TEXT NOT NULL,
    type            VARCHAR(50),
    sent_date       DATETIME DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (user_id) REFERENCES user(user_id)
);

-- ============================================================
-- SEED DATA
-- ============================================================
INSERT IGNORE INTO user_category (category_id, category_name) VALUES
(1, 'Student'),
(2, 'Faculty');

INSERT IGNORE INTO book_category (category_id, category_name) VALUES
(1, 'Regular'),
(2, 'Reference');

INSERT IGNORE INTO admin (username, password) VALUES
('admin', 'admin123');

INSERT IGNORE INTO policy (user_category_id, book_category_id, borrow_days, fine_per_day) VALUES
(1, 1, 14, 2.00),
(1, 2, 7,  3.00),
(2, 1, 30, 1.00),
(2, 2, 14, 2.00);

INSERT IGNORE INTO book (title, author, isbn, category_id, availability_status) VALUES
('Introduction to Algorithms', 'Cormen', '978-0262033848', 1, 'Available'),
('Database System Concepts', 'Silberschatz', '978-0078022159', 1, 'Available'),
('Computer Networks', 'Tanenbaum', '978-0132126953', 2, 'Available'),
('Operating Systems', 'Galvin', '978-1118063330', 1, 'Available'),
('Python Programming', 'Mark Lutz', '978-1449355739', 2, 'Available');
