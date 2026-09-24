import os
import re
import sqlite3
from datetime import datetime, date
from dotenv import load_dotenv

load_dotenv()

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DB_PATH = os.path.join(BASE_DIR, "database", "library.db")

SQLITE_SCHEMA = """
CREATE TABLE IF NOT EXISTS user_category (
    category_id   INTEGER PRIMARY KEY AUTOINCREMENT,
    category_name TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS book_category (
    category_id   INTEGER PRIMARY KEY AUTOINCREMENT,
    category_name TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS admin (
    admin_id  INTEGER PRIMARY KEY AUTOINCREMENT,
    username  TEXT NOT NULL UNIQUE,
    password  TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS user (
    user_id     INTEGER PRIMARY KEY AUTOINCREMENT,
    name        TEXT NOT NULL,
    email       TEXT,
    phone       TEXT,
    category_id INTEGER,
    FOREIGN KEY (category_id) REFERENCES user_category(category_id)
);

CREATE TABLE IF NOT EXISTS login_user (
    login_id  INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id   INTEGER NOT NULL,
    username  TEXT NOT NULL UNIQUE,
    password  TEXT NOT NULL,
    role      TEXT DEFAULT 'user',
    FOREIGN KEY (user_id) REFERENCES user(user_id)
);

CREATE TABLE IF NOT EXISTS book (
    book_id             INTEGER PRIMARY KEY AUTOINCREMENT,
    title               TEXT NOT NULL,
    author              TEXT,
    isbn                TEXT,
    category_id         INTEGER,
    availability_status TEXT DEFAULT 'Available',
    FOREIGN KEY (category_id) REFERENCES book_category(category_id)
);

CREATE TABLE IF NOT EXISTS policy (
    policy_id        INTEGER PRIMARY KEY AUTOINCREMENT,
    user_category_id INTEGER NOT NULL,
    book_category_id INTEGER NOT NULL,
    borrow_days      INTEGER NOT NULL DEFAULT 14,
    fine_per_day     REAL NOT NULL DEFAULT 2.00,
    FOREIGN KEY (user_category_id) REFERENCES user_category(category_id),
    FOREIGN KEY (book_category_id) REFERENCES book_category(category_id)
);

CREATE TABLE IF NOT EXISTS request (
    request_id   INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id      INTEGER NOT NULL,
    book_id      INTEGER NOT NULL,
    request_date TEXT NOT NULL,
    status       TEXT DEFAULT 'Pending',
    FOREIGN KEY (user_id) REFERENCES user(user_id),
    FOREIGN KEY (book_id) REFERENCES book(book_id)
);

CREATE TABLE IF NOT EXISTS "transaction" (
    transaction_id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id        INTEGER NOT NULL,
    book_id        INTEGER NOT NULL,
    issue_date     TEXT,
    due_date       TEXT,
    return_date    TEXT,
    status         TEXT DEFAULT 'Issued',
    FOREIGN KEY (user_id) REFERENCES user(user_id),
    FOREIGN KEY (book_id) REFERENCES book(book_id)
);

CREATE TABLE IF NOT EXISTS fine (
    fine_id        INTEGER PRIMARY KEY AUTOINCREMENT,
    transaction_id INTEGER NOT NULL,
    amount         REAL,
    paid_status    TEXT DEFAULT 'Unpaid',
    FOREIGN KEY (transaction_id) REFERENCES "transaction"(transaction_id)
);

CREATE TABLE IF NOT EXISTS notification (
    notification_id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id         INTEGER NOT NULL,
    message         TEXT NOT NULL,
    type            TEXT,
    sent_date       DATETIME DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (user_id) REFERENCES user(user_id)
);
"""

SQLITE_SEEDS = [
    "INSERT OR IGNORE INTO user_category (category_id, category_name) VALUES (1, 'Student'), (2, 'Faculty');",
    "INSERT OR IGNORE INTO book_category (category_id, category_name) VALUES (1, 'Regular'), (2, 'Reference');",
    "INSERT OR IGNORE INTO admin (admin_id, username, password) VALUES (1, 'admin', 'admin123');",
    "INSERT OR IGNORE INTO policy (policy_id, user_category_id, book_category_id, borrow_days, fine_per_day) VALUES (1, 1, 1, 14, 2.00), (2, 1, 2, 7, 3.00), (3, 2, 1, 30, 1.00), (4, 2, 2, 14, 2.00);",
    "INSERT OR IGNORE INTO book (book_id, title, author, isbn, category_id, availability_status) VALUES (1, 'Introduction to Algorithms', 'Cormen', '978-0262033848', 1, 'Available'), (2, 'Database System Concepts', 'Silberschatz', '978-0078022159', 1, 'Available'), (3, 'Computer Networks', 'Tanenbaum', '978-0132126953', 2, 'Available'), (4, 'Operating Systems', 'Galvin', '978-1118063330', 1, 'Available'), (5, 'Python Programming', 'Mark Lutz', '978-1449355739', 2, 'Available');"
]


