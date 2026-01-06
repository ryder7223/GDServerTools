import requests

url = "http://www.boomlings.com/database/getGJLevels21.php"

startID = 123306097
endID = startID - 101
IDs = [i for i in range(endID, startID)]
IDs = ",".join(map(str, IDs))

data = {
    "secret": "Wmfd2893gb7",
    "str": IDs,
    "type": 26
}

headers = {
    "User-Agent": ""
}

response = requests.post(url, data=data, headers=headers)

data = response.text
levels = data.split("|")

levelIds = []
for level in levels:
    parts = level.split("#")[0].split(":")
    parsed = {parts[i]: parts[i + 1] for i in range(0, len(parts) - 1, 2)}
    if "1" in parsed:
        levelIds.append(int(parsed["1"]))

levelIds.sort()

missing = []
for i in range(len(levelIds) - 1):
    currentId = levelIds[i]
    nextId = levelIds[i + 1]
    if nextId - currentId > 1:
        for missingId in range(currentId + 1, nextId):
            missing.append(missingId)

print(missing)
input()