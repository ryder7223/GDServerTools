# GDServerTools
About 12.7k lines of code I made for Geometry Dash tools.

Please consider starring this if you like it!

---

## [GDReq.py](https://github.com/ryder7223/GDServerTools/blob/main/GDReq.py)
## Installing GDReq
```code
pip install -i https://test.pypi.org/simple/ GDReq
```
GDReq is an API wrapper and response parser designed to make interacting with the Geometry Dash servers through python simpler by creating as much abstraction as possible from the usual difficult process of sending valid requests.
## Example usage:
```py
# Original

import requests

data = {
    "accountID": 12345,
    "targetAccountID": 12345,
    "gjp2": "***",
    "commentID": 54321,
    "secret": "Wmfd2893gb7"
}

headers = {
    "User-Agent": ""
}

r = requests.post('https://www.boomlings.com/database/deleteGJAccComment20.php', data=data, headers=headers)
print(r.text)
input()

# With GDReq

import GDReq

r = GDReq.deleteGJAccComment20(12345, 12345, "***", 54321)
print(r)
input()
```

```py
# Original

import requests
import random
import base64
import string

def xorCipher(data, key):
    resultChars = []
    keyLength = len(key)
    for i, ch in enumerate(data):
        byteVal = ord(ch)
        xKey = ord(key[i % keyLength])
        resultChars.append(chr(byteVal ^ xKey))
    return "".join(resultChars)

def generateRn(length: int | None = None) -> int:
    numLength = length if length else random.randint(3,5)
    return int("".join(random.choices(string.digits, k=numLength)))

def generateUdid(
    start: int = 100_000,
    end: int = 100_000_000
) -> str:
    r = random.randint
    return (
         "S15"
         + str(r(start, end))
         + str(r(start, end))
         + str(r(start, end))
         + str(r(start, end))
    )

def generateChestMenuChk(
    minDigits: int = 10_000,
    maxDigits: int = 999_999
) -> str:
    prefix = "".join(random.choices("1234567890qwertyuiopasdfghjklzxcvbnmQWERTYUIOPASDFGHJKLZXCVBNM", k=5))
    num = str(random.randint(minDigits, maxDigits))
    xored = xorCipher(num, "59182")
    return prefix + base64.urlsafe_b64encode(xored.encode()).decode()


r1, r2 = [generateRn() for _ in range(2)]
chk = generateChestMenuChk()

data = {
    "accountID": 12345,
    "gjp2": "***",
    "chk": chk,
    "udid": generateUdid(),
    "secret": "Wmfd2893gb7",
    "r1": r1,
    "r2": r2
}

headers = {
    "User-Agent": ""
}

r = requests.post('https://www.boomlings.com/database/getGJRewards.php', data=data, headers=headers)
print(r.text)
input()

# With GDReq

import GDReq

r = GDReq.getGJRewards(12345, "***")
print(GDReq.Parse.getGJRewards(r))
input()
```



## [GDLevelInfo.py](https://github.com/ryder7223/GDServerTools/blob/main/GDLevelInfo.py)
GDLevelInfo takes a level id as input and returns statistics about the level, with an option in the script to toggle printing a table containing all object ids (with their respective block names) ordered by frequency.

### Example output
```
Level Information:
Creator Username: ryder7223
Level Name: hitbox test
Level ID: 86669948
Original ID: 0
Description: I hope you like this concept, and maybe use it yourself someday :)
Coins (Real): 0
Coins (Server): 0
Likes: 104
Downloads: 1043
Level Version: -1
Length: Short
Editor Time: 0h 0m 23s
Editor (C) Time: 0h 0m 0s
Uploaded: 3 years
Updated: 3 years
Game Version: 2.1
Requested Rating: -1
songIDs: 971534
Two-Player: No
Feature Score: 0
Level Size: 42.5 KB
Password: (none)
Object Count: 828

Object ID | Name                          | Count
----------+-------------------------------+------
1         | Black Gradient Square         | x599
507       | 3DL Top Middle                | x90
901       | Move Trigger                  | x57
8         | Black Gradient Spike          | x39
914       | Text                          | x11
1859      | Allow Head Collision Modifier | x10
211       | Colored Inner Square          | x9
132       | Large Pulsing Arrow 1         | x3
1007      | Alpha Trigger                 | x2
1049      | Toggle Trigger                | x2
1612      | Hide Player Trigger           | x1
13        | Ship Portal                   | x1
33        | Disable Ghost Trail           | x1
1744      | Grid Patterned Wide Slope     | x1
1743      | Grid Patterned Slope          | x1
12        | Cube Portal                   | x1
```
## [browseUnlisted.py](https://github.com/ryder7223/GDServerTools/blob/main/browseUnlisted.py)
browseUnlisted.py is a web-server which provides an interface for searching through a particular database containing level info.

