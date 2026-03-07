from flask import Flask, request, render_template_string, send_file, Response
import requests
from io import BytesIO
import re

app = Flask(__name__)

HTML = """
<!doctype html>
<title>GD Level Downloader</title>

<h2>Download GMD from Level ID</h2>
<form method="get" action="/download">
  <label for="level_id">Level ID:</label>
  <input type="text" id="level_id" name="level_id" required>
  <button type="submit">Download</button>
</form>

<h2>Convert Raw Level TXT → GMD</h2>
<form method="post" action="/upload" enctype="multipart/form-data">
  <input type="file" name="file" accept=".txt" required>
  <button type="submit">Upload</button>
</form>
"""

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
    ("k48", "45")
]

def parse_level_data(data: str):
    pairs = {}
    parts = data.strip().split(":")
    for i in range(0, len(parts) - 1, 2):
        key = parts[i]
        value = parts[i + 1].split(";")[0]
        pairs[key] = value
    return pairs

def make_gmd(level_id, pairs):
    xml = ['<?xml version="1.0"?><plist version="1.0" gjver="2.0"><dict>']
    for ktag, rawkey, *staticval in k_tag_map:
        if rawkey == "static":
            v = staticval[0]
        else:
            v = pairs.get(rawkey)

        if v is None or v == "":
            continue

        tagType = "s" if ktag in ("k2", "k4", "k3") else "i"
        xml.append(f'<k>{ktag}</k><{tagType}>{v}</{tagType}>')

    xml.append('</dict></plist>')
    return ''.join(xml)

@app.route("/")
def index():
    return render_template_string(HTML)

@app.route("/download")
def download():
    levelId = request.args.get("level_id")
    if not levelId:
        return Response("Missing level_id", status=400)

    url = "http://www.boomlings.com/database/downloadGJLevel22.php"
    data = {"secret": "Wmfd2893gb7", "levelID": levelId}
    headers = {"User-Agent": ""}

    try:
        r = requests.post(url, data=data, headers=headers, timeout=10)
        r.raise_for_status()
    except Exception as e:
        return Response(f"Error fetching level: {e}", status=500)

    if r.text.strip() == "-1":
        return Response("Level not found", status=404)

    pairs = parse_level_data(r.text)
    gmdContent = make_gmd(levelId, pairs)

    levelName = pairs.get("2", f"level_{levelId}")
    safeName = re.sub(r'[^a-zA-Z0-9_ -]', "_", levelName)

    buf = BytesIO(gmdContent.encode("utf-8"))
    buf.seek(0)

    return send_file(
        buf,
        as_attachment=True,
        download_name=f"{levelId} - {safeName}.gmd",
        mimetype="application/octet-stream"
    )

@app.route("/upload", methods=["POST"])
def upload():
    if "file" not in request.files:
        return Response("No file uploaded", status=400)

    file = request.files["file"]

    if file.filename == "":
        return Response("No selected file", status=400)

    try:
        rawData = file.read().decode("utf-8")
    except Exception:
        return Response("Invalid TXT file", status=400)

    pairs = parse_level_data(rawData)
    levelId = pairs.get("1", "txt_level")

    gmdContent = make_gmd(levelId, pairs)

    levelName = pairs.get("2", "txt_level")
    safeName = re.sub(r'[^a-zA-Z0-9_ -]', "_", levelName)

    buf = BytesIO(gmdContent.encode("utf-8"))
    buf.seek(0)

    return send_file(
        buf,
        as_attachment=True,
        download_name=f"{safeName}.gmd",
        mimetype="application/octet-stream"
    )

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5011, debug=True)
