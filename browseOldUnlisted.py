# This version is designed to be used as a secondary endpoint to serve more levels.
# It needs to be forwarded to a public address to function, my main server will
# then be updated to serve that address in tandem with it's main one.

import os
import subprocess
import sqlite3
from flask import Flask, request, render_template_string, send_file, abort, jsonify, Response
from io import BytesIO
import math
import urllib.parse
import requests
import base64, zlib, os
import time
import logging
from functools import wraps
from flask import request, Response
import base64
import json
from threading import Lock

downloadLogPath = "downloadLogs.json"
downloadLogLock = Lock()

log = logging.getLogger('werkzeug')
log.setLevel(logging.ERROR)

# Paths
DB_FILE = "levels.db"
SAVE_DIR = "./save"
MUSIC_LIB_URL = "https://geometrydashfiles.b-cdn.net/music/musiclibrary_02.dat"
MUSIC_LIB_FILE = "musiclibrary.dat"

# Centralized authentication server URL
AUTH_SERVER_URL = "https://unlisted.ryder7223.hrsn.dev"

# Not needed, no credential storage on this machine
AUTH_USERS = {}

def getUsername():
    authHeader = request.headers.get("Authorization")
    if authHeader is None:
        return "None"
    scheme, encoded = authHeader.split(" ", 1)
    decoded = base64.b64decode(encoded).decode("utf-8")
    username, password = decoded.split(":", 1)
    return username

def logLevelDownload(levelId, username=None):
    logEntry = {
        "timestamp": getFormattedTimestamp(),
        "event": "level_download",
        "levelId": levelId,
        "username": username,
        "clientIp": getClientIp(),
        "userAgent": request.user_agent.string,
        "path": request.path
    }

    with downloadLogLock:
        with open(downloadLogPath, "a", encoding="utf-8") as f:
            f.write(json.dumps(logEntry, ensure_ascii=False) + "\n")

def collectRequestAnalytics():
    requestStart = time.time()
    requestTimestamp = getFormattedTimestamp(requestStart)

    clientIp = request.headers.get("X-Forwarded-For", request.remote_addr)
    userAgent = request.user_agent

    data = []

    # Timestamp
    data.append(f"{requestTimestamp}")

    # Client metadata
    data.append(f"clientIp: {clientIp}")
    data.append(f"userAgentString: {userAgent.string}")
    data.append(f"userAgentPlatform: {userAgent.platform}")
    data.append(f"userAgentBrowser: {userAgent.browser}")
    data.append(f"userAgentVersion: {userAgent.version}")
    data.append(f"acceptLanguages: {request.accept_languages}")
    data.append(f"acceptCharsets: {request.accept_charsets}")
    data.append(f"acceptEncodings: {request.accept_encodings}")
    data.append(f"referrer: {request.referrer}")

    # Request details
    data.append(f"method: {request.method}")
    data.append(f"path: {request.path}")
    data.append(f"fullPath: {request.full_path}")
    data.append(f"url: {request.url}")
    data.append(f"{request.query_string.decode(errors='ignore')}")
    data.append(f"contentLength: {request.content_length}")
    data.append(f"mimeType: {request.mimetype}")

    # Headers
    for key, value in request.headers.items():
        data.append(f"header_{key}: {value}")

    # Server context
    data.append(f"processId: {os.getpid()}")

    # Timing
    requestEnd = time.time()
    elapsedMs = (requestEnd - requestStart) * 1000
    data.append(f"processingDurationMs: {elapsedMs:.3f}")

    return data

def convertTime(timeText):
    parts = timeText.split(":")
    hour = int(parts[0])
    minute = parts[1]
    second = parts[2]

    if hour == 0:
        hour = 12
        suffix = " AM"
    elif hour < 12:
        suffix = " AM"
    elif hour == 12:
        suffix = " PM"
    else:
        hour = hour % 12
        suffix = " PM"

    return f"{hour}:{minute}:{second}{suffix}"

def getFormattedTimestamp(epochTime=None):
    if epochTime is None:
        epochTime = time.time()

    localTime = time.localtime(epochTime)

    datePart = time.strftime("%Y-%m-%d", localTime)
    time24 = time.strftime("%H:%M:%S", localTime)
    time12 = convertTime(time24)

    return f"{datePart} {time12}"

def getClientIp():
    if request.headers.get("X-Forwarded-For"):
        # Handles proxies/load balancers
        return request.headers.get("X-Forwarded-For").split(",")[0].strip()
    return request.remote_addr

