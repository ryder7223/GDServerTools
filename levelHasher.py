import requests
import base64
import zlib
import gzip
import io
import hashlib

secret = 'Wmfd2893gb7'
url = 'http://www.boomlings.com/database/downloadGJLevel22.php'

def downloadLevel(levelID):
    data = {
        'levelID': levelID,
        'secret': secret
    }
    headers = {'User-Agent': ''}
    response = requests.post(url, data=data, headers=headers)
    return response.text

def decodeLevel(levelData):
    # Split the response into parts and build a key-value dictionary
    parts = levelData.split(":")
    parsed = {}
    for i in range(0, len(parts) - 1, 2):
        key = parts[i]
        value = parts[i + 1]
        parsed[key] = value
    levelStr = parsed.get('4', None)
    if not levelStr:
        raise ValueError('Level has no data.')
    try:
        b64Decoded = base64.urlsafe_b64decode(levelStr.encode())
        if levelStr.startswith('H4sIA'):
            with gzip.GzipFile(fileobj=io.BytesIO(b64Decoded)) as f:
                decompressed = f.read()
        else:
            decompressed = zlib.decompress(b64Decoded, -zlib.MAX_WBITS)
        return decompressed.decode()
    except Exception as e:
        print('Error decoding level data:', e)
        raise

def extractObjectString(decodedLevel):
    firstSemi = decodedLevel.find(';')
    if firstSemi != -1 and firstSemi + 1 < len(decodedLevel):
        return decodedLevel[firstSemi+1:]
    raise ValueError('Object string not found in decoded level.')

def main():
    levelID = input('Enter the level ID: ').strip()
    print(f'Downloading level {levelID}...')
    rawData = downloadLevel(levelID)
    # Split the response into parts and build a key-value dictionary
    parts = rawData.split(":")
    parsed = {}
    for i in range(0, len(parts) - 1, 2):
        key = parts[i]
        value = parts[i + 1]
        parsed[key] = value
    levelStr = parsed.get('4', None)
    if not levelStr:
        raise ValueError('Level has no data.')
    sha256Hash = hashlib.sha256(levelStr.encode('utf-8')).hexdigest()
    print(f'SHA256 checksum of level {levelID}: {sha256Hash}')

if __name__ == '__main__':
    main()
    input()