import hashlib
import os
import urllib.request
import random

"""
If this program is able to find your password using your GJP2, your password is very weak!
"""

ROCKYOU_URL = "https://github.com/brannondorsey/naive-hashcat/releases/download/data/rockyou.txt"
ROCKYOU_PATH = os.path.join(os.path.dirname(__file__), "rockyou.txt")
SALT = "mI29fmAnxgTs"

def generate_gjp2(password: str, salt: str = SALT) -> str:
    return hashlib.sha1((password + salt).encode()).hexdigest()

def ensure_rockyou():
    if not os.path.isfile(ROCKYOU_PATH):
        print("rockyou.txt not found. Downloading...")
        urllib.request.urlretrieve(ROCKYOU_URL, ROCKYOU_PATH)
        print("Downloaded rockyou.txt.")

def main():
    gjp2_input = input("Enter the gjp2 hash to crack: ").strip()
    ensure_rockyou()
    with open(ROCKYOU_PATH, encoding="utf-8", errors="ignore") as f:
        for i, line in enumerate(f, 1):
            password = line.rstrip("\n\r")
            if generate_gjp2(password) == gjp2_input:
                print(f"Password found: {password}")
                return
            if i % 100000 == 0 and random.randint(1,8) == 5:
                print(f"Checked {i} passwords...")
    print("Password not found in rockyou.txt.")

if __name__ == "__main__":
    main() 
input()