def logAuthEvent(event, username=None):
    clientIp = getClientIp()
    timestamp = getFormattedTimestamp()
    print(f"\n[{timestamp}] AUTH {event} | user={username} | ip={clientIp}")

def checkAuth(authHeader):
    """Check authentication by calling the centralized auth server."""
    if not authHeader:
        logAuthEvent("missing_auth_header")
        return False

    try:
        # Call the centralized authentication server
        auth_url = f"{AUTH_SERVER_URL}/api/auth/verify"
        headers = {"Authorization": authHeader}
        
        try:
            response = requests.post(auth_url, headers=headers, timeout=3)
            if response.status_code == 200:
                data = response.json()
                if data.get("valid"):
                    username = data.get("username", "unknown")
                    logAuthEvent("success", username)
                    return True
                else:
                    logAuthEvent("invalid_credentials")
                    return False
            elif response.status_code == 401:
                logAuthEvent("auth_server_rejected")
                return False
            else:
                logAuthEvent(f"auth_server_error:{response.status_code}")
                return False
        except requests.exceptions.RequestException as e:
            logAuthEvent(f"auth_server_unreachable:{str(e)}")
            # Fallback: if auth server is unreachable, deny access for security
            return False

    except Exception as e:
        logAuthEvent(f"auth_exception:{e}")
        return False

def authenticate():
    return Response(
        "Authentication required",
        401,
        {"WWW-Authenticate": 'Basic realm="Protected"'}
    )

def requireAuth(func):
    @wraps(func)
    def wrapper(*args, **kwargs):
        authHeader = request.headers.get("Authorization")
        if not checkAuth(authHeader):
            return authenticate()
        return func(*args, **kwargs)
    return wrapper

# --- GMD Conversion Logic ---
k_tag_map = [
    ("kCEK", "static", 4),
    ("k1", "1"),
    ("k23", "15"),
    ("k2", "2"),
    ("k4", "4"),
    ("k3", "3"),
    ("k21", "static", 3),
    ("k16", "5"),
    ("k17", "13"),
    ("k80", "46"),
    ("k81", "47"),
    ("k64", "37"),
    ("k42", "30"),
    ("k45", "35"),
    ("k50", "static", 45),
    ("k48", "45"),
]

def parseLevelData(data):
    pairs = {}
    parts = data.strip().split(":")
    i = 0
    while i < len(parts) - 1:
        key = parts[i]
        value = parts[i + 1].split(";")[0] if ";" in parts[i + 1] else parts[i + 1]
        pairs[key] = value
        i += 2
    return pairs

def makeGmd(level_id, pairs, username):
    xml = ['<?xml version="1.0"?><plist version="1.0" gjver="2.0"><dict>']
    for ktag, rawkey, *staticval in k_tag_map:
        if rawkey == "static":
            v = staticval[0]
        else:
            v = pairs.get(rawkey)
        if v is None or v == "":
            continue
        tagtype = "s" if ktag in ("k2", "k4", "k3") else "i"
        xml.append(f'<k>{ktag}</k><{tagtype}>{v}</{tagtype}>')
    if username:
        encodedUsername = base64.b64encode(username.encode("utf-8")).decode("ascii")
        xml.append(f"<k>k9988</k><s>{encodedUsername}</s>")
    xml.append('</dict></plist>')
    return ''.join(xml)

def fetchPublicIp():
    response = requests.get("https://api.ipify.org", timeout=5)
    response.raise_for_status()
    return response.text

def findLevelFile(levelId):
    """Find a file like '{ID} - name.txt' in SAVE_DIR recursively.
    If not found, check I:\\Personal\\Games\\Geometry Dash\\Other\\ServerRip if accessible.
    """
    def searchDirectory(directory):
        for root, _, files in os.walk(directory):
            for f in files:
                if f.startswith(f"{levelId} - ") and f.endswith(".txt"):
                    return os.path.join(root, f)
        return None

    # First, search the normal save directory
    result = searchDirectory(SAVE_DIR)
    if result:
        return result

    # If not found, try the alternative path if accessible
    altPath = "/media/ryder7223/New Volume/Personal/Games/Geometry Dash/Other/ServerRip"
    if os.path.exists(altPath) and os.access(altPath, os.R_OK):
        result = searchDirectory(altPath)
        if result:
            return result

    return None