The schema for the database is as follows:
```sql
CREATE TABLE "levels" (
    "ID"    INTEGER,
    "Name"  TEXT,
    "Username"  TEXT,
    "CreatorPoints" INTEGER,
    "Description"   TEXT,
    "Size"  TEXT,
    "songID"    TEXT,
    "OriginalID"    TEXT,
    "rCoins"    INTEGER,
    "sCoins"    INTEGER,
    "Version"   TEXT,
    "Length"    TEXT,
    "EditorTime"    INTEGER,
    "EditorCTime"   INTEGER,
    "RequestedRating"   TEXT,
    "TwoPlayer" TEXT,
    "ObjectCount"   INTEGER,
    "PlayerID"  TEXT,
    PRIMARY KEY("ID")
);
```
### Features
 - Downloading of levels and songs directly from the website `/download/<levelID>`, `/downloadSong/<songID>`
 - User authentication
 - Selective exclusion of search results based off id, title, and username
 - Exceptions to search exclusion based off the logged in user
 - Detailed logging of ips of users who download levels
 - Automatic conversion of level data to gmd files for download requests
 - Searching by the following parameters
   ```
   level_id
   name
   username
   description
   song_id
   original_id
   version
   length
   rcoins
   scoins
   min_editor_time
   max_editor_time
   editor_ctime
   requested_rating
   two_player
   min_object_count
   max_object_count
   player_id
   min_cp
   max_cp
   min_size
   max_size
   sort_by (id/creator_points/size)
   sort_order (ascending/descending)
   search_mode (contains/exclusive)
   case_sensitive
   page_size
   page
   ```
 - An API endpoint at `/api/search` which returns response data as json
 - Playing of songs by level id `/playID/<levelID>`
 - Playing of songs based off the current daily or weekly level `/currentDailySong`, `/currentWeeklySong`
 - Support for merging search results with external web-server instances




## [browseOldUnlisted.py](https://github.com/ryder7223/GDServerTools/blob/main/browseOldUnlisted.py)
Functionally identical to [browseUnlisted.py](https://github.com/ryder7223/GDServerTools/blob/main/browseUnlisted.py) but uses an external web-server for user authentication. Intended to be referenced by a "main" instance of browseUnlisted.py which uses this instance's API to serve extra results from another database.




## [buildImage.py](https://github.com/ryder7223/GDServerTools/blob/main/buildImage.py)
A very WIP script which takes GMD files as input and generates an image of the level.

### Required files
 - object.json
 - GJ_GameSheet-uhd.plist
 - GJ_GameSheet02-uhd.plist
 - GJ_GameSheet.plist
 - GJ_GameSheet02.plist
 - GJ_GameSheet-uhd.png
 - GJ_GameSheet02-uhd.png
 - GJ_GameSheet.png
 - GJ_GameSheet02.png

### What's missing?
The script does not properly handle multi-part-object rotation or colours.




## [findUnlisted.py](https://github.com/ryder7223/GDServerTools/blob/main/findUnlisted.py)
A program that runs forever until terminated which scans for new unlisted ids, and attempts to download them. Then it does the following:

 - Writes information about each level to a database
 - Adds to a csv containing creators, their respective creator points, and downloaded level ids
 - Saves it's live terminal output of downloads to timestamped log files.

### How does it work?
1. Loading a recent tab page.
2. Checking which ids are returned.
3. Looking for gaps between adjacent ids.
   These gaps are caused by levels being
   deleted or uploaded unlisted.
4. It then tries to download these levels.




## [findOldUnlisted.py](https://github.com/ryder7223/GDServerTools/blob/main/findOldUnlisted.py)
Does the same thing as findUnlisted.py, but it's method of scanning is different.

### How does it work?
1. Loading a recent tab page.
2. Requesting a 100 ID list for listed levels up to the newest id.
3. Checking which ids are returned.
4. Looking for gaps between adjacent ids. These gaps are caused by levels being deleted or uploaded unlisted.
5. It then tries to download these levels.
6. It then checks the recent tab until a new 100 levels are uploaded.
7. Finally it repeats with the 100 new ids.




## [editGDShare.py](https://github.com/ryder7223/GDServerTools/blob/main/editGDShare.py)
Allows for the editing, adding, and removing of k tags in gmd files.
