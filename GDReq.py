import requests
import base64
from typing import Any, Union, List
import hashlib
import re

class GDReq:

	class Tools:

		class Encryption:

			@staticmethod
			def decodeMessage(message: str) -> str:
				return GDReq.Tools.xorCipher(
					GDReq.Tools.b64DecodeUrlSafe(message),
					GDReq.Tools.getXorKey(2)
					)

			@staticmethod
			def encodeMessage(message: str) -> str:
				return GDReq.Tools.b64EncodeUrlSafe(
					GDReq.Tools.xorCipher(
						message,
						GDReq.Tools.getXorKey(2))
					)

		@staticmethod
		def b64EncodeUrlSafe(data: str) -> str:
			return base64.urlsafe_b64encode(data.encode("utf-8")).decode("utf-8")

		@staticmethod
		def b64DecodeUrlSafe(b64: str) -> str:
			return base64.urlsafe_b64decode(b64).decode("utf-8")

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
		def writeResponse(response: str | bytes):
			if isinstance(response, bytes):
				with open("response.txt", "wb") as file:
					file.write(response)
			else:
				with open("response.txt", "w") as file:
					file.write(response)

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
				case _:
					raise ValueError(f"Invalid XOR key index: {index}")


	class Accounts:

		@staticmethod
		def backupGJAccountNew(
			userName: str,
			password: str,
			saveData: str,
			gameVersion: int = 22,
			binaryVersion: int = 42,
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
			seed2: str,
			binaryVersion: int | None = None,
			gdw: int | None = None,
			wt: int | None = None,
			wt2: int | None = None,
			seed: str | None = None,
			extraString: str | None = None,
			levelInfo: str | None = None
		) -> str:
			secret = GDReq.Tools.getSecret(1)

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
			chk = GDReq.Tools.genChk(6, [userName, GDReq.Tools.b64EncodeUrlSafe(comment), levelID, percent, 0], 2)

			data: dict[str, str | int] = {
				"accountID": accountID,
				"gjp2": gjp2,
				"userName": userName,
				"comment": GDReq.Tools.b64EncodeUrlSafe(comment),
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
			seed: str,
			seed2: str,
			binaryVersion: int | None = None
		) -> str:
			secret = GDReq.Tools.getSecret(1)

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
			like: int | None = None,
			chk: str | None = None
		) -> str:
			secret = GDReq.Tools.getSecret(1)

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
			chk: str,
			gameVersion: int | None = None,
			binaryVersion: int | None = None,
			gdw: int | None = None,
			accountID: int | None = None,
			gjp2: str | None = None,
			uuid: str | None = None
		) -> str:
			secret = GDReq.Tools.getSecret(1)

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
			chk: str,
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
			chk: str,
			gameVersion: int | None = None,
			binaryVersion: int | None = None,
			gdw: int | None = None,
			accountID: int | None = None,
			gjp2: str | None = None,
			uuid: str | None = None,
			world: int | None = None
		) -> str:
			secret = GDReq.Tools.getSecret(1)

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
		def fetchMusicLibraryDat(useV2: bool = True) -> bytes:
			url = (
				"https://geometrydashfiles.b-cdn.net/music/musiclibrary_02.dat"
				if useV2
				else "https://geometrydashfiles.b-cdn.net/music/musiclibrary.dat"
			)

			response = requests.get(url, headers={"User-Agent": ""})
			return response.content

		@staticmethod
		def fetchSfxLibraryDat() -> bytes:
			response = requests.get(
				"https://geometrydashfiles.b-cdn.net/sfx/sfxlibrary.dat",
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
