import requests
import os
import re
from time import sleep

def safe_post(url, data, headers, retries=3, timeout=10):
    for attempt in range(1, retries + 1):
        try:
            return requests.post(url, data=data, headers=headers, timeout=timeout)
        except requests.exceptions.RequestException as e:
            print(f"[Network Error] {e} (attempt {attempt}/{retries})")
            if attempt < retries:
                sleep(2)
                continue
            return None

def get_user_id(username):
    url = "http://www.boomlings.com/database/getGJUsers20.php"
    data = {"str": username, "secret": "Wmfd2893gb7"}
    headers = {"User-Agent": ""}

    response = safe_post(url, data, headers)
    if not response or response.text.strip() == "-1":
        return None

    parts = response.text.split("#")[0].split(":")
    parsed = {parts[i]: parts[i+1] for i in range(0, len(parts)-1, 2)}
    return parsed.get("2")  # userID

def get_total_pages(userID):
    url = "http://www.boomlings.com/database/getGJLevels21.php"
    data = {"str": userID, "type": 5, "local": 0, "page": 0, "secret": "Wmfd2893gb7"}
    headers = {"User-Agent": ""}
    response = safe_post(url, data, headers)
    if not response or response.text.strip() == "-1":
        return 0

    sections = response.text.split("#")
    if len(sections) < 4:
        return 0
    page_info = sections[3]  # e.g., "325:0:10"
    total_levels = int(page_info.split(":")[0])
    total_pages = (total_levels + 9) // 10
    return total_pages

def parse_level_ids(response_text):
    levels_data = response_text.split("#")[0]
    entries = levels_data.split("|")
    ids = []
    for entry in entries:
        parts = entry.split(":")
        parsed = {parts[i]: parts[i+1] for i in range(0, len(parts)-1, 2)}
        if "1" in parsed:
            ids.append(int(parsed["1"]))
    return ids

def download_level(level_id, save_dir):
    url = "http://www.boomlings.com/database/downloadGJLevel22.php"
    data = {"secret": "Wmfd2893gb7", "levelID": level_id}
    headers = {"User-Agent": ""}

    response = safe_post(url, data, headers)
    if not response or response.text.strip() == "-1":
        print(f"[Skip] Level {level_id} not found.")
        return

    level_data = response.text
    title = "unknown_title"
    match = re.search(r":2:([^:\n\r|#]+)", level_data)
    if match:
        title = match.group(1).strip()
    safe_title = re.sub(r'[^\w\-_ \.]', '_', title)[:50]

    os.makedirs(save_dir, exist_ok=True)
    file_path = f"{save_dir}/{level_id} - {safe_title}.txt"
    with open(file_path, "w", encoding="utf-8") as f:
        f.write(level_data)
    print(f"[Saved] {level_id} - {safe_title}")

def get_existing_max_id(save_dir):
    """Find the largest level ID already saved in the folder, or 0 if none."""
    if not os.path.exists(save_dir):
        return 0
    ids = []
    for fname in os.listdir(save_dir):
        match = re.match(r"^(\d+) -", fname)
        if match:
            try:
                ids.append(int(match.group(1)))
            except ValueError:
                continue
    return max(ids) if ids else 0

def main():
    username = input("Enter account name: ").strip()
    userID = get_user_id(username)
    if not userID:
        print(f"[Error] Could not find user: {username}")
        return

    print(f"[Info] Username '{username}' has userID {userID}")
    total_pages = get_total_pages(userID)
    print(f"[Info] Found {total_pages} pages of levels.")

    save_dir = username
    os.makedirs(save_dir, exist_ok=True)

    existing_max_id = get_existing_max_id(save_dir)
    if existing_max_id > 0:
        print(f"[Info] Resuming. Largest saved level ID: {existing_max_id}")
    else:
        print(f"[Info] No existing levels found. Downloading all.")

    for page in range(total_pages):
        print(f"[Request] Fetching page {page+1}/{total_pages}")
        url = "http://www.boomlings.com/database/getGJLevels21.php"
        data = {"str": userID, "type": 5, "local": 0, "page": page, "secret": "Wmfd2893gb7"}
        headers = {"User-Agent": ""}
        response = safe_post(url, data, headers)
        if not response or response.text.strip() == "-1":
            continue

        level_ids = parse_level_ids(response.text)

        for level_id in level_ids:
            if level_id <= existing_max_id:
                print(f"[Info] Reached already-downloaded level ID {level_id}. Stopping.")
                return  # stop immediately

            download_level(level_id, save_dir)
            sleep(10)  # avoid rate limit

        sleep(2)  # pause between pages

    print("[Done] All available levels downloaded.")

if __name__ == "__main__":
    main()
