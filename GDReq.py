from os import stat
import requests
import base64
from typing import Any, Union, List, Sequence
import hashlib
import re
import gzip
import io
import zlib
import random
import string
import time
from collections import Counter
import xml.etree.ElementTree as ET

class GDReq:

	class Tools:

		class Parsing:

			@staticmethod
			def parseLevelData(levelData: str) -> dict:
				parts = levelData.split("#")[0].split(":")
				return dict(
					sorted({
						parts[i]:
							parts[i+1] for i in range(
								0, len(parts)-1, 2
						)}.items(),
							key=lambda item: int(item[0])
					))

			@staticmethod
			def parseServerKeyValues(row: str) -> dict[str, str]:
				parts = row.split(":")
				if len(parts) % 2 != 0:
					raise ValueError("Colon-delimited row must have an even segment count")
				return {parts[i]: parts[i + 1] for i in range(0, len(parts), 2)}

		class LevelInfo:

			@staticmethod
			def _decodeUrlSafeB64ToText(data: str) -> str:
				try:
					return GDReq.Tools.b64DecodeUrlSafe(data)
				except Exception:
					return data

			@staticmethod
			def _detectSourceType(inputString: str) -> str:
				s = inputString.lstrip()
				if s.startswith("<?xml") or "<plist" in s[:200] or "<dict" in s[:400]:
					return "gmd"
				return "server"

			@staticmethod
			def _parseGmd(gmdXml: str) -> dict[str, Any]:
				root = ET.fromstring(gmdXml)
				mainDict = root.find("dict")
				if mainDict is None:
					mainDict = root.find(".//dict")
				if mainDict is None:
					raise ValueError("Main <dict> element not found in gmd input")

				children = list(mainDict)
				out: dict[str, Any] = {}
				for i in range(0, len(children) - 1, 2):
					kElem = children[i]
					vElem = children[i + 1]
					if kElem.tag != "k":
						continue
					key = kElem.text or ""
					if not key:
						continue

					if vElem.tag == "t":
						value: Any = True
					elif vElem.tag == "f":
						value = False
					elif vElem.tag == "i":
						try:
							value = int(vElem.text or "0")
						except Exception:
							value = vElem.text or ""
					else:
						value = vElem.text if vElem.text is not None else ""

					if key in ("k3",):
						if isinstance(value, str) and value:
							value = GDReq.Tools.LevelInfo._decodeUrlSafeB64ToText(value)

					out[key] = value
				return out

			@staticmethod
			def _parseServerLevel(serverLevel: str) -> dict[str, str]:
				levelPart = serverLevel.split("#", 1)[0].strip()
				return GDReq.Tools.Parsing.parseServerKeyValues(levelPart)

			@staticmethod
			def _decodeServerLevel(serverLevel: str) -> str:
				meta = GDReq.Tools.LevelInfo._parseServerLevel(serverLevel)
				levelStr = meta.get("4", "")
				return GDReq.Tools.Encryption.decodeString(levelStr, 16)

			@staticmethod
			def _parseOffline(decodedLevelString: str) -> dict[str, str]:
				if not decodedLevelString:
					return {}
				semi = decodedLevelString.find(";")
				header = decodedLevelString if semi == -1 else decodedLevelString[:semi]
				parts = header.split(",")
				out: dict[str, str] = {}
				for i in range(0, len(parts) - 1, 2):
					k = parts[i].strip()
					v = parts[i + 1].strip()
					if k:
						out[k] = v
				return out

			@staticmethod
			def _getObjectString(decodedLevelString: str) -> str:
				semi = decodedLevelString.find(";")
				if semi == -1:
					return ""
				return decodedLevelString[semi + 1 :]

			@staticmethod
			def _parseObjects(objectString: str) -> list[dict[str, str]]:
				objects = objectString.split(";")
				parsed: list[dict[str, str]] = []
				for obj in objects:
					if not obj.strip():
						continue
					fields = obj.split(",")
					objDict: dict[str, str] = {}
					for i in range(0, len(fields) - 1, 2):
						objDict[fields[i]] = fields[i + 1]
					parsed.append(objDict)
				return parsed

			@staticmethod
			def getObjectCounts(objectString: str) -> Counter:
				objects = objectString.split(";")
				objectIds: list[str] = []
				for obj in objects:
					if not obj.strip():
						continue
					fields = obj.split(",")
					for i in range(0, len(fields) - 1, 2):
						if fields[i] == "1":
							objId = fields[i + 1]
							if objId == "747":
								objectIds.append(objId)
								objectIds.append(objId)
							elif objId == "31":
								pass
							else:
								objectIds.append(objId)
							break
				return Counter(objectIds)

			@staticmethod
			def getCoinCount(objectString: str) -> int:
				coinCount = 0
				objects = objectString.split(";")
				for obj in objects:
					if not obj.strip():
						continue
					fields = obj.split(",")
					for i in range(0, len(fields) - 1, 2):
						if fields[i] == "1" and fields[i + 1] == "1329":
							coinCount += 1
							break
				return coinCount

			@staticmethod
			def _formatBytes(size: Any) -> str:
				try:
					size = int(size)
				except Exception:
					return "NA"
				for unit in ["B", "KB", "MB", "GB", "TB"]:
					if size < 1024:
						return f"{size:.1f} {unit}"
					size /= 1024
				return f"{size:.1f} PB"

			@staticmethod
			def _secondsToHms(seconds: Any) -> str:
				try:
					seconds = int(seconds)
				except Exception:
					return "NA"
				h = seconds // 3600
				m = (seconds % 3600) // 60
				s = seconds % 60
				return f"{h}h {m}m {s}s"

			@staticmethod
			def _extractPassword(rawData: str) -> str:
				"""
				Extracts level password, will not work on gmd files
				"""
				meta = GDReq.Tools.LevelInfo._parseServerLevel(rawData)
				encoded = meta.get("27", "")
				if encoded in ("", "0", "Aw=="):
					return "(none)"
				try:
					if encoded.isdigit():
						return encoded
					decoded = GDReq.Tools.decodeLevelPassword(encoded)
					decoded = decoded[1:].lstrip("0")
					return decoded if decoded else "(free copy)"
				except Exception:
					return "(error)"

			@staticmethod
			def _getLevelInfo(
				meta: dict[str, str],
				rawData: str,
				decoded: str,
				objectString: str,
				counts: dict,
				coinCount: int
			) -> dict[str, str]:
				info: dict[str, str] = {}
				info["Level Name"] = meta.get("2", "NA")
				info["Level ID"] = meta.get("1", "NA")
				info["Original ID"] = meta.get("30", "NA")
				descB64 = meta.get("3", "")
				try:
					info["Description"] = base64.urlsafe_b64decode(descB64.encode()).decode(errors="replace")
				except Exception:
					info["Description"] = descB64 or "NA"
				info["rCoins"] = str(coinCount)
				info["sCoins"] = meta.get("37", "NA")

				likes = int(meta.get("14", "0")) if meta.get("14", "").lstrip("-").isdigit() else 0
				dislikes = int(meta.get("16", "0")) if meta.get("16", "").lstrip("-").isdigit() else 0
				if likes == 0 and dislikes == 0:
					info["Likes"] = "0"
				elif likes > dislikes:
					info["Likes"] = str(likes - dislikes)
				elif dislikes > likes:
					info["Dislikes"] = str(dislikes - likes)
				else:
					info["Likes"] = str(likes)

				info["Downloads"] = meta.get("10", "NA")
				info["Level Version"] = meta.get("5", "NA")

				lengthMap = {
					"0": "Tiny", "1": "Short", "2": "Medium", "3": "Long", "4": "XL", "5": "Platformer"
				}
				info["Length"] = lengthMap.get(meta.get("15", ""), "NA")
				info["Editor Time"] = GDReq.Tools.LevelInfo._secondsToHms(meta.get("46", "NA"))
				info["Editor (C) Time"] = GDReq.Tools.LevelInfo._secondsToHms(meta.get("47", "NA"))
				info["Uploaded"] = meta.get("28", meta.get("17", "NA"))
				info["Updated"] = meta.get("29", meta.get("18", "NA"))

				gv = meta.get("13", "")
				if gv.isdigit():
					if int(gv) <= 7:
						info["Game Version"] = f"1.{int(gv)-1}"
					elif int(gv) == 10:
						info["Game Version"] = "1.7"
					else:
						info["Game Version"] = f"{int(gv)//10}.{int(gv)%10}"
				else:
					info["Game Version"] = "NA"

				info["Requested Rating"] = meta.get("39", "NA")
				info["songIDs"] = (
					meta.get("12", "")
					if meta.get("12", "") != "0"
					else meta.get("52", "")
					if meta.get("52", "")
					else meta.get("35", "")
				).split("#")[0]
				info["Two-Player"] = "Yes" if meta.get("31", "0") == "1" else "No"
				info["Feature Score"] = meta.get("19", "NA")
				info["Level Size"] = f"{GDReq.Tools.LevelInfo._formatBytes(len(objectString.encode('utf-8')))}"
				info["Password"] = GDReq.Tools.LevelInfo._extractPassword(rawData)
				info["Object Count"] = str(sum(counts.values()))
				return info

			@staticmethod
			def getObjectsById(
				objectString: str,
				objectIds: Sequence[int | str],
				posOnly: bool | None = None
			) -> dict[str, list[dict[str, str]]]:
				"""
				Returns the x and y positions of object ids as a dictionary,
				by default this also includes other object keys and values
				"""
				requested = {str(x) for x in objectIds}
				if not requested:
					return {}

				out: dict[str, list[dict[str, str]]] = {}
				for obj in GDReq.Tools.LevelInfo._parseObjects(objectString):
					objId = obj.get("1")
					if objId is None or objId not in requested:
						continue

					if posOnly:
						entry = {
							"x": obj.get("2", "N/A"),
							"y": obj.get("3", "N/A")
						}
					else:
						entry = {
							"x": obj.get("2", "N/A"),
							"y": obj.get("3", "N/A"),
							"object": obj
						}
					if objId not in out:
						out[objId] = [entry]
					else:
						out[objId].append(entry)
				return out

			@staticmethod
			def getAllLevelInfo(inputString: str, sourceType: str | None = None) -> dict[str, Any]:
				"""
				returns a dictionary containing:
				```py
				["sourceType"],
				["gmdInfo"], # Exists only for GMD level strings
				["serverInfo"], # Exists only for server response level strings
				["startObject"],
				["decodedLevelString"],
				["objectString"],
				["objectIdCounts"],
				["objectCount"],
				["levelInfo"] # Exists only for server response level strings
				```
				Usage:
				```
				sourceType: returns either "gmd" or "server"
				gmdInfo: returns a dictionary of all k values
				serverInfo: is for server response level strings, it returns a dictionary of every key
				startObject: returns a dictionary of all KA Level Start Object values
				decodedLevelString: returns the decoded object data of a level including startObject values
				objectString: returns the decoded object data of a level not including startObject values
				objectIdCounts: returns a dictionary of every object id and how many if each there are
				objectCount: returns the object count of a 
				levelInfo: is for server response level strings, it returns a dictionary of online level info
				```
				levelInfo contains the following values:
				```py
				["Level Name"],
				["Level ID"],
				["Original ID"],
				["Description"],
				["rCoins"],
				["sCoins"],
				["Likes"], # Exists if likes > dislikes
				["Dislikes"], # Exists if dislikes > likes
				["Downloads"],
				["Level Version"],
				["Length"],
				["Editor Time"],
				["Editor (C) Time"],
				["Uploaded"],
				["Updated"],
				["Requested Rating"],
				["songIDs"],
				["Two-Player"],
				["Feature Score"],
				["Level Size"],
				["Password"],
				["Object Count"]
				```
				"""
				if sourceType is None:
					sourceType = GDReq.Tools.LevelInfo._detectSourceType(inputString)
				sourceType = sourceType.lower().strip()

				result: dict[str, Any] = {
					"sourceType": sourceType,
					"gmdInfo": {},
					"serverInfo": {},
					"startObject": {},
					"decodedLevelString": None,
					"objectString": None,
					"objectIdCounts": None,
					"objectCount": None,
				}

				if sourceType == "gmd":
					kTags = GDReq.Tools.LevelInfo._parseGmd(inputString)
					result["gmdInfo"] = kTags
					levelData = kTags.get("k4", "")
					if isinstance(levelData, str) and levelData:
						decoded = GDReq.Tools.Encryption.decodeString(levelData, 16)
						result["decodedLevelString"] = decoded
				elif sourceType == "server":
					serverMeta = GDReq.Tools.LevelInfo._parseServerLevel(inputString)
					result["serverInfo"] = serverMeta
					levelStr = serverMeta.get("4", "")
					if levelStr:
						decoded = GDReq.Tools.Encryption.decodeString(levelStr, 16)
						result["decodedLevelString"] = decoded
				else:
					raise ValueError(f"Unknown sourceType: {sourceType}")

				decodedLevelString = result.get("decodedLevelString")
				if isinstance(decodedLevelString, str) and decodedLevelString:
					startObject = GDReq.Tools.LevelInfo._parseOffline(decodedLevelString)
					objString = GDReq.Tools.LevelInfo._getObjectString(decodedLevelString)
					GDReq.Tools.writeResponse(decodedLevelString)
					result["startObject"] = startObject
					result["objectString"] = objString
					counts = GDReq.Tools.LevelInfo.getObjectCounts(objString) if objString else Counter()
					result["objectIdCounts"] = dict(counts)
					result["objectCount"] = int(sum(counts.values()))
					result["decodedLevelString"] = objString
					if result["serverInfo"]:
						coinCount = GDReq.Tools.LevelInfo.getCoinCount(objString)
						result["levelInfo"] = GDReq.Tools.LevelInfo._getLevelInfo(
							result["serverInfo"], inputString, decodedLevelString, objString, counts, coinCount
						)

				return result

			@staticmethod
			def _parseGmdString(gmdXml: str) -> dict[str, Any]:
				return GDReq.Tools.LevelInfo._parseGmd(gmdXml)

			@staticmethod
			def _parseServerLevelResponse(rawServerResponse: str) -> dict[str, str]:
				return GDReq.Tools.LevelInfo._parseServerLevel(rawServerResponse)

			@staticmethod
			def _decodeLevelStringFromServerLevel(serverRow: str) -> str:
				return GDReq.Tools.LevelInfo._decodeServerLevel(serverRow)

			@staticmethod
			def _parsestartObjectFromDecodedLevelString(decodedLevelString: str) -> dict[str, str]:
				return GDReq.Tools.LevelInfo._parseOffline(decodedLevelString)

			@staticmethod
			def _extractObjectStringFromDecodedLevelString(decodedLevelString: str) -> str:
				return GDReq.Tools.LevelInfo._getObjectString(decodedLevelString)

			@staticmethod
			def _countObjectIds(objectString: str) -> dict:
				return dict(GDReq.Tools.LevelInfo.getObjectCounts(objectString))

		class Encryption:

			@staticmethod
			def decodeString(data: str, type_: int) -> str:
				"""
				```
				Type 1: Player Save Data
				- Type 2:  Player Messages
				- Type 3:  Vault Codes
				Type 4:  Daily Challenges
				Type 5:  Level Password
				Type 6:  Comment Integrity
				Type 7:  Account Password
				Type 8:  Level Leaderboard Integrity
				Type 9:  Level Integrity
				Type 10: Load Data
				Type 11: Multiplayer
				Type 12: Music/SFX Library Secret
				Type 13: Rating Integrity
				Type 14: Chest Rewards
				Type 15: Stat Submission Integrity
				- Type 16: Level Object Data
				```
				"""
				if type_ == 2:
					return GDReq.Tools.xorCipher(
					GDReq.Tools.b64DecodeUrlSafe(data),
					GDReq.Tools.getXorKey(2)
					)

				elif type_ == 3:
					return GDReq.Tools.xorCipher(
						GDReq.Tools.b64DecodeUrlSafe(data),
						GDReq.Tools.getXorKey(3)
					)[:-12]

				elif type_ == 16:
					if not data or data in ("0", "Aw=="):
						return ""
				
					data += "=" * (-len(data) % 4)
				
					for decompressor in [
						lambda x: gzip.GzipFile(fileobj=io.BytesIO(x)).read(),
						lambda x: zlib.decompress(x, -zlib.MAX_WBITS),
						lambda x: x,
					]:
						try:
							return decompressor(
								GDReq.Tools.b64DecodeUrlSafeBytes(data.encode())
								).decode()
				
						except Exception:
							continue
					return ""

				else: return data

			@staticmethod
			def encodeString(data: str, type_: int, useGzip: bool = True) -> str:
				"""
				```
				Type 1: Player Save Data
				- Type 2:  Player Messages
				- Type 3:  Vault Codes
				Type 4:  Daily Challenges
				Type 5:  Level Password
				Type 6:  Comment Integrity
				Type 7:  Account Password
				Type 8:  Level Leaderboard Integrity
				Type 9:  Level Integrity
				Type 10: Load Data
				Type 11: Multiplayer
				Type 12: Music/SFX Library Secret
				Type 13: Rating Integrity
				Type 14: Chest Rewards
				Type 15: Stat Submission Integrity
				- Type 16: Level Object Data
				```
				"""
				if type_ == 2:
					return GDReq.Tools.b64EncodeUrlSafe(
					GDReq.Tools.xorCipher(
						data,
						GDReq.Tools.getXorKey(2))
					)

				elif type_ == 3:
					return GDReq.Tools.b64EncodeUrlSafe(
						GDReq.Tools.xorCipher(
						data + GDReq.Tools.getSalt(8),
						GDReq.Tools.getXorKey(3))
					)

				elif type_ == 16:
					data2 = data.encode()
					if useGzip:
						buf = io.BytesIO()
						with gzip.GzipFile(fileobj=buf, mode="wb", mtime=0) as f:
							f.write(data2)
						compressed = buf.getvalue()
					else:
						compressed = zlib.compress(data2)[2:-4]
					return GDReq.Tools.b64EncodeUrlSafeBytes(compressed).decode()

				else: return data

			@staticmethod
			def encodeLevelStr(decoded: str, useGzip: bool = True) -> str:
				data = decoded.encode()
				if useGzip:
					buf = io.BytesIO()
					with gzip.GzipFile(fileobj=buf, mode="wb", mtime=0) as f:
						f.write(data)
					compressed = buf.getvalue()
				else:
					compressed = zlib.compress(data)[2:-4]
				return GDReq.Tools.b64EncodeUrlSafeBytes(compressed).decode()

		class Hashes:

			_SALT_LEVEL = "xI25fpAapCQg"

			@staticmethod
			def hashGetGJLevels(levelRows: Sequence[dict | Sequence]) -> str:
				"""
				Per-level segments: first digit of level ID, last digit, stars, coin count,
				1 if coins verified else 0. Salt xI25fpAapCQg; result is SHA-1 hex.
				"""
				salt = GDReq.Tools.Hashes._SALT_LEVEL
				parts: list[str] = []
				for row in levelRows:
					if isinstance(row, dict):
						lid = int(row["1"])
						stars = int(row["18"])
						coins = int(row["37"])
						verified = int(row.get("38", 0))
					else:
						lid, stars, coins, verified = (
							int(row[0]), int(row[1]), int(row[2]), int(row[3])
						)
					s = str(lid)
					parts.append(s[0])
					parts.append(s[-1])
					parts.append(str(stars))
					parts.append(str(coins))
					parts.append(str(verified))
				raw = "".join(parts) + salt
				return hashlib.sha1(raw.encode()).hexdigest()

			@staticmethod
			def hashDownloadGJLevel1(levelString: str) -> str:
				"""Undecoded level string sampling + level salt; SHA-1 hex."""
				salt = GDReq.Tools.Hashes._SALT_LEVEL
				if len(levelString) < 41:
					return hashlib.sha1(f"{levelString}{salt}".encode()).hexdigest()
				m = len(levelString) // 40
				sampled = "".join(levelString[i * m] for i in range(40))
				return hashlib.sha1(f"{sampled}{salt}".encode()).hexdigest()

			@staticmethod
			def normalizePasswordForDownloadHash(password: int) -> int:
				"""0 no copy, 1 free copy; otherwise if < 1_000_000 add 1_000_000."""
				if password in (0, 1):
					return password
				if password < 1_000_000:
					return password + 1_000_000
				return password

			@staticmethod
			def hashDownloadGJLevel2(
				playerId: int,
				stars: int,
				demon: int,
				levelId: int,
				coinsVerified: int,
				featureScore: int,
				password: int,
				dailyNumber: int = 0
			) -> str:
				salt = GDReq.Tools.Hashes._SALT_LEVEL
				pw = GDReq.Tools.Hashes.normalizePasswordForDownloadHash(password)
				segments = [
					str(playerId),
					str(stars),
					str(demon),
					str(levelId),
					str(coinsVerified),
					str(featureScore),
					str(pw),
					str(dailyNumber),
				]
				return hashlib.sha1(("".join(segments) + salt).encode()).hexdigest()

			@staticmethod
			def hashGetGJMapPacks(packRows: Sequence[dict | Sequence]) -> str:
				salt = GDReq.Tools.Hashes._SALT_LEVEL
				parts: list[str] = []
				for row in packRows:
					if isinstance(row, dict):
						pid = int(row["1"])
						stars = int(row["4"])
						coins = int(row["5"])
					else:
						pid, stars, coins = int(row[0]), int(row[1]), int(row[2])
					s = str(pid)
					parts.extend((s[0], s[-1], str(stars), str(coins)))
				return hashlib.sha1(("".join(parts) + salt).encode()).hexdigest()

			@staticmethod
			def hashGetGJGauntlets(gauntletRows: Sequence[dict | Sequence]) -> str:
				salt = GDReq.Tools.Hashes._SALT_LEVEL
				parts: list[str] = []
				for row in gauntletRows:
					if isinstance(row, dict):
						gid = str(row["1"])
						levels = str(row["3"])
					else:
						gid, levels = str(row[0]), str(row[1])
					parts.append(gid)
					parts.append(levels)
				return hashlib.sha1(("".join(parts) + salt).encode()).hexdigest()

			@staticmethod
			def hashGetGJChallenges(undecodedResponse: str) -> str:
				"""Full undecoded body without the first 5 characters + challenges salt."""
				salt = GDReq.Tools.getSalt(6)
				return hashlib.sha1((undecodedResponse[5:] + salt).encode()).hexdigest()

			@staticmethod
			def hashGetGJRewards(undecodedResponse: str) -> str:
				salt = GDReq.Tools.getSalt(7)
				return hashlib.sha1((undecodedResponse[5:] + salt).encode()).hexdigest()

		@staticmethod
		def b64EncodeUrlSafe(data: str) -> str:
			return base64.urlsafe_b64encode(data.encode("utf-8")).decode("utf-8")

		@staticmethod
		def b64DecodeUrlSafe(b64: str) -> str:
			return base64.urlsafe_b64decode(b64).decode("utf-8")

		@staticmethod
		def b64DecodeUrlSafeBytes(b64: bytes) -> bytes:
			return base64.urlsafe_b64decode(b64)

		@staticmethod
		def b64EncodeUrlSafeBytes(data: bytes) -> bytes:
			return base64.urlsafe_b64encode(data)

		@staticmethod
		def getSecret(type: int) -> str:
			"""
			Returns any of the 5 secrets.
			These are the options:
			```
			1: Common
			2: Account/MP
			3: Level
			4: Mod
			5: Admin
			```
			"""
			match type:
				case 1:
					return "Wmfd2893gb7"
				case 2:
					return "Wmfv3899gc9"
				case 3:
					return "Wmfv2898gc9"
				case 4:
					return "Wmfp3879gc3"
				case 5:
					return "Wmfx2878gb9"
				case _:
					return "None"

		@staticmethod
		def writeResponse(response: Any,
			fileName: str | None = None,
			extension: str | None = None
			):

			if fileName:
				name = fileName
			else:
				name = "response"

			if extension:
				ext = extension
			else:
				ext = "txt"

			if isinstance(response, bytes):
				with open(f"{name}.{ext}", "wb") as file:
					file.write(response)
			elif isinstance(response, str):
				with open(f"{name}.{ext}", "w") as file:
					file.write(response)
			else:
				with open(f"{name}.{ext}", "w") as file:
					file.write(str(response))

		@staticmethod
		def makeReq(url: str, data: dict):
			response = requests.post(url, data, headers={"User-Agent": ""})
			return response

		@staticmethod
		def checkResponse(response: str) -> bool:
			if re.fullmatch(r"-\d+", response):
				return False
			return True

		@staticmethod
		def xorCipher(data: str, key: int | str) -> str:
			resultChars = []

			# Special case: integer key 11
			if isinstance(key, int):
				if key != 11:
					raise ValueError("Only integer key supported is 11")

				for ch in data:
					byteVal = ord(ch)
					resultChars.append(chr(byteVal ^ key))

				return "".join(resultChars)

			# String key (cyclic XOR)
			if not key:
				raise ValueError("Key must not be empty")

			keyLength = len(key)

			for i, ch in enumerate(data):
				byteVal = ord(ch)
				xKey = ord(key[i % keyLength])
				resultChars.append(chr(byteVal ^ xKey))

			return "".join(resultChars)

		@staticmethod
		def genChk(keyIndex, values: List[Union[int, str]] | None = None, saltIndex: int = 1) -> str:
			salt: str = GDReq.Tools.getSalt(saltIndex)
			key: int | str = GDReq.Tools.getXorKey(keyIndex)
			if values is None:
				values = []

			values.append(salt)

			string = "".join(map(str, values))
			hashed = hashlib.sha1(string.encode()).hexdigest()

			xored = GDReq.Tools.xorCipher(hashed, key)
			chk = GDReq.Tools.b64EncodeUrlSafe(xored)

			return chk
		
		@staticmethod
		def generateClassicLeaderboardSeed(
			jumps: int,
			percentage: int,
			seconds: int,
			hasPlayed: bool = True
		) -> int:
			return (
				1482 * (int(hasPlayed) + 1)
				+ (jumps + 3991) * (percentage + 8354)
				+ ((seconds + 4085) ** 2) - 50028039
			)

		@staticmethod
		def generatePlatformerHash(bestTime, bestPoints):
			number = (((bestTime + 7890) % 34567) * 601 + ((abs(bestPoints) + 3456) % 78901) * 967 + 94819) % 94433
			return ((number ^ number >> 16) * 829) % 77849

		@staticmethod
		def getXorKey(index: int) -> int | str:
			"""
			```
			1:  Key 11:	Player Save Data
			2:  Key 14251: Player Messages
			3:  Key 19283: Vault Codes
			4:  Key 19847: Daily Challenges
			5:  Key 26364: Level Password
			6:  Key 29481: Comment Integrity
			7:  Key 37526: Account Password
			8:  Key 39673: Level Leaderboard Integrity
			9:  Key 41274: Level Integrity
			10: Key 48291: Load Data
			11: Key 52832: Multiplayer
			12: Key 57709: Music/SFX Library Secret
			13: Key 58281: Rating Integrity
			14: Key 59182: Chest Rewards
			15: Key 85271: Stat Submission Integrity
			```
			"""
			match index:
				case 1:
					return 11
				case 2:
					return "14251"
				case 3:
					return "19283"
				case 4:
					return "19847"
				case 5:
					return "26364"
				case 6:
					return "29481"
				case 7:
					return "37526"
				case 8:
					return "39673"
				case 9:
					return "41274"
				case 10:
					return "48291"
				case 11:
					return "52832"
				case 12:
					return "57709"
				case 13:
					return "58281"
				case 14:
					return "59182"
				case 15:
					return "85271"
				case _:
					raise ValueError(f"Invalid XOR key index: {index}")

		@staticmethod
		def getSalt(index: int) -> str:
			"""
			```
			1: xI25fpAapCQg: Level, getGJMapPacks, getGJGauntlets
			2: xPT6iUrtws0J: Comment
			3: ysg6pUrtjn0J: Like or Rate
			4: xI35fsAapCRg: User Profile
			5: yPg6pUrtWn0J: Level Leaderboard
			6: oC36fpYaPtdg: getGJChallenges
			7: pC26fpYaQCtg: getGJRewards
			8: ask2fpcaqCQ2: Vault of Secrets + Chamber of Time Codes
			9: mI29fmAnxgTs: GJP2
			```
			"""
			match index:
				case 1:
					return "xI25fpAapCQg"
				case 2:
					return "xPT6iUrtws0J"
				case 3:
					return "ysg6pUrtjn0J"
				case 4:
					return "xI35fsAapCRg"
				case 5:
					return "yPg6pUrtWn0J"
				case 6:
					return "oC36fpYaPtdg"
				case 7:
					return "pC26fpYaQCtg"
				case 8:
					return "ask2fpcaqCQ2"
				case 9:
					return "mI29fmAnxgTs"
				case _:
					raise ValueError(f"Invalid salt index: {index}")

		@staticmethod
		def generateGjp2(password: str, salt: str | None = None) -> str:
			if salt is None:
				salt = GDReq.Tools.getSalt(9)
			return hashlib.sha1((password + salt).encode()).hexdigest()

		@staticmethod
		def encodeGjp(password: str) -> str:
			xored = GDReq.Tools.xorCipher(password, GDReq.Tools.getXorKey(7))
			b = base64.b64encode(xored.encode()).decode()
			return b.replace("+", "-").replace("/", "_").rstrip("=")

		@staticmethod
		def decodeGjp(gjp: str) -> str:
			padded = gjp + "=" * (-len(gjp) % 4)
			s = padded.replace("-", "+").replace("_", "/")
			raw = base64.b64decode(s.encode()).decode()
			return GDReq.Tools.xorCipher(raw, GDReq.Tools.getXorKey(7))

		@staticmethod
		def encodeLevelPassword(plain: str) -> str:
			xored = GDReq.Tools.xorCipher(plain, GDReq.Tools.getXorKey(5))
			b = base64.b64encode(xored.encode()).decode()
			return b.replace("+", "-").replace("/", "_").rstrip("=")

		@staticmethod
		def decodeLevelPassword(encoded: str) -> str:
			padded = encoded + "=" * (-len(encoded) % 4)
			s = padded.replace("-", "+").replace("_", "/")
			raw = base64.b64decode(s.encode()).decode()
			return GDReq.Tools.xorCipher(raw, GDReq.Tools.getXorKey(5))

		@staticmethod
		def generateRs(length: int = 10) -> str:
			alphabet = string.ascii_letters + string.digits
			return "".join(random.choices(alphabet, k=length))

		@staticmethod
		def generateUuid(parts: Sequence[int] = (8, 4, 4, 4, 10)) -> str:
			return "-".join(GDReq.Tools.generateRs(n) for n in parts)

		@staticmethod
		def generateUdid(
			start: int = 100_000,
			end: int = 100_000_000
		) -> str:
			r = random.randint
			return (
				"S15"
				+ str(r(start, end))
				+ str(r(start, end))
				+ str(r(start, end))
				+ str(r(start, end))
			)

		@staticmethod
		def generateCdnExpires(offsetSeconds: int = 3600) -> int:
			return int(time.time()) + offsetSeconds

		@staticmethod
		def generateCdnToken(endpoint: str, expires: int) -> str:
			payload = f"8501f9c2-75ba-4230-8188-51037c4da102{endpoint}{expires}"
			digestAscii = hashlib.md5(payload.encode()).hexdigest()
			return GDReq.Tools.b64EncodeUrlSafe(digestAscii)

		@staticmethod
		def sampleStringForUploadSeed(data: str, charCount: int = 50) -> str:
			if len(data) < charCount:
				return data
			step = len(data) // charCount
			return data[::step][:charCount]

		@staticmethod
		def generateLevelUploadSeed2(levelString: str) -> str:
			sample = GDReq.Tools.sampleStringForUploadSeed(levelString, 50)
			return GDReq.Tools.genChk(9, [sample], 1)

		@staticmethod
		def generateListSeed2(length: int = 5) -> str:
			alphabet = string.ascii_letters + string.digits
			return "".join(random.choices(alphabet, k=length))

		@staticmethod
		def generateListUploadSeed(listLevels: str, accountId: int, seed2: str) -> str:
			sample = GDReq.Tools.sampleStringForUploadSeed(listLevels, 50)
			digest = hashlib.sha1(f"{sample}{accountId}".encode()).hexdigest()
			return GDReq.Tools.b64EncodeUrlSafe(GDReq.Tools.xorCipher(digest, seed2))

		@staticmethod
		def _randomClientTokenPrefix(length: int = 5) -> str:
			alphabet = "1234567890qwertyuiopasdfghjklzxcvbnmQWERTYUIOPASDFGHJKLZXCVBNM"
			return "".join(random.choices(alphabet, k=length))

		@staticmethod
		def generateQuestChk(
			minDigits: int = 10_000,
			maxDigits: int = 999_999,
			urlSafeB64: bool = True
		) -> str:
			prefix = GDReq.Tools._randomClientTokenPrefix(5)
			num = str(random.randint(minDigits, maxDigits))
			xored = GDReq.Tools.xorCipher(num, GDReq.Tools.getXorKey(4))
			if urlSafeB64:
				return prefix + GDReq.Tools.b64EncodeUrlSafe(xored)
			return prefix + base64.b64encode(xored.encode()).decode()

		@staticmethod
		def generateChestMenuChk(
			minDigits: int = 10_000,
			maxDigits: int = 999_999
		) -> str:
			prefix = GDReq.Tools._randomClientTokenPrefix(5)
			num = str(random.randint(minDigits, maxDigits))
			xored = GDReq.Tools.xorCipher(num, GDReq.Tools.getXorKey(14))
			return prefix + GDReq.Tools.b64EncodeUrlSafe(xored)

		@staticmethod
		def generateWraithRewardChk(
			minDigits: int = 10_000,
			maxDigits: int = 1_000_000
		) -> str:
			prefix = GDReq.Tools._randomClientTokenPrefix(5)
			num = str(random.randint(minDigits, maxDigits))
			xored = GDReq.Tools.xorCipher(num, GDReq.Tools.getXorKey(14))
			return prefix + base64.b64encode(xored.encode()).decode()

		@staticmethod
		def genChkDownloadLevel(
			levelId: int,
			inc: int,
			rs: str,
			accountId: int,
			udid: str,
			uuid: str
		) -> str:
			return GDReq.Tools.genChk(9, [levelId, inc, rs, accountId, udid, uuid], 1)

		@staticmethod
		def genChkRateStars(
			levelId: int,
			stars: int,
			rs: str,
			accountId: int,
			udid: str,
			uuid: str
		) -> str:
			return GDReq.Tools.genChk(13, [levelId, stars, rs, accountId, udid, uuid], 3)

		@staticmethod
		def genChkLikeItem(
			special: int,
			itemId: int,
			like: int,
			type_: int,
			rs: str,
			accountId: int,
			udid: str,
			uuid: str
		) -> str:
			return GDReq.Tools.genChk(
				13, [special, itemId, like, type_, rs, accountId, udid, uuid], 3
			)

		@staticmethod
		def genChkLeaderboard(values: List[Union[int, str]]) -> str:
			return GDReq.Tools.genChk(8, values, 5)

		@staticmethod
		def genChkLevelComment(
			userName: str,
			commentB64: str,
			levelId: int,
			percent: int ,
			commentType: int = 0
		) -> str:
			return GDReq.Tools.genChk(
				6, [userName, commentB64, levelId, percent, commentType], 2
			)

		@staticmethod
		def encodeVaultCode(plain: str) -> str:
			return GDReq.Tools.Encryption.encodeString(plain, 3)

		@staticmethod
		def decodeVaultCode(encoded: str) -> str:
			return GDReq.Tools.Encryption.decodeString(encoded, 3)

		@staticmethod
		def encodeLeaderboardProgressString(differences: Sequence[int]) -> str:
			s = ",".join(str(d) for d in differences)
			xored = GDReq.Tools.xorCipher(s, GDReq.Tools.getXorKey(9))
			return GDReq.Tools.b64EncodeUrlSafe(xored)

		@staticmethod
		def decodeLeaderboardProgressString(encoded: str) -> list[int]:
			raw = GDReq.Tools.xorCipher(GDReq.Tools.b64DecodeUrlSafe(encoded), GDReq.Tools.getXorKey(9))
			if not raw:
				return []
			return [int(x) for x in raw.split(",") if x]

		@staticmethod
		def decodeXorUrlSafeB64Response(
			responseText: str,
			xorKeyIndex: int,
			prefixLen: int = 5
		) -> str:
			encoded = responseText.split("|", 1)[0]
			payload = encoded[prefixLen:]
			decoded = GDReq.Tools.xorCipher(
				GDReq.Tools.b64DecodeUrlSafe(payload),
				GDReq.Tools.getXorKey(xorKeyIndex)
			)
			return decoded

		@staticmethod
		def encodeLevelStringForOfficialPlist(levelString: str) -> str:
			gz = gzip.compress(levelString.encode())
			b64 = base64.urlsafe_b64encode(gz)
			return b64[13:].decode()

		@staticmethod
		def decodeLevelStringFromOfficialPlist(fragment: str) -> str:
			combined = "H4sIAAAAAAAAA" + fragment
			raw = base64.urlsafe_b64decode(combined.encode())
			return zlib.decompress(raw, 15 | 32).decode()


	class Accounts:

		@staticmethod
		def backupGJAccountNew(
			userName: str,
			password: str,
			saveData: str,
			gameVersion: int = 22,
			binaryVersion: int = 47,
			gdw: int | None = None
		) -> str:
			secret = GDReq.Tools.getSecret(2)

			data: dict[str, str | int] = {
				"userName": userName,
				"password": password,
				"saveData": saveData,
				"gameVersion": gameVersion,
				"binaryVersion": binaryVersion,
				"secret": secret
			}

			if gdw is not None:
				data["gdw"] = gdw

			response = GDReq.Tools.makeReq("http://www.robtopgames.org/database/accounts/backupGJAccountNew.php", data)

			if not GDReq.Tools.checkResponse(response.text):
				print(f"backupGJAccountNew Failed: {response.text}")

			return response.text

		@staticmethod
		def loginGJAccount(
			udid: str,
			userName: str,
			password: str,
			sID: str | None = None
		) -> str:
			secret = GDReq.Tools.getSecret(2)

			data: dict[str, str | int] = {
				"udid": udid,
				"userName": userName,
				"password": password,
				"secret": secret
			}
			if sID is not None:
				data["sID"] = sID
			response = GDReq.Tools.makeReq(
				"http://www.boomlings.com/database/accounts/loginGJAccount.php",
				data
			)
			if not GDReq.Tools.checkResponse(response.text):
				print(f"loginGJAccount Failed: {response.text}")
			return response.text

		@staticmethod
		def registerGJAccount(userName: str, password: str, email: str) -> str:
			secret = GDReq.Tools.getSecret(2)

			data: dict[str, str | int] = {
				"userName": userName,
				"password": password,
				"email": email,
				"secret": secret
			}
			response = GDReq.Tools.makeReq(
				"http://www.boomlings.com/database/accounts/registerGJAccount.php",
				data
			)
			if not GDReq.Tools.checkResponse(response.text):
				print(f"registerGJAccount Failed: {response.text}")
			return response.text

		@staticmethod
		def syncGJAccountNew(
			accountID: int,
			gjp2: str,
			gameVersion: int | None = None,
			binaryVersion: int | None = None,
			gdw: int | None = None
		) -> str:
			secret = GDReq.Tools.getSecret(2)

			data: dict[str, str | int] = {
				"accountID": accountID,
				"gjp2": gjp2,
				"secret": secret
			}
			if gameVersion is not None:
				data["gameVersion"] = gameVersion
			if binaryVersion is not None:
				data["binaryVersion"] = binaryVersion
			if gdw is not None:
				data["gdw"] = gdw
			response = GDReq.Tools.makeReq(
				"http://www.robtopgames.org/database/accounts/syncGJAccountNew.php",
				data
			)
			if not GDReq.Tools.checkResponse(response.text):
				print(f"syncGJAccountNew Failed: {response.text}")
			return response.text

		@staticmethod
		def updateGJAccSettings20(
			accountID: int,
			gjp2: str,
			mS: int | None = None,
			frS: int | None = None,
			cS: int | None = None,
			yt: str | None = None,
			twitter: str | None = None,
			twitch: str | None = None
		) -> str:
			secret = GDReq.Tools.getSecret(2)

			data: dict[str, str | int] = {
				"accountID": accountID,
				"gjp2": gjp2,
				"secret": secret
			}
			if mS is not None:
				data["mS"] = mS
			if frS is not None:
				data["frS"] = frS
			if cS is not None:
				data["cS"] = cS
			if yt is not None:
				data["yt"] = yt
			if twitter is not None:
				data["twitter"] = twitter
			if twitch is not None:
				data["twitch"] = twitch
			response = GDReq.Tools.makeReq(
				"http://www.boomlings.com/database/updateGJAccSettings20.php",
				data
			)
			if not GDReq.Tools.checkResponse(response.text):
				print(f"updateGJAccSettings20 Failed: {response.text}")
			return response.text


	class Users:

		@staticmethod
		def getGJScores20(
			accountID: int | None = None,
			gjp2: str | None = None,
			type: str | None = None,
			count: int | None = None,
			gameVersion: int | None = None,
			binaryVersion: int | None = None,
			gdw: int | None = None
		) -> str:
			secret = GDReq.Tools.getSecret(1)

			data: dict[str, str | int] = {
				"secret": secret
			}

			if gameVersion is not None:
				data["gameVersion"] = gameVersion

			if binaryVersion is not None:
				data["binaryVersion"] = binaryVersion

			if gdw is not None:
				data["gdw"] = gdw

			if accountID is not None:
				data["accountID"] = accountID

			if gjp2 is not None:
				data["gjp2"] = gjp2

			if type is not None:
				data["type"] = type  # "top", "relative", "friends", "creators"

			if count is not None:
				# Hard cap at 100 (server-side limit)
				data["count"] = min(count, 100)

			response = GDReq.Tools.makeReq(
				"http://www.boomlings.com/database/getGJScores20.php",
				data
			)

			if not GDReq.Tools.checkResponse(response.text):
				print(f"getGJScores20 Failed: {response.text}")

			return response.text

		@staticmethod
		def getGJUserInfo20(
			targetAccountID: int,
			gameVersion: int | None = None,
			binaryVersion: int | None = None,
			gdw: int | None = None,
			accountID: int | None = None,
			gjp2: str | None = None
			) -> str:
			secret = GDReq.Tools.getSecret(1)

			data: dict[str, str | int] = {
				"targetAccountID": targetAccountID,
				"secret": secret
			}

			if gameVersion is not None:
				data["gameVersion"] = gameVersion

			if binaryVersion is not None:
				data["binaryVersion"] = binaryVersion

			if gdw is not None:
				data["gdw"] = gdw

			if accountID is not None:
				data["accountID"] = accountID

			if gjp2 is not None:
				data["gjp2"] = gjp2

			response = GDReq.Tools.makeReq(
				"http://www.boomlings.com/database/getGJUserInfo20.php",
				data
			)

			if not GDReq.Tools.checkResponse(response.text):
				print(f"getGJUserInfo20 Failed: {response.text}")

			return response.text

		@staticmethod
		def getGJUsers20(
			gameVersion: int | None = None,
			binaryVersion: int | None = None,
			gdw: int | None = None,
			str_: int | None = None,
			page: int | None = None,
			total: int | None = None
			) -> str:
			secret = GDReq.Tools.getSecret(1)

			data: dict[str, str | int] = {
				"secret": secret
			}

			if gameVersion is not None:
				data["gameVersion"] = gameVersion

			if binaryVersion is not None:
				data["binaryVersion"] = binaryVersion

			if gdw is not None:
				data["gdw"] = gdw

			if str_ is not None:
				data["str"] = str_

			if page is not None:
				data["page"] = page

			if total is not None:
				data["total"] = total

			response = GDReq.Tools.makeReq(
				"http://www.boomlings.com/database/getGJUsers20.php",
				data
			)

			if not GDReq.Tools.checkResponse(response.text):
				print(f"getGJUsers20 Failed: {response.text}")

			return response.text

		@staticmethod
		def updateGJUserScore22(
			accountID: int,
			gjp2: str,
			stars: int,
			moons: int,
			demons: int,
			diamonds: int,
			icon: int,
			iconType: int,
			coins: int,
			userCoins: int,
			accIcon: int,
			accShip: int,
			accBall: int,
			accBird: int,
			accDart: int,
			accRobot: int,
			accGlow: int,
			accSpider: int,
			accExplosion: int,
			accSwing: int,
			accJetpack: int,
			dinfo: str,
			dinfow: int,
			dinfog: int,
			sinfo: str,
			sinfod: int,
			sinfog: int,		
			gameVersion: int | None = None,
			binaryVersion: int | None = None,
			gdw: int | None = None,
			userName: str | None = None,
			color1: int | None = None,
			color2: int | None = None,
			color3: int | None = None,
			special: int | None = None,
			seed: str | None = None
		) -> str:
			secret = GDReq.Tools.getSecret(1)

			if seed is None:
				import random
				chars = "1234567890qwertyuiopasdfghjklzxcvbnmQWERTYUIOPASDFGHJKLZXCVBNM"
				seed = "".join(random.sample(chars, 10))

			seed2 = GDReq.Tools.genChk(
				15,
				[
					accountID,
					userCoins,
					demons,
					stars,
					coins,
					iconType,
					icon,
					diamonds,
					accIcon,
					accShip,
					accBall,
					accBird,
					accDart,
					accRobot,
					accGlow,
					accSpider,
					accExplosion,
					len(dinfo.split(",")) if dinfo else 0,
					dinfow,
					dinfog,
					sinfo,
					sinfod,
					sinfog
				],
				4
			)

			data: dict[str, str | int] = {
				"accountID": accountID,
				"gjp2": gjp2,
				"stars": stars,
				"moons": moons,
				"demons": demons,
				"diamonds": diamonds,
				"icon": icon,
				"iconType": iconType,
				"coins": coins,
				"userCoins": userCoins,
				"accIcon": accIcon,
				"accShip": accShip,
				"accBall": accBall,
				"accBird": accBird,
				"accDart": accDart,
				"accRobot": accRobot,
				"accGlow": accGlow,
				"accSpider": accSpider,
				"accExplosion": accExplosion,
				"accSwing": accSwing,
				"accJetpack": accJetpack,
				"dinfo": dinfo,
				"dinfow": dinfow,
				"dinfog": dinfog,
				"sinfo": sinfo,
				"sinfod": sinfod,
				"sinfog": sinfog,
				"seed": seed,
				"seed2": seed2,
				"secret": secret
			}

			if gameVersion is not None:
				data["gameVersion"] = gameVersion

			if binaryVersion is not None:
				data["binaryVersion"] = binaryVersion

			if gdw is not None:
				data["gdw"] = gdw

			if userName is not None:
				data["userName"] = userName

			if color1 is not None:
				data["color1"] = color1

			if color2 is not None:
				data["color2"] = color2

			if color3 is not None:
				data["color3"] = color3

			if special is not None:
				data["special"] = special

			response = GDReq.Tools.makeReq(
				"http://www.boomlings.com/database/updateGJUserScore22.php",
				data
			)

			if not GDReq.Tools.checkResponse(response.text):
				print(f"updateGJUserScore22 Failed: {response.text}")

			return response.text

	class Levels:

		@staticmethod
		def deleteGJLevelUser20(
			accountID: int,
			gjp2: str,
			levelID: int,
			gameVersion: int | None = None,
			binaryVersion: int | None = None,
			gdw: int | None = None
			) -> str:
			secret = GDReq.Tools.getSecret(2)

			data: dict[str, str | int] = {
				"accountID": accountID,
				"gjp2": gjp2,
				"levelID": levelID,
				"secret": secret
			}

			if gameVersion is not None:
				data["gameVersion"] = gameVersion

			if binaryVersion is not None:
				data["binaryVersion"] = binaryVersion

			if gdw is not None:
				data["gdw"] = gdw

			response = GDReq.Tools.makeReq(
				"http://www.boomlings.com/database/deleteGJLevelUser20.php",
				data
			)

			if not GDReq.Tools.checkResponse(response.text):
				print(f"deleteGJLevelUser20 Failed: {response.text}")

			return response.text

		@staticmethod
		def uploadGJLevel21(
			gameVersion: int,
			accountID: int,
			gjp2: str,
			userName: str,
			levelID: int,
			levelName: str,
			levelDesc: str,
			levelVersion: int,
			levelLength: int,
			audioTrack: int,
			auto: int,
			password: int,
			original: int,
			twoPlayer: int,
			songID: int,
			objects: int,
			coins: int,
			requestedStars: int,
			unlisted: int,
			ldm: int,
			levelString: str,
			seed2: str | None = None,
			binaryVersion: int | None = None,
			gdw: int | None = None,
			wt: int | None = None,
			wt2: int | None = None,
			seed: str | None = None,
			extraString: str | None = None,
			levelInfo: str | None = None
		) -> str:
			secret = GDReq.Tools.getSecret(1)
			if seed2 is None:
				seed2 = GDReq.Tools.generateLevelUploadSeed2(levelString)

			data: dict[str, str | int] = {
				"gameVersion": gameVersion,
				"accountID": accountID,
				"gjp2": gjp2,
				"userName": userName,
				"levelID": levelID,
				"levelName": levelName,
				"levelDesc": levelDesc,
				"levelVersion": levelVersion,
				"levelLength": levelLength,
				"audioTrack": audioTrack,
				"auto": auto,
				"password": password,
				"original": original,
				"twoPlayer": twoPlayer,
				"songID": songID,
				"objects": objects,
				"coins": coins,
				"requestedStars": requestedStars,
				"unlisted": unlisted,
				"ldm": ldm,
				"levelString": levelString,
				"seed2": seed2,
				"secret": secret
			}
			if binaryVersion is not None:
				data["binaryVersion"] = binaryVersion

			if gdw is not None:
				data["gdw"] = gdw

			if wt is not None:
				data["wt"] = wt

			if wt2 is not None:
				data["wt2"] = wt2

			if seed is not None:
				data["seed"] = seed

			if extraString is not None:
				data["extraString"] = extraString

			if levelInfo is not None:
				data["levelInfo"] = levelInfo

			response = GDReq.Tools.makeReq(
				"http://www.boomlings.com/database/uploadGJLevel21.php",
				data
			)

			if not GDReq.Tools.checkResponse(response.text):
				print(f"uploadGJLevel21 Failed: {response.text}")

			return response.text

		@staticmethod
		def updateGJDesc20(
			accountID: int,
			gjp2: str,
			levelID: int,
			levelDesc: str,
			gameVersion: int | None = None,
			binaryVersion: int | None = None,
			gdw: int | None = None
		) -> str:
			secret = GDReq.Tools.getSecret(1)

			data: dict[str, str | int] = {
				"accountID": accountID,
				"gjp2": gjp2,
				"levelID": levelID,
				"levelDesc": levelDesc,
				"secret": secret
			}

			if gameVersion is not None:
				data["gameVersion"] = gameVersion

			if binaryVersion is not None:
				data["binaryVersion"] = binaryVersion

			if gdw is not None:
				data["gdw"] = gdw

			response = GDReq.Tools.makeReq(
				"http://www.boomlings.com/database/updateGJDesc20.php",
				data
			)

			if not GDReq.Tools.checkResponse(response.text):
				print(f"updateGJDesc20 Failed: {response.text}")

			return response.text

		@staticmethod
		def suggestGJStars(
			gameVersion: int,
			binaryVersion: int,
			accountID: int,
			gjp2: str,
			levelID: int,
			stars: int,
			feature: int,
			gdw: int = 0
		) -> str:
			secret = GDReq.Tools.getSecret(4)

			data: dict[str, str | int] = {
				"gameVersion": gameVersion,
				"binaryVersion": binaryVersion,
				"accountID": accountID,
				"gjp2": gjp2,
				"levelID": levelID,
				"stars": stars,
				"feature": feature,
				"gdw": gdw,
				"secret": secret
			}

			response = GDReq.Tools.makeReq(
				"http://www.boomlings.com/database/suggestGJStars20.php",
				data
			)

			if not GDReq.Tools.checkResponse(response.text):
				print(f"suggestGJStars Failed: {response.text}")

			return response.text

		@staticmethod
		def reportGJLevel(levelID: int | None = None) -> str:
			secret = GDReq.Tools.getSecret(1)

			data: dict[str, str | int] = {
				"secret": secret
			}

			if levelID is not None:
				data["levelID"] = levelID
			response = GDReq.Tools.makeReq(
				"http://www.boomlings.com/database/reportGJLevel.php",
				data
			)
			if not GDReq.Tools.checkResponse(response.text):
				print(f"reportGJLevel Failed: {response.text}")
			return response.text

		@staticmethod
		def rateGJStars211(
			levelID: int,
			stars: int,
			rs: str | None = None,
			accountID: int | None = None,
			gjp2: str | None = None,
			udid: str | None = None,
			uuid: str | None = None,
			chk: str | None = None,
			gameVersion: int | None = None,
			binaryVersion: int | None = None,
			gdw: int | None = None
		) -> str:
			secret = GDReq.Tools.getSecret(1)
			if chk is None and (rs is not None and
								accountID is not None and
								udid is not None and
								uuid is not None):
				chk = GDReq.Tools.genChkRateStars(
					levelID, stars, rs, accountID, udid, uuid
				)

			data: dict[str, str | int] = {
				"levelID": levelID,
				"stars": stars,
				"secret": secret
			}

			if rs is not None:
				data["rs"] = rs

			if accountID is not None:
				data["accountID"] = accountID

			if gjp2 is not None:
				data["gjp2"] = gjp2

			if udid is not None:
				data["udid"] = udid

			if uuid is not None:
				data["uuid"] = uuid

			if chk is not None:
				data["chk"] = chk

			if gameVersion is not None:
				data["gameVersion"] = gameVersion

			if binaryVersion is not None:
				data["binaryVersion"] = binaryVersion

			if gdw is not None:
				data["gdw"] = gdw

			response = GDReq.Tools.makeReq(
				"http://www.boomlings.com/database/rateGJStars211.php",
				data
			)

			if not GDReq.Tools.checkResponse(response.text):
				print(f"rateGJStars211 Failed: {response.text}")

			return response.text

		@staticmethod
		def rateGJDemon21(
			gameVersion: int,
			binaryVersion: int,
			accountID: int,
			gjp2: str,
			levelID: int,
			rating: int,
			gdw: int | None = None
		) -> str:
			secret = GDReq.Tools.getSecret(4)

			data: dict[str, str | int] = {
				"gameVersion": gameVersion,
				"binaryVersion": binaryVersion,
				"accountID": accountID,
				"gjp2": gjp2,
				"levelID": levelID,
				"rating": rating,
				"secret": secret
			}

			if gdw is not None:
				data["gdw"] = gdw

			response = GDReq.Tools.makeReq(
				"http://www.boomlings.com/database/rateGJDemon21.php",
				data
			)

			if not GDReq.Tools.checkResponse(response.text):
				print(f"rateGJDemon21 Failed: {response.text}")

			return response.text

		@staticmethod
		def getGJMapPacks21(
			gameVersion: int | None = None,
			binaryVersion: int | None = None,
			gdw: int | None = None,
			page: int | None = None
		) -> str:
			secret = GDReq.Tools.getSecret(1)

			data: dict[str, str | int] = {
				"secret": secret
			}

			if gameVersion is not None:
				data["gameVersion"] = gameVersion

			if binaryVersion is not None:
				data["binaryVersion"] = binaryVersion

			if gdw is not None:
				data["gdw"] = gdw

			if page is not None:
				data["page"] = page

			response = GDReq.Tools.makeReq(
				"http://www.boomlings.com/database/getGJMapPacks21.php",
				data
			)

			if not GDReq.Tools.checkResponse(response.text):
				print(f"getGJMapPacks21 Failed: {response.text}")

			return response.text

		@staticmethod
		def getGJGauntlets21(
			gameVersion: int | None = None,
			binaryVersion: int | None = None,
			gdw: int | None = None,
			special: int | None = None
		) -> str:
			secret = GDReq.Tools.getSecret(1)

			data: dict[str, str | int] = {
				"secret": secret
			}

			if gameVersion is not None:
				data["gameVersion"] = gameVersion

			if binaryVersion is not None:
				data["binaryVersion"] = binaryVersion

			if gdw is not None:
				data["gdw"] = gdw

			if special is not None:
				data["special"] = special

			response = GDReq.Tools.makeReq(
				"http://www.boomlings.com/database/getGJGauntlets21.php",
				data
			)

			if not GDReq.Tools.checkResponse(response.text):
				print(f"getGJGauntlets21 Failed: {response.text}")

			return response.text

		@staticmethod
		def getGJDailyLevel(
			gameVersion: int | None = None,
			binaryVersion: int | None = None,
			gdw: int | None = None,
			accountID: int | None = None,
			gjp2: str | None = None,
			weekly: int | None = None
		) -> str:
			secret = GDReq.Tools.getSecret(1)

			data: dict[str, str | int] = {
				"secret": secret
			}

			if gameVersion is not None:
				data["gameVersion"] = gameVersion

			if binaryVersion is not None:
				data["binaryVersion"] = binaryVersion

			if gdw is not None:
				data["gdw"] = gdw

			if accountID is not None:
				data["accountID"] = accountID

			if gjp2 is not None:
				data["gjp2"] = gjp2

			if weekly is not None:
				data["weekly"] = weekly

			response = GDReq.Tools.makeReq(
				"http://www.boomlings.com/database/getGJDailyLevel.php",
				data
			)

			if not GDReq.Tools.checkResponse(response.text):
				print(f"getGJDailyLevel Failed: {response.text}")

			return response.text

		@staticmethod
		def downloadGJLevel22(
			levelID: int,
			gameVersion: int | None = None,
			binaryVersion: int | None = None,
			gdw: int | None = None,
			accountID: int | None = None,
			gjp2: str | None = None,
			udid: str | None = None,
			uuid: str | None = None,
			inc: int | None = None,
			extras: int | None = None,
			rs: str | None = None,
			chk: str | None = None
		) -> str:
			secret = GDReq.Tools.getSecret(1)
			incForChk = 1 if inc is None else inc
			autoChk = False
			if chk is None and (rs is not None and
								accountID is not None and
								udid is not None and
								uuid is not None):
				chk = GDReq.Tools.genChkDownloadLevel(
					levelID, incForChk, rs, accountID, udid, uuid
				)
				autoChk = True

			data: dict[str, str | int] = {
				"levelID": levelID,
				"secret": secret
			}

			if gameVersion is not None:
				data["gameVersion"] = gameVersion

			if binaryVersion is not None:
				data["binaryVersion"] = binaryVersion

			if gdw is not None:
				data["gdw"] = gdw

			if accountID is not None:
				data["accountID"] = accountID

			if gjp2 is not None:
				data["gjp2"] = gjp2

			if udid is not None:
				data["udid"] = udid

			if uuid is not None:
				data["uuid"] = uuid

			if inc is not None:
				data["inc"] = inc
			elif autoChk:
				data["inc"] = incForChk

			if extras is not None:
				data["extras"] = extras

			if rs is not None:
				data["rs"] = rs

			if chk is not None:
				data["chk"] = chk

			response = GDReq.Tools.makeReq(
				"http://www.boomlings.com/database/downloadGJLevel22.php",
				data
			)

			if not GDReq.Tools.checkResponse(response.text):
				print(f"downloadGJLevel22 Failed: {response.text}")

			return response.text

		@staticmethod
		def getGJLevels21(
			gameVersion: int | None = None,
			binaryVersion: int | None = None,
			type_: int | None = None,
			str_: str | int | None = None,
			page: int | None = None,
			total: int | None = None,
			gjp: str | None = None,
			gjp2: str | None = None,
			accountID: int | None = None,
			gdw: int | None = None,
			gauntlet: int | None = None,
			diff: int | None = None,
			demonFilter: int | None = None,
			len_: int | None = None,
			uncompleted: int | None = None,
			onlyCompleted: int | None = None,
			completedLevels: str | None = None,
			featured: int | None = None,
			original: int | None = None,
			twoPlayer: int | None = None,
			coins: int | None = None,
			epic: int | None = None,
			legendary: int | None = None,
			mythic: int | None = None,
			noStar: int | None = None,
			star: int | None = None,
			song: int | None = None,
			customSong: int | None = None,
			followed: str | None = None,
			local: int | None = None,
			udid: str | None = None,
			uuid: str | None = None
		) -> str:
			secret = GDReq.Tools.getSecret(1)

			data: dict[str, str | int] = {
				"secret": secret
			}

			if gameVersion is not None:
				data["gameVersion"] = gameVersion

			if binaryVersion is not None:
				data["binaryVersion"] = binaryVersion

			if type_ is not None:
				data["type"] = type_

			if str_ is not None:
				data["str"] = str_

			if page is not None:
				data["page"] = page

			if total is not None:
				data["total"] = total

			if gjp is not None:
				data["gjp"] = gjp

			if gjp2 is not None:
				data["gjp2"] = gjp2

			if accountID is not None:
				data["accountID"] = accountID

			if gdw is not None:
				data["gdw"] = gdw

			if gauntlet is not None:
				data["gauntlet"] = gauntlet

			if diff is not None:
				data["diff"] = diff

			if demonFilter is not None:
				data["demonFilter"] = demonFilter

			if len_ is not None:
				data["len"] = len_

			if uncompleted is not None:
				data["uncompleted"] = uncompleted

			if onlyCompleted is not None:
				data["onlyCompleted"] = onlyCompleted

			if completedLevels is not None:
				data["completedLevels"] = completedLevels

			if featured is not None:
				data["featured"] = featured

			if original is not None:
				data["original"] = original

			if twoPlayer is not None:
				data["twoPlayer"] = twoPlayer

			if coins is not None:
				data["coins"] = coins

			if epic is not None:
				data["epic"] = epic

			if legendary is not None:
				data["legendary"] = legendary

			if mythic is not None:
				data["mythic"] = mythic

			if noStar is not None:
				data["noStar"] = noStar

			if star is not None:
				data["star"] = star

			if song is not None:
				data["song"] = song

			if customSong is not None:
				data["customSong"] = customSong

			if followed is not None:
				data["followed"] = followed

			if local is not None:
				data["local"] = local

			if udid is not None:
				data["udid"] = udid

			if uuid is not None:
				data["uuid"] = uuid

			response = GDReq.Tools.makeReq(
				"http://www.boomlings.com/database/getGJLevels21.php",
				data
			)

			if not GDReq.Tools.checkResponse(response.text):
				print(f"getGJLevels21 Failed: {response.text}")

			return response.text

		@staticmethod
		def getGJLevelScores211(
			accountID: int,
			gjp2: str,
			levelID: int,
			gameVersion: int | None = None,
			binaryVersion: int | None = None,
			gdw: int | None = None,
			time: int | None = None,
			points: int | None = None,
			plat: int | None = None,
			percent: int | None = None,
			type_: int | None = None,
			s1: int | None = None,
			s2: int | None = None,
			s3: int | None = None,
			s4: int | None = None,
			s5: float | None = None,
			s6: str | None = None,
			s7: str | None = None
		) -> str:
			secret = GDReq.Tools.getSecret(1)

			data: dict[str, str | int | float] = {
				"accountID": accountID,
				"gjp2": gjp2,
				"levelID": levelID,
				"secret": secret
			}

			if gameVersion is not None:
				data["gameVersion"] = gameVersion

			if binaryVersion is not None:
				data["binaryVersion"] = binaryVersion

			if gdw is not None:
				data["gdw"] = gdw

			if time is not None:
				data["time"] = time

			if points is not None:
				data["points"] = points

			if plat is not None:
				data["plat"] = plat

			if percent is not None:
				data["percent"] = percent

			if type_ is not None:
				data["type"] = type_

			if s1 is not None:
				data["s1"] = s1

			if s2 is not None:
				data["s2"] = s2

			if s3 is not None:
				data["s3"] = s3

			if s4 is not None:
				data["s4"] = s4

			if s5 is not None:
				data["s5"] = s5

			if s6 is not None:
				data["s6"] = s6

			if s7 is not None:
				data["s7"] = s7

			response = GDReq.Tools.makeReq(
				"http://www.boomlings.com/database/getGJLevelScores211.php",
				data
			)

			if not GDReq.Tools.checkResponse(response.text):
				print(f"getGJLevelScores211 Failed: {response.text}")

			return response.text

		@staticmethod
		def getGJLevelScoresPlat(
			accountID: int,
			gjp2: str,
			levelID: int,
			gameVersion: int | None = None,
			binaryVersion: int | None = None,
			gdw: int | None = None,
			time: int | None = None,
			points: int | None = None,
			plat: int | None = None,
			percent: int | None = None,
			type_: int | None = None,
			mode: int | None = None,
			s1: int | None = None,
			s2: int | None = None,
			s3: int | None = None,
			s4: int | None = None,
			s5: float | None = None,
			s6: str | None = None,
			s7: str | None = None
		) -> str:
			secret = GDReq.Tools.getSecret(1)

			data: dict[str, str | int | float] = {
				"accountID": accountID,
				"gjp2": gjp2,
				"levelID": levelID,
				"secret": secret
			}

			if gameVersion is not None:
				data["gameVersion"] = gameVersion

			if binaryVersion is not None:
				data["binaryVersion"] = binaryVersion

			if gdw is not None:
				data["gdw"] = gdw

			if time is not None:
				data["time"] = time

			if points is not None:
				data["points"] = points

			if plat is not None:
				data["plat"] = plat

			if percent is not None:
				data["percent"] = percent

			if type_ is not None:
				data["type"] = type_

			if mode is not None:
				data["mode"] = mode

			if s1 is not None:
				data["s1"] = s1

			if s2 is not None:
				data["s2"] = s2

			if s3 is not None:
				data["s3"] = s3

			if s4 is not None:
				data["s4"] = s4

			if s5 is not None:
				data["s5"] = s5

			if s6 is not None:
				data["s6"] = s6

			if s7 is not None:
				data["s7"] = s7

			response = GDReq.Tools.makeReq(
				"http://www.boomlings.com/database/getGJLevelScoresPlat.php",
				data
			)

			if not GDReq.Tools.checkResponse(response.text):
				print(f"getGJLevelScoresPlat Failed: {response.text}")

			return response.text

	class Comments:

		@staticmethod
		def getGJComments21(
			levelID: int,
			page: int,
			gameVersion: int | None = None,
			binaryVersion: int | None = None,
			gdw: int | None = None,
			mode: int | None = None,
			total: int | None = None
		) -> str:
			secret = GDReq.Tools.getSecret(1)

			data: dict[str, str | int] = {
				"levelID": levelID,
				"page": page,
				"secret": secret
			}

			if gameVersion is not None:
				data["gameVersion"] = gameVersion

			if binaryVersion is not None:
				data["binaryVersion"] = binaryVersion

			if gdw is not None:
				data["gdw"] = gdw

			if mode is not None:
				data["mode"] = mode

			if total is not None:
				data["total"] = total

			response = GDReq.Tools.makeReq(
				"http://www.boomlings.com/database/getGJComments21.php",
				data
			)

			if not GDReq.Tools.checkResponse(response.text):
				print(f"getGJComments21 Failed: {response.text}")

			return response.text

		@staticmethod
		def getGJCommentHistory(
			userID: int,
			page: int,
			gameVersion: int | None = None,
			binaryVersion: int | None = None,
			gdw: int | None = None,
			mode: int | None = None,
			total: int | None = None
		) -> str:
			secret = GDReq.Tools.getSecret(1)

			data: dict[str, str | int] = {
				"userID": userID,
				"page": page,
				"secret": secret
			}

			if gameVersion is not None:
				data["gameVersion"] = gameVersion

			if binaryVersion is not None:
				data["binaryVersion"] = binaryVersion

			if gdw is not None:
				data["gdw"] = gdw

			if mode is not None:
				data["mode"] = mode

			if total is not None:
				data["total"] = total

			response = GDReq.Tools.makeReq(
				"http://www.boomlings.com/database/getGJCommentHistory.php",
				data
			)

			if not GDReq.Tools.checkResponse(response.text):
				print(f"getGJCommentHistory Failed: {response.text}")

			return response.text

		@staticmethod
		def getGJAccountComments20(
			accountID: int,
			page: int,
			gameVersion: int | None = None,
			binaryVersion: int | None = None,
			gdw: int | None = None,
			total: int | None = None
		) -> str:
			secret = GDReq.Tools.getSecret(1)

			data: dict[str, str | int] = {
				"accountID": accountID,
				"page": page,
				"secret": secret
			}

			if gameVersion is not None:
				data["gameVersion"] = gameVersion

			if binaryVersion is not None:
				data["binaryVersion"] = binaryVersion

			if gdw is not None:
				data["gdw"] = gdw

			if total is not None:
				data["total"] = total

			response = GDReq.Tools.makeReq(
				"http://www.boomlings.com/database/getGJAccountComments20.php",
				data
			)

			if not GDReq.Tools.checkResponse(response.text):
				print(f"getGJAccountComments20 Failed: {response.text}")

			return response.text

		@staticmethod
		def uploadGJAccComment20(
			accountID: int,
			gjp2: str,
			comment: str,
			gameVersion: int | None = None,
			binaryVersion: int | None = None,
			gdw: int | None = None,
			cType: int | None = None
		) -> str:
			secret = GDReq.Tools.getSecret(1)

			data: dict[str, str | int] = {
				"accountID": accountID,
				"gjp2": gjp2,
				"comment": GDReq.Tools.b64EncodeUrlSafe(comment),
				"secret": secret
			}

			if gameVersion is not None:
				data["gameVersion"] = gameVersion

			if binaryVersion is not None:
				data["binaryVersion"] = binaryVersion

			if gdw is not None:
				data["gdw"] = gdw

			if cType is not None:
				data["cType"] = cType  # 0 = level, 1 = user

			response = GDReq.Tools.makeReq(
				"http://www.boomlings.com/database/uploadGJAccComment20.php",
				data
			)

			if not GDReq.Tools.checkResponse(response.text):
				print(f"uploadGJAccComment20 Failed: {response.text}")

			return response.text

		@staticmethod
		def deleteGJAccComment20(
			accountID: int,
			targetAccountID: int,
			gjp2: str,
			commentID: int,
			gameVersion: int | None = None,
			binaryVersion: int | None = None,
			gdw: int | None = None
			) -> str:
			secret = GDReq.Tools.getSecret(1)

			data: dict[str, str | int] = {
				"accountID": accountID,
				"targetAccountID": targetAccountID,
				"gjp2": gjp2,
				"commentID": commentID,
				"secret": secret
			}

			if gameVersion is not None:
				data["gameVersion"] = gameVersion

			if binaryVersion is not None:
				data["binaryVersion"] = binaryVersion

			if gdw is not None:
				data["gdw"] = gdw

			response = GDReq.Tools.makeReq(
				"http://www.boomlings.com/database/deleteGJAccComment20.php",
				data
			)

			if not GDReq.Tools.checkResponse(response.text):
				print(f"deleteGJAccComment20 Failed: {response.text}")

			return response.text

		@staticmethod
		def uploadGJComment21(
			accountID: int,
			gjp2: str,
			userName: str,
			comment: str,
			levelID: int,
			percent: int,
			gameVersion: int | None = None,
			binaryVersion: int | None = None,
			gdw: int | None = None
			) -> str:
			secret = GDReq.Tools.getSecret(1)
			commentB64 = GDReq.Tools.b64EncodeUrlSafe(comment)
			chk = GDReq.Tools.genChkLevelComment(
				userName, commentB64, levelID, percent, 0
			)

			data: dict[str, str | int] = {
				"accountID": accountID,
				"gjp2": gjp2,
				"userName": userName,
				"comment": commentB64,
				"secret": secret,
				"levelID": levelID,
				"percent": percent,
				"chk": chk
			}

			if gameVersion is not None:
				data["gameVersion"] = gameVersion

			if binaryVersion is not None:
				data["binaryVersion"] = binaryVersion

			if gdw is not None:
				data["gdw"] = gdw

			response = GDReq.Tools.makeReq(
				"http://www.boomlings.com/database/uploadGJComment21.php", 
				data
			)

			if not GDReq.Tools.checkResponse(response.text):
				print(f"uploadGJComment21 Failed: {response.text}")

			return response.text

		@staticmethod
		def deleteGJComment20(
			accountID: int,
			gjp2: str,
			commentID: int,
			levelID: int,
			gameVersion: int | None = None,
			binaryVersion: int | None = None,
			gdw: int | None = None
			) -> str:
			secret = GDReq.Tools.getSecret(1)

			data: dict[str, str | int] = {
				"accountID": accountID,
				"gjp2": gjp2,
				"commentID": commentID,
				"levelID": levelID,
				"secret": secret
			}

			if gameVersion is not None:
				data["gameVersion"] = gameVersion

			if binaryVersion is not None:
				data["binaryVersion"] = binaryVersion

			if gdw is not None:
				data["gdw"] = gdw

			response = GDReq.Tools.makeReq(
				"http://www.boomlings.com/database/deleteGJComment20.php",
				data
			)

			if not GDReq.Tools.checkResponse(response.text):
				print(f"deleteGJComment20 Failed: {response.text}")

			return response.text

	class Lists:

		@staticmethod
		def uploadGJLevelList(
			gameVersion: int,
			accountID: int,
			gjp2: str,
			listID: int,
			listName: str,
			listDesc: str,
			listVersion: int,
			original: int,
			difficulty: int,
			unlisted: int,
			listLevels: str,
			seed: str | None = None,
			seed2: str | None = None,
			binaryVersion: int | None = None
		) -> str:
			secret = GDReq.Tools.getSecret(1)
			if seed2 is None:
				seed2 = GDReq.Tools.generateListSeed2()
			if seed is None:
				seed = GDReq.Tools.generateListUploadSeed(listLevels, accountID, seed2)

			data: dict[str, str | int] = {
				"gameVersion": gameVersion,
				"accountID": accountID,
				"gjp2": gjp2,
				"listID": listID,
				"listName": listName,
				"listDesc": listDesc,
				"listVersion": listVersion,
				"original": original,
				"difficulty": difficulty,
				"unlisted": unlisted,
				"listLevels": listLevels,
				"seed": seed,
				"seed2": seed2,
				"secret": secret
			}

			if binaryVersion is not None:
				data["binaryVersion"] = binaryVersion

			response = GDReq.Tools.makeReq(
				"http://www.boomlings.com/database/uploadGJLevelList.php",
				data
			)

			if not GDReq.Tools.checkResponse(response.text):
				print(f"uploadGJLevelList Failed: {response.text}")

			return response.text

		@staticmethod
		def getGJLevelLists(
			gameVersion: int | None = None,
			binaryVersion: int | None = None,
			type_: int | None = None,
			str_: str | int | None = None,
			page: int | None = None,
			gjp2: str | None = None,
			accountID: int | None = None,
			diff: int | None = None,
			demonFilter: int | None = None,
			star: int | None = None,
			followed: str | None = None,
			udid: str | None = None,
			uuid: str | None = None
		) -> str:
			secret = GDReq.Tools.getSecret(1)

			data: dict[str, str | int] = {
				"secret": secret
			}

			if gameVersion is not None:
				data["gameVersion"] = gameVersion

			if binaryVersion is not None:
				data["binaryVersion"] = binaryVersion

			if type_ is not None:
				data["type"] = type_

			if str_ is not None:
				data["str"] = str_

			if page is not None:
				data["page"] = page

			if gjp2 is not None:
				data["gjp2"] = gjp2

			if accountID is not None:
				data["accountID"] = accountID

			if diff is not None:
				data["diff"] = diff

			if demonFilter is not None:
				data["demonFilter"] = demonFilter

			if star is not None:
				data["star"] = star

			if followed is not None:
				data["followed"] = followed

			if udid is not None:
				data["udid"] = udid

			if uuid is not None:
				data["uuid"] = uuid

			response = GDReq.Tools.makeReq(
				"http://www.boomlings.com/database/getGJLevelLists.php",
				data
			)

			if not GDReq.Tools.checkResponse(response.text):
				print(f"getGJLevelLists Failed: {response.text}")

			return response.text

		@staticmethod
		def deleteGJLevelList(
			accountID: int,
			gjp2: str,
			listID: int,
			gameVersion: int | None = None,
			binaryVersion: int | None = None,
			udid: str | None = None,
			uuid: str | None = None
		) -> str:
			secret = GDReq.Tools.getSecret(3)

			data: dict[str, str | int] = {
				"accountID": accountID,
				"gjp2": gjp2,
				"listID": listID,
				"secret": secret
			}

			if gameVersion is not None:
				data["gameVersion"] = gameVersion

			if binaryVersion is not None:
				data["binaryVersion"] = binaryVersion

			if udid is not None:
				data["udid"] = udid

			if uuid is not None:
				data["uuid"] = uuid

			response = GDReq.Tools.makeReq(
				"http://www.boomlings.com/database/deleteGJLevelList.php",
				data
			)

			if not GDReq.Tools.checkResponse(response.text):
				print(f"deleteGJLevelList Failed: {response.text}")

			return response.text

	class Misc:

		@staticmethod
		def getSaveData(
			gameVersion: int | None = None,
			binaryVersion: int | None = None,
			gdw: int | None = None
		) -> str:
			secret = GDReq.Tools.getSecret(1)

			data: dict[str, str | int] = {
				"secret": secret
			}

			if gameVersion is not None:
				data["gameVersion"] = gameVersion

			if binaryVersion is not None:
				data["binaryVersion"] = binaryVersion

			if gdw is not None:
				data["gdw"] = gdw

			response = GDReq.Tools.makeReq(
				"http://www.boomlings.com/database/getSaveData.php",
				data
			)

			if not GDReq.Tools.checkResponse(response.text):
				print(f"getSaveData Failed: {response.text}")

			return response.text

		@staticmethod
		def getAccountURL(accountID: int, type_: int) -> str:
			secret = GDReq.Tools.getSecret(1)

			data: dict[str, str | int] = {
				"accountID": accountID,
				"type": type_,
				"secret": secret
			}

			response = GDReq.Tools.makeReq(
				"http://www.boomlings.com/database/getAccountURL.php",
				data
			)

			if not GDReq.Tools.checkResponse(response.text):
				print(f"getAccountURL Failed: {response.text}")

			return response.text

		@staticmethod
		def likeGJItem211(
			itemID: int,
			type_: int,
			gameVersion: int | None = None,
			binaryVersion: int | None = None,
			gdw: int | None = None,
			accountID: int | None = None,
			gjp2: str | None = None,
			udid: str | None = None,
			uuid: str | None = None,
			rs: str | None = None,
			special: int = 0,
			like: int | None = None,
			chk: str | None = None
		) -> str:
			secret = GDReq.Tools.getSecret(1)
			likeVal = 1 if like is None else like
			if chk is None and (rs is not None and
								accountID is not None and
								udid is not None and
								uuid is not None):
				chk = GDReq.Tools.genChkLikeItem(
					special, itemID, likeVal, type_, rs, accountID, udid, uuid
				)

			data: dict[str, str | int] = {
				"itemID": itemID,
				"type": type_,
				"secret": secret
			}

			if gameVersion is not None:
				data["gameVersion"] = gameVersion

			if binaryVersion is not None:
				data["binaryVersion"] = binaryVersion

			if gdw is not None:
				data["gdw"] = gdw

			if accountID is not None:
				data["accountID"] = accountID

			if gjp2 is not None:
				data["gjp2"] = gjp2

			if udid is not None:
				data["udid"] = udid

			if uuid is not None:
				data["uuid"] = uuid

			if rs is not None:
				data["rs"] = rs

			if like is not None:
				data["like"] = like

			if chk is not None:
				data["chk"] = chk

			response = GDReq.Tools.makeReq(
				"http://www.boomlings.com/database/likeGJItem211.php",
				data
			)

			if not GDReq.Tools.checkResponse(response.text):
				print(f"likeGJItem211 Failed: {response.text}")

			return response.text

		@staticmethod
		def requestUserAccess(
			accountID: int,
			gjp2: str,
			gameVersion: int | None = None,
			binaryVersion: int | None = None,
			gdw: int | None = None
		) -> str:
			secret = GDReq.Tools.getSecret(1)

			data: dict[str, str | int] = {
				"accountID": accountID,
				"gjp2": gjp2,
				"secret": secret
			}

			if gameVersion is not None:
				data["gameVersion"] = gameVersion

			if binaryVersion is not None:
				data["binaryVersion"] = binaryVersion

			if gdw is not None:
				data["gdw"] = gdw

			response = GDReq.Tools.makeReq(
				"http://www.boomlings.com/database/requestUserAccess.php",
				data
			)

			if not GDReq.Tools.checkResponse(response.text):
				print(f"requestUserAccess Failed: {response.text}")

			return response.text

		@staticmethod
		def restoreGJItems(udid: str) -> str:
			secret = GDReq.Tools.getSecret(1)

			data: dict[str, str | int] = {
				"udid": udid,
				"secret": secret
			}

			response = GDReq.Tools.makeReq(
				"http://www.boomlings.com/database/restoreGJItems.php",
				data
			)

			if not GDReq.Tools.checkResponse(response.text):
				print(f"restoreGJItems Failed: {response.text}")

			return response.text

		@staticmethod
		def getTop1000() -> str:
			response = requests.get(
				"http://www.boomlings.com/database/accounts/getTop1000.php",
				headers={"User-Agent": ""}
			)

			return response.text

	class Rewards:

		@staticmethod
		def getGJSecretReward(
			udid: str,
			chk: str | None = None,
			gameVersion: int | None = None,
			binaryVersion: int | None = None,
			gdw: int | None = None,
			accountID: int | None = None,
			gjp2: str | None = None,
			uuid: str | None = None
		) -> str:
			secret = GDReq.Tools.getSecret(1)
			if chk is None:
				chk = GDReq.Tools.generateWraithRewardChk()

			data: dict[str, str | int] = {
				"udid": udid,
				"chk": chk,
				"secret": secret
			}

			if gameVersion is not None:
				data["gameVersion"] = gameVersion

			if binaryVersion is not None:
				data["binaryVersion"] = binaryVersion

			if gdw is not None:
				data["gdw"] = gdw

			if accountID is not None:
				data["accountID"] = accountID

			if gjp2 is not None:
				data["gjp2"] = gjp2

			if uuid is not None:
				data["uuid"] = uuid

			response = GDReq.Tools.makeReq(
				"http://www.boomlings.com/database/getGJSecretReward.php",
				data
			)

			if not GDReq.Tools.checkResponse(response.text):
				print(f"getGJSecretReward Failed: {response.text}")

			return response.text

		@staticmethod
		def getGJRewards(
			udid: str,
			chk: str | None = None,
			gameVersion: int | None = None,
			binaryVersion: int | None = None,
			gdw: int | None = None,
			accountID: int | None = None,
			gjp2: str | None = None,
			uuid: str | None = None,
			rewardType: int | None = None,
			r1: int | None = None,
			r2: int | None = None
		) -> str:
			secret = GDReq.Tools.getSecret(1)
			if chk is None:
				chk = GDReq.Tools.generateChestMenuChk()

			data: dict[str, str | int] = {
				"udid": udid,
				"chk": chk,
				"secret": secret
			}

			if gameVersion is not None:
				data["gameVersion"] = gameVersion

			if binaryVersion is not None:
				data["binaryVersion"] = binaryVersion

			if gdw is not None:
				data["gdw"] = gdw

			if accountID is not None:
				data["accountID"] = accountID

			if gjp2 is not None:
				data["gjp2"] = gjp2

			if uuid is not None:
				data["uuid"] = uuid

			if rewardType is not None:
				data["rewardType"] = rewardType

			if r1 is not None:
				data["r1"] = r1

			if r2 is not None:
				data["r2"] = r2

			response = GDReq.Tools.makeReq(
				"http://www.boomlings.com/database/getGJRewards.php",
				data
			)

			if not GDReq.Tools.checkResponse(response.text):
				print(f"getGJRewards Failed: {response.text}")

			return response.text

		@staticmethod
		def getGJChallenges(
			udid: str,
			chk: str | None = None,
			gameVersion: int | None = None,
			binaryVersion: int | None = None,
			gdw: int | None = None,
			accountID: int | None = None,
			gjp2: str | None = None,
			uuid: str | None = None,
			world: int | None = None
		) -> str:
			secret = GDReq.Tools.getSecret(1)
			if chk is None:
				chk = GDReq.Tools.generateQuestChk()

			data: dict[str, str | int] = {
				"udid": udid,
				"chk": chk,
				"secret": secret
			}

			if gameVersion is not None:
				data["gameVersion"] = gameVersion

			if binaryVersion is not None:
				data["binaryVersion"] = binaryVersion

			if gdw is not None:
				data["gdw"] = gdw

			if accountID is not None:
				data["accountID"] = accountID

			if gjp2 is not None:
				data["gjp2"] = gjp2

			if uuid is not None:
				data["uuid"] = uuid

			if world is not None:
				data["world"] = world

			response = GDReq.Tools.makeReq(
				"http://www.boomlings.com/database/getGJChallenges.php",
				data
			)

			if not GDReq.Tools.checkResponse(response.text):
				print(f"getGJChallenges Failed: {response.text}")

			return response.text

	class Socials:

		@staticmethod
		def getGJMessages20(
			accountID: int,
			gjp2: str,
			gameVersion: int | None = None,
			binaryVersion: int | None = None,
			gdw: int | None = None,
			page: int | None = None,
			total: int | None = None,
			getSent: int | None = None
		) -> str:
			secret = GDReq.Tools.getSecret(1)

			data: dict[str, str | int] = {
				"accountID": accountID,
				"gjp2": gjp2,
				"secret": secret
			}

			if gameVersion is not None:
				data["gameVersion"] = gameVersion

			if binaryVersion is not None:
				data["binaryVersion"] = binaryVersion

			if gdw is not None:
				data["gdw"] = gdw

			if page is not None:
				data["page"] = page

			if total is not None:
				data["total"] = total

			if getSent is not None:
				data["getSent"] = getSent

			response = GDReq.Tools.makeReq(
				"http://www.boomlings.com/database/getGJMessages20.php",
				data
			)

			if not GDReq.Tools.checkResponse(response.text):
				print(f"getGJMessages20 Failed: {response.text}")

			return response.text

		@staticmethod
		def downloadGJMessage20(
			accountID: int,
			gjp2: str,
			messageID: int,
			gameVersion: int | None = None,
			binaryVersion: int | None = None,
			gdw: int | None = None
		) -> str:
			secret = GDReq.Tools.getSecret(1)

			data: dict[str, str | int] = {
				"accountID": accountID,
				"gjp2": gjp2,
				"messageID": messageID,
				"secret": secret
			}

			if gameVersion is not None:
				data["gameVersion"] = gameVersion

			if binaryVersion is not None:
				data["binaryVersion"] = binaryVersion

			if gdw is not None:
				data["gdw"] = gdw

			response = GDReq.Tools.makeReq(
				"http://www.boomlings.com/database/downloadGJMessage20.php",
				data
			)

			if not GDReq.Tools.checkResponse(response.text):
				print(f"downloadGJMessage20 Failed: {response.text}")

			return response.text

		@staticmethod
		def uploadGJMessage20(
			accountID: int,
			gjp2: str,
			toAccountID: int,
			subject: str,
			body: str,
			gameVersion: int | None = None,
			binaryVersion: int | None = None,
			gdw: int | None = None
		) -> str:
			secret = GDReq.Tools.getSecret(1)

			data: dict[str, str | int] = {
				"accountID": accountID,
				"gjp2": gjp2,
				"toAccountID": toAccountID,
				"subject": GDReq.Tools.b64EncodeUrlSafe(subject),
				"body": GDReq.Tools.b64EncodeUrlSafe(body),
				"secret": secret
			}

			if gameVersion is not None:
				data["gameVersion"] = gameVersion

			if binaryVersion is not None:
				data["binaryVersion"] = binaryVersion

			if gdw is not None:
				data["gdw"] = gdw

			response = GDReq.Tools.makeReq(
				"http://www.boomlings.com/database/uploadGJMessage20.php",
				data
			)

			if not GDReq.Tools.checkResponse(response.text):
				print(f"uploadGJMessage20 Failed: {response.text}")

			return response.text

		@staticmethod
		def deleteGJMessages20(
			accountID: int,
			gjp2: str,
			messageID: int,
			gameVersion: int | None = None,
			binaryVersion: int | None = None,
			gdw: int | None = None,
			isSender: int | None = None
		) -> str:
			secret = GDReq.Tools.getSecret(1)

			data: dict[str, str | int] = {
				"accountID": accountID,
				"gjp2": gjp2,
				"messageID": messageID,
				"secret": secret
			}

			if gameVersion is not None:
				data["gameVersion"] = gameVersion

			if binaryVersion is not None:
				data["binaryVersion"] = binaryVersion

			if gdw is not None:
				data["gdw"] = gdw

			if isSender is not None:
				data["isSender"] = isSender

			response = GDReq.Tools.makeReq(
				"http://www.boomlings.com/database/deleteGJMessages20.php",
				data
			)

			if not GDReq.Tools.checkResponse(response.text):
				print(f"deleteGJMessages20 Failed: {response.text}")

			return response.text

		@staticmethod
		def getGJFriendRequests20(
			accountID: int,
			gjp2: str,
			gameVersion: int | None = None,
			binaryVersion: int | None = None,
			gdw: int | None = None,
			page: int | None = None,
			total: int | None = None,
			getSent: int | None = None
		) -> str:
			secret = GDReq.Tools.getSecret(1)

			data: dict[str, str | int] = {
				"accountID": accountID,
				"gjp2": gjp2,
				"secret": secret
			}

			if gameVersion is not None:
				data["gameVersion"] = gameVersion

			if binaryVersion is not None:
				data["binaryVersion"] = binaryVersion

			if gdw is not None:
				data["gdw"] = gdw

			if page is not None:
				data["page"] = page

			if total is not None:
				data["total"] = total

			if getSent is not None:
				data["getSent"] = getSent

			response = GDReq.Tools.makeReq(
				"http://www.boomlings.com/database/getGJFriendRequests20.php",
				data
			)

			if not GDReq.Tools.checkResponse(response.text):
				print(f"getGJFriendRequests20 Failed: {response.text}")

			return response.text

		@staticmethod
		def uploadFriendRequest20(
			accountID: int,
			toAccountID: int,
			gjp2: str,
			gameVersion: int | None = None,
			binaryVersion: int | None = None,
			gdw: int | None = None
		) -> str:
			secret = GDReq.Tools.getSecret(1)

			data: dict[str, str | int] = {
				"accountID": accountID,
				"toAccountID": toAccountID,
				"gjp2": gjp2,
				"secret": secret
			}

			if gameVersion is not None:
				data["gameVersion"] = gameVersion

			if binaryVersion is not None:
				data["binaryVersion"] = binaryVersion

			if gdw is not None:
				data["gdw"] = gdw

			response = GDReq.Tools.makeReq(
				"http://www.boomlings.com/database/uploadFriendRequest20.php",
				data
			)

			if not GDReq.Tools.checkResponse(response.text):
				print(f"uploadFriendRequest20 Failed: {response.text}")

			return response.text

		@staticmethod
		def deleteGJFriendRequests20(
			accountID: int,
			gjp2: str,
			targetAccountID: int,
			gameVersion: int | None = None,
			binaryVersion: int | None = None,
			gdw: int | None = None,
			accounts: str | None = None,
			isSender: int | None = None
		) -> str:
			secret = GDReq.Tools.getSecret(1)

			data: dict[str, str | int] = {
				"accountID": accountID,
				"gjp2": gjp2,
				"targetAccountID": targetAccountID,
				"secret": secret
			}

			if gameVersion is not None:
				data["gameVersion"] = gameVersion

			if binaryVersion is not None:
				data["binaryVersion"] = binaryVersion

			if gdw is not None:
				data["gdw"] = gdw

			if accounts is not None:
				data["accounts"] = accounts

			if isSender is not None:
				data["isSender"] = isSender

			response = GDReq.Tools.makeReq(
				"http://www.boomlings.com/database/deleteGJFriendRequests20.php",
				data
			)

			if not GDReq.Tools.checkResponse(response.text):
				print(f"deleteGJFriendRequests20 Failed: {response.text}")

			return response.text

		@staticmethod
		def acceptGJFriendRequest20(
			accountID: int,
			targetAccountID: int,
			gjp2: str,
			gameVersion: int | None = None,
			binaryVersion: int | None = None,
			gdw: int | None = None,
			requestID: int | None = None
		) -> str:
			secret = GDReq.Tools.getSecret(1)

			data: dict[str, str | int] = {
				"accountID": accountID,
				"targetAccountID": targetAccountID,
				"gjp2": gjp2,
				"secret": secret
			}

			if gameVersion is not None:
				data["gameVersion"] = gameVersion

			if binaryVersion is not None:
				data["binaryVersion"] = binaryVersion

			if gdw is not None:
				data["gdw"] = gdw

			if requestID is not None:
				data["requestID"] = requestID

			response = GDReq.Tools.makeReq(
				"http://www.boomlings.com/database/acceptGJFriendRequest20.php",
				data
			)

			if not GDReq.Tools.checkResponse(response.text):
				print(f"acceptGJFriendRequest20 Failed: {response.text}")

			return response.text

		@staticmethod
		def readGJFriendRequest20(
			accountID: int,
			gjp2: str,
			requestID: int,
			gameVersion: int | None = None,
			binaryVersion: int | None = None,
			gdw: int | None = None
		) -> str:
			secret = GDReq.Tools.getSecret(1)

			data: dict[str, str | int] = {
				"accountID": accountID,
				"gjp2": gjp2,
				"requestID": requestID,
				"secret": secret
			}

			if gameVersion is not None:
				data["gameVersion"] = gameVersion

			if binaryVersion is not None:
				data["binaryVersion"] = binaryVersion

			if gdw is not None:
				data["gdw"] = gdw

			response = GDReq.Tools.makeReq(
				"http://www.boomlings.com/database/readGJFriendRequest20.php",
				data
			)

			if not GDReq.Tools.checkResponse(response.text):
				print(f"readGJFriendRequest20 Failed: {response.text}")

			return response.text

		@staticmethod
		def removeGJFriend20(
			accountID: int,
			gjp2: str,
			targetAccountID: int,
			gameVersion: int | None = None,
			binaryVersion: int | None = None,
			gdw: int | None = None
		) -> str:
			secret = GDReq.Tools.getSecret(1)

			data: dict[str, str | int] = {
				"accountID": accountID,
				"gjp2": gjp2,
				"targetAccountID": targetAccountID,
				"secret": secret
			}

			if gameVersion is not None:
				data["gameVersion"] = gameVersion

			if binaryVersion is not None:
				data["binaryVersion"] = binaryVersion

			if gdw is not None:
				data["gdw"] = gdw

			response = GDReq.Tools.makeReq(
				"http://www.boomlings.com/database/removeGJFriend20.php",
				data
			)

			if not GDReq.Tools.checkResponse(response.text):
				print(f"removeGJFriend20 Failed: {response.text}")

			return response.text

		@staticmethod
		def blockGJUser20(
			accountID: int,
			gjp2: str,
			targetAccountID: int,
			gameVersion: int | None = None,
			binaryVersion: int | None = None,
			gdw: int | None = None
		) -> str:
			secret = GDReq.Tools.getSecret(1)

			data: dict[str, str | int] = {
				"accountID": accountID,
				"gjp2": gjp2,
				"targetAccountID": targetAccountID,
				"secret": secret
			}

			if gameVersion is not None:
				data["gameVersion"] = gameVersion

			if binaryVersion is not None:
				data["binaryVersion"] = binaryVersion

			if gdw is not None:
				data["gdw"] = gdw

			response = GDReq.Tools.makeReq(
				"http://www.boomlings.com/database/blockGJUser20.php",
				data
			)

			if not GDReq.Tools.checkResponse(response.text):
				print(f"blockGJUser20 Failed: {response.text}")

			return response.text

		@staticmethod
		def unblockGJUser20(
			accountID: int,
			gjp2: str,
			targetAccountID: int,
			gameVersion: int | None = None,
			binaryVersion: int | None = None,
			gdw: int | None = None
		) -> str:
			secret = GDReq.Tools.getSecret(1)

			data: dict[str, str | int] = {
				"accountID": accountID,
				"gjp2": gjp2,
				"targetAccountID": targetAccountID,
				"secret": secret
			}

			if gameVersion is not None:
				data["gameVersion"] = gameVersion

			if binaryVersion is not None:
				data["binaryVersion"] = binaryVersion

			if gdw is not None:
				data["gdw"] = gdw

			response = GDReq.Tools.makeReq(
				"http://www.boomlings.com/database/unblockGJUser20.php",
				data
			)

			if not GDReq.Tools.checkResponse(response.text):
				print(f"unblockGJUser20 Failed: {response.text}")

			return response.text

		@staticmethod
		def getGJUserList20(
			accountID: int,
			gjp2: str,
			gameVersion: int | None = None,
			binaryVersion: int | None = None,
			gdw: int | None = None,
			type_: int | None = None
		) -> str:
			secret = GDReq.Tools.getSecret(1)

			data: dict[str, str | int] = {
				"accountID": accountID,
				"gjp2": gjp2,
				"secret": secret
			}

			if gameVersion is not None:
				data["gameVersion"] = gameVersion

			if binaryVersion is not None:
				data["binaryVersion"] = binaryVersion

			if gdw is not None:
				data["gdw"] = gdw

			if type_ is not None:
				data["type"] = type_

			response = GDReq.Tools.makeReq(
				"http://www.boomlings.com/database/getGJUserList20.php",
				data
			)

			if not GDReq.Tools.checkResponse(response.text):
				print(f"getGJUserList20 Failed: {response.text}")

			return response.text

	class Songs:

		@staticmethod
		def getGJSongInfo(
			songID: int,
			gameVersion: int | None = None,
			binaryVersion: int | None = None,
			accountID: int | None = None,
			gjp2: str | None = None,
			udid: str | None = None,
			uuid: str | None = None
		) -> str:
			secret = GDReq.Tools.getSecret(1)

			data: dict[str, str | int] = {
				"songID": songID,
				"secret": secret
			}

			if gameVersion is not None:
				data["gameVersion"] = gameVersion

			if binaryVersion is not None:
				data["binaryVersion"] = binaryVersion

			if accountID is not None:
				data["accountID"] = accountID

			if gjp2 is not None:
				data["gjp2"] = gjp2

			if udid is not None:
				data["udid"] = udid

			if uuid is not None:
				data["uuid"] = uuid

			response = GDReq.Tools.makeReq(
				"http://www.boomlings.com/database/getGJSongInfo.php",
				data
			)

			if not GDReq.Tools.checkResponse(response.text):
				print(f"getGJSongInfo Failed: {response.text}")

			return response.text

		@staticmethod
		def getGJTopArtists(
			gameVersion: int | None = None,
			binaryVersion: int | None = None,
			gdw: int | None = None,
			page: int | None = None,
			total: int | None = None
		) -> str:
			secret = GDReq.Tools.getSecret(1)

			data: dict[str, str | int] = {
				"secret": secret
			}

			if gameVersion is not None:
				data["gameVersion"] = gameVersion

			if binaryVersion is not None:
				data["binaryVersion"] = binaryVersion

			if gdw is not None:
				data["gdw"] = gdw

			if page is not None:
				data["page"] = page

			if total is not None:
				data["total"] = total

			response = GDReq.Tools.makeReq(
				"http://www.boomlings.com/database/getGJTopArtists.php",
				data
			)

			if not GDReq.Tools.checkResponse(response.text):
				print(f"getGJTopArtists Failed: {response.text}")

			return response.text

		@staticmethod
		def testSong(songID: int) -> str:
			response = requests.get(
				f"http://www.boomlings.com/database/testSong.php?songID={songID}",
				headers={"User-Agent": ""}
			)

			return response.text

		@staticmethod
		def fetchMusicLibraryDat(
			useV2: bool = True,
			expires: int | None = None,
			token: str | None = None
		) -> bytes:
			endpoint = (
				"/music/musiclibrary_02.dat" if useV2 else "/music/musiclibrary.dat"
			)
			url = "https://geometrydashfiles.b-cdn.net" + endpoint
			params: dict[str, str | int] = {}
			if expires is not None:
				params["expires"] = expires
			if token is None and expires is not None:
				token = GDReq.Tools.generateCdnToken(endpoint, expires)
			if token is not None:
				params["token"] = token

			response = requests.get(
				url,
				params=params or None,
				headers={"User-Agent": ""}
			)
			return response.content

		@staticmethod
		def fetchSfxLibraryDat(
			expires: int | None = None,
			token: str | None = None
		) -> bytes:
			endpoint = "/sfx/sfxlibrary.dat"
			url = "https://geometrydashfiles.b-cdn.net" + endpoint
			params: dict[str, str | int] = {}
			if expires is not None:
				params["expires"] = expires
			if token is None and expires is not None:
				token = GDReq.Tools.generateCdnToken(endpoint, expires)
			if token is not None:
				params["token"] = token

			response = requests.get(
				url,
				params=params or None,
				headers={"User-Agent": ""}
			)

			return response.content

	class Multiplayer:

		@staticmethod
		def joinMPLobby(
			accountID: int,
			gjp2: str,
			gameID: int,
			lastCommentID: int,
			gameVersion: int | None = None,
			binaryVersion: int | None = None,
			gdw: int | None = None
		) -> str:
			secret = GDReq.Tools.getSecret(2)

			data: dict[str, str | int] = {
				"accountID": accountID,
				"gjp2": gjp2,
				"secret": secret,
				"gameID": gameID,
				"lastCommentID": lastCommentID
			}

			if gameVersion is not None:
				data["gameVersion"] = gameVersion

			if binaryVersion is not None:
				data["binaryVersion"] = binaryVersion

			if gdw is not None:
				data["gdw"] = gdw

			response = GDReq.Tools.makeReq(
				"https://www.geometrydash.com/database/joinMPLobby.php",
				data
			)

			if not GDReq.Tools.checkResponse(response.text):
				print(f"joinMPLobby Failed: {response.text}")

			return response.text

		@staticmethod
		def exitMPLobby(
			accountID: int,
			gjp2: str,
			gameID: int,
			gameVersion: int | None = None,
			binaryVersion: int | None = None,
			gdw: int | None = None
		) -> str:
			secret = GDReq.Tools.getSecret(2)

			data: dict[str, str | int] = {
				"accountID": accountID,
				"gjp2": gjp2,
				"secret": secret,
				"gameID": gameID
			}

			if gameVersion is not None:
				data["gameVersion"] = gameVersion

			if binaryVersion is not None:
				data["binaryVersion"] = binaryVersion

			if gdw is not None:
				data["gdw"] = gdw

			response = GDReq.Tools.makeReq(
				"https://www.geometrydash.com/database/exitMPLobby.php",
				data
			)

			if not GDReq.Tools.checkResponse(response.text):
				print(f"exitMPLobby Failed: {response.text}")

			return response.text

		@staticmethod
		def uploadMPComment(
			accountID: int,
			gjp2: str,
			extra: str,
			comment: str,
			gameID: int,
			chk: str | None = None,
			gameVersion: int | None = None,
			binaryVersion: int | None = None,
			gdw: int | None = None
		) -> str:
			secret = GDReq.Tools.getSecret(2)
			if chk is None:
				chk = GDReq.Tools.genChk(11, [accountID, comment, gameID, extra], 1)

			data: dict[str, str | int] = {
				"accountID": accountID,
				"gjp2": gjp2,
				"extra": extra,
				"comment": comment,
				"secret": secret,
				"gameID": gameID,
				"chk": chk
			}

			if gameVersion is not None:
				data["gameVersion"] = gameVersion

			if binaryVersion is not None:
				data["binaryVersion"] = binaryVersion

			if gdw is not None:
				data["gdw"] = gdw

			response = GDReq.Tools.makeReq(
				"https://www.geometrydash.com/database/uploadMPComment.php",
				data
			)

			if not GDReq.Tools.checkResponse(response.text):
				print(f"uploadMPComment Failed: {response.text}")

			return response.text
