import os
import re

# Map output k-tags to raw keys or 'lookup'
k_tag_map = [
    ("kCEK", "static", 4),
    ("k1", "1"),
    ("k18", "static", 1),      # hardcoded
    ("k36", "static", 12),     # hardcoded
    ("k23", "15"),
    ("k2", "2"),
    ("k4", "4"),
    ("k5", "creator"),
    ("k95", "57"),
    ("k6", "6"),
    ("k60", "accountID"),
    ("k21", "15"),             # length (from :15)
    ("k16", "5"),              # level version (from :5)
    ("k17", "13"),             # game version (from :13)
    ("k80", "46"),
    ("k81", "47"),
    ("k83", "static", 134),    # hardcoded
    ("k64", "37"),
    ("k41", "41"),
    ("k42", "30"),
    ("k45", "35"),
    ("k50", "static", 45),     # hardcoded
    ("k48", "45"),
]

# Example lookups (replace with your real data)
creator_lookup = {
    "123297488": "Yetta1"
}
account_id_lookup = {
    "123297488": "23965199"
}

def parse_level_data(data):
    pairs = {}
    parts = data.strip().split(":")
    i = 0
    while i < len(parts) - 1:
        key = parts[i]
        value = parts[i+1].split(";")[0] if ";" in parts[i+1] else parts[i+1]
        pairs[key] = value
        i += 2
    return pairs

def make_gmd(level_id, pairs):
    xml = ['<?xml version="1.0"?><plist version="1.0" gjver="2.0"><dict>']
    for ktag, rawkey, *staticval in k_tag_map:
        if rawkey == "static":
            v = staticval[0]
        elif rawkey == "creator":
            v = creator_lookup.get(level_id)
        elif rawkey == "accountID":
            v = account_id_lookup.get(level_id)
        else:
            v = pairs.get(rawkey)
        if v is None or v == "":
            continue
        tagtype = "s" if ktag in ("k2", "k4", "k5") else "i"
        xml.append(f'<k>{ktag}</k><{tagtype}>{v}</{tagtype}>')
    xml.append('</dict></plist>')
    return ''.join(xml)

def main():
    for filename in os.listdir("."):
        if filename.endswith(".txt"):
            txt_path = filename
            gmd_path = filename[:-4] + ".gmd"
            with open(txt_path, "r", encoding="utf-8") as f:
                data = f.read()
            pairs = parse_level_data(data)
            level_id = pairs.get("1")
            xml_content = make_gmd(level_id, pairs)
            with open(gmd_path, "w", encoding="utf-8") as f:
                f.write(xml_content)
            print(f"Converted {filename} to {filename[:-4]}.gmd")

if __name__ == "__main__":
    main() 