import requests

username = input("Enter your username: ")

url = "http://www.boomlings.com/database/getGJUsers20.php"

data = {
    "secret": "Wmfd2893gb7",
    "str": username
}

headers = {
    "User-Agent": ""
}

response = requests.post(url, data=data, headers=headers)
parts = response.text.split("#")[0].split(":")
parsed = {}

for i in range(0, len(parts) - 1, 2):
    key = parts[i]
    value = parts[i + 1]
    parsed[key] = value

accountID = parsed["16"]
print(f"Account ID: {accountID}")
input()