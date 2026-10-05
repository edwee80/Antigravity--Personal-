from books import BookDatabase

db = BookDatabase()

print("--- Testing Edrey Authentication ---")
ok, res = db.authenticate_user("edrey", "edrey123")
print("Edrey login ok:", ok, res)

ok_fail, res_fail = db.authenticate_user("edrey", "wrong")
print("Edrey wrong pass fail:", not ok_fail, res_fail)

print("\n--- Testing Sarah Registration & Auth ---")
ok_reg, res_reg = db.register_user("sarah", "sarah123", "Sarah")
print("Sarah register ok:", ok_reg, res_reg)
if not ok_reg and "already taken" in str(res_reg):
    ok_auth, res_auth = db.authenticate_user("sarah", "sarah123")
    print("Sarah existing user login ok:", ok_auth, res_auth)
    sarah_id = res_auth["id"]
else:
    sarah_id = res_reg["id"]

print("\n--- Testing Isolation ---")
edrey_stats = db.get_library_overall_stats(user_id=1)
sarah_stats = db.get_library_overall_stats(user_id=sarah_id)
print("Edrey total books:", edrey_stats["total_books"])
print("Sarah total books:", sarah_stats["total_books"])

# Add a book specifically to Sarah's library
db.add_book("Atomic Habits", "James Clear", "Want to Read", None, 0, 320, "Self-Help & Growth", user_id=sarah_id)

edrey_stats_after = db.get_library_overall_stats(user_id=1)
sarah_stats_after = db.get_library_overall_stats(user_id=sarah_id)
print("\nAfter Sarah added a book:")
print("Edrey total books (should remain 6):", edrey_stats_after["total_books"])
print("Sarah total books (should be 1):", sarah_stats_after["total_books"])

sarah_books = db.get_books("Want to Read", user_id=sarah_id)
print("Sarah want to read titles:", sarah_books["title"].tolist())

edrey_books = db.get_books("Want to Read", user_id=1)
print("Edrey want to read titles:", edrey_books["title"].tolist())
