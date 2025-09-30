"""
You need these files to be in the same folder as this script:
object.json
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

# -------------------------
# Utilities for parsing .gmd
# -------------------------
def find_value_elem_for_key(dict_elem, key_name):
    """Given a <dict> element (plist-like), find the value element for key_name (e.g. 'k4')"""
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
    # base64 URLsafe often loses padding. Add it back.
    s2 = s.strip()
    missing = len(s2) % 4
    if missing:
        s2 += "=" * (4 - missing)
    return s2

def decode_level_string(level_str):
    """Decode the k4 level string robustly (base64 + gzip or zlib). Returns decoded text (str)."""
    if not level_str:
        raise ValueError("Empty level string.")
    s = level_str.strip()
    # Sometimes the string isn't base64-encoded at all; try quick heuristics.
    # 1) Try URL-safe base64 decode, then try gzip, then zlib (raw), then zlib normal
    s_padded = ensure_b64_padding(s)
    b = None
    try:
        b = base64.urlsafe_b64decode(s_padded.encode('utf-8'))
    except Exception:
        # maybe the string is already decoded/plain
        b = None

    # If base64 decode looks plausible, attempt decompression
    if b is not None:
        # Try gzip
        try:
            if b[:2] == b'\x1f\x8b' or s.startswith('H4sIA'):  # gzip magic or base64 gzip hint
                with gzip.GzipFile(fileobj=io.BytesIO(b)) as f:
                    data = f.read()
                    return data.decode('utf-8', errors='replace')
        except Exception:
            pass
        # Try zlib raw (wbits=-MAX_WBITS)
        try:
            data = zlib.decompress(b, -zlib.MAX_WBITS)
            return data.decode('utf-8', errors='replace')
        except Exception:
            pass
        # Try normal zlib
        try:
            data = zlib.decompress(b)
            return data.decode('utf-8', errors='replace')
        except Exception:
            pass
        # As a last resort, try to decode the bytes directly as utf-8
        try:
            return b.decode('utf-8', errors='replace')
        except Exception:
            pass

    # If we couldn't base64 decode, maybe it's stored plain in the file
    # or it's double-encoded; attempt to detect raw zlib/gzip ascii header:
    if s.startswith('eJ') or s.startswith('x\x9c') or s.startswith('\\x78\\x9c'):
        # try base64 decode again with padding
        try:
            b2 = base64.b64decode(s)
            try:
                return zlib.decompress(b2, -zlib.MAX_WBITS).decode('utf-8', errors='replace')
            except Exception:
                return b2.decode('utf-8', errors='replace')
        except Exception:
            pass

    # As final fallback, return the raw string (some .gmd files store unencoded)
    return s

def parse_level_string(decoded_level):
    """Return (colorString, objectString, prefix_before_color)
    prefix_before_color is everything up to and including the first comma (used when saving).
    """
    if decoded_level is None:
        return '', '', ''
    first_comma = decoded_level.find(',')
    if first_comma == -1:
        # No commas — treat entire string as object data
        return '', decoded_level, ''
    second_comma = decoded_level.find(',', first_comma + 1)
    if second_comma == -1:
        # Only one comma -> no color block
        return '', decoded_level[first_comma + 1:], decoded_level[:first_comma + 1]
    color_string = decoded_level[first_comma + 1:second_comma]
    object_string = decoded_level[second_comma + 1:]
    prefix = decoded_level[:first_comma + 1]
    return color_string, object_string, prefix

def parse_color_data(color_string):
    """Parse color string into list of dicts (each dict contains color keys as in the sample)"""
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
    """Return list of object dicts where keys are the numeric keys as strings"""
    objects = []
    if not object_string:
        return objects
    for obj_chunk in object_string.split(';'):
        if not obj_chunk:
            continue
        parts = obj_chunk.split(',')
        obj = {}
        # parts come as key,value,key,value... but sometimes trailing comma exists
        for i in range(0, len(parts) - 1, 2):
            k = parts[i]
            v = parts[i+1]
            obj[k] = v
        objects.append(obj)
    return objects

# -------------------------
# Plist parsing helper (for spritesheets)
# -------------------------
def parse_plist_frames(plist_path):
    """Parse a cocos2d-style plist (XML) and return a dict of frame_name -> frame_data dict"""
    if not os.path.isfile(plist_path):
        return {}
    try:
        tree = ET.parse(plist_path)
        root = tree.getroot()
        # Find the top-level dict and then the 'frames' key
        frames_dict = None
        for child in root.iter():
            if child.tag == 'dict':
                # iterate children pairwise
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
                    # parse keys inside this dict
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
                                    # fallback: read text if present
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
    """
    rect_string examples:
      "{{10,20},{30,40}}"
      "{10,20,30,40}" (some variants)
      "{10,20},{30,40}"
    Return (x,y,w,h) ints
    """
    if not rect_string:
        return None
    s = rect_string.strip()
    # Remove all braces, then split by non-digit separators keeping negatives
    # But we need to be careful to preserve numbers. Use regex to find ints.
    nums = re.findall(r'-?\d+', s)
    if len(nums) >= 4:
        x, y, w, h = map(int, nums[:4])
        return x, y, w, h
    return None

# -------------------------
# Sprite resolution & transforms
# -------------------------
class SpriteResolver:
    """Resolves and returns PIL.Image objects for objects (with caching)."""
    def __init__(self, search_dir):
        self.dir = search_dir
        self.cache = {}  # key -> PIL.Image
        # Attempt to load object.json if present
        self.object_json = None
        oj_path = os.path.join(self.dir, 'object.json')
        if os.path.isfile(oj_path):
            try:
                with open(oj_path, 'r', encoding='utf-8') as f:
                    self.object_json = json.load(f)
            except Exception:
                self.object_json = None
        # parse plists that are commonly used
        self.frames = {}
        for plist_name in ('GJ_GameSheet-uhd.plist', 'GJ_GameSheet02-uhd.plist', 'GJ_GameSheet.plist', 'GJ_GameSheet02.plist'):
            p = os.path.join(self.dir, plist_name)
            if os.path.isfile(p):
                parsed = parse_plist_frames(p)
                # Attach the spritesheet base png name inference
                # Assume corresponding png is same name but .png
                png_name = plist_name.rsplit('.', 1)[0] + '.png'
                for k, v in parsed.items():
                    v_copy = dict(v)
                    v_copy['__plist_source'] = plist_name
                    v_copy['__spritesheet_png'] = png_name
                    self.frames[k] = v_copy
        # Pre-open spritesheets found
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
        """
        Return a PIL.Image for the object (RGBA), or None if not found.
        Resolution order:
          1) <objid>.png where objid is obj['1']
          2) <blockid>.png where blockid is obj['80']
          3) object.json -> texture name -> splice from spritesheet frames mapping
          4) <texturename>.png in directory
        """
        # Build a cache key from object attributes that identify its graphic
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
                texture_guess = entry.get('frame') or entry.get('Frame') or entry.get('image') or None
                if texture_guess:
                    key_candidates.append(f"frame:{texture_guess}")
            except Exception:
                pass
        # fallback: sometimes '1' is actually block id; include it as fallback filename
        if objid:
            key_candidates.append(f"file:{objid}.png")
        if blockid:
            key_candidates.append(f"file:{blockid}.png")
        if texture_guess:
            key_candidates.append(f"file:{texture_guess}")
    
        for kc in key_candidates:
            if kc in self.cache:
                return self.cache[kc].copy()
    
        # Try direct file by objid
        if objid:
            for ext in ('.png', '.jpg', '.jpeg'):
                fn = f"{objid}{ext}"
                img = self._load_file_image(fn)
                if img:
                    self.cache[f"objid:{objid}"] = img.copy()
                    return img.copy()
    
        # Try blockid file
        if blockid:
            for ext in ('.png', '.jpg', '.jpeg'):
                fn = f"{blockid}{ext}"
                img = self._load_file_image(fn)
                if img:
                    self.cache[f"block:{blockid}"] = img.copy()
                    return img.copy()
                # other naming patterns
                fn2 = f"block_{blockid}{ext}"
                img = self._load_file_image(fn2)
                if img:
                    self.cache[f"block:{blockid}"] = img.copy()
                    return img.copy()
    
        # Try object.json texture + plist frames
        if texture_guess:
            # frame keys sometimes include suffixes like '-uhd', or '@2x', or different naming
            # Try direct exact first
            frame_candidates = [texture_guess]
            # also try with .png or without extension
            if texture_guess.endswith('.png'):
                frame_candidates.append(texture_guess)
                frame_candidates.append(texture_guess[:-4])
            else:
                frame_candidates.append(texture_guess + '.png')
            # Try to find frame in parsed frames
            for fc in frame_candidates:
                if fc in self.frames:
                    frame = self.frames[fc]
                    rect = parse_texture_rect(frame.get('textureRect') or frame.get('frame') or '')
                    if rect:
                        x, y, w, h = rect
                        sheet_name = frame.get('__spritesheet_png', 'GJ_GameSheet-uhd.png')
                        # try to load sheet
                        sheet = self.spritesheets.get(sheet_name)
                        if sheet is None:
                            # maybe sheet exists under other name
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
    
                                # --- FIX: downscale UHD assets ---
                                if '-uhd' in sheet_name.lower():
                                    new_w = max(1, crop.width // 4)
                                    new_h = max(1, crop.height // 4)
                                    crop = crop.resize((new_w, new_h), resample=Image.BICUBIC)
    
                                self.cache[f"frame:{texture_guess}"] = crop.copy()
                                return crop.copy()
                            except Exception:
                                pass
            # If frame not found or cropping failed, try a file named texture_guess in folder
            fn = texture_guess
            if not fn.lower().endswith(('.png', '.jpg', '.jpeg')):
                fn_candidates = [fn + '.png', fn + '.jpg']
            else:
                fn_candidates = [fn]
            for fnc in fn_candidates:
                img = self._load_file_image(fnc)
                if img:
                    self.cache[f"frame:{texture_guess}"] = img.copy()
                    return img.copy()
    
        # Try plain filename heuristics
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
    
        # Nothing found
        return None


def apply_transforms(sprite, obj, color_lookup=None):
    """Apply flips, rotation, scale, opacity, tint (simple multiply) to sprite and return a new image."""
    if sprite is None:
        return None
    img = sprite.copy()

    # Scale: key '32' is generic scale; keys '150' and '151' are scale X/Y in some formats
    # The values might be integers representing percent * 100 or floats; we try to parse.
    scale = 1.0
    try:
        if '32' in obj:
            scale = float(obj.get('32', 1.0))
            if scale == 0:
                scale = 1.0
        # some editors store scale as integer percent (e.g. 100) - guard:
        if scale > 10:  # assume 100 means 1.0
            scale = scale / 100.0
    except Exception:
        scale = 1.0

    scale_x = scale_y = scale
    try:
        if '150' in obj or '151' in obj:
            sx = float(obj.get('150', obj.get('32', scale)))
            sy = float(obj.get('151', obj.get('32', scale)))
            # guard for percent style
            if sx > 10:
                sx = sx / 100.0
            if sy > 10:
                sy = sy / 100.0
            scale_x, scale_y = sx, sy
    except Exception:
        pass
    # Warping support: keys '128' (scaleX warp), '129' (scaleY warp)
    try:
        warp_x = float(obj.get('128', scale_x))
        warp_y = float(obj.get('129', scale_y))
        # Guard for percent style (if > 10 assume 100 means 1.0)
        if warp_x > 10:
            warp_x = warp_x / 100.0
        if warp_y > 10:
            warp_y = warp_y / 100.0
        if warp_x != 1.0 or warp_y != 1.0:
            new_w = max(1, int(round(img.width * warp_x)))
            new_h = max(1, int(round(img.height * warp_y)))
            img = img.resize((new_w, new_h), resample=Image.BICUBIC)
    except Exception:
        pass


    if scale_x != 1.0 or scale_y != 1.0:
        new_w = max(1, int(round(img.width * scale_x)))
        new_h = max(1, int(round(img.height * scale_y)))
        try:
            img = img.resize((new_w, new_h), resample=Image.BICUBIC)
        except Exception:
            img = img.resize((new_w, new_h))

    # Flips
    if obj.get('4') in ('1', 'true', 'True'):
        img = img.transpose(Image.FLIP_LEFT_RIGHT)
    if obj.get('5') in ('1', 'true', 'True'):
        img = img.transpose(Image.FLIP_TOP_BOTTOM)

    # Rotation (key '6' degrees)
    try:
        if '6' in obj:
            rot = float(obj.get('6', 0.0))
            if abs(rot) > 0.0001:
                # Geometry Dash rotation is clockwise degrees; PIL rotates counter-clockwise.
                # We'll negate the angle to match GD's approx orientation.
                img = img.rotate(-rot, expand=True, resample=Image.BICUBIC)
    except Exception:
        pass

    # Opacity (key '35' - 0..100)
    try:
        if '35' in obj:
            op = float(obj.get('35', 100))
            if op <= 0:
                return None
            if op < 100:
                alpha = int(max(0, min(255, round(255 * (op / 100.0)))))
                # ensure img has alpha
                if img.mode != 'RGBA':
                    img = img.convert('RGBA')
                a = img.split()[-1].point(lambda p: int(p * (alpha / 255.0)))
                img.putalpha(a)
    except Exception:
        pass

    # Color tint: object may reference color channels '21' and '22' which refer to colorData entries where key '1','2','3' are r,g,b
    try:
        color_channel = obj.get('21') or obj.get('22')
        if color_channel and color_lookup:
            # color_lookup: mapping channelId -> color dict
            cdict = color_lookup.get(color_channel)
            if cdict:
                r = int(cdict.get('1', 0))
                g = int(cdict.get('2', 0))
                b = int(cdict.get('3', 0))
                # apply a simple multiply tint to RGB channels while preserving alpha
                if img.mode != 'RGBA':
                    img = img.convert('RGBA')
                alpha = img.split()[-1]
                base_rgb = img.convert('RGB')
                color_img = Image.new('RGB', img.size, (r, g, b))
                # multiply
                try:
                    mixed = ImageChops.multiply(base_rgb, color_img)
                    mixed.putalpha(alpha)
                    img = mixed
                except Exception:
                    # fallback: blend
                    tint_overlay = Image.new('RGBA', img.size, (r, g, b, 64))
                    img = Image.alpha_composite(img, tint_overlay)
    except Exception:
        pass

    return img

# -------------------------
# Compose level into image
# -------------------------
def build_level_image(objects, sprite_resolver, color_data_list, padding=64):
    """
    objects: list of object dicts
    sprite_resolver: SpriteResolver instance
    color_data_list: list of color dicts (each has key '6' for channel id)
    """
    if not objects:
        raise ValueError("No objects to render.")

    # build color lookup by channel id (key '6')
    color_lookup = {}
    for col in color_data_list:
        if '6' in col:
            color_lookup[col['6']] = col

    resolved_items = []  # tuples of (obj, image_after_transform, x, y, zsort)
    # iterate and resolve sprites
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

        # Resolve sprite
        sprite = sprite_resolver.resolve(obj)
        if sprite is None:
            continue

        sprite = apply_transforms(sprite, obj, color_lookup=color_lookup)
        if sprite is None:
            continue

        # Geometry Dash coordinates: Y grows upward; PIL origin is top-left.
        # We'll flip Y later when placing.
        zorder = int(obj.get('25', obj.get('24', 0)))  # prefer z-order, fallback to z-layer
        resolved_items.append((obj, sprite, x + offx, y + offy, zorder))

    if not resolved_items:
        raise ValueError("No drawable sprites resolved.")

    # Compute bounds
    min_x = min(x for (_, _, x, _, _) in resolved_items)
    max_x = max(x for (_, img, x, _, _) in resolved_items)
    min_y = min(y for (_, _, _, y, _) in resolved_items)
    max_y = max(y for (_, _, _, y, _) in resolved_items)

    width = int(ceil(max_x - min_x + 2 * padding))
    height = int(ceil(max_y - min_y + 2 * padding))

    # Create canvas (transparent background)
    canvas = Image.new("RGBA", (width, height), (0, 0, 0, 0))

    # Sort items by zorder (ascending, so higher z goes on top)
    resolved_items.sort(key=lambda tup: tup[4])

    for obj, sprite, x, y, z in resolved_items:
        px = int(round(x - min_x + padding - sprite.width / 2))
        py = int(round((max_y - y) + padding - sprite.height / 2))
        try:
            canvas.alpha_composite(sprite, (px, py))
        except Exception:
            # Fallback if alpha_composite fails due to size mismatch
            canvas.paste(sprite, (px, py), sprite)

    return canvas

# -------------------------
# Main entry
# -------------------------
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
        #objects = [obj for obj in objects if obj.get('135') != '1']

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
