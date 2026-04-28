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
1. Getting the latest level ID from the recent tab.
2. Requesting a 100 ID window starting from that ID.
3. Checking which ids are returned.
4. Looking for gaps between adjacent ids.
   These gaps are caused by levels being
   deleted or uploaded unlisted.
5. It then tries to download these levels.
6. It will then check if the creator of each level
   has creator points so that it's easier
   to find interesting levels.
7. Once a batch is processed, it waits for 100 new
   IDs to appear on the recent tab before repeating.
8. All levels and logs are saved, so
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

import subprocess
import importlib
import sys

requiredModules = ['urllib3', 'idna', 'charset_normalizer', 'certifi', 'requests', 'colorama']

def installMissingModules(modules):
    pip = 'pip'
    try:
        importlib.import_module(pip)
    except ImportError:
        print(f"{pip} is not installed. Installing...")
        subprocess.check_call([sys.executable, "-m", "ensurepip", "--upgrade"])
    for module in modules:
        try:
            importlib.import_module(module)
        except ImportError:
            print(f"{module} is not installed. Installing...")
            subprocess.check_call([sys.executable, "-m", "pip", "install", module])

installMissingModules(requiredModules)

import requests, random
from colorama import init, Fore
from time import sleep
import os
import re
import sqlite3
import csv
import base64
import gzip
import io
import zlib
from collections import Counter
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
        self.terminal.flush()
        self.log.flush()

if not os.path.exists("logs"):
    os.makedirs("logs")

log_filename = f"logs/log_{datetime.now().strftime('%Y-%m-%d_%H-%M-%S')}.txt"
sys.stdout = Logger(log_filename)
# --- End Logger Setup ---

init(autoreset=True)

LOGS_DIR = "./logs"
SAVE_DIR = "./save"
CSV_FILE = os.path.join(LOGS_DIR, "unlistedLevelsCreator.csv")
DB_FILE = "levels.db"
windowSize = 100

# --- Helpers for parsing level data ---
def decode_level(level_data):
    parts = level_data.split("#")[0].split(":")
    parsed = {parts[i]: parts[i+1] for i in range(0, len(parts)-1, 2)}
    level_str = parsed.get("4", "")

    if not level_str or level_str in ("0", "Aw=="):
        return ""

    level_str += "=" * (-len(level_str) % 4)
    try:
        b64_decoded = base64.urlsafe_b64decode(level_str.encode())
    except Exception:
        return ""

    for decompressor in [
        lambda x: gzip.GzipFile(fileobj=io.BytesIO(x)).read(),
        lambda x: zlib.decompress(x, -zlib.MAX_WBITS),
        lambda x: x,
    ]:
        try:
            return decompressor(b64_decoded).decode()
        except Exception:
            continue
    return ""

def extract_object_string(decoded_level):
    first_semi = decoded_level.find(";")
    if first_semi != -1 and first_semi + 1 < len(decoded_level):
        return decoded_level[first_semi+1:]
    return ""

def count_rcoins(object_string):
    coin_count = 0
    for obj in object_string.split(";"):
        if not obj.strip():
            continue
        fields = obj.split(",")
        for i in range(0, len(fields)-1, 2):
            if fields[i] == "1" and fields[i+1] == "1329":
                coin_count += 1
                break
    return coin_count

def count_object_ids(object_string):
    object_ids = []
    for obj in object_string.split(";"):
        if not obj.strip():
            continue
        fields = obj.split(",")
        for i in range(0, len(fields)-1, 2):
            if fields[i] == "1":
                obj_id = fields[i+1]
                if obj_id == "747":
                    object_ids.extend([obj_id, obj_id])
                elif obj_id == "31":
                    pass
                else:
                    object_ids.append(obj_id)
                break
    return sum(Counter(object_ids).values())

