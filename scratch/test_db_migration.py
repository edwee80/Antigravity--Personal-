import sqlite3
import hashlib
import os
import hmac

def hash_pw(password: str) -> str:
    salt = os.urandom(16).hex()
    dk = hashlib.pbkdf2_hmac('sha256', password.encode('utf-8'), salt.encode('utf-8'), 100000)
    return f"{salt}:{dk.hex()}"

def migrate(db_name="books.db"):
    conn = sqlite3.connect(db_name)
    cursor = conn.cursor()

    # 1. Create users table
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            username TEXT UNIQUE NOT NULL COLLATE NOCASE,
            password_hash TEXT NOT NULL,
            display_name TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    ''')

    # 2. Check books table for user_id
    cursor.execute("PRAGMA table_info(books)")
    columns = [col[1] for col in cursor.fetchall()]
    if 'user_id' not in columns:
        print("Adding user_id column to books table...")
        cursor.execute("ALTER TABLE books ADD COLUMN user_id INTEGER")

    # 3. Create default user 'edrey' if not exists
    cursor.execute("SELECT id, username, display_name FROM users WHERE username = 'edrey'")
    edrey_user = cursor.fetchone()
    if not edrey_user:
        print("Creating default user 'edrey'...")
        pw_hash = hash_pw("edrey123")
        cursor.execute(
            "INSERT INTO users (username, password_hash, display_name) VALUES (?, ?, ?)",
            ("edrey", pw_hash, "Edrey")
        )
        edrey_id = cursor.lastrowid
    else:
        edrey_id = edrey_user[0]

    # 4. Migrate orphan books to edrey
    cursor.execute("UPDATE books SET user_id = ? WHERE user_id IS NULL", (edrey_id,))
    migrated_count = cursor.rowcount
    print(f"Assigned {migrated_count} orphan books to user 'edrey' (ID {edrey_id})")

    conn.commit()

    # Check books and users
    cursor.execute("SELECT id, username, display_name FROM users")
    users = cursor.fetchall()
    print("Users in DB:", users)

    cursor.execute("SELECT id, title, user_id FROM books")
    books = cursor.fetchall()
    print(f"Books in DB ({len(books)}):", books)

    conn.close()

if __name__ == '__main__':
    migrate()
