import streamlit as st
import sqlite3
import pandas as pd
import urllib.request
import urllib.parse
import json
import os
import uuid
import base64
import hashlib
import hmac

# Local storage directory for user-uploaded book covers
COVERS_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "covers")
os.makedirs(COVERS_DIR, exist_ok=True)

@st.cache_data
def get_library_bg_base64(mtime: float = 0.0) -> str:
    """Read the bookshelf background image and return base64 string."""
    bg_path = os.path.join(COVERS_DIR, "library_bookshelf_bg.jpg")
    if os.path.exists(bg_path):
        try:
            with open(bg_path, "rb") as f:
                return base64.b64encode(f.read()).decode("utf-8")
        except Exception as e:
            print("Error loading background image:", e)
    return ""

def save_uploaded_cover(uploaded_file) -> str | None:
    """Save an uploaded image file locally and return its relative path."""
    if uploaded_file is None:
        return None
    try:
        ext = os.path.splitext(uploaded_file.name)[1].lower()
        if not ext or ext not in [".jpg", ".jpeg", ".png", ".webp"]:
            ext = ".jpg"
        filename = f"cover_{uuid.uuid4().hex[:10]}{ext}"
        filepath = os.path.join(COVERS_DIR, filename)
        with open(filepath, "wb") as f:
            f.write(uploaded_file.getbuffer())
        return os.path.relpath(filepath, os.path.dirname(os.path.abspath(__file__)))
    except Exception as e:
        print("Error saving cover:", e)
        return None

POPULAR_GENRES = [
    "Fiction",
    "Non-Fiction",
    "Romance",
    "Islamic Studies",
    "Mystery & Thriller",
    "Sci-Fi & Fantasy",
    "Self-Help & Growth",
    "Biography & Memoir",
    "History & Politics",
    "Young Adult",
    "Classics",
    "Horror",
    "Poetry & Essays",
    "Custom..."
]

def infer_genre(subjects: list) -> str | None:
    """Infer common genre/theme category from Open Library subjects."""
    if not subjects:
        return None
    text = " ".join([str(s) for s in subjects]).lower()
    if any(k in text for k in ["romance", "love story", "contemporary romance", "erotic", "billionaire", "gods_of_the_game"]):
        return "Romance"
    if any(k in text for k in ["science fiction", "sci-fi", "space", "fantasy", "magic"]):
        return "Sci-Fi & Fantasy"
    if any(k in text for k in ["mystery", "thriller", "suspense", "detective", "crime", "murder"]):
        return "Mystery & Thriller"
    if any(k in text for k in ["habit", "self-actualization", "self-help", "productivity", "psychology", "personal development"]):
        return "Self-Help & Growth"
    if any(k in text for k in ["biography", "autobiography", "memoir"]):
        return "Biography & Memoir"
    if any(k in text for k in ["history", "historical", "war", "civilization"]):
        return "History & Politics"
    if any(k in text for k in ["horror", "supernatural", "ghost"]):
        return "Horror"
    if any(k in text for k in ["non-fiction", "nonfiction", "business", "economics", "science"]):
        return "Non-Fiction"
    if any(k in text for k in ["fiction", "literature", "novel"]):
        return "Fiction"
    return None

@st.cache_data(show_spinner=False, ttl=3600)
def fetch_book_details(title: str, author: str) -> dict:
    """Fetch book cover image URL, median page count, and suggested genre from Open Library."""
    title_clean = (title or "").strip()
    author_clean = (author or "").strip()
    if not title_clean:
        return {"cover_url": None, "total_pages": 0, "suggested_genre": None}
    
    query = f"{title_clean} {author_clean}".strip()
    url = (
        f"https://openlibrary.org/search.json?"
        f"q={urllib.parse.quote(query)}&fields=title,author_name,cover_i,isbn,number_of_pages_median,subject&limit=5"
    )
    req = urllib.request.Request(
        url, 
        headers={'User-Agent': 'PersonalLibraryApp/2.0 (contact: library@antigravity.local)'}
    )
    
    cover_url = None
    total_pages = 0
    suggested_genre = None
    
    try:
        with urllib.request.urlopen(req, timeout=5) as response:
            data = json.loads(response.read().decode('utf-8'))
            for doc in data.get('docs', []):
                if not cover_url:
                    if doc.get('cover_i'):
                        cover_url = f"https://covers.openlibrary.org/b/id/{doc['cover_i']}-L.jpg"
                    elif doc.get('isbn'):
                        cover_url = f"https://covers.openlibrary.org/b/isbn/{doc['isbn'][0]}-L.jpg"
                if not total_pages and doc.get('number_of_pages_median'):
                    try:
                        total_pages = int(doc.get('number_of_pages_median'))
                    except (ValueError, TypeError):
                        pass
                if not suggested_genre and doc.get('subject'):
                    suggested_genre = infer_genre(doc['subject'])
                if cover_url and total_pages and suggested_genre:
                    break
    except Exception:
        pass
        
    return {"cover_url": cover_url, "total_pages": total_pages, "suggested_genre": suggested_genre}

def hash_password(password: str) -> str:
    """Generate salted PBKDF2-SHA256 password hash."""
    salt = os.urandom(16).hex()
    dk = hashlib.pbkdf2_hmac('sha256', password.encode('utf-8'), salt.encode('utf-8'), 100000)
    return f"{salt}:{dk.hex()}"

def verify_password(password: str, stored_hash: str) -> bool:
    """Verify password against stored salt:hash string."""
    try:
        salt, dk_hex = stored_hash.split(':')
        dk = hashlib.pbkdf2_hmac('sha256', password.encode('utf-8'), salt.encode('utf-8'), 100000)
        return hmac.compare_digest(dk.hex(), dk_hex)
    except Exception:
        return False

def get_current_user() -> dict | None:
    """Retrieve currently authenticated user dict from session state."""
    return st.session_state.get("logged_in_user")

def get_current_user_id() -> int:
    """Retrieve current user ID, defaulting to 1 for backwards compatibility."""
    user = get_current_user()
    if user and isinstance(user, dict) and "id" in user:
        return user["id"]
    return 1

