"""
Supported Platforms:
 - Windows
 - MacOS

How to run:

You need Python 3.12.x to be installed, you can find it here:
Windows: https://www.python.org/ftp/python/3.12.4/python-3.12.4-amd64.exe
macOS: https://www.python.org/ftp/python/3.12.4/python-3.12.4-macos11.pkg
This program uses modules that need to be installed before you can run this.
This is the install command, which should be ran in the terminal.

Windows: py -3.12 -m pip install pycryptodome
macOS: python3.12 -m pip install pycryptodome

Then to run the program, open a terminal in the folder of the script, and run the following.

Windows: py -3.12 updatePassword.py
macOS: python3.12 updatePassword.py

The mac option will work for ios, you just need access to the folder containing the save file.
"""


import os
import platform
import base64
import gzip
import hashlib
from pathlib import Path
from Crypto.Cipher import AES


GJP2_SALT = "mI29fmAnxgTs"
XOR_KEY = 11

KEY = (
    b"\x69\x70\x75\x39\x54\x55\x76\x35\x34\x79\x76\x5d\x69\x73\x46\x4d"
    b"\x68\x35\x40\x3b\x74\x2e\x35\x77\x33\x34\x45\x32\x52\x79\x40\x7b"
)


def xorBytes(data: bytes, key: int) -> bytes:
    return bytes(b ^ key for b in data)


def clearScreen() -> None:
    if platform.system() == "Windows":
        os.system("cls")
    else:
        os.system("clear")

# ---------------- Windows ----------------

def decryptWindowsSave(encryptedText: str) -> bytes:
    xored = xorBytes(encryptedText.encode(), XOR_KEY)
    base64Decoded = base64.urlsafe_b64decode(xored)
    decompressed = gzip.decompress(base64Decoded)
    return decompressed


def encryptWindowsSave(decryptedData: bytes) -> str:
    compressed = gzip.compress(decryptedData)
    base64Encoded = base64.urlsafe_b64encode(compressed)
    xored = xorBytes(base64Encoded, XOR_KEY)
    return xored.decode()


def getWindowsSavePath() -> Path:
    localAppData = os.environ.get("LOCALAPPDATA")
    if localAppData:
        autoPath = Path(localAppData) / "GeometryDash" / "CCGameManager.dat"
        if autoPath.exists():
            return autoPath

    manualPath = input("Save file not found automatically.\nEnter full path to CCGameManager.dat: ").strip()
    path = Path(manualPath)
    if not path.exists():
        raise FileNotFoundError("Provided save file path does not exist")

    return path


# ---------------- macOS ----------------

def removePad(data: bytes) -> bytes:
    last = data[-1]
    if last < 16:
        data = data[:-last]
    return data


def addPad(data: bytes) -> bytes:
    lenR = len(data) % 16
    if lenR:
        toAdd = 16 - lenR
        data += toAdd.to_bytes(1, "little") * toAdd
    return data


def decryptMacSave(data: bytes) -> bytes:
    cipher = AES.new(KEY, AES.MODE_ECB)
    return removePad(cipher.decrypt(data))


def encryptMacSave(data: bytes) -> bytes:
    cipher = AES.new(KEY, AES.MODE_ECB)
    return cipher.encrypt(addPad(data))


def getMacSavePath() -> Path:
    autoPath = Path.home() / "Library" / "Application Support" / "GeometryDash" / "CCGameManager.dat"
    if autoPath.exists():
        return autoPath

    manualPath = input("Save file not found automatically.\nEnter full path to CCGameManager.dat: ").strip()
    path = Path(manualPath)
    if not path.exists():
        raise FileNotFoundError("Provided save file path does not exist")

    return path


# ---------------- Shared ----------------

def generateGjp2(password: str) -> str:
    return hashlib.sha1((password + GJP2_SALT).encode()).hexdigest()


def replaceGjp2(saveData: bytes, newGjp2: str) -> bytes:
    marker = b"<k>GJA_005</k><s>"
    startIndex = saveData.find(marker)
    if startIndex == -1:
        raise RuntimeError("GJA_005 key not found in save file")

    valueStart = startIndex + len(marker)
    valueEnd = saveData.find(b"</s>", valueStart)
    if valueEnd == -1:
        raise RuntimeError("Malformed GJA_005 entry")

    return saveData[:valueStart] + newGjp2.encode() + saveData[valueEnd:]


def main() -> None:
    platformChoice = input("Select platform (windows / mac): ").strip().lower()
    if platformChoice not in ("windows", "mac"):
        raise RuntimeError("Invalid platform selection")

    if platformChoice == "windows":
        savePath = getWindowsSavePath()
        with savePath.open("r", encoding="utf-8", errors="ignore") as file:
            encryptedText = file.read()

        decryptedData = decryptWindowsSave(encryptedText)

        newPassword = input("Enter new Geometry Dash account password: ")
        newGjp2 = generateGjp2(newPassword)

        modifiedData = replaceGjp2(decryptedData, newGjp2)
        reEncryptedText = encryptWindowsSave(modifiedData)

        with savePath.open("w", encoding="utf-8") as file:
            file.write(reEncryptedText)

    else:
        savePath = getMacSavePath()
        with savePath.open("rb") as file:
            encryptedBytes = file.read()

        decryptedData = decryptMacSave(encryptedBytes)

        newPassword = input("Enter new Geometry Dash account password: ")
        newGjp2 = generateGjp2(newPassword)

        modifiedData = replaceGjp2(decryptedData, newGjp2)
        reEncryptedBytes = encryptMacSave(modifiedData)

        with savePath.open("wb") as file:
            file.write(reEncryptedBytes)

    print("Save file updated successfully.")


if __name__ == "__main__":
    clearScreen()
    try:
        main()
    except:

        input("\nEnter to exit...")

