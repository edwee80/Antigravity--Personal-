import sqlite3

conn = sqlite3.connect('books.db')
c = conn.cursor()
c.execute("DELETE FROM books WHERE title = 'Atomic Habits'")
c.execute("DELETE FROM users WHERE username = 'sarah'")
conn.commit()

c.execute("SELECT id, username, display_name FROM users")
print("Active users:", c.fetchall())
c.execute("SELECT id, title, user_id FROM books")
print("Active books:", len(c.fetchall()))
conn.close()
