###################################
#       Using this program        #
#   may be considered unethical,  #
#   you are at fault for leaking  #
#       other peoples work        #
###################################

#####################
'''
How does this work?

This program finds unlisted ids by:
1. Loading a recent tab page.
2. Checking which ids are returned.
3. Looking for gaps between adjacent levels.
   These gaps are caused by levels being
   deleted or uploaded unlisted.
4. It then tries to download these levels.
5. It will then check if the creator of each level
   has creator points so that it's easier
   to find interesting levels.
6. All levels and logs are saved, so
   even if someone deletes their level, you'll
   have a copy.

You can use my other program levelDataToGMD.py to
convert any of these saved levels to gmd files
which can be imported into the game via the GDShare
mod, all you have to do is run it in the same
directory as the saved level files and every one
will be copied to a gmd file.
'''
#####################

import requests, random
from colorama import init, Fore
from time import sleep
import os
import re
import sys
from datetime import datetime

# --- Logger Setup ---
class Logger:
    def __init__(self, filename):
        self.terminal = sys.stdout
        self.log = open(filename, "a", encoding="utf-8")

    def write(self, message):
        self.terminal.write(message)
        self.log.write(message)

    def flush(self):
        # This flush method is needed for python 3 compatibility.
        # This helps logger to write in file in real time.
        self.terminal.flush()
        self.log.flush()

# Create a 'logs' directory if it doesn't exist
if not os.path.exists("logs"):
    os.makedirs("logs")

# Create a unique log file name with a timestamp
log_filename = f"logs/log_{datetime.now().strftime('%Y-%m-%d_%H-%M-%S')}.txt"
sys.stdout = Logger(log_filename)
# --- End of Logger Setup ---


init(autoreset=True)

Tries = 1
waitTime = 3

while True:
    found_ids = []
    used_pages = set()

    for _ in range(Tries):
        # Generate a unique random page number
        # Here we only use page 0, since it
        # yields the best results
        while True:
            randPage = random.randint(0,0)
            if randPage not in used_pages:
                used_pages.add(randPage)
                break
        url = "http://www.boomlings.com/database/getGJLevels21.php"

        data = {
            "secret": "Wmfd2893gb7",
            "type": "4",
            "page": randPage
        }

        headers = {
            "User-Agent": ""
        }

        print(f"[Request] Getting levels for page: {randPage}")
        response = requests.post(url, data=data, headers=headers)
        result = response.text
        splitLevels = result.split("|")
        level_ids = []
        for item in splitLevels:
            if item[:2] == "1:":
                # The level ID is after '1:' and before the next ':'
                parts = item.split(":")
                if len(parts) > 1:
                    try:
                        level_id = int(parts[1])
                        level_ids.append(level_id)
                    except ValueError:
                        pass

        if not level_ids:
            continue
        else:
            level_ids.sort()
            missing = []
            for i in range(len(level_ids) - 1):
                current_id = level_ids[i]
                next_id = level_ids[i + 1]
                if next_id - current_id > 1:
                    # There are missing IDs between current_id and next_id
                    for missing_id in range(current_id + 1, next_id):
                        missing.append(missing_id)
            if missing:
                check_url = "http://www.boomlings.com/database/downloadGJLevel22.php"
                for missing_id in missing:
                    check_data = {
                        "secret": "Wmfd2893gb7",
                        "levelID": missing_id
                    }
                    sleep(waitTime)
                    check_response = requests.post(check_url, data=check_data, headers=headers)
                    if check_response.text.strip() != "-1":
                        found_ids.append(missing_id)
                        # Extract the level title from the level data (key :2)
                        level_data = check_response.text
                        title = "unknown_title"
                        try:
                            # Find the value for key :2
                            parts = level_data.split(":2")
                            if len(parts) > 1:
                                # The value is after ':2' and before the next ':'
                                after = parts[1]
                                # Remove leading ':' if present
                                if after.startswith(":"):
                                    after = after[1:]
                                # The title ends at the next ':' or '#' or '|' or newline
                                for sep in [":", "#", "|", "\n"]:
                                    if sep in after:
                                        after = after.split(sep)[0]
                                title = after.strip()
                        except Exception:
                            pass
                        # Sanitize the title for filesystem safety
                        safe_title = re.sub(r'[^\w\-_ \.]', '_', title)[:50]  # limit length
                        os.makedirs("save", exist_ok=True)
                        with open(f"save/{missing_id} - {safe_title}.txt", "w", encoding="utf-8") as f:
                            f.write(level_data)

    if found_ids:
        print("")
        found_green = False
        for level_id in found_ids:
            try:
                # Step 1: Get username from level ID
                print(f"[Request] Getting username for level ID: {level_id}")
                url = "http://www.boomlings.com/database/getGJLevels21.php"
                data = {
                    "secret": "Wmfd2893gb7",
                    "str": str(level_id),
                    "type": 0
                }
                headers = {"User-Agent": ""}
                sleep(waitTime)
                response = requests.post(url, data=data, headers=headers)
                if response.text.strip() == "-1":
                    print(f"[Response] Level ID {level_id} not found.\n")
                    continue
                try:
                    username = response.text.split("#")[1].split(":")[1]
                    print(f"[Response] Username for level ID {level_id}: {username}")
                except Exception:
                    print(f"[Error] Could not parse username for level ID {level_id}.")
                    continue
                # Step 2: Get accountID from username
                print(f"[Request] Getting accountID for username: {username}")
                url = "http://www.boomlings.com/database/getGJUsers20.php"
                data = {
                    "secret": "Wmfd2893gb7",
                    "str": username
                }
                sleep(waitTime)
                response = requests.post(url, data=data, headers=headers)
                if response.text.strip() == "-1":
                    print(f"[Response] Username {username} not found.")
                    continue
                parts = response.text.split("#")[0].split(":")
                parsed = {}
                for i in range(0, len(parts) - 1, 2):
                    key = parts[i]
                    value = parts[i + 1]
                    parsed[key] = value
                accountID = parsed.get("16")
                if not accountID:
                    print(f"[Error] Could not parse accountID for username {username}.")
                    continue
                print(f"[Response] AccountID for username {username}: {accountID}")
                # Step 3: Get creator points from accountID
                print(f"[Request] Getting creator points for accountID: {accountID}")
                url = "http://www.boomlings.com/database/getGJUserInfo20.php"
                data = {
                    "secret": "Wmfd2893gb7",
                    "targetAccountID": accountID
                }
                sleep(waitTime)
                response = requests.post(url, data=data, headers=headers)
                if response.text.strip() == "-1":
                    print(f"[Response] AccountID {accountID} not found.")
                    continue
                parts = response.text.split(",")[0].split(":")
                parsed = {}
                for i in range(0, len(parts) - 1, 2):
                    key = parts[i]
                    value = parts[i + 1]
                    parsed[key] = value
                creatorPoints = int(parsed.get("8", 0))
                print(f"[Response] Creator points for accountID {accountID}: {creatorPoints}\n")
                if creatorPoints > 0:
                    print(Fore.GREEN + f"Level ID {level_id} (Creator Points: {creatorPoints})")
                    found_green = True
            except Exception as e:
                print(f"[Exception] {e}")
                continue
        if not found_green:
            print(f"No level IDs with creator points found in {Tries} runs.")
    else:
        print(f"No missing level IDs found in {Tries} runs.")
    #input()
    sleep(10)