"""
You need these files to be in the same folder as this script:
objects.json
GJ_GameSheet-uhd.plist
GJ_GameSheet02-uhd.plist
GJ_GameSheet.plist
GJ_GameSheet02.plist
GJ_GameSheet-uhd.png
GJ_GameSheet02-uhd.png
GJ_GameSheet.png
GJ_GameSheet02.png
"""

import os
import sys
import io
import re
import json
import base64
import zlib
import gzip
import xml.etree.ElementTree as ET
from math import ceil
from PIL import Image, ImageChops, ImageOps

def find_value_elem_for_key(dict_elem, key_name):
    children = list(dict_elem)
    for i in range(0, len(children) - 1, 2):
        key_elem = children[i]
        val_elem = children[i + 1]
        if (key_elem.tag == 'key' and key_elem.text == key_name) or (key_elem.text == key_name):
            return val_elem
    return None

def find_text_for_key(dict_elem, key_name):
    ve = find_value_elem_for_key(dict_elem, key_name)
    if ve is None:
        return None
    return ve.text

def ensure_b64_padding(s):
    s2 = s.strip()
    missing = len(s2) % 4
    if missing:
        s2 += "=" * (4 - missing)
    return s2

def decode_level_string(level_str):
    if not level_str:
        raise ValueError("Empty level string.")
    s = level_str.strip()
    s_padded = ensure_b64_padding(s)
    b = None
    try:
        b = base64.urlsafe_b64decode(s_padded.encode('utf-8'))
    except Exception:
        b = None

    if b is not None:
        try:
            if b[:2] == b'\x1f\x8b' or s.startswith('H4sIA'):
                with gzip.GzipFile(fileobj=io.BytesIO(b)) as f:
                    data = f.read()
                    return data.decode('utf-8', errors='replace')
        except Exception:
            pass
        try:
            data = zlib.decompress(b, -zlib.MAX_WBITS)
            return data.decode('utf-8', errors='replace')
        except Exception:
            pass
        try:
            data = zlib.decompress(b)
            return data.decode('utf-8', errors='replace')
        except Exception:
            pass
        try:
            return b.decode('utf-8', errors='replace')
        except Exception:
            pass

    if s.startswith('eJ') or s.startswith('x\x9c') or s.startswith('\\x78\\x9c'):
        try:
            b2 = base64.b64decode(s)
            try:
                return zlib.decompress(b2, -zlib.MAX_WBITS).decode('utf-8', errors='replace')
            except Exception:
                return b2.decode('utf-8', errors='replace')
        except Exception:
            pass

    return s

def parse_level_string(decoded_level):
    if decoded_level is None:
        return '', '', ''
    first_comma = decoded_level.find(',')
    if first_comma == -1:
        return '', decoded_level, ''
    second_comma = decoded_level.find(',', first_comma + 1)
    if second_comma == -1:
        return '', decoded_level[first_comma + 1:], decoded_level[:first_comma + 1]
    color_string = decoded_level[first_comma + 1:second_comma]
    object_string = decoded_level[second_comma + 1:]
    prefix = decoded_level[:first_comma + 1]
    return color_string, object_string, prefix

def parse_color_data(color_string):
    colors = []
    if not color_string:
        return colors
    for color_chunk in color_string.split('|'):
        if not color_chunk:
            continue
        parts = color_chunk.split('_')
        d = {}
        for i in range(0, len(parts) - 1, 2):
            k = parts[i]
            v = parts[i+1]
            d[k] = v
        colors.append(d)
    return colors

def parse_object_string(object_string):
    objects = []
    if not object_string:
        return objects
    for obj_chunk in object_string.split(';'):
        if not obj_chunk:
            continue
        parts = obj_chunk.split(',')
        obj = {}
        for i in range(0, len(parts) - 1, 2):
            k = parts[i]
            v = parts[i+1]
            obj[k] = v
        objects.append(obj)
    return objects