def _init_sqlite_db():
    os.makedirs(os.path.dirname(DB_PATH), exist_ok=True)
    conn = sqlite3.connect(DB_PATH, timeout=30.0)
    conn.executescript(SQLITE_SCHEMA)
    for s in SQLITE_SEEDS:
        conn.execute(s)
    conn.commit()
    conn.close()


def adapt_sql(sql):
    # Quote the reserved keyword 'transaction' when used as a table name
    sql = re.sub(r'\btransaction\b', '"transaction"', sql, flags=re.IGNORECASE)
    # Replace MySQL parameter placeholder %s with SQLite placeholder ?
    sql = sql.replace('%s', '?')
    return sql


class SQLiteCursorWrapper:
    def __init__(self, cursor, dictionary=False):
        self._cursor = cursor
        self._dictionary = dictionary

    def execute(self, sql, params=None):
        sql = adapt_sql(sql)
        if params is not None:
            return self._cursor.execute(sql, params)
        return self._cursor.execute(sql)

    def executemany(self, sql, seq_of_params):
        sql = adapt_sql(sql)
        return self._cursor.executemany(sql, seq_of_params)

    def fetchone(self):
        row = self._cursor.fetchone()
        if row is None:
            return None
        if self._dictionary:
            cols = [col[0] for col in self._cursor.description]
            return dict(zip(cols, row))
        return row

    def fetchall(self):
        rows = self._cursor.fetchall()
        if not rows:
            return []
        if self._dictionary:
            cols = [col[0] for col in self._cursor.description]
            return [dict(zip(cols, r)) for r in rows]
        return rows

    def fetchmany(self, size=None):
        rows = self._cursor.fetchmany(size) if size is not None else self._cursor.fetchmany()
        if not rows:
            return []
        if self._dictionary:
            cols = [col[0] for col in self._cursor.description]
            return [dict(zip(cols, r)) for r in rows]
        return rows

    @property
    def lastrowid(self):
        return self._cursor.lastrowid

    @property
    def rowcount(self):
        return self._cursor.rowcount

    def close(self):
        try:
            self._cursor.close()
        except Exception:
            pass


class SQLiteConnectionWrapper:
    def __init__(self, conn):
        self._conn = conn

    def cursor(self, dictionary=False):
        return SQLiteCursorWrapper(self._conn.cursor(), dictionary=dictionary)

    def commit(self):
        self._conn.commit()

    def rollback(self):
        self._conn.rollback()

    def close(self):
        try:
            self._conn.close()
        except Exception:
            pass


def _get_sqlite_connection():
    if not os.path.exists(DB_PATH):
        _init_sqlite_db()

    conn = sqlite3.connect(DB_PATH, check_same_thread=False, timeout=30.0)
    # Register MySQL compatible functions
    conn.create_function("CURDATE", 0, lambda: date.today().isoformat())
    conn.create_function("NOW", 0, lambda: datetime.now().strftime("%Y-%m-%d %H:%M:%S"))

    def _datediff(d1, d2):
        if not d1 or not d2:
            return 0
        try:
            t1 = datetime.strptime(str(d1)[:10], "%Y-%m-%d")
            t2 = datetime.strptime(str(d2)[:10], "%Y-%m-%d")
            return (t1 - t2).days
        except Exception:
            return 0

    conn.create_function("DATEDIFF", 2, _datediff)
    return SQLiteConnectionWrapper(conn)


def get_connection():
    """Return a database connection (SQLite by default or MySQL if configured and available)."""
    engine = os.getenv("DB_ENGINE", "sqlite").lower()

    if engine == "mysql":
        try:
            import mysql.connector
            return mysql.connector.connect(
                host=os.getenv("DB_HOST", "localhost"),
                user=os.getenv("DB_USER", "root"),
                password=os.getenv("DB_PASSWORD", ""),
                database=os.getenv("DB_NAME", "library_db"),
            )
        except Exception as e:
            print(f"[Database Warning] Failed to connect to MySQL ({e}). Falling back to SQLite.")

    return _get_sqlite_connection()