def formatSize(size_str):
    """Convert '11601 B' to readable B/KB/MB."""
    if not size_str:
        return ""
    try:
        num = int(size_str.split()[0])
        if num >= 1024**2:
            return f"{num / (1024**2):.2f} MB"
        elif num >= 1024:
            return f"{num / 1024:.2f} KB"
        else:
            return f"{num} B"
    except Exception:
        return size_str

def parseSizeToInt(size_str):
    """Convert size like '11601 B' to integer bytes for filtering."""
    try:
        return int(size_str.split()[0])
    except:
        return 0

def downloadMusiclibrary(file_name=MUSIC_LIB_FILE):
    if not os.path.exists(file_name):
        r = requests.get(MUSIC_LIB_URL)
        r.raise_for_status()
        with open(file_name, "wb") as f:
            f.write(r.content)

def decodeAndInflate(file_name):
    with open(file_name, "rb") as f:
        encoded = f.read()
    decoded = base64.urlsafe_b64decode(encoded)
    inflated = zlib.decompress(decoded)
    return inflated.decode("utf-8")

def parseMusicLibrary(content):
    version, artists_str, songs_str, tags_str = content.split("|", 3)
    songs = {}
    for entry in songs_str.split(";"):
        if not entry.strip():
            continue
        parts = entry.split(",")
        try:
            song_id = int(parts[0])
        except ValueError:
            continue
        song_name = parts[1] if len(parts) > 1 else f"song_{song_id}"
        songs[song_id] = song_name
    return songs

downloadMusiclibrary()
_music_content = decodeAndInflate(MUSIC_LIB_FILE)
MUSIC_LIBRARY = parseMusicLibrary(_music_content)

# --- Flask App ---
app = Flask(__name__)

