import xml.etree.ElementTree as ET
import hashlib


def getLevelStringFromGmd(fileName):
    tree = ET.parse(fileName)
    root = tree.getroot()
    mainDict = root.find("dict")
    if mainDict is None:
        raise ValueError("Main <dict> element not found in file.")
    children = list(mainDict)
    levelString = None
    for i in range(0, len(children) - 1, 2):
        keyElem = children[i]
        valElem = children[i + 1]
        if keyElem.text == "k4":
            levelString = valElem.text
            break
    if not levelString:
        raise ValueError("Level string (k4) not found in the .gmd file.")
    return levelString


def main():
    fileName = input("Enter the .gmd file name: ").strip()
    try:
        levelString = getLevelStringFromGmd(fileName)
        sha256Hash = hashlib.sha256(levelString.encode("utf-8")).hexdigest()
        print(f"SHA256 checksum of level string in {fileName}: {sha256Hash}")
    except Exception as e:
        print(f"Error: {e}")


if __name__ == "__main__":
    main()
    input() 