import subprocess
import importlib
import sys

# Auto-install modules
requiredModules = ['requests', 'flask']

def installMissingModules(modules):
    pip = 'pip'
    try:
        importlib.import_module(pip)
    except ImportError:
        subprocess.check_call([sys.executable, "-m", "ensurepip", "--upgrade"])
    for module in modules:
        try:
            importlib.import_module(module)
        except ImportError:
            subprocess.check_call([sys.executable, "-m", "pip", "install", module])

installMissingModules(requiredModules)

import requests
import urllib.parse
import os
from flask import Flask, Response
from io import BytesIO

def parseDailyLevels(rawString):
    levelsPart = rawString.split("~|~")[0]
    levelBlocks = levelsPart.split("|")

    parsedLevels = []

    for block in levelBlocks:
        if not block:
            continue

        segments = block.split(":")
        if len(segments) % 2 != 0:
            segments = segments[:-1]

        levelDict = {}
        for i in range(0, len(segments), 2):
            key = segments[i]
            value = segments[i + 1]
            levelDict[key] = value

        parsedLevels.append(levelDict)

    return parsedLevels

def getDailySongID(weekly):
    url = "http://www.boomlings.com/database/getGJLevels21.php"
    if weekly == 0:
        version = 21
    else:
        version = 22
    data = {
        "secret": "Wmfd2893gb7",
        "type": version
    }

    headers = {"User-Agent": ""}

    response = requests.post(url, data=data, headers=headers)
    levels = parseDailyLevels(response.text)
    songID = levels[0].get("35")
    return int(songID)

app = Flask(__name__)

@app.route("/downloadSong/<int:songID>")
def downloadSong(songID):
    try:
        if songID >= 10000000:
            songURL = f"https://geometrydashfiles.b-cdn.net/music/{songID}.ogg"
            songName = songID
            mimetype = "audio/ogg"
            ext = "ogg"
        else:
            url = "http://www.boomlings.com/database/getGJSongInfo.php"
            data = {
                "secret": "Wmfd2893gb7",
                "binaryVersion": 45,
                "songID": songID
            }
            headers = {"User-Agent": ""}
            response = requests.post(url, data=data, headers=headers)
            response.raise_for_status()

            if "-2" in response.text:
                return Response(f"Error: File Not Found for ID {songID}.", status=404)

            parts = response.text.split("~|~")
            parsed = {parts[i]: parts[i + 1] for i in range(0, len(parts) - 1, 2)}

            songURL = urllib.parse.unquote(parsed.get("10"))
            songName = songID
            mimetype = "audio/mpeg"
            ext = "mp3"

        remote = requests.get(songURL, stream=True)
        remote.raise_for_status()

        def streamFile(r):
            for chunk in r.iter_content(chunk_size=4096):
                if chunk:
                    yield chunk

        headers = {"Content-Disposition": f"attachment; filename={songName}.{ext}"}

        return Response(
            streamFile(remote),
            headers=headers,
            mimetype=mimetype,
            direct_passthrough=True
        )

    except Exception as e:
        return Response(f"Error downloading song: {e}", status=500)

@app.route("/currentDailySong")
def getDailySong():
    songID = getDailySongID(0)
    return downloadSong(songID)

@app.route("/currentWeeklySong")
def getWeeklySong():
    songID = getDailySongID(1)
    return downloadSong(songID)

@app.route("/playID/<int:levelID>")
def playID(levelID):
    try:
        url = "http://www.boomlings.com/database/getGJLevels21.php"

        data = {
            "secret": "Wmfd2893gb7",
            "type": 0,
            "str": levelID
        }

        headers = {"User-Agent": ""}
        response = requests.post(url, data=data, headers=headers)
        response.raise_for_status()

        raw = response.text

        if "~|~" not in raw:
            return Response("Error: Unexpected response format.", status=500)

        parts = raw.split("~|~")
        if len(parts) < 2:
            return Response("Error: Missing song ID section.", status=500)

        # Song ID is immediately after the "~|~" and before the next "~"
        songID = parts[1].split("~")[0]

        if not songID.isdigit():
            return Response(f"Error extracting song ID: {songID}", status=400)

        return downloadSong(int(songID))

    except Exception as e:
        return Response(f"Error handling playID request: {e}", status=500)

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5001)