HTML = """
<!doctype html>
<html>
<head>
  <title>Level Browser</title>
  <style>
    :root {
      --bg: #f8f9fa;
      --text: #111;
      --card: #ffffff;
      --border: #ccc;
      --muted: #555;
      --accent: #007bff;
      --accentHover: #0056b3;
      --success: #28a745;
      --successHover: #1e7e34;
      --infoBg: #f1f3f5;
    }

    body.dark {
      --bg: #0f1115;
      --text: #cfd3da;
      --card: #1a1d23;
      --border: #2c313a;
      --muted: #9aa0aa;
      --accent: #4da3ff;
      --accentHover: #2f82da;
      --success: #3fbf6f;
      --successHover: #2f9a59;
      --infoBg: #22262e;
    }

    body {
      font-family: sans-serif;
      margin: 2em;
      background: var(--bg);
      color: var(--text);
      transition: background 0.0s, color 0.0s;
    }

    h1 {
      display: flex;
      align-items: center;
      justify-content: space-between;
    }

    .search-bar { margin-bottom: 2em; }

    input, select, button {
      padding: 0.5em;
      margin: 0.3em;
      border: 1px solid var(--border);
      border-radius: 6px;
      background: var(--card);
      color: var(--text);
    }

    button {
      background: var(--accent);
      color: white;
      border: none;
      cursor: pointer;
    }

    button:hover { background: var(--accentHover); }

    .results {
      display: grid;
      grid-template-columns: repeat(auto-fill, minmax(250px, 1fr));
      gap: 1em;
    }

    .card {
      background: var(--card);
      border-radius: 10px;
      box-shadow: 0 2px 6px rgba(0,0,0,0.2);
      padding: 1em;
      position: relative;
    }

    .card h3 { margin: 0; font-size: 1.2em; }
    .card p { margin: 0.3em 0; }

    .download-btn {
      display: inline-block;
      margin-top: 0.5em;
      padding: 0.4em 0.8em;
      background: var(--success);
      color: white;
      text-decoration: none;
      border-radius: 5px;
    }

    .download-btn:hover { background: var(--successHover); }

    .pagination { margin-top: 1em; }
    .pagination input[type="number"] { width: 60px; }

    .info-btn {
      position: absolute;
      top: 6px;
      right: 8px;
      background: none;
      border: none;
      cursor: pointer;
      font-weight: bold;
      color: var(--accent);
    }

    .extra-info {
      display: none;
      margin-top: 0.6em;
      font-size: 0.9em;
      background: var(--infoBg);
      padding: 0.6em;
      border-radius: 6px;
    }

    .extra-info p { margin: 0.2em 0; }

    .theme-toggle {
      font-size: 0.9em;
      padding: 0.4em 0.8em;
    }

    footer {
      margin-top: 3em;
      padding: 1em;
      text-align: center;
      color: var(--muted);
      font-size: 0.9em;
    }

    a { color: var(--accent); }
  </style>  <script>
    function toggleInfo(id) {
      var e = document.getElementById("info-" + id);
      if (e.style.display === "none" || e.style.display === "") {
        e.style.display = "block";
      } else {
        e.style.display = "none";
      }
    }
    function toggleInfo(id) {
      var e = document.getElementById("info-" + id);
      e.style.display = (e.style.display === "block") ? "none" : "block";
    }

    function applyTheme(theme) {
      if (theme === "dark") {
        document.body.classList.add("dark");
      } else {
        document.body.classList.remove("dark");
      }
      localStorage.setItem("theme", theme);
    }

    function toggleTheme() {
      var isDark = document.body.classList.contains("dark");
      applyTheme(isDark ? "light" : "dark");
    }

    document.addEventListener("DOMContentLoaded", function () {
      var savedTheme = localStorage.getItem("theme") || "light";
      applyTheme(savedTheme);
    });
  </script>
</head>
<body>
  <h1>Level Browser</h1>
  <button class="theme-toggle" onclick="toggleTheme()">Toggle Dark Mode</button>
  <form class="search-bar" method="get">
    <input type="text" name="level_id" placeholder="Level ID" value="{{level_id}}">
    <input type="text" name="name" placeholder="Level Name" value="{{name}}">
    <input type="text" name="username" placeholder="Username" value="{{username}}">
    <input type="text" name="description" placeholder="Description" value="{{description}}">
    <input type="text" name="song_id" placeholder="Song IDs (comma-separated)" value="{{song_id}}">

    <!-- New exclusive-search fields -->
    <input type="text" name="original_id" placeholder="OriginalID" value="{{original_id}}">
    <input type="text" name="version" placeholder="Version" value="{{version}}">
    <input type="text" name="length" placeholder="Length (Tiny/Short/...)" value="{{length}}">
    <input type="number" name="rcoins" placeholder="rCoins" value="{{rcoins}}">
    <input type="number" name="scoins" placeholder="sCoins" value="{{scoins}}">
    <input type="number" name="min_editor_time" placeholder="Min EditorTime" value="{{min_editor_time}}">
    <input type="number" name="max_editor_time" placeholder="Max EditorTime" value="{{max_editor_time}}">
    <input type="number" name="editor_ctime" placeholder="EditorCTime" value="{{editor_ctime}}">
    <input type="text" name="requested_rating" placeholder="RequestedRating" value="{{requested_rating}}">
    <select name="two_player">
      <option value="" {% if two_player == "" %}selected{% endif %}>TwoPlayer (Any)</option>
      <option value="Yes" {% if two_player == "Yes" %}selected{% endif %}>Yes</option>
      <option value="No" {% if two_player == "No" %}selected{% endif %}>No</option>
    </select>
    <input type="number" name="min_object_count" placeholder="Min ObjectCount" value="{{min_object_count}}">
    <input type="number" name="max_object_count" placeholder="Max ObjectCount" value="{{max_object_count}}">
    <input type="number" name="player_id" placeholder="Player ID" value="{{player_id}}">

    <input type="number" name="min_cp" placeholder="Min CP" value="{{min_cp}}">
    <input type="number" name="max_cp" placeholder="Max CP" value="{{max_cp}}">
    <input type="number" name="min_size" placeholder="Min Size (B)" value="{{min_size}}">
    <input type="number" name="max_size" placeholder="Max Size (B)" value="{{max_size}}">
    <select name="sort_by">
      <option value="ID" {% if sort_by == "ID" %}selected{% endif %}>Sort by ID</option>
      <option value="CreatorPoints" {% if sort_by == "CreatorPoints" %}selected{% endif %}>Sort by Creator Points</option>
      <option value="Size" {% if sort_by == "Size" %}selected{% endif %}>Sort by Size</option>
    </select>
    <select name="sort_order">
      <option value="asc" {% if sort_order == "asc" %}selected{% endif %}>Ascending</option>
      <option value="desc" {% if sort_order == "desc" %}selected{% endif %}>Descending</option>
    </select>
    <select name="search_mode">
      <option value="exclusive" {% if search_mode == "exclusive" %}selected{% endif %}>Exclusive</option>
      <option value="contains" {% if search_mode == "contains" %}selected{% endif %}>Contains</option>
    </select>
    <select name="case_sensitive">
      <option value="insensitive" {% if case_sensitive == "insensitive" %}selected{% endif %}>Case Insensitive</option>
      <option value="sensitive" {% if case_sensitive == "sensitive" %}selected{% endif %}>Case Sensitive</option>
    </select>
    <input type="number" name="page_size" min="1" value="{{page_size}}" placeholder="Page size">
    <input type="hidden" name="page" value="1">
    <button type="submit">Search</button>
  </form>

  {% if results %}
  <div class="results">
    {% for row in results %}
    <div class="card">
      <button class="info-btn" onclick="toggleInfo({{row[0]}})">(i)</button>
      <h3>{{row[1]}}</h3>
      <p><b>ID:</b> {{row[0]}}</p>
      <p><b>Creator:</b> {{row[2]}}</p>
      <p><b>Player ID:</b> {{row[17]}}</p>
      <p><b>CP:</b> {{row[3]}}</p>
      <p><b>Description:</b> {{row[4]}}</p>
      <p><b>Song IDs:</b> 
        {% for song_id in row[6].split(",") %}
          <a href="/downloadSong/{{ song_id|trim }}">{{ song_id|trim }}</a>{% if not loop.last %}, {% endif %}
        {% endfor %}
      </p>
      <p><b>Size:</b> {{row[5]}}</p>
      <a class="download-btn" href="/download/{{row[0]}}">Download GMD</a>

      <div class="extra-info" id="info-{{row[0]}}">
        <p><b>OriginalID:</b> {{row[7]}}</p>
        <p><b>rCoins:</b> {{row[8]}}</p>
        <p><b>sCoins:</b> {{row[9]}}</p>
        <p><b>Version:</b> {{row[10]}}</p>
        <p><b>Length:</b> {{row[11]}}</p>
        <p><b>EditorTime:</b> {{row[12]}}</p>
        <p><b>EditorCTime:</b> {{row[13]}}</p>
        <p><b>RequestedRating:</b> {{row[14]}}</p>
        <p><b>TwoPlayer:</b> {{row[15]}}</p>
        <p><b>ObjectCount:</b> {{row[16]}}</p>
      </div>
    </div>
    {% endfor %}
  </div>

  <div class="pagination">
    <form method="get" style="display:inline;">
      {% for key, value in request.args.items() %}
        {% if key != "page" %}
          <input type="hidden" name="{{key}}" value="{{value}}">
        {% endif %}
      {% endfor %}
      <button type="submit" name="page" value="{{page-1}}" {% if page <= 1 %}disabled{% endif %}>Previous</button>
    </form>

    Page <form method="get" style="display:inline;">
      <input type="number" name="page" value="{{page}}" min="1" max="{{total_pages}}">
      {% for key, value in request.args.items() %}
        {% if key != "page" %}
          <input type="hidden" name="{{key}}" value="{{value}}">
        {% endif %}
      {% endfor %}
      <button type="submit">Go</button>
    </form>

    <form method="get" style="display:inline;">
      {% for key, value in request.args.items() %}
        {% if key != "page" %}
          <input type="hidden" name="{{key}}" value="{{value}}">
        {% endif %}
      {% endfor %}
      <button type="submit" name="page" value="{{page+1}}" {% if page >= total_pages %}disabled{% endif %}>Next</button>
    </form>

    <p>Page {{page}} of {{total_pages}}</p>
  </div>
  <!-- -->
  <footer style="margin-top:3em; padding:1em; text-align:center; color:#555; font-size:0.9em;">
    Contact: <a href="https://discord.com/users/965846070229884938" style="color:#007bff; text-decoration:none;">Ryder7223</a>
  {% elif searched %}
    <p>No results found.</p>
  {% endif %}
</body>
</html>
"""

