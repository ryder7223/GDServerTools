import os
import re
from time import sleep
import GDReq

def getUserID(username):
	response = GDReq.getGJUsers20(str_=username)
	parsed = GDReq.Parse.getGJUsers20(response)
	return parsed["users"][0]["userID"]

def getTotalPages(userID):
	response = GDReq.getGJLevels21(str_=userID, type_=5, page=0)
	parsed = GDReq.Parse.getGJLevels21(response)
	totalLevels = parsed["pagination"]["total"]
	totalPages = (totalLevels + 9) // 10
	return totalPages

def parseLevelIDs(responseText):
	levelsData = GDReq.Parse.getGJLevels21(responseText)["levels"]
	ids = []
	for entry in levelsData:
		ids.append(entry["levelID"])
	return ids

def downloadLevel(levelID, saveDir):
	levelData = GDReq.downloadGJLevel22(levelID=levelID)
	parsed = GDReq.Parse.downloadGJLevel22(levelData)
	title = parsed["level"]["levelName"]
	safeTitle = re.sub(r'[^\w\-_ \.]', '_', title)[:50]
	os.makedirs(saveDir, exist_ok=True)
	filePath = f"{saveDir}/{levelID} - {safeTitle}.txt"
	with open(filePath, "w", encoding="utf-8") as f:
		f.write(levelData)
	print(f"[Saved] {levelID} - {safeTitle}")

def getExistingMaxID(saveDir):
	"""Find the largest level ID already saved in the folder, or 0 if none."""
	if not os.path.exists(saveDir):
		return 0
	ids = []
	for fname in os.listdir(saveDir):
		match = re.match(r"^(\d+) -", fname)
		if match:
			try:
				ids.append(int(match.group(1)))
			except ValueError:
				continue
	return max(ids) if ids else 0

def main():
	username = input("Enter account name: ").strip()
	userID = getUserID(username)
	if not userID:
		print(f"[Error] Could not find user: {username}")
		return

	print(f"[Info] Username '{username}' has userID {userID}")
	totalPages = getTotalPages(userID)
	print(f"[Info] Found {totalPages} pages of levels.")

	saveDir = username
	os.makedirs(saveDir, exist_ok=True)

	existingMaxID = getExistingMaxID(saveDir)
	if existingMaxID > 0:
		print(f"[Info] Resuming. Largest saved level ID: {existingMaxID}")
	else:
		print(f"[Info] No existing levels found. Downloading all.")

	for page in range(totalPages):
		response = GDReq.getGJLevels21(str_=userID, type_=5, local=0, page=page)
		levelIDs = parseLevelIDs(response)

		for levelID in levelIDs:
			if levelID <= existingMaxID:
				print(f"[Info] Reached already-downloaded level ID {levelID}. Stopping.")
				return  # stop immediately

			downloadLevel(levelID, saveDir)
			sleep(10)  # avoid rate limit

		sleep(2)  # pause between pages

	print("[Done] All available levels downloaded.")

if __name__ == "__main__":
	main()
