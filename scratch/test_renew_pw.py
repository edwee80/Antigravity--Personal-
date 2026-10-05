import sqlite3
from books import BookDatabase, hash_password, verify_password

db = BookDatabase()

# Test 1: update_password (forgot password flow)
print("--- Test update_password ---")
ok, res = db.update_password("edrey", "newsecret123")
print("Update pw success:", ok, res)

# Verify login with new password
ok_login, user = db.authenticate_user("edrey", "newsecret123")
print("Login with new pw:", ok_login, user)

# Verify old password no longer works
ok_old, _ = db.authenticate_user("edrey", "edrey123")
print("Old pw rejected:", not ok_old)

# Test 2: change_password (logged-in flow)
print("\n--- Test change_password ---")
ok_chg, msg = db.change_password(user["id"], "wrong", "anotherpass1")
print("Change with wrong current pw fails:", not ok_chg, msg)

ok_chg2, msg2 = db.change_password(user["id"], "newsecret123", "edrey123")
print("Change back to edrey123 succeeds:", ok_chg2, msg2)

# Verify back to edrey123
ok_final, _ = db.authenticate_user("edrey", "edrey123")
print("Final login with edrey123 works:", ok_final)
