import os
import io
import gzip
import zlib
import base64
import requests
import xml.etree.ElementTree as ET
import matplotlib.pyplot as plt
import numpy as np

SECRET = 'Wmfd2893gb7'
GD_LEVEL_URL = 'http://www.boomlings.com/database/downloadGJLevel22.php'
sectionsNum = 100

# Decode the level string from the raw data
def decode_level(level_data):
    parts = level_data.split("#")[0].split(":")
    parsed = {parts[i]: parts[i + 1] for i in range(0, len(parts) - 1, 2)}
    level_str = parsed.get("4", "")
    b64_decoded = base64.urlsafe_b64decode(level_str.encode())
    if level_str.startswith('H4sIA'):
        with gzip.GzipFile(fileobj=io.BytesIO(b64_decoded)) as f:
            decompressed = f.read()
    else:
        decompressed = zlib.decompress(b64_decoded, -zlib.MAX_WBITS)
    return decompressed.decode()

def download_level(level_id):
    data = {'levelID': level_id, 'secret': SECRET}
    headers = {'User-Agent': ''}
    response = requests.post(GD_LEVEL_URL, data=data, headers=headers)
    return response.text

def decode_level_string(level_str):
    b64_decoded = base64.urlsafe_b64decode(level_str.encode())
    if level_str.startswith('H4sIA'):
        with gzip.GzipFile(fileobj=io.BytesIO(b64_decoded)) as f:
            decompressed = f.read()
    else:
        decompressed = zlib.decompress(b64_decoded, -zlib.MAX_WBITS)
    return decompressed.decode('utf-8', errors='ignore')

def extract_object_string(decoded_level):
    first_semi = decoded_level.find(';')
    if first_semi != -1 and first_semi + 1 < len(decoded_level):
        return decoded_level[first_semi+1:]
    raise ValueError('Object string not found in decoded level.')

def parse_objects(object_string):
    objects = object_string.split(';')
    parsed = []
    for obj in objects:
        if not obj.strip():
            continue
        fields = obj.split(',')
        obj_dict = {}
        for i in range(0, len(fields) - 1, 2):
            key = fields[i]
            value = fields[i+1]
            obj_dict[key] = value
        parsed.append(obj_dict)
    return parsed

def get_level_string_from_gmd(file_path):
    tree = ET.parse(file_path)
    root = tree.getroot()
    main_dict = root.find("dict")
    if main_dict is None:
        raise ValueError("Main <dict> not found in .gmd file.")

    children = list(main_dict)
    for i in range(0, len(children) - 1, 2):
        if children[i].text == 'k4':
            return children[i + 1].text
    raise ValueError("Level string (k4) not found in .gmd file.")

def main():
    user_input = input("Enter a Geometry Dash level ID or a .gmd filename: ").strip()

    try:
        if user_input.lower().endswith('.gmd'):
            if not os.path.exists(user_input):
                raise FileNotFoundError(f"GMD file not found: {user_input}")
            level_string = get_level_string_from_gmd(user_input)
            decoded_level = decode_level_string(level_string)
            level_label = os.path.basename(user_input)
        else:
            raw_data = download_level(user_input)
            decoded_level = decode_level(raw_data)
            level_label = f"ID: {user_input}"

        object_string = extract_object_string(decoded_level)
        objects = parse_objects(object_string)

    except Exception as e:
        print(f"Error: {e}")
        return

    x_positions = []
    for obj in objects:
        x = obj.get('2')
        if x is not None:
            try:
                x_positions.append(float(x))
            except ValueError:
                continue

    if not x_positions:
        print('No x positions found in this level.')
        return

    min_x = min(x_positions)
    max_x = max(x_positions)
    if min_x == max_x:
        print('All objects have the same x position.')
        return

    bins = [min_x + (max_x - min_x) * i / sectionsNum for i in range(sectionsNum + 1)]
    counts, _ = np.histogram(x_positions, bins=bins)

    max_count = max(counts)
    norm_counts = [c / max_count if max_count else 0 for c in counts]

    plt.figure(figsize=(12, 6))
    plt.bar(range(1, sectionsNum + 1), norm_counts, width=1.0, edgecolor='black')
    plt.xlabel(f'Section (1-{sectionsNum})')
    plt.ylabel('Normalized Object Density')
    plt.title(f'Object Density Across Level ({level_label})')
    plt.ylim(0, 1)
    plt.tight_layout()
    plt.show()

if __name__ == '__main__':
    main()