def search_levels(level_id, name, username, description, song_id, min_cp, max_cp,
                  min_size, max_size, search_mode, case_sensitive,
                  sort_by, sort_order, page, page_size,
                  original_id, rcoins, scoins, version, length,
                  min_editor_time, max_editor_time, editor_ctime,
                  requested_rating, two_player, min_object_count, max_object_count, player_id):
    conn = sqlite3.connect(DB_FILE)
    cur = conn.cursor()

    select_sql = """
        SELECT
          ID, Name, Username, CreatorPoints, Description, Size, songID,
          OriginalID, rCoins, sCoins, Version, Length, EditorTime, EditorCTime,
          RequestedRating, TwoPlayer, ObjectCount, PlayerID
        FROM levels
        WHERE 1=1
    """

    where = []
    params = []

    # Helper functions
    def exact_text(field, value):
        if value is None or value == "":
            return
        # exact match: use COLLATE to control case for equality (works reliably)
        if case_sensitive == "sensitive":
            where.append(f"{field} = ? COLLATE BINARY")
            params.append(value)
        else:
            where.append(f"{field} = ? COLLATE NOCASE")
            params.append(value)

    def contains_text(field, value):
        if value is None or value == "":
            return
        if case_sensitive == "sensitive":
            # Use instr(...) > 0 for a reliable case-sensitive substring check
            # This avoids relying on LIKE's platform-dependent case rules
            where.append(f"instr({field}, ?) > 0")
            params.append(value)
        else:
            # Case-insensitive substring: use LIKE with NOCASE collation
            where.append(f"{field} LIKE ? COLLATE NOCASE")
            params.append(f"%{value}%")

    def text_filter(field, value, exclusive=None):
        # If exclusive not specified, use global search_mode
        if exclusive is None:
            exclusive = (search_mode == "exclusive")
        if exclusive:
            exact_text(field, value)
        else:
            contains_text(field, value)

    def exact_num(field, value):
        if value is None or value == "":
            return
        where.append(f"{field} != '' AND {field} = ?")
        params.append(value)

    def range_min(field, value):
        if value is None or value == "":
            return
        where.append(f"{field} != '' AND {field} >= ?")
        params.append(value)

    def range_max(field, value):
        if value is None or value == "":
            return
        where.append(f"{field} != '' AND {field} <= ?")
        params.append(value)

    # Level ID (always exact)
    if level_id:
        if case_sensitive == "sensitive":
            where.append("CAST(ID AS TEXT) = ?")
            params.append(level_id)
        else:
            where.append("LOWER(CAST(ID AS TEXT)) = LOWER(?)")
            params.append(level_id)

    # Name, Username, Description
    text_filter("Name", name)
    text_filter("Username", username)
    text_filter("Description", description)

    # Song IDs
    if song_id:
        song_ids = [s.strip() for s in song_id.split(",") if s.strip()]
        for sid in song_ids:
            where.append("(',' || songID || ',') LIKE ?")
            params.append(f"%,{sid},%")

    # New fields
    text_filter("OriginalID", original_id, exclusive=True)
    exact_num("rCoins", rcoins)
    exact_num("sCoins", scoins)
    text_filter("Version", version, exclusive=True)
    text_filter("Length", length, exclusive=True)
    range_min("EditorTime", min_editor_time)
    range_max("EditorTime", max_editor_time)
    exact_num("EditorCTime", editor_ctime)
    text_filter("RequestedRating", requested_rating, exclusive=True)
    if two_player:
        text_filter("TwoPlayer", two_player, exclusive=True)
    range_min("ObjectCount", min_object_count)
    range_max("ObjectCount", max_object_count)
    text_filter("PlayerID", player_id)

    # CP range
    range_min("CreatorPoints", min_cp)
    range_max("CreatorPoints", max_cp)

    # Size range
    if min_size:
        where.append("CAST(REPLACE(Size,' B','') AS INTEGER) >= ?")
        params.append(min_size)
    if max_size:
        where.append("CAST(REPLACE(Size,' B','') AS INTEGER) <= ?")
        params.append(max_size)

    # Assemble final SQL
    sql = select_sql + (" AND " + " AND ".join(where) if where else "")

    # Sorting
    if sort_by == "Size":
        sql += f" ORDER BY CAST(REPLACE(Size,' B','') AS INTEGER) {sort_order.upper()}"
    elif sort_by in ("ID", "CreatorPoints"):
        sql += f" ORDER BY {sort_by} {sort_order.upper()}"

    # Pagination
    offset = (page - 1) * page_size
    sql_with_pagination = sql + " LIMIT ? OFFSET ?"
    params_with_pagination = params + [page_size, offset]

    cur.execute(sql_with_pagination, params_with_pagination)
    results = cur.fetchall()

    # Total count
    count_sql = "SELECT COUNT(*) FROM levels WHERE 1=1" + (" AND " + " AND ".join(where) if where else "")
    cur.execute(count_sql, params)
    total_count = cur.fetchone()[0]

    conn.close()

    results = [(
        row[0], row[1], row[2], row[3], row[4],
        formatSize(row[5]),  # Size formatted
        row[6],  # songID
        row[7],  # OriginalID
        row[8],  # rCoins
        row[9],  # sCoins
        row[10], # Version
        row[11], # Length
        row[12], # EditorTime
        row[13], # EditorCTime
        row[14], # RequestedRating
        row[15], # TwoPlayer
        row[16], # ObjectCount
        row[17]  # PlayerID
    ) for row in results]

    return results, total_count