def parse_fields(level_data, file_path):
    parts = level_data.split("#")[0].split(":")
    parsed = {parts[i]: parts[i+1] for i in range(0, len(parts)-1, 2)}

    encoded_desc = parsed.get("3", "")
    description = decode_description(encoded_desc) if encoded_desc else ""

    size_bytes = os.path.getsize(file_path)
    size_str = f"{size_bytes} B"

    songID = (
        parsed.get("12", "")
        if parsed.get("12", "") != "0"
        else parsed.get("52", "")
        if parsed.get("52", "")
        else parsed.get("35", "")
    )

    decoded_level = decode_level(level_data)
    rCoins, object_count = 0, 0
    if decoded_level:
        obj_str = extract_object_string(decoded_level)
        if obj_str:
            rCoins = count_rcoins(obj_str)
            object_count = count_object_ids(obj_str)

    length_map = {
        "0": "Tiny",
        "1": "Short",
        "2": "Medium",
        "3": "Long",
        "4": "XL",
        "5": "Platformer",
    }
    length = length_map.get(parsed.get("15", ""), "")

    fields = {
        "Name": parsed.get("2", "unknown_title"),
        "Description": description,
        "Size": size_str,
        "songID": songID,
        "OriginalID": parsed.get("30", ""),
        "rCoins": rCoins,
        "sCoins": parsed.get("37", ""),
        "Version": parsed.get("5", ""),
        "Length": length,
        "EditorTime": parsed.get("46", ""),
        "EditorCTime": parsed.get("47", ""),
        "RequestedRating": parsed.get("39", ""),
        "TwoPlayer": "Yes" if parsed.get("31", "0") == "1" else "No",
        "ObjectCount": object_count,
        "PlayerID": parsed.get("6", "")
    }
    return fields

# --- Database Setup ---
def create_database():
    conn = sqlite3.connect(DB_FILE)
    cur = conn.cursor()
    cur.execute("""
        CREATE TABLE IF NOT EXISTS levels (
            ID INTEGER PRIMARY KEY,
            Username TEXT,
            CreatorPoints INTEGER
        )
    """)
    conn.commit()
    conn.close()

def ensure_columns(fields):
    conn = sqlite3.connect(DB_FILE, timeout=30)
    cur = conn.cursor()
    cur.execute("PRAGMA table_info(levels)")
    existing_cols = [row[1] for row in cur.fetchall()]
    for col in fields.keys():
        if col not in existing_cols:
            cur.execute(f"ALTER TABLE levels ADD COLUMN {col} TEXT")
            print(f"[DB] Added missing column: {col}")
    conn.commit()
    conn.close()

def insert_level(level_id, username, creator_points, fields):
    conn = sqlite3.connect(DB_FILE, timeout=30)
    cur = conn.cursor()
    cols = ["ID", "Username", "CreatorPoints"] + list(fields.keys())
    placeholders = ", ".join("?" * len(cols))
    cur.execute(f"""
        INSERT OR REPLACE INTO levels ({", ".join(cols)})
        VALUES ({placeholders})
    """, (level_id, username, creator_points, *fields.values()))
    conn.commit()
    conn.close()

def decode_description(encoded_desc):
    try:
        missing_padding = len(encoded_desc) % 4
        if missing_padding:
            encoded_desc += "=" * (4 - missing_padding)
        return base64.urlsafe_b64decode(encoded_desc).decode("utf-8", errors="ignore")
    except Exception:
        return ""

# --- CSV Updater ---
def update_csv(username, creator_points, level_id):
    rows = []
    found_user = False
    if os.path.exists(CSV_FILE):
        with open(CSV_FILE, "r", encoding="utf-8") as f:
            reader = csv.reader(f)
            for row in reader:
                if row and row[0] == username:
                    found_user = True
                    if str(level_id) not in row[2:]:
                        row.append(str(level_id))
                rows.append(row)

    if not found_user:
        rows.append([username, str(creator_points), str(level_id)])

    with open(CSV_FILE, "w", encoding="utf-8", newline="") as f:
        writer = csv.writer(f)
        writer.writerows(rows)

# --- Network helper ---
def safe_post(url, data, headers, retries=3, timeout=10):
    sleep(0.2)
    for attempt in range(1, retries + 1):
        try:
            return requests.post(url, data=data, headers=headers, timeout=timeout)
        except requests.exceptions.RequestException as e:
            print(f"[Network Error] {e} (attempt {attempt}/{retries})")
            if attempt < retries:
                sleep(2)
                continue
            return None

