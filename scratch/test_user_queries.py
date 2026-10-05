import sqlite3
import pandas as pd

conn = sqlite3.connect('books.db')

# Verify edrey books
edrey_df = pd.read_sql_query("SELECT id, title, user_id FROM books WHERE user_id = 1", conn)
print("Edrey books count:", len(edrey_df))

# Test query for user 2 (should be 0)
u2_df = pd.read_sql_query("SELECT id, title, user_id FROM books WHERE user_id = 2", conn)
print("User 2 books count:", len(u2_df))

conn.close()