@app.route("/")
@requireAuth
def index():
    info = collectRequestAnalytics()
    print(f"\n[{getFormattedTimestamp()}] {info[14]}")
    level_id = request.args.get("level_id", "")
    name = request.args.get("name", "")
    username = request.args.get("username", "")
    description = request.args.get("description", "")
    song_id = request.args.get("song_id", "")

    # New fields
    original_id = request.args.get("original_id", "")
    rcoins = request.args.get("rcoins", "")
    scoins = request.args.get("scoins", "")
    version = request.args.get("version", "")
    length = request.args.get("length", "")
    min_editor_time = request.args.get("min_editor_time", "")
    max_editor_time = request.args.get("max_editor_time", "")
    editor_ctime = request.args.get("editor_ctime", "")
    requested_rating = request.args.get("requested_rating", "")
    two_player = request.args.get("two_player", "")
    min_object_count = request.args.get("min_object_count", "")
    max_object_count = request.args.get("max_object_count", "")

    min_cp = request.args.get("min_cp")
    max_cp = request.args.get("max_cp")
    min_size = request.args.get("min_size")
    max_size = request.args.get("max_size")
    player_id = request.args.get("player_id")
    search_mode = request.args.get("search_mode", "contains")
    case_sensitive = request.args.get("case_sensitive", "insensitive")
    sort_by = request.args.get("sort_by", "ID")
    sort_order = request.args.get("sort_order", "desc")
    page_size = int(request.args.get("page_size") or 10)
    page = int(request.args.get("page", 1))

    results, total_count = search_levels(
        level_id, name, username, description, song_id,
        min_cp, max_cp, min_size, max_size,
        search_mode, case_sensitive, sort_by,
        sort_order, page, page_size,
        original_id, rcoins, scoins, version, length,
        min_editor_time, max_editor_time, editor_ctime,
        requested_rating, two_player, min_object_count, max_object_count, player_id
    )

    total_pages = max(1, math.ceil(total_count / page_size))

    return render_template_string(
        HTML,
        level_id=level_id, name=name, username=username,
        description=description, song_id=song_id,
        min_cp=min_cp, max_cp=max_cp,
        min_size=min_size, max_size=max_size,
        search_mode=search_mode, case_sensitive=case_sensitive,
        sort_by=sort_by, sort_order=sort_order,
        results=results, searched=True,
        page=page, page_size=page_size, total_pages=total_pages,
        request=request,
        original_id=original_id, rcoins=rcoins, scoins=scoins,
        version=version, length=length,
        min_editor_time=min_editor_time, max_editor_time=max_editor_time,
        editor_ctime=editor_ctime, requested_rating=requested_rating,
        two_player=two_player, min_object_count=min_object_count,
        max_object_count=max_object_count, player_id=player_id
    )

