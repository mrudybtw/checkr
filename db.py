import sqlite3
from contextlib import contextmanager

DATABASE = 'monitoring.db'  # Имя файла базы данных


@contextmanager
def get_db():
    """Контекстный менеджер для работы с базой данных."""
    conn = sqlite3.connect(DATABASE)
    conn.row_factory = sqlite3.Row  # Чтобы получать результаты в виде словарей
    try:
        yield conn.cursor()
        conn.commit()
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()


def init_db():
    """Создает таблицы в базе данных."""
    with get_db() as cursor:
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS users (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                username TEXT UNIQUE NOT NULL,
                password TEXT NOT NULL,  -- Будем хранить хеш пароля
                email TEXT UNIQUE NOT NULL
            )
        """)

        cursor.execute("""
            CREATE TABLE IF NOT EXISTS websites (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER NOT NULL,
                url TEXT NOT NULL,
                created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (user_id) REFERENCES users (id)
            )
        """)

        cursor.execute("""
            CREATE TABLE IF NOT EXISTS checks (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                website_id INTEGER NOT NULL,
                status TEXT NOT NULL,
                response_time REAL,
                status_code INTEGER,
                error TEXT,
                checked_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (website_id) REFERENCES websites (id)
            )
        """)

def add_user(username, password, email):
    with get_db() as db:
        db.execute("INSERT INTO users (username, password, email) VALUES (?, ?, ?)", (username, password, email))
        #получаем ID
        last_row_id = db.lastrowid
        return last_row_id

def get_user_by_username(username):
    with get_db() as db:
        result = db.execute("SELECT * FROM users where username = ?", (username,)).fetchone()
        return result
    
def get_user_by_id(id):
      with get_db() as db:
        result = db.execute("SELECT * FROM users where id = ?", (id,)).fetchone()
        return result

def add_website(user_id, url):
    with get_db() as db:
        db.execute("INSERT INTO websites (user_id, url) VALUES (?, ?)", (user_id, url))
        #получаем ID
        last_row_id = db.lastrowid
        return last_row_id

def get_websites_by_user_id(user_id):
    with get_db() as db:
        return db.execute("SELECT * FROM websites WHERE user_id = ?", (user_id,)).fetchall()
    
def get_website_by_id(website_id):
     with get_db() as db:
        result = db.execute("SELECT * FROM websites where id = ?", (website_id,)).fetchone()
        return result

def add_check_result(website_id, status, response_time, status_code, error=None):
    with get_db() as db:
        db.execute("""
            INSERT INTO checks (website_id, status, response_time, status_code, error)
            VALUES (?, ?, ?, ?, ?)
        """, (website_id, status, response_time, status_code, error))
        last_row_id = db.lastrowid
        return last_row_id

def get_checks_by_website_id(website_id):
     with get_db() as db:
        return db.execute("SELECT * FROM checks WHERE website_id = ? ORDER BY checked_at DESC", (website_id,)).fetchall()