import hashlib

def generate_gjp2(password: str, salt: str = "mI29fmAnxgTs") -> str:
    return hashlib.sha1((password + salt).encode()).hexdigest()

if __name__ == "__main__":
    password = input("Enter your Geometry Dash account password: ")
    gjp2 = generate_gjp2(password)
    print(f"Your gjp2 hash: {gjp2}") 
input()