def update_creator_points(username, new_cp):
    conn = sqlite3.connect(DB_FILE, timeout=30)
    cur = conn.cursor()
    cur.execute("SELECT DISTINCT CreatorPoints FROM levels WHERE Username=?", (username,))
    rows = cur.fetchall()
    if not rows or any(row[0] != new_cp for row in rows):
        cur.execute("UPDATE levels SET CreatorPoints=? WHERE Username=?", (new_cp, username))
        print(f"[INFO] Updated CreatorPoints for {username} -> {new_cp}")
    conn.commit()
    conn.close()

# --- Get latest ID from recent tab ---
def get_latest_id(headers):
    """Fetch the most recent level ID from the recent tab (type 0, page 0)."""
    url = "http://www.boomlings.com/database/getGJLevels21.php"
    data = {
        "secret": "Wmfd2893gb7",
        "type": 4,
        "str": "",
        "page": 0,
    }
    response = safe_post(url, data, headers)
    if not response or response.text.strip() == "-1":
        return None

    latest_id = None
    for item in response.text.split("|"):
        if item[:2] == "1:":
            parts = item.split(":")
            if len(parts) > 1:
                try:
                    level_id = int(parts[1])
                    if latest_id is None or level_id > latest_id:
                        latest_id = level_id
                except ValueError:
                    pass
    return latest_id

# --- Process a window of IDs for gaps ---
def process_window(startId, endId, headers, waitTime):
    """
    Request IDs [startId, endId) via type 26, find gaps, attempt downloads.
    Returns a list of found unlisted level IDs.
    """
    requestIds = [str(i) for i in range(startId, endId)]
    requestStr = ",".join(requestIds)

    url = "http://www.boomlings.com/database/getGJLevels21.php"

    data = {
        "secret": "Wmfd2893gb7",
        "type": 26,
        "str": requestStr
    }

    sleep(waitTime)
    print(f"[Request] Checking IDs {startId} -> {endId - 1}")
    response = safe_post(url, data, headers)
    if not response:
        print("[Error] No response for window request.")
        return []
    result = response.text

    level_ids = []
    for item in result.split("|"):
        if item[:2] == "1:":
            parts = item.split(":")
            if len(parts) > 1:
                try:
                    level_ids.append(int(parts[1]))
                except ValueError:
                    pass

    if not level_ids:
        print("[Info] No listed levels found in this window.")
        return []

    level_ids.sort()

    # Find gaps — IDs that exist in our range but weren't returned
    # Only look for gaps within the range of returned IDs
    missing = []
    for i in range(len(level_ids) - 1):
        current_id = level_ids[i]
        next_id = level_ids[i + 1]
        if next_id - current_id > 1:
            for missing_id in range(current_id + 1, next_id):
                missing.append(missing_id)

    if not missing:
        print("[Info] No gaps found in this window.")
        return []

    found_ids = []
    check_url = "http://www.boomlings.com/database/downloadGJLevel22.php"

    for missing_id in missing:
        print(f"[INFO] Checking ID: {missing_id}")
        check_data = {"secret": "Wmfd2893gb7", "levelID": missing_id}
        check_response = safe_post(check_url, check_data, headers)
        sleep(waitTime)
        if not check_response:
            continue
        if check_response.text.strip() == "-1":
            continue

        found_ids.append(missing_id)
        level_data = check_response.text

        title = "unknown_title"
        try:
            match = re.search(r":2:([^:\n\r|#]+)", level_data)
            if match:
                title = match.group(1).strip()
        except Exception:
            pass

        safe_title = re.sub(r'[^\w\-_ \.]', '_', title)[:50]
        os.makedirs(SAVE_DIR, exist_ok=True)
        file_path = f"{SAVE_DIR}/{missing_id} - {safe_title}.txt"
        with open(file_path, "w", encoding="utf-8") as f:
            f.write(level_data)

        fields = parse_fields(level_data, file_path)
        ensure_columns(fields)

        print(f"[Request] Getting username for level ID: {missing_id}")
        u_url = "http://www.boomlings.com/database/getGJLevels21.php"
        u_data = {"secret": "Wmfd2893gb7", "str": str(missing_id), "type": 0}
        u_response = safe_post(u_url, u_data, headers)
        if not u_response or u_response.text.strip() == "-1":
            print(f"[Response] Level ID {missing_id} not found.\n")
            continue
        try:
            username = u_response.text.split("#")[1].split(":")[1]
            print(f"[Response] Username for level ID {missing_id}: {username}")
        except Exception:
            print(f"[Error] Could not parse username for level ID {missing_id}.")
            continue

        print(f"[Request] Getting accountID for username: {username}")
        a_url = "http://www.boomlings.com/database/getGJUsers20.php"
        a_data = {"secret": "Wmfd2893gb7", "str": username}
        a_response = safe_post(a_url, a_data, headers)
        if not a_response or a_response.text.strip() == "-1":
            print(f"[Response] Username {username} not found.")
            continue
        a_parts = a_response.text.split("#")[0].split(":")
        a_parsed = {a_parts[i]: a_parts[i+1] for i in range(0, len(a_parts)-1, 2)}
        accountID = a_parsed.get("16")
        if not accountID:
            print(f"[Error] Could not parse accountID for username {username}.")
            continue
        print(f"[Response] AccountID for username {username}: {accountID}")

        i_url = "http://www.boomlings.com/database/getGJUserInfo20.php"
        i_data = {"secret": "Wmfd2893gb7", "targetAccountID": accountID}
        i_response = safe_post(i_url, i_data, headers)
        if not i_response or i_response.text.strip() == "-1":
            print(f"[Response] AccountID {accountID} not found.")
            continue
        i_parts = i_response.text.split(",")[0].split(":")
        i_parsed = {i_parts[i]: i_parts[i+1] for i in range(0, len(i_parts)-1, 2)}
        creatorPoints = int(i_parsed.get("8", 0))
        print(f"[Response] Creator points for accountID {accountID}: {creatorPoints}")

        update_creator_points(username, creatorPoints)
        update_csv(username, creatorPoints, missing_id)
        insert_level(missing_id, username, creatorPoints, fields)
        print(Fore.GREEN + f"Added {missing_id} ({title}) to database and CSV.\n")

    return found_ids

