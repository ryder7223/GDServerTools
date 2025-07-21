import requests
import base64
import sys

def encode_desc(desc):
    b64 = base64.urlsafe_b64encode(desc)
    return b64

def main():
    print("Update Geometry Dash Level Description")
    level_id = input("Enter the level ID: ").strip()
    desc = input("Enter the new description: ").strip().encode("utf-8")
    level_desc = encode_desc(desc).decode("utf-8")

    data = {
        "accountID": "",
        "gjp2": "",
        "levelID": level_id,
        "levelDesc": level_desc,
        "secret": "Wmfd2893gb7",
    }
    
    headers = {
        "User-Agent": ""
    }

    url = "http://www.boomlings.com/database/updateGJDesc20.php"
    try:
        resp = requests.post(url, data=data, headers=headers)
        print("Server response:", resp.text)
    except Exception as e:
        print("Error sending request:", e)

if __name__ == "__main__":
    main()
    input()