@app.route("/api/search")
@requireAuth
def apiSearch():
    args = request.args.to_dict(flat=True)

    page = int(args.pop("page", 1))
    pageSize = int(args.pop("page_size", 50))

    results, totalCount = search_levels(
        args.get("level_id", ""),
        args.get("name", ""),
        args.get("username", ""),
        args.get("description", ""),
        args.get("song_id", ""),
        args.get("min_cp"),
        args.get("max_cp"),
        args.get("min_size"),
        args.get("max_size"),
        args.get("search_mode", "contains"),
        args.get("case_sensitive", "insensitive"),
        args.get("sort_by", "ID"),
        args.get("sort_order", "desc"),
        page,
        pageSize,
        args.get("original_id", ""),
        args.get("rcoins", ""),
        args.get("scoins", ""),
        args.get("version", ""),
        args.get("length", ""),
        args.get("min_editor_time", ""),
        args.get("max_editor_time", ""),
        args.get("editor_ctime", ""),
        args.get("requested_rating", ""),
        args.get("two_player", ""),
        args.get("min_object_count", ""),
        args.get("max_object_count", ""),
        args.get("player_id", "")
    )
    results = [row + ("remote",) for row in results]

    return jsonify({
        "results": results,
        "total": totalCount
    })

@app.route("/download/<int:level_id>")
@requireAuth
def download(level_id):
    info = collectRequestAnalytics()
    username = getUsername()
    print(f"\n[{getFormattedTimestamp()}] {username} downloaded level {level_id}")
    logLevelDownload(level_id, username)
    file_path = findLevelFile(str(level_id))
    if not file_path:
        abort(404, description="Level file not found\n\nContact me to enable older downloads, I'll get back to you as fast as I can.")
        #abort(404, description="Level file not found\n\nOlder levels are archived seperately and are thus harder to serve, contact me for specific requests.")

    filename = os.path.splitext(os.path.basename(file_path))[0]  # remove extension
    if " - " in filename:
        _, level_name = filename.split(" - ", 1)
    else:
        level_name = filename

    safe_level_name = "".join(c for c in level_name if c.isalnum() or c in " _-").rstrip()

    with open(file_path, "r", encoding="utf-8") as f:
        data = f.read()
    pairs = parseLevelData(data)
    xml_content = makeGmd(level_id, pairs, username)

    buf = BytesIO(xml_content.encode("utf-8"))
    buf.seek(0)
    return send_file(
        buf,
        as_attachment=True,
        download_name=f"{level_id} - {safe_level_name}.gmd",
        mimetype="application/octet-stream"
    )