# --- Main ---
waitTime = 2.3
POLL_INTERVAL = 8  # seconds between recent-tab polls when waiting for next batch

create_database()
headers = {"User-Agent": ""}

# Bootstrap: get the current latest ID to establish our starting window
print("[Startup] Fetching latest level ID from recent tab...")
while True:
    latest_id = get_latest_id(headers)
    if latest_id:
        break
    print("[Startup] Could not fetch latest ID, retrying in 5s...")
    sleep(5)

# Align to the window boundary just below the latest ID.
# nextWindowStart is the first ID of the next un-processed window.
# We start scanning from (latest_id - windowSize + 1) so our first
# window contains the latest ID.
nextWindowStart = latest_id - windowSize + 1

print(f"[Startup] Starting forward scan from ID {nextWindowStart} (latest: {latest_id})")

while True:
    windowEnd = nextWindowStart + windowSize  # exclusive upper bound

    # --- Poll until the recent tab has caught up to the end of our target window ---
    while True:
        current_latest = get_latest_id(headers)
        if current_latest is None:
            print("[Poll] Could not fetch latest ID, retrying...")
            sleep(POLL_INTERVAL)
            continue

        if current_latest >= windowEnd - 1:
            # The server has published at least up to the end of our window
            break

        remaining = (windowEnd - 1) - current_latest
        print(f"[Poll] Latest ID is {current_latest}, waiting for {windowEnd - 1} "
              f"({remaining} more needed)... checking again in {POLL_INTERVAL}s")
        sleep(POLL_INTERVAL)

    # --- Process the window ---
    found = process_window(nextWindowStart, windowEnd, headers, waitTime)
    if found:
        print(Fore.CYAN + f"[Summary] Found {len(found)} unlisted level(s) in window "
              f"{nextWindowStart}-{windowEnd - 1}: {found}")
    else:
        print(f"[Summary] No unlisted levels found in window {nextWindowStart}-{windowEnd - 1}.")

    # Advance to the next window
    nextWindowStart = windowEnd