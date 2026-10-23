import os
import re
from time import sleep
import GDReq

def getUserIDAndAccountID(username):
	response = GDReq.getGJUsers20(str_=username)
	parsed = GDReq.Parse.getGJUsers20(response)
	return parsed["users"][0]["userID"], parsed["users"][0]["accountID"]

def getTotalPages(userID, local, accountID=None, gjp2=None):
	params = {"str_": userID, "type_": 5, "page": 0, "local": local}
	if local:
		params.update({"accountID": accountID, "gjp2": gjp2})

	response = GDReq.getGJLevels21(**params)
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

def downloadLevel(levelID, saveDir, local, accountID=None, gjp2=None):
	params = {"levelID": levelID}
	if local:
		params.update({"accountID": accountID, "gjp2": gjp2})
	levelData = GDReq.downloadGJLevel22(**params)
	parsed = GDReq.Parse.downloadGJLevel22(levelData)
	title = parsed["level"]["levelName"]
	safeTitle = re.sub(r'[^\w\-_ \.]', '_', title)[:50]
	os.makedirs(saveDir, exist_ok=True)
	filePath = f"{saveDir}/{levelID} - {safeTitle}.txt"
	with open(filePath, "w", encoding="utf-8") as f:
		f.write(levelData)
	print(f"[Saved] {levelID} - {safeTitle}")

def getExistingLevelIDs(saveDir):
	"""Find all level IDs already saved in the folder."""
	if not os.path.exists(saveDir):
		return set()
	ids = set()
	for fname in os.listdir(saveDir):
		match = re.match(r"^(\d+) -", fname)
		if match:
			ids.add(int(match.group(1)))
	return ids

def main():
	username = input("Enter account name: ").strip()
	userID, accountID = getUserIDAndAccountID(username)
	if not userID:
		print(f"[Error] Could not find user: {username}")
		return

	ownAccount = input("Are you archiving your own account? (y/n): ").strip().lower() in ("y", "yes")
	local = int(ownAccount)
	gjp2 = None

	if ownAccount:
		gjp2 = input("Enter your gjp2: ").strip()

	print(f"[Info] Username '{username}' has userID {userID}")
	totalPages = getTotalPages(userID, local, accountID, gjp2)
	print(f"[Info] Found {totalPages} pages of levels.")

	saveDir = username
	os.makedirs(saveDir, exist_ok=True)

	existingIDs = getExistingLevelIDs(saveDir)
	if existingIDs:
		print(f"[Info] Resuming. Found {len(existingIDs)} existing levels.")
	else:
		print("[Info] No existing levels found. Downloading all.")

	for page in range(totalPages):
		params = {"str_": userID, "type_": 5, "local": local, "page": page}
		if ownAccount:
			params.update({"accountID": accountID, "gjp2": gjp2})
		response = GDReq.getGJLevels21(**params)
		levelIDs = parseLevelIDs(response)

		for levelID in levelIDs:
			if int(levelID) in existingIDs:
				print(f"[Info] Level ID {levelID} already downloaded. Skipping.")
				continue

			downloadLevel(levelID, saveDir, local, accountID, gjp2)
			existingIDs.add(int(levelID))
			sleep(10)  # avoid rate limit

		sleep(2)  # pause between pages

	print("[Done] All available levels downloaded.")

if __name__ == "__main__":
	main()