@app.route("/downloadSong/<int:songID>")
def downloadSong(songID):
    info = collectRequestAnalytics()
    username = getUsername()
    print(f"\n[{getFormattedTimestamp()}] {username} requested song {songID}")
    try:
        if songID >= 10000000:
            # Direct CDN OGG file
            songURL = f"https://geometrydashfiles.b-cdn.net/music/{songID}.ogg"
            songName = songID #MUSIC_LIBRARY.get(songID, f"song_{songID}")
            mimetype = "audio/ogg"
            ext = "ogg"
        else:
            # Use Boomlings API
            url = "http://www.boomlings.com/database/getGJSongInfo.php"
            data = {
                "secret": "Wmfd2893gb7",
                "binaryVersion": 45,
                "songID": songID
            }
            headers = {"User-Agent": ""}
            response = requests.post(url, data=data, headers=headers)
            #print("\n\n\n\n" + response.text + "\n\n\n\n")
            response.raise_for_status()
            if "-2" in response.text:
                return Response(f"Error: File Not Found. No Audio Project exists with ID {songID}. It may have been deleted, or possibly never existed at all.", status=404)

            level = response.text
            parts = level.split("~|~")
            parsed = {parts[i]: parts[i + 1] for i in range(0, len(parts) - 1, 2)}

            songURL = urllib.parse.unquote(parsed.get("10"))
            songName = songID #parsed.get("2", f"song_{songID}")
            mimetype = "audio/mpeg"
            ext = "mp3"

        # Download file into memory
        r = requests.get(songURL, stream=True)
        r.raise_for_status()
        file_data = BytesIO(r.content)
        def streamRemoteFile(remoteResponse):
            for chunk in remoteResponse.iter_content(chunk_size=4096):
                if chunk:
                    yield chunk
        headers = {"Content-Disposition": f"attachment; filename={songName}.{ext}"}
        # Send back to client
        return Response(
            streamRemoteFile(r),
            headers=headers,
            mimetype=mimetype,
            direct_passthrough=True
        )

    except Exception as e:
        return Response(f"Error downloading song: {e}", status=500)

@app.route("/playID/<int:levelID>")
def playID(levelID):
    info = collectRequestAnalytics()
    username = getUsername()
    print(f"\n[{getFormattedTimestamp()}] {username} requested song for level {levelID}")
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

@app.route("/currentDailySong")
def getDailySong():
    info = collectRequestAnalytics()
    username = getUsername()
    print(f"\n[{getFormattedTimestamp()}] {username} requested Daily")
    songID = getDailySongID(0)
    return downloadSong(songID)

@app.route("/currentWeeklySong")
def getWeeklySong():
    info = collectRequestAnalytics()
    username = getUsername()
    print(f"\n[{getFormattedTimestamp()}] {username} requested Weekly")
    songID = getDailySongID(1)
    return downloadSong(songID)

@app.route("/IP")
def getIP():
    publicIp = fetchPublicIp()
    return publicIp

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000, debug=True)
