import os
import shutil
import re

def getScriptName():
	return os.path.basename(__file__)

def extractLeadingNumber(name):
	match = re.match(r"^(\d+)", name)
	if match:
		return int(match.group(1))
	return None

def extractPackNumber(folderName):
	match = re.match(r"^Pack\s+(\d+)$", folderName)
	if match:
		return int(match.group(1))
	return None

def main():
	currentDir = os.path.dirname(os.path.abspath(__file__))
	scriptName = getScriptName()

	entries = os.listdir(currentDir)

	files = []
	packFolders = []

	for entry in entries:
		fullPath = os.path.join(currentDir, entry)
		if os.path.isfile(fullPath) and entry != scriptName:
			num = extractLeadingNumber(entry)
			if num is not None:
				files.append((num, entry))
		elif os.path.isdir(fullPath):
			packNum = extractPackNumber(entry)
			if packNum is not None:
				packFolders.append(packNum)

	if not files:
		print("No numbered files found.")
		return

	files.sort(key=lambda x: x[0])

	selectedFiles = [f[1] for f in files[:3000]]
	if not selectedFiles:
		print("No files selected.")
		return

	highestPack = max(packFolders) if packFolders else 0
	nextPackNumber = highestPack + 1
	nextPackFolder = os.path.join(currentDir, f"Pack {nextPackNumber}")
	os.makedirs(nextPackFolder, exist_ok=True)

	print(f"Creating {nextPackFolder}")

	for f in selectedFiles:
		shutil.move(os.path.join(currentDir, f), os.path.join(nextPackFolder, f))

	batchCount = 4
	totalFiles = len(selectedFiles)
	baseBatchSize = totalFiles // batchCount
	remainder = totalFiles % batchCount

	batchSizes = [baseBatchSize + (1 if i < remainder else 0) for i in range(batchCount)]

	index = 0
	for i in range(batchCount):
		batchFolder = os.path.join(nextPackFolder, f"Batch {i+1}")
		os.makedirs(batchFolder, exist_ok=True)

		batchFiles = selectedFiles[index:index + batchSizes[i]]
		index += batchSizes[i]

		for bf in batchFiles:
			shutil.move(os.path.join(nextPackFolder, bf), os.path.join(batchFolder, bf))

		print(f"Placed {len(batchFiles)} files into {batchFolder}")

if __name__ == "__main__":
	main()