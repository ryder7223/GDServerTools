'''
How to use:

Enter any level ID or name of a .gmd file in
the same folder as this program. That's it!
'''


import re
import requests
import base64
import zlib
import gzip
import io
import xml.etree.ElementTree as ET

SECRET = 'Wmfd2893gb7'
GD_LEVEL_URL = 'http://www.boomlings.com/database/downloadGJLevel22.php'

def get_level_string_from_gmd(file_name):
    tree = ET.parse(file_name)
    root = tree.getroot()
    main_dict = root.find('dict')
    if main_dict is None:
        raise ValueError('Main <dict> element not found in file.')
    children = list(main_dict)
    for i in range(0, len(children) - 1, 2):
        key_elem = children[i]
        val_elem = children[i + 1]
        if key_elem.text == 'k4':
            return val_elem.text
    raise ValueError('Level string (k4) not found in the .gmd file.')

def download_level(level_id):
    data = {'levelID': level_id, 'secret': SECRET}
    headers = {'User-Agent': ''}
    response = requests.post(GD_LEVEL_URL, data=data, headers=headers)
    return response.text

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

def main():
    arg = input('Enter a level ID or .gmd file name: ').strip()
    # Detect if it's a file or an ID
    if re.match(r'.*\..*', arg):
        # It's a file
        level_string = get_level_string_from_gmd(arg)
        decoded = base64.urlsafe_b64decode(level_string.encode())
        try:
            if level_string.startswith('H4sIA'):
                with gzip.GzipFile(fileobj=io.BytesIO(decoded)) as f:
                    decompressed = f.read()
            else:
                decompressed = zlib.decompress(decoded, -zlib.MAX_WBITS)
            decoded_level = decompressed.decode()
        except Exception as e:
            print('Error decoding level string from file:', e)
            input()
            return
    else:
        # It's a level ID
        try:
            raw_data = download_level(arg)
            decoded_level = decode_level(raw_data)
        except Exception as e:
            print('Error downloading or decoding level:', e)
            input()
            return
    try:
        object_string = extract_object_string(decoded_level)
    except Exception as e:
        print('Error extracting object string:', e)
        input()
        return
    objects = parse_objects(object_string)
    found = False
    counter = 0
    table_rows = []
    for obj in objects:
        if obj.get('1') == '914' and '31' in obj:
            found = True
            counter += 1
            try:
                msg = base64.urlsafe_b64decode(obj['31'].encode()).decode(errors='replace')
                x = obj.get('2', 'N/A')
                y = obj.get('3', 'N/A')
                table_rows.append((counter, msg, x, y))
            except Exception as e:
                table_rows.append((counter, f"Error decoding key 31: {e}", obj.get('2', 'N/A'), obj.get('3', 'N/A')))
    if found:
        # Calculate column widths
        header_row = ("#", "Message", "X", "Y")
        idx_width = max(len(str(row[0])) for row in table_rows + [header_row])
        msg_width = max(len(str(row[1])) for row in table_rows + [header_row])
        x_width = max(len(str(row[2])) for row in table_rows + [header_row])
        y_width = max(len(str(row[3])) for row in table_rows + [header_row])
        # Print header
        header = f"{'#':<{idx_width}}  {'Message':<{msg_width}}  {'X':>{x_width}}  {'Y':>{y_width}}"
        print(header)
        print("-" * len(header))
        # Print rows
        for row in table_rows:
            print(f"{row[0]:<{idx_width}}  {row[1]:<{msg_width}}  {row[2]:>{x_width}}  {row[3]:>{y_width}}")
    else:
        print('No text found.')
    input()

if __name__ == '__main__':
    main()
    input()
