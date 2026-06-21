"""
Reads pack folders recursively for level files and appends them to a json file called packRanges.json specifying the pack number and start and end ids.
"""

import json
import re
from pathlib import Path

rootDir = Path(r"D:\Personal\Games\Geometry Dash\Other\ServerRip")
outputFile = rootDir / "packRanges.json"

packPattern = re.compile(r"Pack\s+(\d+)$", re.IGNORECASE)
filePattern = re.compile(r"^(\d+)\s*-\s*.*\.txt$", re.IGNORECASE)


def extractId(filePath: Path) -> int | None:
    match = filePattern.match(filePath.name)
    if not match:
        return None

    try:
        with filePath.open("r", encoding="utf-8", errors="strict") as file:
            file.read(1)

        return int(match.group(1))

    except Exception:
        return None


def findFirstReadableId(directory: Path) -> int | None:
    try:
        files = sorted(
            (path for path in directory.iterdir() if path.is_file()),
            key=lambda path: path.name
        )

        for filePath in files:
            fileId = extractId(filePath)

            if fileId is not None:
                return fileId

    except Exception:
        pass

    return None


def findLastReadableId(directory: Path) -> int | None:
    try:
        files = sorted(
            (path for path in directory.iterdir() if path.is_file()),
            key=lambda path: path.name,
            reverse=True
        )

        for filePath in files:
            fileId = extractId(filePath)

            if fileId is not None:
                return fileId

    except Exception:
        pass

    return None


def processPack(packDir: Path) -> tuple[int, int] | None:
    batch1 = packDir / "Batch 1"
    batch4 = packDir / "Batch 4"

    if batch1.is_dir() and batch4.is_dir():
        startId = findFirstReadableId(batch1)
        endId = findLastReadableId(batch4)
    else:
        startId = findFirstReadableId(packDir)
        endId = findLastReadableId(packDir)

    if startId is None or endId is None:
        return None

    return startId, endId


existingData = {}

if outputFile.exists():
    try:
        with outputFile.open("r", encoding="utf-8") as file:
            existingData = json.load(file)
    except Exception as error:
        print(f"Failed to read existing JSON: {error}")


for packDir in rootDir.iterdir():
    if not packDir.is_dir():
        continue

    match = packPattern.match(packDir.name)

    if not match:
        continue

    packNumber = int(match.group(1))
    packKey = str(packNumber)

    if packKey in existingData:
        continue

    try:
        result = processPack(packDir)

        if result is None:
            print(f"Skipping Pack {packNumber}: unable to determine range")
            continue

        startId, endId = result

        existingData[packKey] = {
            "startId": startId,
            "endId": endId
        }

        print(f"Added Pack {packNumber}: {startId} -> {endId}")

    except Exception as error:
        print(f"Skipping Pack {packNumber}: {error}")


sortedData = {
    str(packNumber): existingData[str(packNumber)]
    for packNumber in sorted(int(key) for key in existingData)
}

with outputFile.open("w", encoding="utf-8") as file:
    json.dump(sortedData, file, indent=4)

print(f"Saved {len(sortedData)} pack entries")