def parse_plist_frames(plist_path):
    if not os.path.isfile(plist_path):
        return {}
    try:
        tree = ET.parse(plist_path)
        root = tree.getroot()
        frames_dict = None
        for child in root.iter():
            if child.tag == 'dict':
                child_list = list(child)
                for i in range(0, len(child_list) - 1):
                    k = child_list[i]
                    v = child_list[i + 1]
                    if k.tag == 'key' and k.text == 'frames' and v.tag == 'dict':
                        frames_dict = v
                        break
                if frames_dict is not None:
                    break
        if frames_dict is None:
            return {}
        frames = {}
        elems = list(frames_dict)
        i = 0
        while i < len(elems):
            if elems[i].tag == 'key':
                name = elems[i].text
                if i + 1 < len(elems) and elems[i+1].tag == 'dict':
                    frame_elem = elems[i+1]
                    frame_data = {}
                    j = 0
                    children = list(frame_elem)
                    while j < len(children):
                        if children[j].tag == 'key':
                            keyname = children[j].text
                            if j + 1 < len(children):
                                val = children[j+1]
                                if val.tag == 'string':
                                    frame_data[keyname] = val.text
                                elif val.tag == 'true':
                                    frame_data[keyname] = True
                                elif val.tag == 'false':
                                    frame_data[keyname] = False
                                elif val.tag == 'integer':
                                    frame_data[keyname] = int(val.text)
                                else:
                                    frame_data[keyname] = val.text if val.text is not None else ''
                                j += 2
                            else:
                                j += 1
                        else:
                            j += 1
                    frames[name] = frame_data
                    i += 2
                else:
                    i += 1
            else:
                i += 1
        return frames
    except Exception:
        return {}

def parse_texture_rect(rect_string):
    if not rect_string:
        return None
    s = rect_string.strip()
    nums = re.findall(r'-?\d+', s)
    if len(nums) >= 4:
        x, y, w, h = map(int, nums[:4])
        return x, y, w, h
    return None

