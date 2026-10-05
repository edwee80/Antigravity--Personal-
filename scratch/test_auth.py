import sqlite3
import hashlib
import os
import hmac

def hash_pw(password: str) -> str:
    salt = os.urandom(16).hex()
    dk = hashlib.pbkdf2_hmac('sha256', password.encode('utf-8'), salt.encode('utf-8'), 100000)
    return f"{salt}:{dk.hex()}"

def verify_pw(password: str, stored: str) -> bool:
    try:
        salt, dk_hex = stored.split(':')
        dk = hashlib.pbkdf2_hmac('sha256', password.encode('utf-8'), salt.encode('utf-8'), 100000)
        return hmac.compare_digest(dk.hex(), dk_hex)
    except Exception as e:
        print("verify error:", e)
        return False

# Test hashing
pw = "edrey123"
hashed = hash_pw(pw)
print("Hashed:", hashed)
print("Verify correct:", verify_pw(pw, hashed))
print("Verify wrong:", verify_pw("wrong", hashed))
