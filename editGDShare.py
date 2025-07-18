import xml.etree.ElementTree as ET
import base64
import os

# Mapping dictionary for level keys with type information and descriptions
levelKeys = {
    "k1": {"desc": "Level ID", "type": "integer"},
    "k2": {"desc": "Level Name", "type": "string"},
    "k3": {"desc": "Description", "type": "string", "b64": True},
    "k5": {"desc": "Creator", "type": "string"},
    "k6": {"desc": "UserID", "type": "integer"},
    "k7": {"desc": "Level Difficulty", "type": "integer"},
    "k8": {"desc": "Official Song ID", "type": "integer"},
    "k9": {"desc": "Rating", "type": "integer"},
    "k10": {"desc": "RatingSum", "type": "integer"},
    "k11": {"desc": "Downloads", "type": "integer"},
    "k12": {"desc": "Set Completes", "type": "integer"},
    "k13": {"desc": "Is Editable", "type": "bool"},
    "k14": {"desc": "Verified", "type": "bool"},
    "k15": {"desc": "Uploaded", "type": "bool"},
    "k16": {"desc": "Level Version", "type": "integer"},
    "k17": {"desc": "Game Version", "type": "integer"},
    "k18": {"desc": "Attempts", "type": "integer"},
    "k19": {"desc": "Normal Mode Percentage", "type": "integer"},
    "k20": {"desc": "Practice Mode Percentage", "type": "integer"},
    "k21": {"desc": "Level Type", "type": "integer"},
    "k22": {"desc": "Like Rating", "type": "integer"},
    "k23": {"desc": "Length", "type": "string"},
    "k24": {"desc": "Dislikes", "type": "integer"},
    "k25": {"desc": "Is Demon", "type": "bool"},
    "k26": {"desc": "Stars", "type": "integer"},
    "k27": {"desc": "Feature Score", "type": "integer"},
    "k33": {"desc": "Auto", "type": "bool"},
    "k34": {"desc": "Replay Data", "type": "string"},
    "k35": {"desc": "Is Playable?", "type": "bool"},
    "k36": {"desc": "Jumps", "type": "integer"},
    "k37": {"desc": "Required Coins", "type": "integer"},
    "k38": {"desc": "Is Unlocked", "type": "bool"},
    "k39": {"desc": "Level Size", "type": "integer"},
    "k40": {"desc": "Build Version", "type": "integer"},
    "k41": {"desc": "Password", "type": "integer"},
    "k42": {"desc": "Original", "type": "integer"},
    "k43": {"desc": "Two-Player Mode", "type": "bool"},
    "k45": {"desc": "Custom Song ID", "type": "integer"},
    "k46": {"desc": "Level Revision", "type": "integer"},
    "k47": {"desc": "Has Been Modified", "type": "bool"},
    "k48": {"desc": "Object Count", "type": "integer"},
    "k50": {"desc": "Binary Version", "type": "integer"},
    "k51": {"desc": "Capacity 001", "type": "integer"},
    "k52": {"desc": "Capacity 002", "type": "integer"},
    "k53": {"desc": "Capacity 003", "type": "integer"},
    "k54": {"desc": "Capacity 004", "type": "integer"},
    "k60": {"desc": "AccountID", "type": "integer"},
    "k61": {"desc": "First Coin Acquired", "type": "bool"},
    "k62": {"desc": "Second Coin Acquired", "type": "bool"},
    "k63": {"desc": "Third Coin Acquired", "type": "bool"},
    "k64": {"desc": "Total Coins", "type": "integer"},
    "k65": {"desc": "Are Coins Verified", "type": "bool"},
    "k66": {"desc": "Requested Stars", "type": "integer"},
    "k67": {"desc": "Capacity String", "type": "string"},
    "k68": {"desc": "Triggered AntiCheat", "type": "bool"},
    "k69": {"desc": "High Object Count", "type": "bool"},
    "k71": {"desc": "Mana Orb Percentage", "type": "integer"},
    "k72": {"desc": "Has Low Detail Mode", "type": "bool"},
    "k73": {"desc": "Toggle LDM", "type": "bool"},
    "k74": {"desc": "Timely ID", "type": "integer"},
    "k75": {"desc": "Epic Rating", "type": "integer"},
    "k76": {"desc": "Demon Type", "type": "integer"},
    "k77": {"desc": "Is Gauntlet", "type": "bool"},
    "k78": {"desc": "Is Alt Game", "type": "bool"},
    "k79": {"desc": "Unlisted", "type": "bool"},
    "k80": {"desc": "Seconds Spent Editing", "type": "integer"},
    "k81": {"desc": "Seconds spent Editing (copies)", "type": "integer"},
    "k82": {"desc": "Is Level Favourited", "type": "bool"},
    "k83": {"desc": "Level Order", "type": "integer"},
    "k84": {"desc": "Level Folder", "type": "integer"},
    "k85": {"desc": "Clicks", "type": "integer"},
    "k86": {"desc": "Player Time", "type": "integer"},
    "k87": {"desc": "Level Seed", "type": "string"},
    "k88": {"desc": "Level Progress", "type": "string"},
    "k89": {"desc": "vfDChk", "type": "bool"},
    "k90": {"desc": "Leaderboard percentage", "type": "integer"},
    "k95": {"desc": "Verification Time", "type": "integer"},
    "k104": {"desc": "Song list", "type": "string"},
    "k105": {"desc": "SFX list", "type": "string"},
    "k107": {"desc": "Best Time", "type": "integer"},
    "k108": {"desc": "Best Points", "type": "integer"},
    "k109": {"desc": "Local Best Times", "type": "integer"},
    "k110": {"desc": "Local Best Points", "type": "integer"},
    "k111": {"desc": "Platformer Seed", "type": "integer"},
    "k112": {"desc": "No Shake", "type": "bool"}
}