class BookDatabase:
    """Object-oriented wrapper for local SQLite database operations with user multi-tenancy."""
    def __init__(self, db_name="books.db"):
        self.db_name = db_name
        self._create_table()

    def _get_connection(self):
        return sqlite3.connect(self.db_name)

    def _create_table(self):
        with self._get_connection() as conn:
            # Users table
            conn.execute('''
                CREATE TABLE IF NOT EXISTS users (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    username TEXT UNIQUE NOT NULL COLLATE NOCASE,
                    password_hash TEXT NOT NULL,
                    display_name TEXT,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            ''')
            # Books table with user_id
            conn.execute('''
                CREATE TABLE IF NOT EXISTS books (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    user_id INTEGER,
                    title TEXT NOT NULL,
                    author TEXT NOT NULL,
                    status TEXT NOT NULL,
                    cover_url TEXT,
                    current_page INTEGER DEFAULT 0,
                    total_pages INTEGER DEFAULT 0,
                    genre TEXT DEFAULT 'Fiction'
                )
            ''')
            cursor = conn.cursor()
            cursor.execute("PRAGMA table_info(books)")
            columns = [col[1] for col in cursor.fetchall()]
            if 'user_id' not in columns:
                cursor.execute("ALTER TABLE books ADD COLUMN user_id INTEGER")
            if 'cover_url' not in columns:
                cursor.execute("ALTER TABLE books ADD COLUMN cover_url TEXT")
            if 'current_page' not in columns:
                cursor.execute("ALTER TABLE books ADD COLUMN current_page INTEGER DEFAULT 0")
            if 'total_pages' not in columns:
                cursor.execute("ALTER TABLE books ADD COLUMN total_pages INTEGER DEFAULT 0")
            if 'genre' not in columns:
                cursor.execute("ALTER TABLE books ADD COLUMN genre TEXT DEFAULT 'Fiction'")

            # Seed default edrey account if no users exist
            cursor.execute("SELECT COUNT(*) FROM users")
            if cursor.fetchone()[0] == 0:
                pw_hash = hash_password("edrey123")
                cursor.execute(
                    "INSERT INTO users (username, password_hash, display_name) VALUES (?, ?, ?)",
                    ("edrey", pw_hash, "Edrey")
                )
                edrey_id = cursor.lastrowid
                cursor.execute("UPDATE books SET user_id = ? WHERE user_id IS NULL", (edrey_id,))

    def register_user(self, username, password, display_name=None):
        """Register a new distinct user account."""
        username = (username or "").strip()
        if not username:
            return False, "Username cannot be empty."
        if not password or len(password) < 4:
            return False, "Password must be at least 4 characters long."
        if not display_name or not display_name.strip():
            display_name = username.capitalize()
        else:
            display_name = display_name.strip()
            
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT id FROM users WHERE username = ?", (username,))
            if cursor.fetchone():
                return False, f"Username '{username}' is already taken. Please choose another."
            
            pw_hash = hash_password(password)
            cursor.execute(
                "INSERT INTO users (username, password_hash, display_name) VALUES (?, ?, ?)",
                (username, pw_hash, display_name)
            )
            user_id = cursor.lastrowid
            return True, {"id": user_id, "username": username, "display_name": display_name}

    def authenticate_user(self, username, password):
        """Validate user credentials and return user dict."""
        username = (username or "").strip()
        if not username or not password:
            return False, "Please enter both username and password."
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT id, username, password_hash, display_name FROM users WHERE username = ?", (username,))
            row = cursor.fetchone()
            if not row:
                return False, "User not found. Please check your username or register."
            user_id, uname, stored_hash, dname = row
            if verify_password(password, stored_hash):
                return True, {"id": user_id, "username": uname, "display_name": dname or uname}
            else:
                return False, "Incorrect password. Please try again."

    def update_password(self, username, new_password):
        """Renew or reset password for a given username."""
        username = (username or "").strip()
        if not username:
            return False, "Please enter your username."
        if not new_password or len(new_password) < 4:
            return False, "New password must be at least 4 characters long."

        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT id, username, display_name FROM users WHERE username = ?", (username,))
            row = cursor.fetchone()
            if not row:
                return False, f"Account '{username}' was not found in the registry."
            
            new_hash = hash_password(new_password)
            cursor.execute("UPDATE users SET password_hash = ? WHERE id = ?", (new_hash, row[0]))
            conn.commit()
            return True, {"id": row[0], "username": row[1], "display_name": row[2] or row[1]}

    def change_password(self, user_id, current_password, new_password):
        """Change password for an authenticated user verifying their current password."""
        if not new_password or len(new_password) < 4:
            return False, "New password must be at least 4 characters long."

        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT password_hash FROM users WHERE id = ?", (user_id,))
            row = cursor.fetchone()
            if not row:
                return False, "User account not found."
            if not verify_password(current_password, row[0]):
                return False, "Current password is incorrect."

            new_hash = hash_password(new_password)
            cursor.execute("UPDATE users SET password_hash = ? WHERE id = ?", (new_hash, user_id))
            conn.commit()
            return True, "Password updated successfully!"

    def delete_user_account(self, user_id, password_confirm):
        """Permanently delete a user account and all their cataloged books."""
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT password_hash FROM users WHERE id = ?", (user_id,))
            row = cursor.fetchone()
            if not row:
                return False, "User account not found."
            if not verify_password(password_confirm, row[0]):
                return False, "Incorrect password. Cannot delete account."

            # Delete all books belonging to this user
            conn.execute("DELETE FROM books WHERE user_id = ?", (user_id,))
            # Delete user account
            conn.execute("DELETE FROM users WHERE id = ?", (user_id,))
            conn.commit()
            return True, "Account and all associated volumes permanently deleted."

    def add_book(self, title, author, status, cover_url=None, current_page=0, total_pages=0, genre="Fiction", user_id=None):
        if user_id is None:
            user_id = get_current_user_id()
        with self._get_connection() as conn:
            conn.execute(
                '''INSERT INTO books (title, author, status, cover_url, current_page, total_pages, genre, user_id) 
                   VALUES (?, ?, ?, ?, ?, ?, ?, ?)''', 
                (title, author, status, cover_url, current_page, total_pages, genre, user_id)
            )

    def get_books(self, status, genre_filter=None, sort_order="Title (A → Z)", user_id=None):
        if user_id is None:
            user_id = get_current_user_id()
        with self._get_connection() as conn:
            if sort_order == "Author (A → Z)":
                order_clause = "ORDER BY author COLLATE NOCASE ASC, title COLLATE NOCASE ASC"
            elif sort_order == "Title (Z → A)":
                order_clause = "ORDER BY title COLLATE NOCASE DESC"
            else:
                order_clause = "ORDER BY title COLLATE NOCASE ASC"

            if genre_filter and genre_filter != "All Themes":
                return pd.read_sql_query(
                    f"SELECT id, title, author, cover_url, current_page, total_pages, genre FROM books WHERE user_id=? AND status=? AND genre=? {order_clause}", 
                    conn, 
                    params=(user_id, status, genre_filter)
                )
            else:
                return pd.read_sql_query(
                    f"SELECT id, title, author, cover_url, current_page, total_pages, genre FROM books WHERE user_id=? AND status=? {order_clause}", 
                    conn, 
                    params=(user_id, status)
                )

    def get_all_genres(self, user_id=None):
        if user_id is None:
            user_id = get_current_user_id()
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT DISTINCT genre FROM books WHERE user_id=? AND genre IS NOT NULL AND genre != ''", (user_id,))
            genres = [row[0] for row in cursor.fetchall()]
            return genres if genres else ["Fiction"]

    def update_page(self, book_id, current_page, total_pages=None, user_id=None):
        if user_id is None:
            user_id = get_current_user_id()
        with self._get_connection() as conn:
            if total_pages is not None:
                conn.execute(
                    'UPDATE books SET current_page=?, total_pages=? WHERE id=? AND user_id=?', 
                    (current_page, total_pages, book_id, user_id)
                )
            else:
                conn.execute('UPDATE books SET current_page=? WHERE id=? AND user_id=?', (current_page, book_id, user_id))

    def update_total_pages(self, book_id, total_pages, user_id=None):
        if user_id is None:
            user_id = get_current_user_id()
        with self._get_connection() as conn:
            conn.execute('UPDATE books SET total_pages=? WHERE id=? AND user_id=?', (total_pages, book_id, user_id))

    def update_genre(self, book_id, new_genre, user_id=None):
        if user_id is None:
            user_id = get_current_user_id()
        with self._get_connection() as conn:
            conn.execute('UPDATE books SET genre=? WHERE id=? AND user_id=?', (new_genre, book_id, user_id))

    def update_cover(self, book_id, cover_url, user_id=None):
        if user_id is None:
            user_id = get_current_user_id()
        with self._get_connection() as conn:
            conn.execute('UPDATE books SET cover_url=? WHERE id=? AND user_id=?', (cover_url, book_id, user_id))

    def update_status(self, book_id, new_status, user_id=None):
        if user_id is None:
            user_id = get_current_user_id()
        with self._get_connection() as conn:
            conn.execute('UPDATE books SET status=? WHERE id=? AND user_id=?', (new_status, book_id, user_id))

    def delete_book(self, book_id, user_id=None):
        if user_id is None:
            user_id = get_current_user_id()
        with self._get_connection() as conn:
            conn.execute('DELETE FROM books WHERE id=? AND user_id=?', (book_id, user_id))

    def get_category_summary(self, user_id=None):
        """Retrieve aggregated volume statistics grouped by category/genre for a specific user."""
        if user_id is None:
            user_id = get_current_user_id()
        with self._get_connection() as conn:
            query = """
            SELECT 
                COALESCE(NULLIF(genre, ''), 'General') as category,
                COUNT(*) as total_books,
                SUM(CASE WHEN status = 'Want to Read' THEN 1 ELSE 0 END) as want_count,
                SUM(CASE WHEN status = 'Ongoing' THEN 1 ELSE 0 END) as ongoing_count,
                SUM(CASE WHEN status = 'Read' THEN 1 ELSE 0 END) as read_count,
                SUM(COALESCE(total_pages, 0)) as total_pages,
                SUM(COALESCE(current_page, 0)) as pages_read
            FROM books
            WHERE user_id = ?
            GROUP BY COALESCE(NULLIF(genre, ''), 'General')
            ORDER BY category COLLATE NOCASE ASC
            """
            return pd.read_sql_query(query, conn, params=(user_id,))

    def get_books_by_genre(self, genre, status_filter=None, sort_order="Title (A → Z)", user_id=None):
        """Retrieve all books belonging to a specific genre/theme folder for a specific user."""
        if user_id is None:
            user_id = get_current_user_id()
        with self._get_connection() as conn:
            if sort_order == "Author (A → Z)":
                order_clause = "ORDER BY author COLLATE NOCASE ASC, title COLLATE NOCASE ASC"
            elif sort_order == "Title (Z → A)":
                order_clause = "ORDER BY title COLLATE NOCASE DESC"
            elif sort_order == "Progress (%)":
                order_clause = "ORDER BY (CAST(current_page AS FLOAT) / NULLIF(total_pages, 0)) DESC, title COLLATE NOCASE ASC"
            elif sort_order == "Page Count":
                order_clause = "ORDER BY total_pages DESC, title COLLATE NOCASE ASC"
            else:
                order_clause = "ORDER BY title COLLATE NOCASE ASC"

            if status_filter and status_filter != "All Statuses":
                query = f"SELECT id, title, author, cover_url, current_page, total_pages, genre, status FROM books WHERE user_id=? AND COALESCE(NULLIF(genre, ''), 'General')=? AND status=? {order_clause}"
                return pd.read_sql_query(query, conn, params=(user_id, genre, status_filter))
            else:
                query = f"SELECT id, title, author, cover_url, current_page, total_pages, genre, status FROM books WHERE user_id=? AND COALESCE(NULLIF(genre, ''), 'General')=? {order_clause}"
                return pd.read_sql_query(query, conn, params=(user_id, genre))

    def get_library_overall_stats(self, user_id=None):
        """Retrieve total collection metrics across the user's private library."""
        if user_id is None:
            user_id = get_current_user_id()
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                SELECT 
                    COUNT(*) as total_books,
                    COUNT(DISTINCT COALESCE(NULLIF(genre, ''), 'General')) as total_genres,
                    SUM(CASE WHEN status = 'Want to Read' THEN 1 ELSE 0 END) as want_count,
                    SUM(CASE WHEN status = 'Ongoing' THEN 1 ELSE 0 END) as ongoing_count,
                    SUM(CASE WHEN status = 'Read' THEN 1 ELSE 0 END) as read_count,
                    SUM(COALESCE(total_pages, 0)) as total_pages,
                    SUM(COALESCE(current_page, 0)) as pages_read
                FROM books
                WHERE user_id = ?
            """, (user_id,))
            row = cursor.fetchone()
            if not row or row[0] is None:
                return {
                    "total_books": 0, "total_genres": 0, "want_count": 0,
                    "ongoing_count": 0, "read_count": 0, "total_pages": 0, "pages_read": 0
                }
            return {
                "total_books": row[0] or 0,
                "total_genres": row[1] or 0,
                "want_count": row[2] or 0,
                "ongoing_count": row[3] or 0,
                "read_count": row[4] or 0,
                "total_pages": row[5] or 0,
                "pages_read": row[6] or 0,
            }

# Initialize the database connection
db = BookDatabase()

st.set_page_config(page_title="Personal Library", page_icon="🏛️", layout="wide")

# ================= GRAND CLASSICAL WOODEN BOOKCASE THEME =================
bg_path = os.path.join(COVERS_DIR, "library_bookshelf_bg.jpg")
bg_mtime = os.path.getmtime(bg_path) if os.path.exists(bg_path) else 0.0
bg_b64 = get_library_bg_base64(bg_mtime)
if bg_b64:
    st.markdown(
        f"""
        <style>
        .stApp {{
            background-image: linear-gradient(rgba(14, 9, 6, 0.84), rgba(8, 5, 3, 0.89)), url("data:image/jpeg;base64,{bg_b64}") !important;
            background-size: cover !important;
            background-position: center center !important;
            background-attachment: fixed !important;
            background-repeat: no-repeat !important;
        }}
        </style>
        """,
        unsafe_allow_html=True
    )

st.markdown(
    """
    <style>
    @import url('https://fonts.googleapis.com/css2?family=Cinzel:wght@500;600;700;800&family=Playfair+Display:ital,wght@0,500;0,600;0,700;1,400&family=Plus+Jakarta+Sans:wght@400;500;600;700&display=swap');

    /* Enforce Dark Color Scheme Globally & Disable Light Mode */
    :root, html, body {
        color-scheme: dark !important;
    }

    /* Top Bar - Restored with Clean Ambient Styling */
    header[data-testid="stHeader"] {
        background: transparent !important;
        display: flex !important;
        visibility: visible !important;
    }
    header[data-testid="stHeader"] button,
    header[data-testid="stHeader"] svg {
        color: #f7ebe0 !important;
        fill: #f7ebe0 !important;
    }
    #MainMenu {
        display: block !important;
        visibility: visible !important;
    }
    /* Hide Theme selectbox inside Settings modal so Light mode cannot be picked */
    div[data-testid="stSettingsModal"] div[data-testid="stSelectbox"] {
        display: none !important;
    }

    /* Main Canvas Fallback - Warm ambient wood library study lighting */
    .stApp {
        background: radial-gradient(ellipse 110% 70% at 50% -10%, #3e2a1d 0%, #241810 45%, #150d08 100%);
        color: #f3e7d8 !important;
        font-family: 'Plus Jakarta Sans', sans-serif !important;
    }

    /* Classical Headings - Gold Foil & Carved Wood Typography */
    h1, h2, h3, h4 {
        font-family: 'Cinzel', Georgia, serif !important;
        color: #f7e8d5 !important;
        letter-spacing: 0.6px !important;
        text-shadow: 0 2px 4px rgba(0, 0, 0, 0.7) !important;
    }

    /* Sidebar - Fluted Oak Bookcase Cabinet */
    section[data-testid="stSidebar"] {
        background: linear-gradient(180deg, #1b120c 0%, #261911 50%, #19100a 100%) !important;
        border-right: 4px solid #5a3a22 !important;
        box-shadow: 6px 0 25px rgba(0, 0, 0, 0.65) !important;
    }
    section[data-testid="stSidebar"] * {
        color: #eeddcc !important;
    }

    /* Bookcase Alcoves / Card Containers - Built-in Solid Oak Shelves */
    div[data-testid="stVerticalBlockBorderWrapper"] {
        background: linear-gradient(180deg, #1d130c 0%, #291b12 70%, #20150d 100%) !important;
        border: 2px solid #5c3b24 !important;
        border-radius: 8px !important;
        box-shadow: inset 0 0 30px rgba(0, 0, 0, 0.75), 0 10px 25px rgba(0, 0, 0, 0.6) !important;
        position: relative;
        transition: transform 0.18s ease, border-color 0.18s ease, box-shadow 0.18s ease;
    }
    div[data-testid="stVerticalBlockBorderWrapper"]:hover {
        border-color: #8f603c !important;
        box-shadow: inset 0 0 25px rgba(0, 0, 0, 0.65), 0 12px 30px rgba(0, 0, 0, 0.75) !important;
        transform: translateY(-2px);
    }

    /* Solid Wooden Shelf Plinth under books */
    .bookshelf-plinth {
        height: 8px;
        background: linear-gradient(180deg, #b8804c 0%, #8c572c 35%, #593315 100%);
        border-radius: 2px 2px 3px 3px;
        box-shadow: 0 5px 12px rgba(0, 0, 0, 0.7), inset 0 1px 0 rgba(255, 235, 195, 0.45);
        margin: 10px 0 4px 0;
    }

    /* Book Cover Styling - Standing upright on a wooden shelf */
    .book-cover-frame {
        position: relative;
        padding-bottom: 2px;
    }
    .book-cover-frame img {
        border-radius: 4px 6px 6px 4px !important;
        box-shadow: -5px 6px 16px rgba(0, 0, 0, 0.75), 0 0 2px rgba(255, 255, 255, 0.15) !important;
        border-left: 3px solid rgba(255, 255, 255, 0.25) !important;
        border-top: 1px solid rgba(255, 255, 255, 0.1) !important;
        border-bottom: 1px solid rgba(0, 0, 0, 0.4) !important;
        transition: transform 0.2s ease;
    }
    .book-cover-frame img:hover {
        transform: scale(1.02);
    }

    /* Input Controls - Dark Walnut wood with warm brass glow */
    .stTextInput input, .stNumberInput input {
        background-color: #20150e !important;
        color: #f7ebe0 !important;
        border: 1px solid #563823 !important;
        border-radius: 5px !important;
    }
    .stTextInput input:focus, .stNumberInput input:focus {
        border-color: #c48b52 !important;
        box-shadow: 0 0 0 1px #c48b52 !important;
    }
    div[data-baseweb="select"] > div {
        background-color: #20150e !important;
        border-color: #563823 !important;
        color: #f7ebe0 !important;
        border-radius: 5px !important;
    }

    /* File Uploader styling - Classical Oak Cabinet */
    div[data-testid="stFileUploader"] {
        background: #20150e !important;
        border: 1px dashed #6b472c !important;
        border-radius: 6px !important;
        padding: 10px !important;
    }
    div[data-testid="stFileUploader"] section {
        padding: 0 !important;
    }
    div[data-testid="stFileUploader"] button {
        background: linear-gradient(180deg, #382518 0%, #291b11 100%) !important;
        border: 1px solid #6b472c !important;
        color: #f0dfce !important;
    }

    /* Theme Filter Pills - Antique Library Catalog Tabs */
    div[data-testid="stPills"] {
        gap: 8px !important;
    }
    div[data-testid="stPills"] button {
        background: linear-gradient(180deg, #2b1d14 0%, #1e140d 100%) !important;
        border: 1px solid #5c3c26 !important;
        color: #eddcd0 !important;
        font-family: 'Cinzel', serif !important;
        font-size: 0.82rem !important;
        letter-spacing: 0.5px !important;
        border-radius: 4px !important;
        padding: 5px 14px !important;
        display: inline-flex !important;
        align-items: center !important;
        justify-content: center !important;
        text-align: center !important;
        transition: all 0.2s ease !important;
    }
    div[data-testid="stPills"] button:hover {
        border-color: #9c6c44 !important;
        color: #ffffff !important;
    }
    div[data-testid="stPills"] button[aria-selected="true"] {
        background: linear-gradient(180deg, #8a2a1d 0%, #681d12 100%) !important;
        border-color: #bd4836 !important;
        color: #fff7f0 !important;
        box-shadow: 0 3px 8px rgba(138, 42, 29, 0.45) !important;
        font-weight: 600 !important;
    }

    /* Honey Amber Oak Progress Bar */
    div[data-testid="stProgress"] > div > div > div > div {
        background: linear-gradient(90deg, #945d2e 0%, #c98848 50%, #e8b87c 100%) !important;
        border-radius: 4px !important;
    }
    div[data-testid="stProgress"] > div > div > div {
        background-color: #160e09 !important;
        border: 1px solid #4a301e !important;
        border-radius: 4px !important;
    }

    /* Buttons - Clean horizontal layout & PERFECTLY CENTERED text */
    div[data-testid="stButton"] {
        display: flex !important;
        justify-content: center !important;
        align-items: center !important;
        width: 100% !important;
    }
    div[data-testid="stButton"] button,
    button[kind="primary"],
    button[kind="secondary"] {
        white-space: nowrap !important;
        font-family: 'Plus Jakarta Sans', sans-serif !important;
        font-size: 0.85rem !important;
        font-weight: 500 !important;
        border-radius: 5px !important;
        padding: 0.38rem 0.65rem !important;
        transition: all 0.2s ease !important;
        display: flex !important;
        align-items: center !important;
        justify-content: center !important;
        text-align: center !important;
    }
    div[data-testid="stButton"] button > div,
    div[data-testid="stButton"] button div[data-testid="stMarkdownContainer"] {
        display: flex !important;
        align-items: center !important;
        justify-content: center !important;
        text-align: center !important;
        width: 100% !important;
        margin: 0 !important;
        padding: 0 !important;
    }
    div[data-testid="stButton"] button p {
        text-align: center !important;
        margin: 0 !important;
        padding: 0 !important;
        line-height: 1.3 !important;
        width: 100% !important;
        display: flex !important;
        align-items: center !important;
        justify-content: center !important;
    }

    /* Primary buttons: Antique Burgundy Leather with Gold Accent */
    button[kind="primary"] {
        background: linear-gradient(180deg, #8a2a1d 0%, #6e1f13 100%) !important;
        color: #fdf3e9 !important;
        border: 1px solid #b34636 !important;
        box-shadow: 0 3px 8px rgba(0, 0, 0, 0.4), inset 0 1px 0 rgba(255, 255, 255, 0.25) !important;
    }
    button[kind="primary"]:hover {
        background: linear-gradient(180deg, #a33424 0%, #7d2417 100%) !important;
        border-color: #d65541 !important;
        transform: translateY(-1px);
    }

    /* Secondary buttons: Polished Oak & Antique Walnut */
    button[kind="secondary"] {
        background: linear-gradient(180deg, #382518 0%, #291b11 100%) !important;
        color: #eedccb !important;
        border: 1px solid #5c3c26 !important;
        box-shadow: 0 2px 5px rgba(0, 0, 0, 0.35), inset 0 1px 0 rgba(255, 255, 255, 0.1) !important;
    }
    button[kind="secondary"]:hover {
        background: linear-gradient(180deg, #4a3221 0%, #342215 100%) !important;
        border-color: #8c5d3a !important;
        color: #ffffff !important;
        transform: translateY(-1px);
    }

    /* Segmented Control Navigation - Classical Mahogany & Gold Plinth */
    div[data-testid="stSegmentedControl"] {
        background: #190f09 !important;
        border: 1.5px solid #5a3a22 !important;
        border-radius: 8px !important;
        padding: 5px !important;
        box-shadow: inset 0 2px 8px rgba(0,0,0,0.6), 0 3px 10px rgba(0,0,0,0.4) !important;
        margin-bottom: 20px !important;
    }
    div[data-testid="stSegmentedControl"] button {
        font-family: 'Cinzel', serif !important;
        font-size: 0.95rem !important;
        font-weight: 700 !important;
        letter-spacing: 0.8px !important;
        color: #c9aa88 !important;
        background: transparent !important;
        border-radius: 6px !important;
        border: none !important;
        padding: 8px 24px !important;
        display: inline-flex !important;
        align-items: center !important;
        justify-content: center !important;
        text-align: center !important;
        transition: all 0.25s ease !important;
    }
    div[data-testid="stSegmentedControl"] button:hover {
        color: #fff2e0 !important;
        background: rgba(255, 235, 205, 0.08) !important;
    }
    div[data-testid="stSegmentedControl"] button[aria-checked="true"],
    div[data-testid="stSegmentedControl"] button[aria-selected="true"] {
        background: linear-gradient(180deg, #8a2a1d 0%, #681d12 100%) !important;
        color: #fff7f0 !important;
        border: 1px solid #b34636 !important;
        box-shadow: 0 4px 12px rgba(0,0,0,0.5), inset 0 1px 0 rgba(255,255,255,0.25) !important;
    }

    /* Antique Wooden Category Folder Box & Metric Cards */
    .folder-container-box {
        background: linear-gradient(145deg, #2a1c12 0%, #1a1008 100%);
        border: 1.5px solid #5e3b23;
        border-radius: 12px;
        padding: 16px 18px;
        margin-bottom: 20px;
        box-shadow: 0 8px 22px rgba(0, 0, 0, 0.55), inset 0 1px 0 rgba(255, 235, 195, 0.15);
        transition: all 0.25s ease;
    }
    .folder-container-box:hover {
        border-color: #9e6439;
        box-shadow: 0 12px 28px rgba(0, 0, 0, 0.7), 0 0 16px rgba(184, 128, 76, 0.25);
        transform: translateY(-2px);
    }
    .metric-archive-card {
        background: linear-gradient(145deg, #24170e 0%, #170e08 100%);
        border: 1px solid #54351f;
        border-radius: 8px;
        padding: 12px 14px;
        box-shadow: 0 4px 12px rgba(0,0,0,0.4), inset 0 1px 0 rgba(255,235,200,0.1);
        text-align: center;
    }

    /* Complete Dark Mode Lock for Dialogs, Menus, Popovers, and Expanders */
    div[data-testid="stExpander"] {
        background-color: #1c120b !important;
        border: 1px solid #563823 !important;
        border-radius: 8px !important;
    }
    div[data-testid="stExpander"] summary {
        color: #f7ebe0 !important;
    }
    div[data-baseweb="popover"], div[data-baseweb="menu"], ul[role="listbox"], li[role="option"] {
        background-color: #1f140d !important;
        color: #f7ebe0 !important;
    }
    li[role="option"]:hover, li[aria-selected="true"] {
        background-color: #3d2719 !important;
        color: #ffffff !important;
    }
    div[role="dialog"], div[data-testid="stModal"] {
        background-color: #1c120b !important;
        color: #f7ebe0 !important;
        border: 1.5px solid #5c3c26 !important;
    }
    </style>
    """,
    unsafe_allow_html=True
)

# Toast notifications
if "finish_toast" in st.session_state:
    st.balloons()
    st.toast(st.session_state.pop("finish_toast"))
if "save_toast" in st.session_state:
    st.toast(st.session_state.pop("save_toast"))

# ================= AUTHENTICATION & MULTI-TENANCY =================
def render_auth_page(database):
    """Render the classical library authentication portal."""
    st.markdown(
        """
        <div style="text-align: center; padding: 25px 0 15px 0; margin-bottom: 20px;">
            <div style="font-family: 'Cinzel', serif; font-size: 2.6rem; font-weight: 800; color: #faede0; letter-spacing: 2px; text-shadow: 0 3px 8px rgba(0,0,0,0.85);">
                🏛️ PERSONAL LIBRARY
            </div>
            <div style="font-family: 'Playfair Display', Georgia, serif; font-size: 1.15rem; font-style: italic; color: #cf9a6b; margin-top: 6px;">
                Grand Archive of Literature & Private Reader Sanctuaries
            </div>
            <div style="height: 4px; max-width: 320px; margin: 16px auto 0 auto; background: linear-gradient(90deg, transparent, #c8915e, transparent); border-radius: 2px;"></div>
        </div>
        """,
        unsafe_allow_html=True
    )

    _, col_auth, _ = st.columns([1, 1.4, 1])
    with col_auth:
        with st.container(border=True):
            st.markdown(
                """
                <div style="text-align: center; margin-bottom: 16px;">
                    <span style="font-size: 32px;">🔐</span>
                    <div style="font-family: 'Cinzel', serif; font-size: 1.35rem; font-weight: 700; color: #faede0; letter-spacing: 0.8px; margin-top: 4px;">
                        READER ACCESS PORTAL
                    </div>
                    <div style="font-size: 0.86rem; color: #cf9a6b; margin-top: 4px;">
                        Each reader possesses an isolated, private library archive.
                    </div>
                </div>
                """,
                unsafe_allow_html=True
            )

            auth_tab_in, auth_tab_reg, auth_tab_renew = st.tabs(["🔑 Sign In", "📝 Register New Reader", "🔄 Reset Password"])

            with auth_tab_in:
                with st.form("form_signin", clear_on_submit=False):
                    login_user = st.text_input("Username", key="auth_login_user", placeholder="e.g. edrey")
                    login_pass = st.text_input("Password", type="password", key="auth_login_pass", placeholder="••••••••")
                    login_btn = st.form_submit_button("🔓 Enter My Library", type="primary", use_container_width=True)

                    if login_btn:
                        ok, res = database.authenticate_user(login_user, login_pass)
                        if ok:
                            st.session_state["logged_in_user"] = res
                            st.session_state["finish_toast"] = f"Welcome back, {res['display_name']}!"
                            st.rerun()
                        else:
                            st.error(res)

            with auth_tab_reg:
                with st.form("form_register", clear_on_submit=False):
                    reg_user = st.text_input("Choose Username", key="auth_reg_user", placeholder="e.g. sarah")
                    reg_name = st.text_input("Reader Name / Display Name", key="auth_reg_name", placeholder="e.g. Sarah")
                    reg_pass1 = st.text_input("Password", type="password", key="auth_reg_pass1", placeholder="At least 4 characters")
                    reg_pass2 = st.text_input("Confirm Password", type="password", key="auth_reg_pass2", placeholder="Re-enter password")
                    reg_btn = st.form_submit_button("📜 Register & Create Sanctuary", type="primary", use_container_width=True)

                    if reg_btn:
                        if not reg_user.strip():
                            st.error("Please enter a username.")
                        elif not reg_pass1 or len(reg_pass1) < 4:
                            st.error("Password must be at least 4 characters long.")
                        elif reg_pass1 != reg_pass2:
                            st.error("Passwords do not match.")
                        else:
                            ok, res = database.register_user(reg_user, reg_pass1, reg_name)
                            if ok:
                                st.session_state["logged_in_user"] = res
                                st.session_state["finish_toast"] = f"Welcome to your private library, {res['display_name']}!"
                                st.rerun()
                            else:
                                st.error(res)

            with auth_tab_renew:
                with st.form("form_renew_pw", clear_on_submit=False):
                    st.caption("Forgot your password? Enter your username and set a new password.")
                    renew_user = st.text_input("Username", key="auth_renew_user", placeholder="Enter your registered username")
                    renew_pass1 = st.text_input("New Password", type="password", key="auth_renew_pass1", placeholder="At least 4 characters")
                    renew_pass2 = st.text_input("Confirm New Password", type="password", key="auth_renew_pass2", placeholder="Re-enter new password")
                    renew_btn = st.form_submit_button("🔐 Renew Password & Enter", type="primary", use_container_width=True)

                    if renew_btn:
                        if not renew_user.strip():
                            st.error("Please enter your username.")
                        elif not renew_pass1 or len(renew_pass1) < 4:
                            st.error("New password must be at least 4 characters long.")
                        elif renew_pass1 != renew_pass2:
                            st.error("Passwords do not match. Please verify your new password.")
                        else:
                            ok, res = database.update_password(renew_user, renew_pass1)
                            if ok:
                                st.session_state["logged_in_user"] = res
                                st.session_state["finish_toast"] = f"Password renewed! Welcome back, {res['display_name']}!"
                                st.rerun()
                            else:
                                st.error(res)

current_user = get_current_user()
if not current_user:
    render_auth_page(db)
    st.stop()

# ================= GRAND WOODEN LIBRARY HEADER =================
user_dname = current_user.get('display_name', 'Reader') if current_user else 'Reader'
user_uname = current_user.get('username', 'reader') if current_user else 'reader'
user_library_title = f"🏛️ {user_dname.upper()}'S LIBRARY"
st.markdown(
    f"""
    <div style="padding: 10px 0 18px 0; border-bottom: 2px solid #5a3c25; margin-bottom: 20px;">
        <div style="display: flex; align-items: baseline; justify-content: space-between; flex-wrap: wrap; gap: 12px;">
            <div>
                <span style="font-family: 'Cinzel', serif; font-size: 2.25rem; font-weight: 800; color: #faede0; letter-spacing: 1.2px; text-shadow: 0 2px 6px rgba(0,0,0,0.8);">
                    {user_library_title}
                </span>
                <span style="font-family: 'Playfair Display', Georgia, serif; font-size: 1.05rem; font-style: italic; color: #cf9a6b; margin-left: 16px;">
                    Grand Archive of Literature & Study
                </span>
            </div>
            <div style="display: flex; align-items: center; gap: 10px;">
                <div style="font-family: 'Cinzel', serif; font-size: 0.82rem; font-weight: 600; color: #dfbe9b; background: linear-gradient(180deg, #3d281a 0%, #2a1a10 100%); padding: 6px 14px; border-radius: 4px; border: 1px solid #6b472c; box-shadow: 0 3px 8px rgba(0,0,0,0.4), inset 0 1px 0 rgba(255,230,190,0.2); letter-spacing: 1px;">
                    👤 {user_dname} (@{user_uname})
                </div>
            </div>
        </div>
        <div style="height: 6px; background: linear-gradient(90deg, #4a301f 0%, #875734 25%, #c8915e 50%, #875734 75%, #4a301f 100%); border-radius: 3px; margin-top: 14px; box-shadow: 0 4px 10px rgba(0,0,0,0.6), inset 0 1px 0 rgba(255, 235, 195, 0.35);"></div>
    </div>
    """,
    unsafe_allow_html=True
)

# ================= LIBRARY VIEW NAVIGATION =================
NAV_SUMMARY = "📁 Summary"
NAV_BOOKCASES = "🏛️ Reading Bookcases"

if "library_nav_view" in st.session_state and st.session_state["library_nav_view"] not in [NAV_SUMMARY, NAV_BOOKCASES]:
    st.session_state["library_nav_view"] = NAV_SUMMARY

nav_view = st.segmented_control(
    "Library Navigation View",
    [NAV_SUMMARY, NAV_BOOKCASES],
    default=NAV_SUMMARY,
    key="library_nav_view",
    label_visibility="collapsed"
)

GENRE_ICONS = {
    "Romance": "💖",
    "Fiction": "📖",
    "Non-Fiction": "🧠",
    "Islamic Studies": "🕌",
    "Mystery & Thriller": "🕵️",
    "Sci-Fi & Fantasy": "🔮",
    "Self-Help & Growth": "🌱",
    "Biography & Memoir": "🖋️",
    "History & Politics": "🏛️",
    "Young Adult": "🎒",
    "Classics": "📜",
    "Horror": "🕯️",
    "Poetry & Essays": "🪶",
}

def get_genre_icon(genre: str) -> str:
    """Return an atmospheric theme icon for the category."""
    return GENRE_ICONS.get(genre, "📁")

def render_status_badge(status):
    """Render a classical leather & gold library status badge."""
    if status == "Ongoing":
        return """<span style="display: inline-block; background: linear-gradient(180deg, #593110 0%, #3a1e08 100%); border: 1px solid #945821; color: #fedbb4; padding: 2px 10px; border-radius: 4px; font-size: 0.74rem; font-family: 'Cinzel', serif; letter-spacing: 0.6px; box-shadow: 0 2px 5px rgba(0,0,0,0.4);">⏳ ONGOING</span>"""
    elif status == "Read":
        return """<span style="display: inline-block; background: linear-gradient(180deg, #1c3d25 0%, #112617 100%); border: 1px solid #2d6b3e; color: #a9f0bd; padding: 2px 10px; border-radius: 4px; font-size: 0.74rem; font-family: 'Cinzel', serif; letter-spacing: 0.6px; box-shadow: 0 2px 5px rgba(0,0,0,0.4);">✅ COMPLETED</span>"""
    else:
        return """<span style="display: inline-block; background: linear-gradient(180deg, #243547 0%, #14202d 100%); border: 1px solid #3c5d7d; color: #bcd8f3; padding: 2px 10px; border-radius: 4px; font-size: 0.74rem; font-family: 'Cinzel', serif; letter-spacing: 0.6px; box-shadow: 0 2px 5px rgba(0,0,0,0.4);">📖 WANT TO READ</span>"""


def render_cover_image(row):
    """Render cover image (online URL or user-uploaded local image) standing on a solid wooden shelf."""
    cover_url = row.get('cover_url')
    if not cover_url or pd.isna(cover_url):
        # Auto-fetch cover and details if missing
        details = fetch_book_details(row['title'], row['author'])
        if details.get("cover_url"):
            cover_url = details["cover_url"]
            db.update_cover(row['id'], cover_url)
        if (not row.get('total_pages') or row['total_pages'] == 0) and details.get("total_pages", 0) > 0:
            db.update_total_pages(row['id'], details["total_pages"])

    # Determine if cover_url exists (either as URL or local file on disk)
    has_valid_cover = False
    if cover_url and pd.notna(cover_url):
        c_str = str(cover_url).strip()
        if c_str.startswith(("http://", "https://")) or os.path.exists(c_str):
            has_valid_cover = True

    if has_valid_cover:
        st.markdown('<div class="book-cover-frame">', unsafe_allow_html=True)
        st.image(cover_url, use_container_width=True)
        st.markdown('<div class="bookshelf-plinth"></div></div>', unsafe_allow_html=True)
    else:
        st.markdown(
            """
            <div style="background: linear-gradient(180deg, #241710 0%, #301f15 100%);
                        border-radius: 6px;
                        aspect-ratio: 2/3;
                        display: flex;
                        flex-direction: column;
                        align-items: center;
                        justify-content: center;
                        color: #c9986b;
                        border: 1px dashed #614028;
                        padding: 8px;
                        text-align: center;
                        box-shadow: inset 0 0 15px rgba(0,0,0,0.6);">
                <span style="font-size: 32px; margin-bottom: 4px;">📖</span>
                <span style="font-size: 11px; font-family: 'Cinzel', serif; letter-spacing: 0.5px; color: #e5cbaf;">CLASSIC VOLUME</span>
            </div>
            <div class="bookshelf-plinth"></div>
            """,
            unsafe_allow_html=True
        )

def render_genre_badge(genre_name):
    """Render a classical leather & gold library theme badge."""
    g = genre_name or "Fiction"
    return f"""
    <span style="display: inline-block; background: linear-gradient(180deg, #332014 0%, #25160d 100%); border: 1px solid #6b472c; color: #e5bf98; padding: 2px 10px; border-radius: 4px; font-size: 0.74rem; font-family: 'Cinzel', serif; letter-spacing: 0.6px; margin: 4px 0 8px 0; box-shadow: 0 2px 4px rgba(0,0,0,0.3);">
        🏷️ {g}
    </span>
    """

def render_want_to_read_card(row):
    """Render a card for books in 'Want to Read'."""
    with st.container(border=True):
        col_img, col_info = st.columns([1, 2.2])
        with col_img:
            render_cover_image(row)
        with col_info:
            st.subheader(row['title'])
            st.write(f"**Author:** {row['author']}")
            st.markdown(render_genre_badge(row.get('genre')), unsafe_allow_html=True)
            
            tot = int(row['total_pages']) if pd.notna(row['total_pages']) else 0
            if tot > 0:
                st.caption(f"📜 Volume Length: {tot} pages")
            
            with st.expander("⚙️ Edit volume details & cover picture"):
                ed_c1, ed_c2 = st.columns(2)
                with ed_c1:
                    new_tot = st.number_input("Total pages", min_value=0, value=tot, step=1, key=f"tot_w_{row['id']}")
                with ed_c2:
                    current_g = row.get('genre', 'Fiction')
                    all_g = [g for g in POPULAR_GENRES if g != "Custom..."]
                    if current_g not in all_g:
                        all_g.append(current_g)
                    g_idx = all_g.index(current_g) if current_g in all_g else 0
                    new_g = st.selectbox("Theme / Genre", all_g, index=g_idx, key=f"genre_w_{row['id']}")
                
                st.markdown("**Update Cover Picture:**")
                new_cover_file = st.file_uploader(
                    "Upload picture file", 
                    type=["jpg", "jpeg", "png", "webp"], 
                    key=f"file_cov_w_{row['id']}"
                )
                new_cover_url = st.text_input(
                    "Or enter image URL", 
                    value=str(row['cover_url']) if (row.get('cover_url') and str(row['cover_url']).startswith('http')) else "", 
                    key=f"url_cov_w_{row['id']}"
                )

                if st.button("Save Changes", key=f"save_w_{row['id']}", use_container_width=True):
                    db.update_total_pages(row['id'], new_tot)
                    db.update_genre(row['id'], new_g)
                    if new_cover_file is not None:
                        saved = save_uploaded_cover(new_cover_file)
                        if saved:
                            db.update_cover(row['id'], saved)
                    elif new_cover_url.strip():
                        db.update_cover(row['id'], new_cover_url.strip())
                    st.toast(f"Updated '{row['title']}'!")
                    st.rerun()

            st.write("")
            c1, c2, c3 = st.columns([1.5, 1.5, 0.9])
            with c1:
                if st.button("Start Reading", key=f"start_{row['id']}", type="primary", use_container_width=True):
                    db.update_status(row['id'], "Ongoing")
                    if int(row['current_page']) == 0:
                        db.update_page(row['id'], 1)
                    st.rerun()
            with c2:
                if st.button("Mark as Read", key=f"want_read_{row['id']}", use_container_width=True):
                    db.update_status(row['id'], "Read")
                    if tot > 0:
                        db.update_page(row['id'], tot)
                    st.rerun()
            with c3:
                if st.button("Delete", key=f"del_want_{row['id']}", use_container_width=True):
                    db.delete_book(row['id'])
                    st.rerun()

def render_ongoing_card(row):
    """Render a card for books in 'Ongoing' with reading progress bar and stopping page input."""
    with st.container(border=True):
        col_img, col_info = st.columns([1, 2.2])
        with col_img:
            render_cover_image(row)
        with col_info:
            st.subheader(row['title'])
            st.write(f"**Author:** {row['author']}")
            st.markdown(render_genre_badge(row.get('genre')), unsafe_allow_html=True)
            
            curr = int(row['current_page']) if pd.notna(row['current_page']) else 0
            tot = int(row['total_pages']) if pd.notna(row['total_pages']) else 0
            
            # Progress Bar and Reading Stats
            if tot > 0:
                pct = min(1.0, max(0.0, curr / tot))
                st.progress(pct)
                st.markdown(f"📖 **Page {curr} of {tot}** ({int(pct * 100)}% complete)")
            else:
                st.markdown(f"📖 **Currently at Page {curr}** *(total length not set)*")
            
            # Key what page number I am at when I stop
            st.markdown("🔖 **Where did you stop reading?**")
            p_c1, p_c2 = st.columns([1.6, 1])
            with p_c1:
                new_page = st.number_input(
                    "Page number",
                    min_value=0,
                    max_value=max(tot, curr + 1000, 1000) if tot > 0 else 10000,
                    value=curr,
                    step=1,
                    key=f"page_input_{row['id']}",
                    label_visibility="collapsed"
                )
            with p_c2:
                if st.button("Save Page", key=f"btn_page_{row['id']}", type="primary", use_container_width=True):
                    db.update_page(row['id'], new_page)
                    if tot > 0 and new_page >= tot:
                        db.update_status(row['id'], "Read")
                        st.session_state["finish_toast"] = f"🎉 Magnifique! You finished reading '{row['title']}'!"
                    else:
                        st.session_state["save_toast"] = f"🔖 Saved! Bookmarked at page {new_page}."
                    st.rerun()
            
            with st.expander("⚙️ Edit volume details & cover picture"):
                ed_c1, ed_c2 = st.columns(2)
                with ed_c1:
                    new_tot = st.number_input("Total pages", min_value=0, value=tot, step=1, key=f"tot_input_{row['id']}")
                with ed_c2:
                    current_g = row.get('genre', 'Fiction')
                    all_g = [g for g in POPULAR_GENRES if g != "Custom..."]
                    if current_g not in all_g:
                        all_g.append(current_g)
                    g_idx = all_g.index(current_g) if current_g in all_g else 0
                    new_g = st.selectbox("Theme / Genre", all_g, index=g_idx, key=f"genre_edit_{row['id']}")
                
                st.markdown("**Update Cover Picture:**")
                new_cover_file = st.file_uploader(
                    "Upload picture file", 
                    type=["jpg", "jpeg", "png", "webp"], 
                    key=f"file_cov_ong_{row['id']}"
                )
                new_cover_url = st.text_input(
                    "Or enter image URL", 
                    value=str(row['cover_url']) if (row.get('cover_url') and str(row['cover_url']).startswith('http')) else "", 
                    key=f"url_cov_ong_{row['id']}"
                )

                if st.button("Save Changes", key=f"btn_tot_{row['id']}", use_container_width=True):
                    db.update_total_pages(row['id'], new_tot)
                    db.update_genre(row['id'], new_g)
                    if new_cover_file is not None:
                        saved = save_uploaded_cover(new_cover_file)
                        if saved:
                            db.update_cover(row['id'], saved)
                    elif new_cover_url.strip():
                        db.update_cover(row['id'], new_cover_url.strip())
                    st.toast(f"Updated '{row['title']}'!")
                    st.rerun()

            st.write("")
            c1, c2, c3 = st.columns([1.3, 1.3, 0.9])
            with c1:
                if st.button("Mark as Read", key=f"finish_ong_{row['id']}", use_container_width=True):
                    db.update_status(row['id'], "Read")
                    if tot > 0:
                        db.update_page(row['id'], tot)
                    st.session_state["finish_toast"] = f"🎉 Finished reading '{row['title']}'!"
                    st.rerun()
            with c2:
                if st.button("Put on Hold", key=f"pause_ong_{row['id']}", use_container_width=True):
                    db.update_status(row['id'], "Want to Read")
                    st.rerun()
            with c3:
                if st.button("Delete", key=f"del_ong_{row['id']}", use_container_width=True):
                    db.delete_book(row['id'])
                    st.rerun()

def render_folder_book_card(row, key_prefix="fld"):
    """Render a comprehensive volume card with progress and controls inside an opened category folder."""
    with st.container(border=True):
        col_img, col_info = st.columns([1, 2.2])
        with col_img:
            render_cover_image(row)
        with col_info:
            st.subheader(row['title'])
            st.write(f"**Author:** {row['author']}")
            st.markdown(
                f"{render_genre_badge(row.get('genre'))} &nbsp; {render_status_badge(row.get('status'))}", 
                unsafe_allow_html=True
            )
            
            curr = int(row['current_page']) if pd.notna(row['current_page']) else 0
            tot = int(row['total_pages']) if pd.notna(row['total_pages']) else 0
            status = row.get('status', 'Want to Read')
            
            if tot > 0:
                pct = int((curr / tot) * 100)
                st.progress(min(1.0, max(0.0, curr / tot)))
                st.caption(f"📖 **Reading Progress:** {curr:,} of {tot:,} pages ({pct}%)")
            else:
                st.caption("📖 Reading progress not tracked (0 total pages specified).")

            # Status and reading controls
            if status == "Ongoing":
                st.write("**Update Current Page:**")
                c_p1, c_p2 = st.columns([1.5, 1])
                with c_p1:
                    new_curr = st.number_input(
                        "Page number", 
                        min_value=0, 
                        max_value=tot if tot > 0 else 10000, 
                        value=curr, 
                        step=1, 
                        key=f"{key_prefix}_pg_{row['id']}",
                        label_visibility="collapsed"
                    )
                with c_p2:
                    if st.button("Save", key=f"{key_prefix}_save_pg_{row['id']}", use_container_width=True):
                        db.update_page(row['id'], new_curr)
                        if tot > 0 and new_curr >= tot:
                            db.update_status(row['id'], "Read")
                            st.session_state["finish_toast"] = f"🎉 Finished reading '{row['title']}'!"
                        else:
                            st.session_state["save_toast"] = f"Updated page to {new_curr}."
                        st.rerun()

                st.write("")
                b1, b2, b3 = st.columns([1.3, 1.3, 0.9])
                with b1:
                    if st.button("Mark as Read", key=f"{key_prefix}_fin_{row['id']}", use_container_width=True):
                        db.update_status(row['id'], "Read")
                        if tot > 0:
                            db.update_page(row['id'], tot)
                        st.session_state["finish_toast"] = f"🎉 Finished reading '{row['title']}'!"
                        st.rerun()
                with b2:
                    if st.button("Put on Hold", key=f"{key_prefix}_hold_{row['id']}", use_container_width=True):
                        db.update_status(row['id'], "Want to Read")
                        st.rerun()
                with b3:
                    if st.button("Delete", key=f"{key_prefix}_del_{row['id']}", use_container_width=True):
                        db.delete_book(row['id'])
                        st.rerun()

            elif status == "Want to Read":
                b1, b2 = st.columns([1.5, 1])
                with b1:
                    if st.button("Start Reading", key=f"{key_prefix}_start_{row['id']}", use_container_width=True):
                        db.update_status(row['id'], "Ongoing")
                        db.update_page(row['id'], 1)
                        st.rerun()
                with b2:
                    if st.button("Delete", key=f"{key_prefix}_del_{row['id']}", use_container_width=True):
                        db.delete_book(row['id'])
                        st.rerun()

            else:  # Read
                b1, b2 = st.columns([1.5, 1])
                with b1:
                    if st.button("Read Again", key=f"{key_prefix}_again_{row['id']}", use_container_width=True):
                        db.update_status(row['id'], "Ongoing")
                        db.update_page(row['id'], 1)
                        st.rerun()
                with b2:
                    if st.button("Delete", key=f"{key_prefix}_del_{row['id']}", use_container_width=True):
                        db.delete_book(row['id'])
                        st.rerun()

            # Edit Details Expander
            with st.expander("⚙️ Edit volume details & cover picture"):
                ed_c1, ed_c2 = st.columns(2)
                with ed_c1:
                    new_tot = st.number_input("Total pages", min_value=0, value=tot, step=1, key=f"{key_prefix}_tot_{row['id']}")
                with ed_c2:
                    current_g = row.get('genre', 'Fiction')
                    all_g = [g for g in POPULAR_GENRES if g != "Custom..."]
                    if current_g not in all_g:
                        all_g.append(current_g)
                    g_idx = all_g.index(current_g) if current_g in all_g else 0
                    new_g = st.selectbox("Theme / Genre Folder", all_g, index=g_idx, key=f"{key_prefix}_g_{row['id']}")
                
                st.markdown("**Update Cover Picture:**")
                new_cover_file = st.file_uploader(
                    "Upload picture file", 
                    type=["jpg", "jpeg", "png", "webp"], 
                    key=f"{key_prefix}_fcov_{row['id']}"
                )
                new_cover_url = st.text_input(
                    "Or enter image URL", 
                    value=str(row['cover_url']) if (row.get('cover_url') and str(row['cover_url']).startswith('http')) else "", 
                    key=f"{key_prefix}_ucov_{row['id']}"
                )

                if st.button("Save Changes", key=f"{key_prefix}_save_{row['id']}", use_container_width=True):
                    db.update_total_pages(row['id'], new_tot)
                    db.update_genre(row['id'], new_g)
                    if new_cover_file is not None:
                        saved = save_uploaded_cover(new_cover_file)
                        if saved:
                            db.update_cover(row['id'], saved)
                    elif new_cover_url.strip():
                        db.update_cover(row['id'], new_cover_url.strip())
                    st.toast(f"Updated '{row['title']}'!")
                    st.rerun()

def render_category_folders_summary_page(db):
    """Render the Category Summary Page showing dossiers/folders for each book category."""
    opened_folder = st.session_state.get("opened_category_folder")

    # ================= ROOT FOLDER DIRECTORY (ALL CATEGORIES) =================
    if not opened_folder:
        # Overview Executive Ribbon
        stats = db.get_library_overall_stats()
        tot_b = stats["total_books"]
        tot_g = stats["total_genres"]
        tot_p = stats["total_pages"]
        read_p = stats["pages_read"]
        comp_b = stats["read_count"]
        ong_b = stats["ongoing_count"]
        want_b = stats["want_count"]
        pct_lib = int((read_p / tot_p) * 100) if tot_p > 0 else 0

        st.markdown(
            f"""
            <div style="background: linear-gradient(145deg, #24170e 0%, #170e08 100%); border: 1.5px solid #5a3c25; border-radius: 10px; padding: 18px 22px; margin-bottom: 22px; box-shadow: 0 6px 18px rgba(0,0,0,0.5), inset 0 1px 0 rgba(255,230,190,0.15);">
                <div style="display: flex; align-items: baseline; justify-content: space-between; flex-wrap: wrap; gap: 8px; margin-bottom: 14px;">
                    <div>
                        <span style="font-family: 'Cinzel', serif; font-size: 1.45rem; font-weight: 700; color: #faede0; letter-spacing: 0.8px;">
                            🗂️ LIBRARY ARCHIVE & CATEGORY DOSSIERS
                        </span>
                        <div style="font-family: 'Playfair Display', Georgia, serif; font-style: italic; font-size: 0.95rem; color: #cf9a6b; margin-top: 2px;">
                            Summary of literary themes, volume distribution, and reading progression
                        </div>
                    </div>
                    <span style="font-family: 'Cinzel', serif; font-size: 0.78rem; color: #dfbe9b; background: #3d281a; padding: 4px 12px; border-radius: 4px; border: 1px solid #6b472c;">
                        TOTAL PORTFOLIO
                    </span>
                </div>
                <div style="display: grid; grid-template-columns: repeat(auto-fit, minmax(130px, 1fr)); gap: 12px; margin-bottom: 14px;">
                    <div class="metric-archive-card">
                        <div style="font-size: 1.3rem;">🗂️</div>
                        <div style="font-family: 'Cinzel', serif; font-size: 1.4rem; font-weight: 700; color: #faede0;">{tot_g}</div>
                        <div style="font-size: 0.75rem; color: #cf9a6b; font-family: 'Plus Jakarta Sans', sans-serif;">Categories</div>
                    </div>
                    <div class="metric-archive-card">
                        <div style="font-size: 1.3rem;">📚</div>
                        <div style="font-family: 'Cinzel', serif; font-size: 1.4rem; font-weight: 700; color: #faede0;">{tot_b}</div>
                        <div style="font-size: 0.75rem; color: #cf9a6b; font-family: 'Plus Jakarta Sans', sans-serif;">Total Volumes</div>
                    </div>
                    <div class="metric-archive-card">
                        <div style="font-size: 1.3rem;">⏳</div>
                        <div style="font-family: 'Cinzel', serif; font-size: 1.4rem; font-weight: 700; color: #f5cb98;">{ong_b}</div>
                        <div style="font-size: 0.75rem; color: #cf9a6b; font-family: 'Plus Jakarta Sans', sans-serif;">In Progress</div>
                    </div>
                    <div class="metric-archive-card">
                        <div style="font-size: 1.3rem;">🏆</div>
                        <div style="font-family: 'Cinzel', serif; font-size: 1.4rem; font-weight: 700; color: #a2edbc;">{comp_b}</div>
                        <div style="font-size: 0.75rem; color: #cf9a6b; font-family: 'Plus Jakarta Sans', sans-serif;">Completed</div>
                    </div>
                    <div class="metric-archive-card">
                        <div style="font-size: 1.3rem;">📖</div>
                        <div style="font-family: 'Cinzel', serif; font-size: 1.4rem; font-weight: 700; color: #faede0;">{read_p:,} / {tot_p:,}</div>
                        <div style="font-size: 0.75rem; color: #cf9a6b; font-family: 'Plus Jakarta Sans', sans-serif;">Pages ({pct_lib}%)</div>
                    </div>
                </div>
            </div>
            """,
            unsafe_allow_html=True
        )

        st.markdown(
            """
            <div style="display: flex; align-items: baseline; justify-content: space-between; margin-bottom: 16px; border-bottom: 1px solid #5a3c25; padding-bottom: 6px;">
                <span style="font-family: 'Cinzel', serif; font-size: 1.35rem; font-weight: 700; color: #faede0; letter-spacing: 0.6px;">
                    📂 Category Folders
                </span>
                <span style="font-family: 'Playfair Display', Georgia, serif; font-style: italic; font-size: 0.9rem; color: #c49265;">
                    Click any folder to inspect its volumes and detailed records
                </span>
            </div>
            """,
            unsafe_allow_html=True
        )

        summary_df = db.get_category_summary()
        if summary_df.empty:
            st.info("No categorized volumes in the library yet. Catalog new books from the sidebar to create category folders!")
            return

        # Render folder cards in 2 columns
        cols = st.columns(2)
        for i, (_, row) in enumerate(summary_df.iterrows()):
            cat = row['category']
            icon = get_genre_icon(cat)
            t_books = int(row['total_books'])
            w_count = int(row['want_count'])
            o_count = int(row['ongoing_count'])
            r_count = int(row['read_count'])
            t_pages = int(row['total_pages'])
            r_pages = int(row['pages_read'])
            pct = int((r_pages / t_pages) * 100) if t_pages > 0 else 0

            with cols[i % 2]:
                with st.container(border=True):
                    # Folder Tab Header
                    st.markdown(
                        f"""
                        <div style="display: flex; align-items: center; justify-content: space-between; margin-bottom: 10px; border-bottom: 1px solid #5a3c25; padding-bottom: 8px;">
                            <div style="display: flex; align-items: center; gap: 9px;">
                                <span style="font-size: 1.5rem;">{icon}</span>
                                <span style="font-family: 'Cinzel', serif; font-size: 1.25rem; font-weight: 700; color: #faede0; letter-spacing: 0.6px;">
                                    {cat}
                                </span>
                            </div>
                            <span style="font-family: 'Cinzel', serif; font-size: 0.8rem; font-weight: 600; color: #dfbe9b; background: linear-gradient(180deg, #3d281a 0%, #2a1a10 100%); padding: 3px 12px; border-radius: 12px; border: 1px solid #6b472c;">
                                {t_books} {'Volume' if t_books == 1 else 'Volumes'}
                            </span>
                        </div>
                        """,
                        unsafe_allow_html=True
                    )

                    # Preview of book covers in this folder
                    sample_books = db.get_books_by_genre(cat).head(4)
                    if not sample_books.empty:
                        preview_cols = st.columns(4)
                        for idx, (_, b_row) in enumerate(sample_books.iterrows()):
                            with preview_cols[idx]:
                                render_cover_image(b_row)
                    
                    # Reading Breakdown Chips
                    st.markdown(
                        f"""
                        <div style="display: flex; flex-wrap: wrap; gap: 8px; margin: 12px 0 8px 0;">
                            <span style="font-family: 'Plus Jakarta Sans', sans-serif; font-size: 0.76rem; background: #101c29; border: 1px solid #3c546b; color: #a8cae6; padding: 2px 8px; border-radius: 4px;">
                                📖 {w_count} in Queue
                            </span>
                            <span style="font-family: 'Plus Jakarta Sans', sans-serif; font-size: 0.76rem; background: #2b1d0e; border: 1px solid #824f24; color: #f5cb98; padding: 2px 8px; border-radius: 4px;">
                                ⏳ {o_count} Ongoing
                            </span>
                            <span style="font-family: 'Plus Jakarta Sans', sans-serif; font-size: 0.76rem; background: #0f2416; border: 1px solid #2f693f; color: #9ce6b5; padding: 2px 8px; border-radius: 4px;">
                                ✅ {r_count} Completed
                            </span>
                        </div>
                        """,
                        unsafe_allow_html=True
                    )

                    # Folder page progress
                    if t_pages > 0:
                        st.progress(min(1.0, max(0.0, r_pages / t_pages)))
                        st.caption(f"📊 **Pages Read:** {r_pages:,} of {t_pages:,} pages ({pct}%)")
                    else:
                        st.caption(f"📊 **Pages Read:** {r_pages:,} pages")

                    st.write("")
                    if st.button(
                        f"📂 Open {cat} Folder ({t_books} volumes)", 
                        key=f"btn_open_folder_{cat}", 
                        type="primary", 
                        use_container_width=True
                    ):
                        st.session_state["opened_category_folder"] = cat
                        st.rerun()

    # ================= OPENED FOLDER VIEW (ALL DETAILS) =================
    else:
        current_cat = opened_folder
        icon = get_genre_icon(current_cat)
        
        # Navigation bar inside folder
        c_back, c_pills = st.columns([1.2, 3.2])
        with c_back:
            if st.button("⬅️ All Category Folders", key="btn_back_folders", use_container_width=True):
                st.session_state["opened_category_folder"] = None
                st.rerun()
        
        with c_pills:
            # Quick switch to any other category
            summary_df = db.get_category_summary()
            all_cat_names = summary_df['category'].tolist()
            if current_cat in all_cat_names:
                selected_cat_pill = st.pills(
                    "Switch Folder",
                    all_cat_names,
                    default=current_cat,
                    key="pills_quick_folder_switch",
                    label_visibility="collapsed"
                )
                if selected_cat_pill and selected_cat_pill != current_cat:
                    st.session_state["opened_category_folder"] = selected_cat_pill
                    st.rerun()

        # Detailed Folder Dossier Banner
        cat_books_all = db.get_books_by_genre(current_cat)
        tot_in_cat = len(cat_books_all)
        w_in_cat = len(cat_books_all[cat_books_all['status'] == 'Want to Read'])
        o_in_cat = len(cat_books_all[cat_books_all['status'] == 'Ongoing'])
        r_in_cat = len(cat_books_all[cat_books_all['status'] == 'Read'])
        tot_pg_cat = int(cat_books_all['total_pages'].sum()) if not cat_books_all.empty else 0
        read_pg_cat = int(cat_books_all['current_page'].sum()) if not cat_books_all.empty else 0
        pct_cat = int((read_pg_cat / tot_pg_cat) * 100) if tot_pg_cat > 0 else 0

        st.markdown(
            f"""
            <div style="background: linear-gradient(145deg, #2a1c12 0%, #1a1008 100%); border: 1.5px solid #6b472c; border-radius: 10px; padding: 18px 22px; margin: 12px 0 20px 0; box-shadow: 0 6px 18px rgba(0,0,0,0.55), inset 0 1px 0 rgba(255,230,190,0.15);">
                <div style="display: flex; align-items: baseline; justify-content: space-between; flex-wrap: wrap; gap: 8px;">
                    <div>
                        <span style="font-family: 'Cinzel', serif; font-size: 1.6rem; font-weight: 700; color: #faede0; letter-spacing: 0.8px;">
                            📂 {icon} {current_cat} Dossier
                        </span>
                        <div style="font-family: 'Playfair Display', Georgia, serif; font-style: italic; font-size: 0.95rem; color: #cf9a6b; margin-top: 2px;">
                            Showing all classified volumes and reading progress records
                        </div>
                    </div>
                    <span style="font-family: 'Cinzel', serif; font-size: 0.85rem; font-weight: 600; color: #faede0; background: linear-gradient(180deg, #442a17 0%, #2a190d 100%); padding: 5px 14px; border-radius: 6px; border: 1px solid #784825;">
                        {tot_in_cat} {'Volume' if tot_in_cat == 1 else 'Volumes'} in Category
                    </span>
                </div>
                <div style="display: flex; flex-wrap: wrap; gap: 12px; margin-top: 14px; padding-top: 12px; border-top: 1px solid #4a301f;">
                    <span style="font-size: 0.82rem; color: #eeddcc;">📖 <strong>Queue:</strong> {w_in_cat}</span>
                    <span style="color: #664429;">•</span>
                    <span style="font-size: 0.82rem; color: #eeddcc;">⏳ <strong>In Progress:</strong> {o_in_cat}</span>
                    <span style="color: #664429;">•</span>
                    <span style="font-size: 0.82rem; color: #eeddcc;">✅ <strong>Completed:</strong> {r_in_cat}</span>
                    <span style="color: #664429;">•</span>
                    <span style="font-size: 0.82rem; color: #eeddcc;">📊 <strong>Reading Completion:</strong> {read_pg_cat:,} / {tot_pg_cat:,} pages ({pct_cat}%)</span>
                </div>
            </div>
            """,
            unsafe_allow_html=True
        )

        # Filters and Sort inside this folder
        f_col1, f_col2 = st.columns([3, 1.4])
        with f_col1:
            st.markdown(
                """
                <span style="font-family: 'Cinzel', serif; font-size: 0.88rem; font-weight: 700; color: #eeddcc; letter-spacing: 0.6px;">
                    FILTER BY READING STATUS:
                </span>
                """,
                unsafe_allow_html=True
            )
            cat_status_choice = st.pills(
                "Filter Status",
                ["All Statuses", "Want to Read", "Ongoing", "Read"],
                default="All Statuses",
                key="cat_filter_status_pills",
                label_visibility="collapsed"
            )
            if cat_status_choice is None:
                cat_status_choice = "All Statuses"

        with f_col2:
            st.markdown(
                """
                <span style="font-family: 'Cinzel', serif; font-size: 0.88rem; font-weight: 700; color: #eeddcc; letter-spacing: 0.6px;">
                    🔤 ARRANGE / SORT:
                </span>
                """,
                unsafe_allow_html=True
            )
            cat_sort_choice = st.selectbox(
                "Sort Order in Folder",
                ["Title (A → Z)", "Author (A → Z)", "Title (Z → A)", "Progress (%)", "Page Count"],
                index=0,
                key="cat_sort_order_select",
                label_visibility="collapsed"
            )

        # Fetch sorted and filtered books in this category
        folder_books_df = db.get_books_by_genre(
            current_cat, 
            status_filter=cat_status_choice, 
            sort_order=cat_sort_choice
        )

        st.write("")
        if folder_books_df.empty:
            st.info(f"No volumes with status '{cat_status_choice}' found in the {current_cat} folder.")
        else:
            # Render book cards in 2 columns
            book_cols = st.columns(2)
            for b_idx, (_, b_row) in enumerate(folder_books_df.iterrows()):
                with book_cols[b_idx % 2]:
                    render_folder_book_card(b_row, key_prefix="fld")

        st.write("")
        if st.button("⬅️ Return to All Category Folders", key="btn_bottom_back_folders", use_container_width=True):
            st.session_state["opened_category_folder"] = None
            st.rerun()



# ================= SIDEBAR: CATALOG & ACQUISITIONS =================
with st.sidebar:
    sb_dname = current_user.get('display_name', 'Reader') if current_user else 'Reader'
    sb_uname = current_user.get('username', 'reader') if current_user else 'reader'
    st.markdown(
        f"""
        <div style="background: linear-gradient(145deg, #2b1d14 0%, #1a1008 100%); border: 1.5px solid #6b472c; border-radius: 8px; padding: 12px 14px; margin-bottom: 12px; box-shadow: 0 4px 12px rgba(0,0,0,0.5);">
            <div style="font-family: 'Cinzel', serif; font-size: 0.72rem; color: #cf9a6b; letter-spacing: 1px;">ACTIVE READER</div>
            <div style="font-family: 'Cinzel', serif; font-size: 1.15rem; font-weight: 700; color: #f7ebe0; margin-top: 2px;">👤 {sb_dname}</div>
            <div style="font-size: 0.78rem; color: #a88970;">@{sb_uname}</div>
        </div>
        """,
        unsafe_allow_html=True
    )
    if st.button("🚪 Sign Out / Switch Reader", key="btn_sidebar_logout", use_container_width=True):
        st.session_state.pop("logged_in_user", None)
        st.session_state["save_toast"] = "Signed out successfully."
        st.rerun()

    st.markdown("<div style='height: 1px; background: #5a3c25; margin: 12px 0 16px 0;'></div>", unsafe_allow_html=True)

    st.markdown(
        """
        <div style="font-family: 'Cinzel', serif; font-size: 1.25rem; font-weight: 700; color: #faede0; margin-bottom: 12px; padding-bottom: 8px; border-bottom: 2px solid #5a3a22; letter-spacing: 0.5px;">
            📚 CATALOG A NEW VOLUME
        </div>
        """,
        unsafe_allow_html=True
    )
    
    # Display any feedback message from previous submission
    if "form_msg" in st.session_state:
        msg_type, msg_text = st.session_state.pop("form_msg")
        if msg_type == "success":
            st.success(msg_text)
        elif msg_type == "warning":
            st.warning(msg_text)

    # Input fields
    new_title = st.text_input("Title", key="input_title", placeholder="e.g. The Striker")
    new_author = st.text_input("Author", key="input_author", placeholder="e.g. Ana Huang")
    new_status = st.selectbox("Shelf Section", ["Want to Read", "Ongoing", "Read"], key="input_status")
    
    # Fetch details (cover + suggested page count + suggested genre)
    detected_details = None
    online_cover = None
    if new_title.strip() and new_author.strip():
        with st.spinner("Searching library registry..."):
            detected_details = fetch_book_details(new_title.strip(), new_author.strip())
        
        if detected_details and detected_details.get("cover_url"):
            online_cover = detected_details["cover_url"]
            st.markdown("**Volume Binding Preview (Online):**")
            st.image(online_cover, use_container_width=True)
            st.markdown('<div class="bookshelf-plinth"></div>', unsafe_allow_html=True)
        else:
            st.info("ℹ️ No online cover found automatically. You can upload a picture below!")

    # Picture upload option if not found online or if user wants custom cover
    # Automatically expanded if no online cover was found and title is entered
    expand_cover_upload = (online_cover is None and bool(new_title.strip()))
    with st.expander("🖼️ Add / Upload Cover Picture", expanded=expand_cover_upload):
        uploaded_cover_file = st.file_uploader(
            "Upload picture from your device", 
            type=["jpg", "jpeg", "png", "webp"], 
            key="input_cover_file",
            help="Upload an image file (JPG, PNG, WEBP) from your device"
        )
        if uploaded_cover_file is not None:
            st.markdown("**Uploaded Picture Preview:**")
            st.image(uploaded_cover_file, use_container_width=True)
            st.markdown('<div class="bookshelf-plinth"></div>', unsafe_allow_html=True)

        custom_url = st.text_input(
            "Or enter Image URL", 
            key="input_custom_url", 
            placeholder="https://..."
        )
        if custom_url.strip() and uploaded_cover_file is None:
            st.image(custom_url.strip(), caption="URL Preview", use_container_width=True)

    # Suggested total pages and genre tracking
    if "last_detected_book" not in st.session_state:
        st.session_state.last_detected_book = ""
        
    current_book_key = f"{new_title.strip().lower()}|{new_author.strip().lower()}"
    if detected_details and current_book_key != st.session_state.last_detected_book:
        st.session_state.last_detected_book = current_book_key
        if detected_details.get("total_pages", 0) > 0:
            st.session_state.input_total_pages = int(detected_details["total_pages"])
        if detected_details.get("suggested_genre"):
            sg = detected_details["suggested_genre"]
            if sg in POPULAR_GENRES:
                st.session_state.input_genre_select = sg

    # Genre / Theme selection
    default_genre_idx = 0
    if "input_genre_select" in st.session_state and st.session_state.input_genre_select in POPULAR_GENRES:
        default_genre_idx = POPULAR_GENRES.index(st.session_state.input_genre_select)

    genre_choice = st.selectbox(
        "Book Theme / Genre", 
        POPULAR_GENRES, 
        index=default_genre_idx,
        key="input_genre_select",
        help="Select or specify the primary theme/genre"
    )

    custom_genre_val = ""
    if genre_choice == "Custom...":
        custom_genre_val = st.text_input(
            "Specify Custom Theme", 
            key="input_custom_genre", 
            placeholder="e.g. Dark Academia, Cyberpunk"
        )

    total_pages_val = st.number_input(
        "Total Pages", 
        min_value=0, 
        value=st.session_state.get("input_total_pages", 0), 
        step=1, 
        key="input_total_pages",
        help="Estimated book length (auto-detected when possible)"
    )

    current_page_val = 0
    if new_status == "Ongoing":
        current_page_val = st.number_input(
            "Current Page", 
            min_value=0, 
            max_value=max(total_pages_val, 1) if total_pages_val > 0 else 10000, 
            value=0, 
            step=1, 
            key="input_current_page",
            help="What page number are you starting or currently at?"
        )

    def handle_add():
        t = st.session_state.get("input_title", "").strip()
        a = st.session_state.get("input_author", "").strip()
        s = st.session_state.get("input_status", "Want to Read")
        g_sel = st.session_state.get("input_genre_select", "Fiction")
        g_cust = st.session_state.get("input_custom_genre", "").strip()
        final_g = g_cust if (g_sel == "Custom..." and g_cust) else (g_sel if g_sel != "Custom..." else "Fiction")

        tot = st.session_state.get("input_total_pages", 0)
        curr = st.session_state.get("input_current_page", 0) if s == "Ongoing" else (tot if s == "Read" else 0)
        
        # Cover resolution: 1. Uploaded file -> 2. Custom URL -> 3. Online detected
        uploaded_file = st.session_state.get("input_cover_file")
        custom_c = st.session_state.get("input_custom_url", "").strip()
        
        if not t or not a:
            st.session_state["form_msg"] = ("warning", "Please fill in both the title and author.")
            return

        final_cover = None
        if uploaded_file is not None:
            final_cover = save_uploaded_cover(uploaded_file)
        elif custom_c:
            final_cover = custom_c
        else:
            details = fetch_book_details(t, a)
            if details and details.get("cover_url"):
                final_cover = details["cover_url"]

        details = fetch_book_details(t, a)
        final_total = tot if tot > 0 else (details["total_pages"] if details else 0)
        final_curr = curr if s == "Ongoing" else (final_total if s == "Read" else 0)

        db.add_book(t, a, s, final_cover, current_page=final_curr, total_pages=final_total, genre=final_g)
        st.session_state["form_msg"] = ("success", f"Cataloged '{t}' under {final_g}!")
        # Clear input fields
        st.session_state["input_title"] = ""
        st.session_state["input_author"] = ""
        st.session_state["input_custom_url"] = ""
        st.session_state["input_custom_genre"] = ""
        st.session_state["last_detected_book"] = ""

    st.button("Add to Library", type="primary", use_container_width=True, on_click=handle_add)

    # ================= SIDEBAR: SETTINGS & ACCOUNT MANAGEMENT =================
    st.markdown("<div style='height: 1px; background: #5a3c25; margin: 26px 0 14px 0;'></div>", unsafe_allow_html=True)
    with st.expander("⚙️ Settings"):
        st.markdown(
            """
            <div style="font-family: 'Cinzel', serif; font-size: 0.88rem; font-weight: 700; color: #eeddcc; margin-bottom: 8px;">
                🔑 CHANGE / RENEW PASSWORD
            </div>
            """,
            unsafe_allow_html=True
        )
        sb_curr_pw = st.text_input("Current Password", type="password", key="sb_curr_pw")
        sb_new_pw1 = st.text_input("New Password", type="password", key="sb_new_pw1")
        sb_new_pw2 = st.text_input("Confirm New Password", type="password", key="sb_new_pw2")
        if st.button("Update Password", key="sb_btn_update_pw", use_container_width=True):
            if not sb_curr_pw:
                st.error("Please enter your current password.")
            elif not sb_new_pw1 or len(sb_new_pw1) < 4:
                st.error("New password must be at least 4 characters.")
            elif sb_new_pw1 != sb_new_pw2:
                st.error("New passwords do not match.")
            else:
                ok, msg = db.change_password(current_user["id"], sb_curr_pw, sb_new_pw1)
                if ok:
                    st.success(msg)
                else:
                    st.error(msg)

        st.markdown("<div style='height: 1px; background: #4a2818; margin: 18px 0 14px 0;'></div>", unsafe_allow_html=True)

        st.markdown(
            """
            <div style="font-family: 'Cinzel', serif; font-size: 0.88rem; font-weight: 700; color: #e57373; margin-bottom: 4px;">
                ⚠️ DANGER ZONE: DELETE ACCOUNT
            </div>
            <div style="font-size: 0.78rem; color: #cf9a6b; margin-bottom: 8px;">
                Permanently erase your reader profile and all your cataloged books. This action cannot be undone.
            </div>
            """,
            unsafe_allow_html=True
        )
        del_pw = st.text_input("Confirm Password to Delete", type="password", key="sb_del_acc_pw")
        del_confirm = st.checkbox("I understand that all my books will be permanently erased", key="sb_del_chk")
        
        if st.button("🗑️ Delete My Account", key="sb_btn_del_acc", type="primary", use_container_width=True):
            if not del_pw:
                st.error("Please enter your password to confirm deletion.")
            elif not del_confirm:
                st.warning("Please check the confirmation box to proceed.")
            else:
                ok, msg = db.delete_user_account(current_user["id"], del_pw)
                if ok:
                    st.session_state.pop("logged_in_user", None)
                    st.session_state.pop("opened_category_folder", None)
                    st.session_state["save_toast"] = "Your account has been permanently deleted."
                    st.rerun()
                else:
                    st.error(msg)


if nav_view == NAV_BOOKCASES:
    # ================= THEME / GENRE FILTER & ALPHABETICAL SORTING =================
    existing_genres = db.get_all_genres()
    filter_options = ["All Themes"] + sorted(list(set(existing_genres)))

    filter_col, sort_col = st.columns([3.3, 1.4])

    with filter_col:
        st.markdown(
            """
            <div style="display: flex; align-items: center; justify-content: space-between; margin-bottom: 6px;">
                <span style="font-family: 'Cinzel', serif; font-size: 0.92rem; font-weight: 700; color: #eeddcc; letter-spacing: 0.8px;">
                    🏷️ FILTER BY THEME / GENRE:
                </span>
            </div>
            """,
            unsafe_allow_html=True
        )
        selected_theme = st.pills(
            "Filter by Theme", 
            filter_options, 
            default="All Themes", 
            label_visibility="collapsed",
            key="library_theme_pills"
        )
        if selected_theme is None:
            selected_theme = "All Themes"

    with sort_col:
        st.markdown(
            """
            <div style="display: flex; align-items: center; justify-content: space-between; margin-bottom: 6px;">
                <span style="font-family: 'Cinzel', serif; font-size: 0.92rem; font-weight: 700; color: #eeddcc; letter-spacing: 0.8px;">
                    🔤 ARRANGE / SORT:
                </span>
            </div>
            """,
            unsafe_allow_html=True
        )
        sort_choice = st.selectbox(
            "Sort Order",
            ["Title (A → Z)", "Author (A → Z)", "Title (Z → A)"],
            index=0,
            label_visibility="collapsed",
            key="library_sort_select"
        )

    if selected_theme != "All Themes":
        st.caption(f"Displaying volumes classified under **{selected_theme}** • Arranged by **{sort_choice}**")
    else:
        st.caption(f"Displaying all volumes • Arranged in alphabetical order (**{sort_choice}**)")

    st.write("")
    # ================= TOP SECTION: Want to Read & Ongoing (2 Classical Bookcase Bays) =================
    col1, col2 = st.columns(2)

    with col1:
        st.markdown(
            """
            <div style="display: flex; align-items: baseline; justify-content: space-between; margin-bottom: 12px; border-bottom: 1px solid #5a3c25; padding-bottom: 6px;">
                <span style="font-family: 'Cinzel', serif; font-size: 1.35rem; font-weight: 700; color: #faede0; letter-spacing: 0.5px;">
                    📖 Want to Read
                </span>
                <span style="font-family: 'Cinzel', serif; font-size: 0.78rem; color: #c49265; letter-spacing: 1px;">
                    BAY I • QUEUE
                </span>
            </div>
            """,
            unsafe_allow_html=True
        )
        to_read_df = db.get_books("Want to Read", genre_filter=selected_theme, sort_order=sort_choice)
    
        if not to_read_df.empty:
            for _, row in to_read_df.iterrows():
                render_want_to_read_card(row)
        else:
            if selected_theme != "All Themes":
                st.info(f"No '{selected_theme}' volumes in queue.")
            else:
                st.info("Your reading queue is empty.")

    with col2:
        st.markdown(
            """
            <div style="display: flex; align-items: baseline; justify-content: space-between; margin-bottom: 12px; border-bottom: 1px solid #5a3c25; padding-bottom: 6px;">
                <span style="font-family: 'Cinzel', serif; font-size: 1.35rem; font-weight: 700; color: #faede0; letter-spacing: 0.5px;">
                    ⏳ Ongoing
                </span>
                <span style="font-family: 'Cinzel', serif; font-size: 0.78rem; color: #c49265; letter-spacing: 1px;">
                    BAY II • CURRENT STUDY
                </span>
            </div>
            """,
            unsafe_allow_html=True
        )
        ongoing_df = db.get_books("Ongoing", genre_filter=selected_theme, sort_order=sort_choice)
    
        if not ongoing_df.empty:
            for _, row in ongoing_df.iterrows():
                render_ongoing_card(row)
        else:
            if selected_theme != "All Themes":
                st.info(f"No '{selected_theme}' volumes currently in progress.")
            else:
                st.info("No books currently in progress.")

    # ================= BOTTOM SECTION: Already Read (Grand Lower Shelf - Full Width Rectangle) =================
    st.markdown(
        """
        <div style="margin-top: 36px; margin-bottom: 16px;">
            <div style="display: flex; align-items: baseline; justify-content: space-between; border-bottom: 1px solid #5a3c25; padding-bottom: 6px;">
                <span style="font-family: 'Cinzel', serif; font-size: 1.45rem; font-weight: 700; color: #faede0; letter-spacing: 0.6px;">
                    ✅ Already Read
                </span>
                <span style="font-family: 'Cinzel', serif; font-size: 0.8rem; color: #c49265; letter-spacing: 1px;">
                    LOWER ARCHIVE • COMPLETED VOLUMES
                </span>
            </div>
            <div style="height: 8px; background: linear-gradient(180deg, #b8804c 0%, #87552e 35%, #59351a 100%); border-radius: 2px 2px 4px 4px; margin-top: 8px; box-shadow: 0 6px 14px rgba(0,0,0,0.65), inset 0 1px 0 rgba(255, 235, 195, 0.45);"></div>
        </div>
        """,
        unsafe_allow_html=True
    )

    read_df = db.get_books("Read", genre_filter=selected_theme, sort_order=sort_choice)

    if not read_df.empty:
        if len(read_df) == 1:
            # Full-width rectangular book shelf card matching top section width
            row = read_df.iloc[0]
            with st.container(border=True):
                c_img, c_info, c_action = st.columns([0.7, 3.2, 1.3])
                with c_img:
                    render_cover_image(row)
                with c_info:
                    st.subheader(row['title'])
                    st.write(f"**Author:** {row['author']}")
                    st.markdown(render_genre_badge(row.get('genre')), unsafe_allow_html=True)
                
                    tot = int(row['total_pages']) if pd.notna(row['total_pages']) else 0
                    if tot > 0:
                        st.caption(f"🏆 Completed Archive • {tot} pages read")
                    else:
                        st.caption("🏆 Completed Archive")
                
                    with st.expander("⚙️ Edit volume details & cover picture"):
                        ed_c1, ed_c2 = st.columns(2)
                        with ed_c1:
                            new_tot = st.number_input("Total pages", min_value=0, value=tot, step=1, key=f"tot_r_{row['id']}")
                        with ed_c2:
                            current_g = row.get('genre', 'Fiction')
                            all_g = [g for g in POPULAR_GENRES if g != "Custom..."]
                            if current_g not in all_g:
                                all_g.append(current_g)
                            g_idx = all_g.index(current_g) if current_g in all_g else 0
                            new_g = st.selectbox("Theme / Genre", all_g, index=g_idx, key=f"genre_r_{row['id']}")
                    
                        st.markdown("**Update Cover Picture:**")
                        new_cover_file = st.file_uploader(
                            "Upload picture file", 
                            type=["jpg", "jpeg", "png", "webp"], 
                            key=f"file_cov_r_{row['id']}"
                        )
                        new_cover_url = st.text_input(
                            "Or enter image URL", 
                            value=str(row['cover_url']) if (row.get('cover_url') and str(row['cover_url']).startswith('http')) else "", 
                            key=f"url_cov_r_{row['id']}"
                        )

                        if st.button("Save Changes", key=f"save_r_{row['id']}", use_container_width=True):
                            db.update_total_pages(row['id'], new_tot)
                            db.update_genre(row['id'], new_g)
                            if new_cover_file is not None:
                                saved = save_uploaded_cover(new_cover_file)
                                if saved:
                                    db.update_cover(row['id'], saved)
                            elif new_cover_url.strip():
                                db.update_cover(row['id'], new_cover_url.strip())
                            st.toast(f"Updated '{row['title']}'!")
                            st.rerun()

                with c_action:
                    st.write("")
                    if st.button("Read Again", key=f"read_again_{row['id']}", use_container_width=True):
                        db.update_status(row['id'], "Ongoing")
                        db.update_page(row['id'], 1)
                        st.rerun()
                    if st.button("Delete", key=f"del_read_{row['id']}", use_container_width=True):
                        db.delete_book(row['id'])
                        st.rerun()
        else:
            # Two-column rectangular shelf grid matching the width of the top columns
            r_cols = st.columns(2)
            for idx, row in read_df.iterrows():
                with r_cols[idx % 2]:
                    with st.container(border=True):
                        c_img, c_info = st.columns([1, 2.5])
                        with c_img:
                            render_cover_image(row)
                        with c_info:
                            st.subheader(row['title'])
                            st.write(f"**Author:** {row['author']}")
                            st.markdown(render_genre_badge(row.get('genre')), unsafe_allow_html=True)
                        
                            tot = int(row['total_pages']) if pd.notna(row['total_pages']) else 0
                            if tot > 0:
                                st.caption(f"🏆 Completed Archive • {tot} pages read")
                            else:
                                st.caption("🏆 Completed Archive")
                        
                            with st.expander("⚙️ Edit volume details & cover picture"):
                                ed_c1, ed_c2 = st.columns(2)
                                with ed_c1:
                                    new_tot = st.number_input("Total pages", min_value=0, value=tot, step=1, key=f"tot_r_{row['id']}")
                                with ed_c2:
                                    current_g = row.get('genre', 'Fiction')
                                    all_g = [g for g in POPULAR_GENRES if g != "Custom..."]
                                    if current_g not in all_g:
                                        all_g.append(current_g)
                                    g_idx = all_g.index(current_g) if current_g in all_g else 0
                                    new_g = st.selectbox("Theme / Genre", all_g, index=g_idx, key=f"genre_r_{row['id']}")
                            
                                st.markdown("**Update Cover Picture:**")
                                new_cover_file = st.file_uploader(
                                    "Upload picture file", 
                                    type=["jpg", "jpeg", "png", "webp"], 
                                    key=f"file_cov_r_{row['id']}"
                                )
                                new_cover_url = st.text_input(
                                    "Or enter image URL", 
                                    value=str(row['cover_url']) if (row.get('cover_url') and str(row['cover_url']).startswith('http')) else "", 
                                    key=f"url_cov_r_{row['id']}"
                                )

                                if st.button("Save Changes", key=f"save_r_{row['id']}", use_container_width=True):
                                    db.update_total_pages(row['id'], new_tot)
                                    db.update_genre(row['id'], new_g)
                                    if new_cover_file is not None:
                                        saved = save_uploaded_cover(new_cover_file)
                                        if saved:
                                            db.update_cover(row['id'], saved)
                                    elif new_cover_url.strip():
                                        db.update_cover(row['id'], new_cover_url.strip())
                                    st.toast(f"Updated '{row['title']}'!")
                                    st.rerun()

                            st.write("")
                            b1, b2 = st.columns(2)
                            with b1:
                                if st.button("Read Again", key=f"read_again_{row['id']}", use_container_width=True):
                                    db.update_status(row['id'], "Ongoing")
                                    db.update_page(row['id'], 1)
                                    st.rerun()
                            with b2:
                                if st.button("Delete", key=f"del_read_{row['id']}", use_container_width=True):
                                    db.delete_book(row['id'])
                                    st.rerun()
    else:
        if selected_theme != "All Themes":
            st.info(f"No completed '{selected_theme}' volumes found.")
        else:
            st.info("No completed volumes on your lower shelf archive yet.")
else:
    # ================= CATEGORY FOLDERS SUMMARY VIEW =================
    render_category_folders_summary_page(db)