class SpriteResolver:
    def __init__(self, search_dir):
        self.dir = search_dir
        self.cache = {}
        self.object_json = None
        oj_path = os.path.join(self.dir, 'object.json')
        if os.path.isfile(oj_path):
            try:
                with open(oj_path, 'r', encoding='utf-8') as f:
                    self.object_json = json.load(f)
            except Exception:
                self.object_json = None
        self.frames = {}
        for plist_name in ('GJ_GameSheet-uhd.plist', 'GJ_GameSheet02-uhd.plist', 'GJ_GameSheet.plist', 'GJ_GameSheet02.plist'):
            p = os.path.join(self.dir, plist_name)
            if os.path.isfile(p):
                parsed = parse_plist_frames(p)
                png_name = plist_name.rsplit('.', 1)[0] + '.png'
                for k, v in parsed.items():
                    v_copy = dict(v)
                    v_copy['__plist_source'] = plist_name
                    v_copy['__spritesheet_png'] = png_name
                    self.frames[k] = v_copy
        self.spritesheets = {}
        for candidate in ('GJ_GameSheet-uhd.png', 'GJ_GameSheet02-uhd.png', 'GJ_GameSheet.png', 'GJ_GameSheet02.png'):
            path = os.path.join(self.dir, candidate)
            if os.path.isfile(path):
                try:
                    self.spritesheets[candidate] = Image.open(path).convert('RGBA')
                except Exception:
                    pass

    def _load_file_image(self, filename):
        path = os.path.join(self.dir, filename)
        if os.path.isfile(path):
            try:
                img = Image.open(path).convert('RGBA')
                return img
            except Exception:
                return None
        return None

    def resolve(self, obj):
        key_candidates = []
        objid = obj.get('1')
        if objid:
            key_candidates.append(f"objid:{objid}")
        blockid = obj.get('80')
        if blockid:
            key_candidates.append(f"block:{blockid}")
        texture_guess = None
        if self.object_json and objid and str(objid) in self.object_json:
            try:
                entry = self.object_json[str(objid)]
                texture_guess = entry.get('texture') or entry.get('Texture') or entry.get('image') or None
                if texture_guess:
                    key_candidates.append(f"texture:{texture_guess}")
            except Exception:
                pass
        if objid:
            key_candidates.append(f"file:{objid}.png")
        if blockid:
            key_candidates.append(f"file:{blockid}.png")
        if texture_guess:
            key_candidates.append(f"file:{texture_guess}")
    
        for kc in key_candidates:
            if kc in self.cache:
                return self.cache[kc].copy()
    
        if objid:
            for ext in ('.png', '.jpg', '.jpeg'):
                fn = f"{objid}{ext}"
                img = self._load_file_image(fn)
                if img:
                    self.cache[f"objid:{objid}"] = img.copy()
                    return img.copy()
    
        if blockid:
            for ext in ('.png', '.jpg', '.jpeg'):
                fn = f"{blockid}{ext}"
                img = self._load_file_image(fn)
                if img:
                    self.cache[f"block:{blockid}"] = img.copy()
                    return img.copy()
                fn2 = f"block_{blockid}{ext}"
                img = self._load_file_image(fn2)
                if img:
                    self.cache[f"block:{blockid}"] = img.copy()
                    return img.copy()
    
        if texture_guess:
            frame_candidates = [texture_guess]
            if texture_guess.endswith('.png'):
                frame_candidates.append(texture_guess)
                frame_candidates.append(texture_guess[:-4])
            else:
                frame_candidates.append(texture_guess + '.png')
            for fc in frame_candidates:
                if fc in self.frames:
                    frame = self.frames[fc]
                    rect = parse_texture_rect(frame.get('textureRect') or frame.get('frame') or '')
                    if rect:
                        x, y, w, h = rect
                        sheet_name = frame.get('__spritesheet_png', 'GJ_GameSheet-uhd.png')
                        sheet = self.spritesheets.get(sheet_name)
                        if sheet is None:
                            sheet = None
                            for sname, simg in self.spritesheets.items():
                                sheet = simg
                                break
                        if sheet is not None:
                            try:
                                if frame.get('textureRotated') in (True, 'true', 'True', '1'):
                                    crop = sheet.crop((x, y, x + h, y + w))
                                    crop = crop.rotate(90, expand=True)
                                else:
                                    crop = sheet.crop((x, y, x + w, y + h))
                                crop = crop.convert('RGBA')
    
                                if '-uhd' in sheet_name.lower():
                                    new_w = max(1, crop.width // 4)
                                    new_h = max(1, crop.height // 4)
                                    crop = crop.resize((new_w, new_h), resample=Image.BICUBIC)
    
                                self.cache[f"texture:{texture_guess}"] = crop.copy()
                                return crop.copy()
                            except Exception:
                                pass
            fn = texture_guess
            if not fn.lower().endswith(('.png', '.jpg', '.jpeg')):
                fn_candidates = [fn + '.png', fn + '.jpg']
            else:
                fn_candidates = [fn]
            for fnc in fn_candidates:
                img = self._load_file_image(fnc)
                if img:
                    self.cache[f"texture:{texture_guess}"] = img.copy()
                    return img.copy()
    
        for prefix in (objid, blockid):
            if not prefix:
                continue
            for ext in ('.png', '.jpg', '.jpeg'):
                candidate = f"{prefix}{ext}"
                img = self._load_file_image(candidate)
                if img:
                    key = f"file:{candidate}"
                    self.cache[key] = img.copy()
                    return img.copy()
    
        return None


def apply_transforms(sprite, obj, color_lookup=None):
    if sprite is None:
        return None
    img = sprite.copy()

    scale = 1.0
    try:
        if '32' in obj:
            scale = float(obj.get('32', 1.0))
            if scale == 0:
                scale = 1.0
        if scale > 10:
            scale = scale / 100.0
    except Exception:
        scale = 1.0

    scale_x = scale_y = scale
    try:
        if '150' in obj or '151' in obj:
            sx = float(obj.get('150', obj.get('32', scale)))
            sy = float(obj.get('151', obj.get('32', scale)))
            if sx > 10:
                sx = sx / 100.0
            if sy > 10:
                sy = sy / 100.0
            scale_x, scale_y = sx, sy
    except Exception:
        pass

    if scale_x != 1.0 or scale_y != 1.0:
        new_w = max(1, int(round(img.width * scale_x)))
        new_h = max(1, int(round(img.height * scale_y)))
        try:
            img = img.resize((new_w, new_h), resample=Image.BICUBIC)
        except Exception:
            img = img.resize((new_w, new_h))

    if obj.get('4') in ('1', 'true', 'True'):
        img = img.transpose(Image.FLIP_LEFT_RIGHT)
    if obj.get('5') in ('1', 'true', 'True'):
        img = img.transpose(Image.FLIP_TOP_BOTTOM)

    try:
        if '6' in obj:
            rot = float(obj.get('6', 0.0))
            if abs(rot) > 0.0001:
                img = img.rotate(-rot, expand=True, resample=Image.BICUBIC)
    except Exception:
        pass

    try:
        if '35' in obj:
            op = float(obj.get('35', 100))
            if op <= 0:
                return None
            if op < 100:
                alpha = int(max(0, min(255, round(255 * (op / 100.0)))))
                if img.mode != 'RGBA':
                    img = img.convert('RGBA')
                a = img.split()[-1].point(lambda p: int(p * (alpha / 255.0)))
                img.putalpha(a)
    except Exception:
        pass

    try:
        color_channel = obj.get('21') or obj.get('22')
        if color_channel and color_lookup:
            cdict = color_lookup.get(color_channel)
            if cdict:
                r = int(cdict.get('1', 0))
                g = int(cdict.get('2', 0))
                b = int(cdict.get('3', 0))
                if img.mode != 'RGBA':
                    img = img.convert('RGBA')
                alpha = img.split()[-1]
                base_rgb = img.convert('RGB')
                color_img = Image.new('RGB', img.size, (r, g, b))
                try:
                    mixed = ImageChops.multiply(base_rgb, color_img)
                    mixed.putalpha(alpha)
                    img = mixed
                except Exception:
                    tint_overlay = Image.new('RGBA', img.size, (r, g, b, 64))
                    img = Image.alpha_composite(img, tint_overlay)
    except Exception:
        pass

    return img

def build_level_image(objects, sprite_resolver, color_data_list, padding=64):
    if not objects:
        raise ValueError("No objects to render.")

    color_lookup = {}
    for col in color_data_list:
        if '6' in col:
            color_lookup[col['6']] = col

    resolved_items = []
    for idx, obj in enumerate(objects):
        try:
            x = float(obj.get('2', 0.0))
            y = float(obj.get('3', 0.0))
            offx = int(obj.get('28', 0))
            offy = int(obj.get('29', 0))
        except Exception:
            x = float(obj.get('2', 0.0))
            y = float(obj.get('3', 0.0))
            offx = offy = 0

        sprite = sprite_resolver.resolve(obj)
        if sprite is None:
            continue

        sprite = apply_transforms(sprite, obj, color_lookup=color_lookup)
        if sprite is None:
            continue

        zorder = int(obj.get('25', obj.get('24', 0)))
        resolved_items.append((obj, sprite, x + offx, y + offy, zorder))

    if not resolved_items:
        raise ValueError("No drawable sprites resolved.")

    min_x = min(x for (_, _, x, _, _) in resolved_items)
    max_x = max(x for (_, img, x, _, _) in resolved_items)
    min_y = min(y for (_, _, _, y, _) in resolved_items)
    max_y = max(y for (_, _, _, y, _) in resolved_items)

    width = int(ceil(max_x - min_x + 2 * padding))
    height = int(ceil(max_y - min_y + 2 * padding))

    canvas = Image.new("RGBA", (width, height), (0, 0, 0, 0))

    resolved_items.sort(key=lambda tup: tup[4])

    for obj, sprite, x, y, z in resolved_items:
        px = int(round(x - min_x + padding - sprite.width / 2))
        py = int(round((max_y - y) + padding - sprite.height / 2))
        try:
            canvas.alpha_composite(sprite, (px, py))
        except Exception:
            canvas.paste(sprite, (px, py), sprite)

    return canvas

def main():
    gmd_file = input("Enter GMD file path: ").strip()
    if not os.path.isfile(gmd_file):
        print(f"File not found: {gmd_file}")
        sys.exit(1)

    try:
        tree = ET.parse(gmd_file)
        root = tree.getroot()
        dict_elem = root.find("dict")
        if dict_elem is None:
            raise ValueError("No <dict> root found in gmd.")

        level_id = find_text_for_key(dict_elem, "k42") or \
                   find_text_for_key(dict_elem, "k38") or \
                   os.path.splitext(os.path.basename(gmd_file))[0]

        level_str = find_text_for_key(dict_elem, "k4")
        if not level_str:
            raise ValueError("No level string (k4) found in gmd.")

        decoded = decode_level_string(level_str)
        color_str, object_str, _ = parse_level_string(decoded)
        colors = parse_color_data(color_str)
        objects = parse_object_string(object_str)

        sprite_resolver = SpriteResolver(os.path.dirname(gmd_file))
        img = build_level_image(objects, sprite_resolver, colors)

        out_path = f"{level_id}.png"
        img.save(out_path)
        print(f"Level rendered and saved as {out_path}")

    except Exception as e:
        print(f"Error: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()