def decode_urlsafe_b64(data):
    missing_padding = len(data) % 4
    if missing_padding:
        data += "=" * (4 - missing_padding)
    try:
        return base64.urlsafe_b64decode(data).decode('utf-8', errors='replace')
    except Exception:
        return data

def encode_urlsafe_b64(data):
    return base64.urlsafe_b64encode(data.encode('utf-8')).decode('utf-8')

def list_level_properties(level_elem):
    properties = []
    children = list(level_elem)
    idx = 1
    for i in range(0, len(children), 2):
        if i+1 >= len(children):
            break
        key_elem = children[i]
        val_elem = children[i+1]
        key = key_elem.text
        if key in levelKeys:
            mapping = levelKeys[key]
            desc = mapping["desc"]
            typ = mapping["type"]
            is_b64 = mapping.get("b64", False)
            if typ == "bool":
                if val_elem.tag == "t":
                    value = "True"
                else:
                    value = "False" if (val_elem.text is None or val_elem.text.strip() == "0") else val_elem.text
            else:
                value = val_elem.text if val_elem.text is not None else ""
                if is_b64:
                    value = decode_urlsafe_b64(value)
            properties.append((idx, key, desc, value, val_elem, typ, is_b64))
            idx += 1
    return properties

def print_available_tags():
    print("Available tags:")
    for k, mapping in levelKeys.items():
        print(f"  {k}: {mapping['desc']} (type: {mapping['type']})")

def main():
    file_name = input("Enter the .gmd file name: ").strip()
    if not os.path.isfile(file_name):
        print("File not found.")
        return
    tree = ET.parse(file_name)
    root = tree.getroot()
    # Find the main <dict> element
    main_dict = root.find("dict")
    if main_dict is None:
        print("Main <dict> element not found in file.")
        return
    
    while True:
        # List all k-keys and their values
        print("\nLevel Properties:")
        props = list_level_properties(main_dict)
        for idx, k_tag, desc, value, _, typ, is_b64 in props:
            print(f"{idx}. {k_tag} ({desc}, type: {typ}{', b64' if is_b64 else ''}): {value}")
        print("\nWhat would you like to do?")
        print("  1. Edit an existing property")
        print("  2. Add a new property")
        print("  3. Remove a property")
        print("  4. Exit and save")
        action = input("Enter 1, 2, 3, or 4: ").strip()
        if action == "1":
            prop_choice = input("Choose a property to edit by number: ").strip()
            if not prop_choice.isdigit():
                print("Invalid property choice.")
                continue
            prop_index = int(prop_choice)
            chosen_prop = None
            for item in props:
                if item[0] == prop_index:
                    chosen_prop = item
                    break
            if not chosen_prop:
                print("Property not found.")
                continue
            print(f"\nCurrent value for {chosen_prop[1]} ({chosen_prop[2]}): {chosen_prop[3]}")
            new_value = input("Enter new value: ")
            # Handle b64 encoding if needed
            if chosen_prop[6]:
                new_value = encode_urlsafe_b64(new_value)
            chosen_prop[4].text = new_value
            print(f"Updated {chosen_prop[1]} to: {new_value}")
        elif action == "2":
            print_available_tags()
            tag_input = input("Enter the tag you want to add (e.g., k45): ").strip()
            if tag_input not in levelKeys:
                print("Tag not found in available tags.")
                continue
            mapping = levelKeys[tag_input]
            new_value = input(f"Enter the new value for {tag_input} ({mapping['desc']}, type: {mapping['type']}): ").strip()
            typ = mapping["type"]
            is_b64 = mapping.get("b64", False)
            if is_b64:
                new_value = encode_urlsafe_b64(new_value)
            if typ == "integer":
                new_val_elem = ET.Element("i")
                new_val_elem.text = new_value
            elif typ == "bool":
                if new_value.lower() in ("true", "1", "yes"):
                    new_val_elem = ET.Element("t")
                else:
                    new_val_elem = ET.Element("s")
                    new_val_elem.text = "0"
            else:
                new_val_elem = ET.Element("s")
                new_val_elem.text = new_value
            new_key_elem = ET.Element("k")
            new_key_elem.text = tag_input
            main_dict.append(new_key_elem)
            main_dict.append(new_val_elem)
            print(f"Added tag {tag_input} with value: {new_value}")
        elif action == "3":
            prop_choice = input("Choose a property to remove by number: ").strip()
            if not prop_choice.isdigit():
                print("Invalid property choice.")
                continue
            prop_index = int(prop_choice)
            chosen_prop = None
            for item in props:
                if item[0] == prop_index:
                    chosen_prop = item
                    break
            if not chosen_prop:
                print("Property not found.")
                continue
            # Remove both the key and value elements from main_dict
            key_elem = None
            val_elem = None
            children = list(main_dict)
            for i in range(0, len(children), 2):
                if i+1 >= len(children):
                    break
                if children[i].text == chosen_prop[1]:
                    key_elem = children[i]
                    val_elem = children[i+1]
                    break
            if key_elem is not None and val_elem is not None:
                main_dict.remove(key_elem)
                main_dict.remove(val_elem)
                print(f"Removed property {chosen_prop[1]} ({chosen_prop[2]})")
            else:
                print("Could not find property elements to remove.")
        elif action == "4":
            out_file = input("Enter the name for the new .gmd file to save: ").strip()
            tree.write(out_file, encoding="utf-8", xml_declaration=True)
            print(f"Saved edited level to {out_file}")
            break
        else:
            print("Invalid selection.")
            continue

if __name__ == "__main__":
    main() 