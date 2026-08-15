"""
An API wrapper and response parser for Geometry Dash
"""

import requests
import base64
from typing import Any, Union, List, Sequence, Literal
import hashlib
import re
import gzip
import io
import zlib
import random
import string
import time
import urllib.request
import os
import ssl
import urllib3

urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

class Parse:

	@staticmethod
	def _decode(value: str):
		try:
			return Tools.b64DecodeUrlSafe(value)
		except Exception:
			return value

	@staticmethod
	def _parseCreators(segment: str):
		creators = []
		entries = segment.split("|")

		for entry in entries:
			parts = entry.split(":")
			creators.append({
				"userID": int(parts[0]),
				"username": parts[1],
				"accountID": int(parts[2])
			})

		return creators

	@staticmethod
	def _parseSongs(segment: str):
		songs = []
		
		for entry in segment.split(":"):
			if not entry:
				continue

			if entry.startswith("~"):
				entry = entry[1:]

			song = Parse._parseKeyValuePairs(entry, splitter="~|~")

			songs.append(song)

		return songs

	@staticmethod
	def _parseKeyValuePairs(segment: str, splitter: str = "~"):
		parts = segment.split(splitter)
		result = {}

		i = 0
		while i < len(parts) - 1:
			key = str(parts[i])
			value = parts[i + 1]
	
			if value.isdigit():
				value = int(value)
			elif value == "":
				value = ""

			result[key] = value
			i += 2

		return result
		
	@staticmethod
	def _parseLevelCommentBlock(block: str):
		contentRaw, senderRaw = block.split(":", 1)
	
		contentData = Parse._parseKeyValuePairs(contentRaw)
		senderData = Parse._parseKeyValuePairs(senderRaw)
	
		if contentData["2"]:
			contentData["2"] = Tools.b64DecodeUrlSafe(contentData["2"])
	
		return {
			"content": contentData,
			"sender": senderData
		}

	@staticmethod
	def _parseAccountCommentBlock(block: str):
		contentData = Parse._parseKeyValuePairs(block)
	
		if contentData["2"]:
			contentData["2"] = Tools.b64DecodeUrlSafe(contentData["2"])
	
		return {
			"content": contentData
		}

	@staticmethod
	def _parsePagination(lastSegment: str):
		try:
			total, offset, amount = lastSegment.split(":")
			return {
				"total": int(total),
				"offset": int(offset),
				"amount": int(amount)
			}
		except Exception:
			return None

	@staticmethod
	def _getObjectMap(type_):
		"""
		Type 1: User
		Type 2: Comment
		Type 3: Comment User
		Type 4: Friend Request
		Type 5: Gauntlet
		Type 6: Gauntlet Names
		Type 7: Level Leaderboard
		Type 8: Level
		Type 9: Song
		Type 10: Message
		Type 11: Map Pack
		Type 12: List
		"""
		if type_ == 1:
			result = {
				"1": "userName",
				"2": "userID",
				"3": "stars",
				"4": "demons",
				"6": "ranking",
				"7": "accountHighlight",
				"8": "creatorPoints",
				"9": "iconID",
				"10": "color1",
				"11": "color2",
				"13": "secretCoins",
				"14": "iconType",
				"15": "special",
				"16": "accountID",
				"17": "userCoins",
				"18": "messageState",
				"19": "friendsState",
				"20": "youTube",
				"21": "accIcon",
				"22": "accShip",
				"23": "accBall",
				"24": "accBird",
				"25": "accWave",
				"26": "accRobot",
				"27": "accStreak",
				"28": "accGlow",
				"29": "isRegistered",
				"30": "globalRank",
				"31": "friendState",
				"38": "messages",
				"39": "friendRequests",
				"40": "newFriends",
				"41": "newFriendRequest",
				"42": "age",
				"43": "accSpider",
				"44": "twitter",
				"45": "twitch",
				"46": "diamonds",
				"48": "accExplosion",
				"49": "modLevel",
				"50": "commentHistoryState",
				"51": "color3",
				"52": "moons",
				"53": "accSwing",
				"54": "accJetpack",
				"55": "demonBreakdown",
				"56": "classicLevelBreakdown",
				"57": "platformerLevelBreakdown"
			}
			return result

		elif type_ == 2:
			result = {
				"1": "levelID",
				"2": "comment",
				"3": "authorPlayerID",
				"4": "likes",
				"5": "dislikes",
				"6": "messageID",
				"7": "spam",
				"8": "authorAccountID",
				"9": "age",
				"10": "percent",
				"11": "modBadge",
				"12": "moderatorChatColor"
			}
			return result

		elif type_ == 3:
			result = {
				"1": "userName",
				"9": "icon",
				"10": "playerColor",
				"11": "playerColor2",
				"14": "iconType",
				"15": "glow",
				"16": "accountID"
			}
			return result

		elif type_ == 4:
			result = {
				"1": "userName",
				"2": "playerID",
				"9": "icon",
				"10": "playerColor",
				"11": "playerColor2",
				"14": "iconType",
				"15": "glow",
				"16": "accountID",
				"32": "friendRequestID",
				"35": "message",
				"37": "age",
				"41": "NewFriendRequest"
			}
			return result

		elif type_ == 5:
			result = {
				"1": "gauntletID",
				"3": "levels",
			}
			return result

		elif type_ == 6:
			result = {
				"1": "Fire",
				"2": "Ice",
				"3": "Poison",
				"4": "Shadow",
				"5": "Lava",
				"6": "Bonus",
				"7": "Chaos",
				"8": "Demon",
				"9": "Time",
				"10": "Crystal",
				"11": "Magic",
				"12": "Spike",
				"13": "Monster",
				"14": "Doom",
				"15": "Death",
				"16": "Forest",
				"17": "Rune",
				"18": "Force",
				"19": "Spooky",
				"20": "Dragon",
				"21": "Water",
				"22": "Haunted",
				"23": "Acid",
				"24": "Witch",
				"25": "Power",
				"26": "Potion",
				"27": "Snake",
				"28": "Toxic",
				"29": "Halloween",
				"30": "Treasure",
				"31": "Ghost",
				"32": "Gem",
				"33": "Inferno",
				"34": "Portal",
				"35": "Strange",
				"36": "Fantasy",
				"37": "Christmas",
				"38": "Surprise",
				"39": "Mystery",
				"40": "Cursed",
				"41": "Cyborg",
				"42": "Castle",
				"43": "Grave",
				"44": "Temple",
				"46": "World",
				"47": "Galaxy",
				"48": "Universe",
				"49": "Discord",
				"50": "Split",
				"51": "NCS I",
				"52": "NCS II",
				"53": "Space",
				"54": "Cosmos"
			}
			return result

		elif type_ == 7:
			result = {
				"1": "userName",
				"2": "playerID",
				"3": "percentage",
				"6": "ranking",
				"9": "icon",
				"10": "playerColor",
				"11": "playerColor2",
				"13": "coins",
				"14": "iconType",
				"15": "special",
				"16": "accountID",
				"42": "age"
			}
			return result

		elif type_ == 8:
			result = {
				"1": "levelID",
				"2": "levelName",
				"3": "description",
				"4": "levelString",
				"5": "version",
				"6": "playerID",
				"8": "difficultyDenominator",
				"9": "difficultyNumerator",
				"10": "downloads",
				"11": "setCompletes",
				"12": "officialSong",
				"13": "gameVersion",
				"14": "likes",
				"15": "length",
				"16": "dislikes",
				"17": "demon",
				"18": "stars",
				"19": "featureScore",
				"25": "auto",
				"26": "recordString",
				"27": "password",
				"28": "uploadDate",
				"29": "updateDate",
				"30": "copiedID",
				"31": "twoPlayer",
				"35": "customSongID",
				"36": "extraString",
				"37": "coins",
				"38": "verifiedCoins",
				"39": "starsRequested",
				"40": "lowDetailMode",
				"41": "dailyNumber",
				"42": "epic",
				"43": "demonDifficulty",
				"44": "isGauntlet",
				"45": "objects",
				"46": "editorTime",
				"47": "editorTimeCopies",
				"48": "settingsString",
				"52": "songIDs",
				"53": "sfxIDs",
				"54": "unknown",
				"57": "verificationTime"
			}
			return result

		elif type_ == 9:
			result = {
				"1": "ID",
				"2": "name",
				"3": "artistID",
				"4": "artistName",
				"5": "size",
				"6": "videoID",
				"7": "youtubeURL",
				"8": "isVerified",
				"9": "songPriority",
				"10": "link",
				"11": "nongEnum",
				"12": "extraArtistIDs",
				"13": "new",
				"14": "newType",
				"15": "extraArtistNames"
			}
			return result

		elif type_ == 10:
			result = {
				"1": "messageID",
				"2": "accountID",
				"3": "playerID",
				"4": "title",
				"5": "messageContent",
				"6": "userName",
				"7": "age",
				"8": "read",
				"9": "sender"
			}
			return result

		elif type_ == 11:
			result = {
				"1": "packID",
				"2": "packName",
				"3": "levels",
				"4": "stars",
				"5": "coins",
				"6": "difficulty",
				"7": "textColor",
				"8": "barColor"
			}
			return result

		elif type_ == 12:
			result = {
				"1": "listID",
				"2": "listName",
				"3": "description",
				"5": "version",
				"7": "difficulty",
				"10": "downloads",
				"14": "likes",
				"19": "rated",
				"28": "uploadDate",
				"29": "updateDate",
				"49": "accountID",
				"50": "username",
				"51": "levelIDs",
				"55": "listReward",
				"56": "listRewardRequirement"
			}
			return result

		else:
			return {}

	@staticmethod
	def _remap(parsed, type_):
		"""
		Type 1: User
		Type 2: Comment
		Type 3: Comment User
		Type 4: Friend Request
		Type 5: Gauntlet
		Type 6: Gauntlet Names
		Type 7: Level Leaderboard
		Type 8: Level
		Type 9: Song
		Type 10: Message
		Type 11: Map Pack
		Type 12: List
		"""
		for oldKey, newKey in Parse._getObjectMap(type_).items():
			if oldKey in parsed:
				parsed[newKey] = parsed.pop(oldKey)

	@staticmethod
	def getGJLevels21(rawText: str, normalise: bool = True):
		'''
		Format:
	
		```py
		{
		    "levels": [
		        {
		            "levelID": levelID,
		            "levelName": levelName,
		            "description": description,
		            "levelString": levelString,
		            "version": version,
		            "playerID": playerID,
		            "difficultyDenominator": difficultyDenominator,
		            "difficultyNumerator": difficultyNumerator,
		            "downloads": downloads,
		            "setCompletes": setCompletes,
		            "officialSong": officialSong,
		            "gameVersion": gameVersion,
		            "likes": likes,
		            "length": length,
		            "dislikes": dislikes,
		            "demon": demon,
		            "stars": stars,
		            "featureScore": featureScore,
		            "auto": auto,
		            "recordString": recordString,
		            "password": password,
		            "uploadDate": uploadDate,
		            "updateDate": updateDate,
		            "copiedID": copiedID,
		            "twoPlayer": twoPlayer,
		            "customSongID": customSongID,
		            "extraString": extraString,
		            "coins": coins,
		            "verifiedCoins": verifiedCoins,
		            "starsRequested": starsRequested,
		            "lowDetailMode": lowDetailMode,
		            "dailyNumber": dailyNumber,
		            "epic": epic,
		            "demonDifficulty": demonDifficulty,
		            "isGauntlet": isGauntlet,
		            "objects": objects,
		            "editorTime": editorTime,
		            "editorTimeCopies": editorTimeCopies,
		            "settingsString": settingsString,
		            "songIDs": songIDs,
		            "sfxIDs": sfxIDs,
		            "unknown": unknown,
		            "verificationTime": verificationTime
		        },
		        ...
		    ],
		    "creators": [
		        {
		            "userID": userID,
		            "username": username,
		            "accountID": accountID
		        },
		        ...
		    ],
		    "songs": [
		        {
		            "ID": ID,
		            "name": name,
		            "artistID": artistID,
		            "artistName": artistName,
		            "size": size,
		            "videoID": videoID,
		            "youtubeURL": youtubeURL,
		            "isVerified": isVerified,
		            "songPriority": songPriority,
		            "link": link,
		            "nongEnum": nongEnum,
		            "extraArtistIDs": extraArtistIDs,
		            "new": new,
		            "newType": newType,
		            "extraArtistNames": extraArtistNames
		        },
		        ...
		    ],
		    "pagination": {
		        "total": total,
		        "offset": offset,
		        "amount": amount
		    },
		    "hash": hash
		}
		```
		'''
		parts = rawText.split("#")

		levelSection = parts[0]
		creatorSection = parts[1]
		songSection = parts[2]
		pageInfo = parts[3]
		hashValue = parts[4]

		levels = []
		for block in levelSection.split("|"):
			parsed = Parse._parseKeyValuePairs(block, splitter=":")

			if not parsed:
				continue

			parsed["3"] = Parse._decode(parsed["3"])

			if normalise is True:
				Parse._remap(parsed, 8)

			levels.append(parsed)


		creators = Parse._parseCreators(creatorSection)
		songs = Parse._parseSongs(songSection)
		if normalise is True:
			for song in songs:
				Parse._remap(song, 9)
		pagination = Parse._parsePagination(pageInfo)

		return {
			"levels": levels,
			"creators": creators,
			"songs": songs,
			"pagination": pagination,
			"hash": hashValue
		}

	@staticmethod
	def getGJComments21(rawText: str, normalise: bool = True):
		'''
		Format:
	
		```py
		{
		    "comments": [
		        {
		            "content": {
		                "levelID": levelID,
		                "comment": comment,
		                "authorPlayerID": authorPlayerID,
		                "likes": likes,
		                "dislikes": dislikes,
		                "messageID": messageID,
		                "spam": spam,
		                "authorAccountID": authorAccountID,
		                "age": age,
		                "percent": percent,
		                "modBadge": modBadge,
		                "moderatorChatColor": moderatorChatColor
		            },
		            "sender": {
		                "userName": userName,
		                "icon": icon,
		                "playerColor": playerColor,
		                "playerColor2": playerColor2,
		                "iconType": iconType,
		                "glow": glow,
		                "accountID": accountID
		            }
		        }
		    ],
		    "pagination": {
		        "total": total,
		        "offset": offset,
		        "amount": amount
		    }
		}
		```
		'''	
		mainPart, paginationPart = rawText.rsplit("#", 1)
		pagination = Parse._parsePagination(paginationPart)
	
		commentBlocks = mainPart.split("|")
	
		comments = []
		for block in commentBlocks:
			parsed = Parse._parseLevelCommentBlock(block)
			if not parsed:
				continue

			if normalise is True:
				Parse._remap(parsed["content"], 2)
				Parse._remap(parsed["sender"], 3)


			comments.append(parsed)
	
		return {
			"comments": comments,
			"pagination": pagination
		}

	@staticmethod
	def getGJAccountComments20(rawText: str, normalise: bool = True):
		'''
		Format:
	
		```py
		{
		    "comments": [
		        {
		            "content": {
		                "levelID": levelID,
		                "comment": comment,
		                "authorPlayerID": authorPlayerID,
		                "likes": likes,
		                "dislikes": dislikes,
		                "messageID": messageID,
		                "spam": spam,
		                "authorAccountID": authorAccountID,
		                "age": age,
		                "percent": percent,
		                "modBadge": modBadge,
		                "moderatorChatColor": moderatorChatColor
		            }
		        }
		    ],
		    "pagination": {
		        "total": total,
		        "offset": offset,
		        "amount": amount
		    }
		}
		```
		'''
		mainPart, paginationPart = rawText.rsplit("#", 1)
		pagination = Parse._parsePagination(paginationPart)
	
		commentBlocks = mainPart.split("|")
	
		comments = []
		for block in commentBlocks:
			parsed = Parse._parseAccountCommentBlock(block)
			if not parsed:
				continue

			if normalise is True:
				Parse._remap(parsed["content"], 2)

			comments.append(parsed)
	
		return {
			"comments": comments,
			"pagination": pagination
		}

	@staticmethod
	def getGJRewards(rawText: str):
		'''
		Format:
		
		```py
		{
		    "rewards": {
		        "randomHash": randomHash,
		        "uuid": uuid,
		        "decodedChk": decodedChk,
		        "udid": udid,
		        "accountID": accountID,
		        "smallChestSecondsLeft": smallChestSecondsLeft,
		        "smallChestRewards": {
		            "orbs": orbs,
		            "diamonds": diamonds,
		            "shardTypes": [
		                shardType1,
		                shardType2
		            ]
		        },
		        "smallChestsClaimedBefore": smallChestsClaimedBefore,
		        "largeChestSecondsLeft": largeChestSecondsLeft,
		        "largeChestRewards": {
		            "orbs": orbs,
		            "diamonds": diamonds,
		            "shardTypes": [
		                shardType1,
		                shardType2
		            ]
		        },
		        "largeChestsClaimedBefore": largeChestsClaimedBefore,
		        "requestType": requestType
		    },
		    "hash": hash
		}
		```
		'''
		data = rawText.split("|")
		rewards = Tools.Encryption.decodeString(data[0], 14).split(":")
		
	
		randomHash = rewards[0]
		uuid = int(rewards[1])
		decodedChk = int(rewards[2])
		udid = rewards[3]
		accountID = int(rewards[4])
		smallChestSecondsLeft = int(rewards[5])
	
		smallChestRewards = rewards[6].split(",")
		orbs1 = int(smallChestRewards[0])
		diamonds1 = int(smallChestRewards[1])
		shard1 = int(smallChestRewards[2])
		shard2 = int(smallChestRewards[3])
	
		smallChestsClaimedBefore = int(rewards[7])
		largeChestSecondsLeft = int(rewards[8])
	
		largeChestRewards = rewards[9].split(",")
		orbs2 = int(largeChestRewards[0])
		diamonds2 = int(largeChestRewards[1])
		shard3 = int(largeChestRewards[2])
		shard4 = int(largeChestRewards[3])
	
		largeChestsClaimedBefore = int(rewards[10])
		requestType = int(rewards[11])
	
	
		return {"rewards": {
					"randomHash": randomHash,
					"uuid": uuid,
					"decodedChk": decodedChk,
					"udid": udid,
					"accountID": accountID,
					"smallChestSecondsLeft": smallChestSecondsLeft,
					"smallChestRewards": {
						"orbs": orbs1,
						"diamonds": diamonds1,
						"shardTypes": [
							shard1,
							shard2
							]
	
						},
					"smallChestsClaimedBefore": smallChestsClaimedBefore,
					"largeChestSecondsLeft": largeChestSecondsLeft,
					"largeChestRewards": {
						"orbs": orbs2,
						"diamonds": diamonds2,
						"shardTypes": [
							shard3,
							shard4
							]
	
						},
					"largeChestsClaimedBefore": largeChestsClaimedBefore,
					"requestType": requestType
					},
				"hash": data[1]
				}

	@staticmethod
	def getGJUserInfo20(rawText: str, normalise: bool = True):
		'''
		Format:
		
		```py
		{
		    "user": {
		        "userName": userName,
		        "userID": userID,
		        "stars": stars,
		        "demons": demons,
		        "ranking": ranking,
		        "accountHighlight": accountHighlight,
		        "creatorPoints": creatorPoints,
		        "iconID": iconID,
		        "color1": color1,
		        "color2": color2,
		        "secretCoins": secretCoins,
		        "iconType": iconType,
		        "special": special,
		        "accountID": accountID,
		        "userCoins": userCoins,
		        "messageState": messageState,
		        "friendsState": friendsState,
		        "youTube": youTube,
		        "accIcon": accIcon,
		        "accShip": accShip,
		        "accBall": accBall,
		        "accBird": accBird,
		        "accWave": accWave,
		        "accRobot": accRobot,
		        "accStreak": accStreak,
		        "accGlow": accGlow,
		        "isRegistered": isRegistered,
		        "globalRank": globalRank,
		        "friendState": friendState,
		        "messages": messages,
		        "friendRequests": friendRequests,
		        "newFriends": newFriends,
		        "newFriendRequest": newFriendRequest,
		        "age": age,
		        "accSpider": accSpider,
		        "twitter": twitter,
		        "twitch": twitch,
		        "diamonds": diamonds,
		        "accExplosion": accExplosion,
		        "modLevel": modLevel,
		        "commentHistoryState": commentHistoryState,
		        "color3": color3,
		        "moons": moons,
		        "accSwing": accSwing,
		        "accJetpack": accJetpack,
		        "demonBreakdown": {
		            "easyDemonCompletions": easyDemonCompletions,
		            "mediumDemonCompletions": mediumDemonCompletions,
		            "hardDemonCompletions": hardDemonCompletions,
		            "insaneDemonCompletions": insaneDemonCompletions,
		            "extremeDemonCompletions": extremeDemonCompletions,
		            "easyPlatformerDemonCompletions": easyPlatformerDemonCompletions,
		            "mediumPlatformerDemonCompletions": mediumPlatformerDemonCompletions,
		            "hardPlatformerDemonCompletions": hardPlatformerDemonCompletions,
		            "insanePlatformerDemonCompletions": insanePlatformerDemonCompletions,
		            "extremePlatformerDemonCompletions": extremePlatformerDemonCompletions,
		            "weeklyDemonCompletions": weeklyDemonCompletions,
		            "gauntletDemonCompletions": gauntletDemonCompletions
		        },
		        "classicLevelBreakdown": {
		            "autoCompletions": autoCompletions,
		            "easyCompletions": easyCompletions,
		            "normalCompletions": normalCompletions,
		            "hardCompletions": hardCompletions,
		            "harderCompletions": harderCompletions,
		            "insaneCompletions": insaneCompletions,
		            "dailyCompletions": dailyCompletions,
		            "gauntletCompletions": gauntletCompletions
		        },
		        "platformerLevelBreakdown": {
		            "autoPlatformerCompletions": autoPlatformerCompletions,
		            "easyPlatformerCompletions": easyPlatformerCompletions,
		            "normalPlatformerCompletions": normalPlatformerCompletions,
		            "hardPlatformerCompletions": hardPlatformerCompletions,
		            "harderPlatformerCompletions": harderPlatformerCompletions,
		            "insanePlatformerCompletions": insanePlatformerCompletions
		        }
		    }
		}
		```
		'''
		user = Parse._parseKeyValuePairs(rawText, ":")
		result = {"user": user}
		for key in result["user"]:
			if key == "55":
				demons = result["user"][key].split(",")
				for index, value in enumerate(demons):
					demons[index] = int(value)
	
				result["user"][key] = {
					"easyDemonCompletions": demons[0],
					"mediumDemonCompletions": demons[1],
					"hardDemonCompletions": demons[2],
					"insaneDemonCompletions": demons[3],
					"extremeDemonCompletions": demons[4],
					"easyPlatformerDemonCompletions": demons[5],
					"mediumPlatformerDemonCompletions": demons[6],
					"hardPlatformerDemonCompletions": demons[7],
					"insanePlatformerDemonCompletions": demons[8],
					"extremePlatformerDemonCompletions": demons[9],
					"weeklyDemonCompletions": demons[10],
					"gauntletDemonCompletions": demons[11]
	
				}
			elif key == "56":
				classics = result["user"][key].split(",")
				for index, value in enumerate(classics):
					classics[index] = int(value)
	
				result["user"][key] = {
					"autoCompletions": classics[0],
					"easyCompletions": classics[1],
					"normalCompletions": classics[2],
					"hardCompletions": classics[3],
					"harderCompletions": classics[4],
					"insaneCompletions": classics[5],
					"dailyCompletions": classics[6],
					"gauntletCompletions": classics[7]
				}
	
			elif key == "57":
				platformers = result["user"][key].split(",")
				for index, value in enumerate(platformers):
					platformers[index] = int(value)
	
				result["user"][key] = {
					"autoPlatformerCompletions": platformers[0],
					"easyPlatformerCompletions": platformers[1],
					"normalPlatformerCompletions": platformers[2],
					"hardPlatformerCompletions": platformers[3],
					"harderPlatformerCompletions": platformers[4],
					"insanePlatformerCompletions": platformers[5]
				}

		if normalise is True:
			Parse._remap(result["user"], 1)
	
		return result

	@staticmethod
	def downloadGJLevel22(rawText: str, normalise: bool = True):
		'''
		Format:
		
		```py
		{
		    "level": {"levelID": levelID,
		              "levelName": levelName,
		              "description": description,
		              "levelString": levelString,
		              "version": version,
		              "playerID": playerID,
		              "difficultyDenominator": difficultyDenominator,
		              "difficultyNumerator": difficultyNumerator,
		              "downloads": downloads,
		              "setCompletes": setCompletes,
		              "officialSong": officialSong,
		              "gameVersion": gameVersion,
		              "likes": likes,
		              "length": length,
		              "dislikes": dislikes,
		              "demon": demon,
		              "stars": stars,
		              "featureScore": featureScore,
		              "auto": auto,
		              "recordString": recordString,
		              "password": password,
		              "uploadDate": uploadDate,
		              "updateDate": updateDate,
		              "copiedID": copiedID,
		              "twoPlayer": twoPlayer,
		              "customSongID": customSongID,
		              "extraString": extraString,
		              "coins": coins,
		              "verifiedCoins": verifiedCoins,
		              "starsRequested": starsRequested,
		              "lowDetailMode": lowDetailMode,
		              "dailyNumber": dailyNumber,
		              "epic": epic,
		              "demonDifficulty": demonDifficulty,
		              "isGauntlet": isGauntlet,
		              "objects": objects,
		              "editorTime": editorTime,
		              "editorTimeCopies": editorTimeCopies,
		              "settingsString": settingsString,
		              "songIDs": songIDs,
		              "sfxIDs": sfxIDs,
		              "unknown": unknown,
		              "verificationTime": verificationTime},
		    "hash1": hash1,
		    "hash2": hash2,
		}
		```
		'''
		data = rawText.split("#")
		level = Parse._parseKeyValuePairs(data[0], ":")
		result = {
			"level": level,
			"hash1": data[1],
			"hash2": data[2],
		}
		if len(data) > 1:
			result["hash1"] = data[1]
			if len(data) > 2:
				result["hash2"] = data[2]

		if len(data) > 3:
			if data[3] != "":
				userID, username, accountID = data[3].split(":")
				result["dailyCreator"] = {
					"userID": userID,
					"username": username,
					"accountID": accountID
				}
			else:
				result["dailyCreator"] = {}
			
			if len(data) > 4:
				if data[4] != "":
					songs = Parse._parseSongs(data[4])
					result["songs"] = songs
					if normalise is True:
						Parse._remap(result["songs"], 9)
				else:
					result["songs"] = []

		for key in result["level"]:
			if key == "3":
				result["level"][key] = Parse._decode(result["level"][key])

			elif key == "27":
				result["level"][key] = Tools.decodeLevelPassword(result["level"][key])

		if normalise is True:
			Parse._remap(result["level"], 8)

		return result

	@staticmethod
	def getGJGauntlets21(rawText: str, normalise: bool = True):
		'''
		Format:
	
		```py
		{
		    "gauntlets": [
		        {
		            "gauntletID": gauntletID,
		            "levels": [
		                levelID,
		                ...
		            ],
		            "gauntletName": gauntletName
		        }
		    ],
		    "hash": hash
		}
		```

		The gauntletIDs are as follows:
		```
		"Fire",
		"Ice",
		"Poison",
		"Shadow",
		"Lava",
		"Bonus",
		"Chaos",
		"Demon",
		"Time",
		"Crystal",
		"Magic",
		"Spike",
		"Monster",
		"Doom",
		"Death",
		"Forest",
		"Rune",
		"Force",
		"Spooky",
		"Dragon",
		"Water",
		"Haunted",
		"Acid",
		"Witch",
		"Power",
		"Potion",
		"Snake",
		"Toxic",
		"Halloween",
		"Treasure",
		"Ghost",
		"Gem",
		"Inferno",
		"Portal",
		"Strange",
		"Fantasy",
		"Christmas",
		"Surprise",
		"Mystery",
		"Cursed",
		"Cyborg",
		"Castle",
		"Grave",
		"Temple",
		"World",
		"Galaxy",
		"Universe",
		"Discord",
		"Split",
		"NCS I",
		"NCS II",
		"Space",
		"Cosmos"
		```
		'''
		data = rawText.split("#")
	
		gauntletSection = data[0]
		hashValue = data[1]
	
		gauntletBlocks = gauntletSection.split("|")
	
		gauntlets = []

		gauntletNameMap = Parse._getObjectMap(6)
	
		for block in gauntletBlocks:
			parsed = Parse._parseKeyValuePairs(block, ":")
	
			parsed["3"] = (
				[
					int(levelID)
					for levelID in parsed["3"].split(",")
				]
				if isinstance(parsed["3"], str)
				else [parsed["3"]]
			)



			if normalise is True:
				Parse._remap(parsed, 5)
				gauntletID = str(parsed["gauntletID"])
				parsed["gauntletName"] = gauntletNameMap.get(
					gauntletID,
					"Unknown"
				)
	
			gauntlets.append(parsed)
	
		return {
			"gauntlets": gauntlets,
			"hash": hashValue
		}

	@staticmethod
	def getGJLevelLists(rawText: str, normalise: bool = True):
		'''
		Format:
		
		```py
		{
		    "lists": [
		        {
		            "listID": listID,
		            "listName": listName,
		            "description": description,
		            "version": version,
		            "difficulty": difficulty,
		            "downloads": downloads,
		            "likes": likes,
		            "rated": rated,
		            "uploadDate": uploadDate,
		            "updateDate": updateDate,
		            "accountID": accountID,
		            "username": username,
		            "levelIDs": [
		                levelID,
		                ...
		            ],
		            "listReward": listReward,
		            "listRewardRequirement": listRewardRequirement
		        }
		    ],
		    "creators": [
		        {
		            "userID": userID,
		            "username": username,
		            "accountID": accountID
		        }
		    ],
		    "pagination": {
		        "total": total,
		        "offset": offset,
		        "amount": amount
		    },
		    "hash": hash
		}
		```
		'''
		parts = rawText.split("#")

		listSection = parts[0]
		creatorSection = parts[1]
		pageInfo = parts[2]
		hashValue = parts[3]

		lists = []
		for block in listSection.split("|"):
			parsed = Parse._parseKeyValuePairs(block, splitter=":")
			parsed["3"] = Parse._decode(parsed["3"])
			parsed["51"] = (
				[
					int(levelID)
					for levelID in parsed["51"].split(",")
				]
				if isinstance(parsed["51"], str)
				else [parsed["51"]]
			)

			if normalise is True:
				Parse._remap(parsed, 12)

			lists.append(parsed)

		creators = Parse._parseCreators(creatorSection)

		pagination = Parse._parsePagination(pageInfo)

		return {
			"lists": lists,
			"creators": creators,
			"pagination": pagination,
			"hash": hashValue
		}

	@staticmethod
	def getGJFriendRequests20(rawText: str, normalise: bool = True):
		'''
		Format:
	
		```py
		{
		    "users": [
		        {
		            "userName": userName,
		            "playerID": playerID,
		            "icon": icon,
		            "playerColor": playerColor,
		            "playerColor2": playerColor2,
		            "iconType": iconType,
		            "glow": glow,
		            "accountID": accountID,
		            "friendRequestID": friendRequestID,
		            "message": message,
		            "age": age,
		            "NewFriendRequest": NewFriendRequest
		        }
		    ],
		    "pagination": {
		        "total": total,
		        "offset": offset,
		        "amount": amount
		    }
		}
		```
		'''
		parts = rawText.split("#")

		userSection = parts[0]
		pageInfo = parts[1]

		users = []
		for block in userSection.split("|"):
			parsed = Parse._parseKeyValuePairs(block, splitter=":")
			parsed["35"] = Parse._decode(parsed["35"])

			if normalise is True:
				Parse._remap(parsed, 4)

			users.append(parsed)

		pagination = Parse._parsePagination(pageInfo)

		return {
			"users": users,
			"pagination": pagination
		}

	@staticmethod
	def getGJMessages20(rawText: str, normalise: bool = True):
		'''
		Format:
		
		```py
		{
		    "messages": [
		        {
		            "messageID": messageID,
		            "accountID": accountID,
		            "playerID": playerID,
		            "title": title,
		            "messageContent": messageContent,
		            "userName": userName,
		            "age": age,
		            "read": read,
		            "sender": sender
		        }
		    ],
		    "pagination": {
		        "total": total,
		        "offset": offset,
		        "amount": amount
		    }
		}
		```
		'''
		parts = rawText.split("#")

		messageSection = parts[0]
		pageInfo = parts[1]

		messages = []
		for block in messageSection.split("|"):
			parsed = Parse._parseKeyValuePairs(block, splitter=":")
			parsed["4"] = Parse._decode(parsed["4"])

			if normalise is True:
				Parse._remap(parsed, 10)

			messages.append(parsed)

		pagination = Parse._parsePagination(pageInfo)

		return {
			"messages": messages,
			"pagination": pagination
		}

	@staticmethod
	def downloadGJMessage20(rawText: str, normalise: bool = True):
		'''
		Format:
		
		```py
		{
		    "message": {
		        "messageID": messageID,
		        "accountID": accountID,
		        "playerID": playerID,
		        "title": title,
		        "messageContent": messageContent,
		        "userName": userName,
		        "age": age,
		        "read": read,
		        "sender": sender
		    }
		}
		```
		'''
		parts = rawText.split("#")

		messageSection = parts[0]
		parsed = {}

		for block in messageSection.split("|"):
			parsed = Parse._parseKeyValuePairs(block, splitter=":")
			parsed["4"] = Parse._decode(parsed["4"])
			parsed["5"] = Tools.Encryption.decodeString(parsed["5"], 2)

			if normalise is True:
				Parse._remap(parsed, 10)

		return {
			"message": parsed
		}

	@staticmethod
	def getGJMapPacks21(rawText: str, normalise: bool = True):
		'''
		Format:
		
		```py
		{
		    "packs": [
		        {
		            "packID": packID,
		            "packName": packName,
		            "levels": [
		                levelID,
		                ...
		            ],
		            "stars": stars,
		            "coins": coins,
		            "difficulty": difficulty,
		            "textColor": {
		                "r": r,
		                "g": g,
		                "b": b
		            },
		            "barColor": {
		                "r": r,
		                "g": g,
		                "b": b
		            }
		        }
		    ],
		    "pagination": {
		        "total": total,
		        "offset": offset,
		        "amount": amount
		    },
		    "hash": hash
		}
		```
		'''
		parts = rawText.split("#")

		mapSection = parts[0]
		pageInfo = parts[1]
		hashValue = parts[2]

		packs = []
		for block in mapSection.split("|"):
			parsed = Parse._parseKeyValuePairs(block, splitter=":")
			parsed["4"] = Parse._decode(parsed["4"])

			parsed["3"] = (
				[
					int(levelID)
					for levelID in parsed["3"].split(",")
				]
				if isinstance(parsed["3"], str)
				else [parsed["3"]]
			)

			r, g, b = map(int, parsed["7"].split(","))
			parsed["7"] = {
				"r": r,
				"g": g,
				"b": b
			}
			
			r, g, b = map(int, parsed["8"].split(","))
			parsed["8"] = {
				"r": r,
				"g": g,
				"b": b
			}
			
			if normalise is True:
				Parse._remap(parsed, 11)

			packs.append(parsed)

		pagination = Parse._parsePagination(pageInfo)

		return {
			"packs": packs,
			"pagination": pagination,
			"hash": hashValue
		}

	@staticmethod
	def getGJDailyLevel(rawText: str):
		'''
		Format:
		
		```py
		{
		    "tempID": tempID,
		    "secondsLeft": secondsLeft
		}
		```
		'''
		parts = rawText.split("|")

		return {
			"tempID": parts[0],
			"secondsLeft": parts[1]
		}

	@staticmethod
	def getGJScores20(rawText: str, normalise: bool = True):
		'''
		Format:
		
		```py
		{
		    "users": [
		        {
		            "userName": userName,
		            "userID": userID,
		            "stars": stars,
		            "demons": demons,
		            "ranking": ranking,
		            "accountHighlight": accountHighlight,
		            "creatorPoints": creatorPoints,
		            "iconID": iconID,
		            "color1": color1,
		            "color2": color2,
		            "secretCoins": secretCoins,
		            "iconType": iconType,
		            "special": special,
		            "accountID": accountID,
		            "userCoins": userCoins,
		            "messageState": messageState,
		            "friendsState": friendsState,
		            "youTube": youTube,
		            "accIcon": accIcon,
		            "accShip": accShip,
		            "accBall": accBall,
		            "accBird": accBird,
		            "accWave": accWave,
		            "accRobot": accRobot,
		            "accStreak": accStreak,
		            "accGlow": accGlow,
		            "isRegistered": isRegistered,
		            "globalRank": globalRank,
		            "friendState": friendState,
		            "messages": messages,
		            "friendRequests": friendRequests,
		            "newFriends": newFriends,
		            "newFriendRequest": newFriendRequest,
		            "age": age,
		            "accSpider": accSpider,
		            "twitter": twitter,
		            "twitch": twitch,
		            "diamonds": diamonds,
		            "accExplosion": accExplosion,
		            "modLevel": modLevel,
		            "commentHistoryState": commentHistoryState,
		            "color3": color3,
		            "moons": moons,
		            "accSwing": accSwing,
		            "accJetpack": accJetpack,
		            "demonBreakdown": {
		                "easyDemonCompletions": easyDemonCompletions,
		                "mediumDemonCompletions": mediumDemonCompletions,
		                "hardDemonCompletions": hardDemonCompletions,
		                "insaneDemonCompletions": insaneDemonCompletions,
		                "extremeDemonCompletions": extremeDemonCompletions,
		                "easyPlatformerDemonCompletions": easyPlatformerDemonCompletions,
		                "mediumPlatformerDemonCompletions": mediumPlatformerDemonCompletions,
		                "hardPlatformerDemonCompletions": hardPlatformerDemonCompletions,
		                "insanePlatformerDemonCompletions": insanePlatformerDemonCompletions,
		                "extremePlatformerDemonCompletions": extremePlatformerDemonCompletions,
		                "weeklyDemonCompletions": weeklyDemonCompletions,
		                "gauntletDemonCompletions": gauntletDemonCompletions
		            },
		            "classicLevelBreakdown": {
		                "autoCompletions": autoCompletions,
		                "easyCompletions": easyCompletions,
		                "normalCompletions": normalCompletions,
		                "hardCompletions": hardCompletions,
		                "harderCompletions": harderCompletions,
		                "insaneCompletions": insaneCompletions,
		                "dailyCompletions": dailyCompletions,
		                "gauntletCompletions": gauntletCompletions
		            },
		            "platformerLevelBreakdown": {
		                "autoPlatformerCompletions": autoPlatformerCompletions,
		                "easyPlatformerCompletions": easyPlatformerCompletions,
		                "normalPlatformerCompletions": normalPlatformerCompletions,
		                "hardPlatformerCompletions": hardPlatformerCompletions,
		                "harderPlatformerCompletions": harderPlatformerCompletions,
		                "insanePlatformerCompletions": insanePlatformerCompletions
		            }
		        },
		        ...
		    ]
		}
		```
		'''
		parts = rawText.split("|")

		users = []
		for block in parts:
			if block != "":
				parsed = Parse._parseKeyValuePairs(block, splitter=":")
				if not parsed:
					continue
				
				if normalise is True:
					Parse._remap(parsed, 1)
			else:
				parsed = {}

			users.append(parsed)

		return {
			"users": users
		}

	@staticmethod
	def getGJLevelScores211(rawText: str, normalise: bool = True):
		'''
		Format:
		
		```py
		{
		    "scores": [
		        {
		            "userName": userName,
		            "playerID": playerID,
		            "percentage": percentage,
		            "ranking": ranking,
		            "icon": icon,
		            "playerColor": playerColor,
		            "playerColor2": playerColor2,
		            "coins": coins,
		            "iconType": iconType,
		            "special": special,
		            "accountID": accountID,
		            "age": age
		        }
		    ]
		}
		```
		'''
		parts = rawText.split("|")

		scores = []
		for block in parts:
			if block != "":
				parsed = Parse._parseKeyValuePairs(block, splitter=":")
			else:
				parsed = {}
			
			if normalise is True:
				Parse._remap(parsed, 7)

			scores.append(parsed)

		return {
			"scores": scores
		}

	@staticmethod
	def getGJLevelScoresPlat(rawText: str):
		'''
		Format:
		
		```py
		{
		    "scores": [
		        {
		            "userName": userName,
		            "playerID": playerID,
		            "percentage": percentage,
		            "ranking": ranking,
		            "icon": icon,
		            "playerColor": playerColor,
		            "playerColor2": playerColor2,
		            "coins": coins,
		            "iconType": iconType,
		            "special": special,
		            "accountID": accountID,
		            "age": age
		        }
		    ]
		}
		```
		'''
		return Parse.getGJLevelScores211(rawText)

	@staticmethod
	def getGJSecretReward(rawText: str):
		'''
		Format:
		
		```py
		{
		    "reward": {
		        "randomHash": randomHash,
		        "decodedChk": decodedChk,
		        "rewardID": rewardID,
		        "chestType": chestType,
		        "rewards": {
		            rewardType: amount,
		            ...
		        }
		    },
		    "hash": hash
		}
		```
		'''
		parts = rawText.split("|")

		reward = {}
		rewardValue = Tools.Encryption.decodeString(parts[0], type_=14).split(":")
		hashValue = parts[1]

		reward["randomHash"] = rewardValue[0]
		reward["decodedChk"] = rewardValue[1]
		reward["rewardID"] = rewardValue[2]
		reward["chestType"] = rewardValue[3]
		reward["rewards"] = Parse._parseKeyValuePairs(rewardValue[4], splitter=",")
		

		return {
			"reward": reward,
			"hash": hashValue
		}

	@staticmethod
	def getGJSongInfo(rawText: str, normalise: bool = True):
		'''
		Format:
		
		```py
		{
		    "song": {
		        "ID": ID,
		        "name": name,
		        "artistID": artistID,
		        "artistName": artistName,
		        "size": size,
		        "videoID": videoID,
		        "youtubeURL": youtubeURL,
		        "isVerified": isVerified,
		        "songPriority": songPriority,
		        "link": link,
		        "nongEnum": nongEnum,
		        "extraArtistIDs": extraArtistIDs,
		        "new": new,
		        "newType": newType,
		        "extraArtistNames": extraArtistNames
		    }
		}
		```
		'''
		song = Parse._parseKeyValuePairs(rawText, splitter="~|~")

		if normalise is True:
			Parse._remap(song, 9)

		return {
			"song": song,
		}

	@staticmethod
	def getGJChallenges(rawText: str):
		'''
		Format:
		
		```py
		{
		    "challenges": {
		        "randomHash": randomHash,
		        "uuid": uuid,
		        "decodedChk": decodedChk,
		        "udid": udid,
		        "accountID": accountID,
		        "secondsLeft": secondsLeft,
		        "queuedQuests": [
		            {
		                "id": id,
		                "type": type,
		                "goal": goal,
		                "reward": reward,
		                "name": name
		            }
		        ]
		    },
		    "hash": hash
		}
		```
		'''
		parts = rawText.split("|")

		challenges = {}
		challengeValue = Tools.Encryption.decodeString(parts[0], type_=4).split(":")
		hashValue = parts[1]

		challenges["randomHash"] = challengeValue[0]
		challenges["uuid"] = challengeValue[1]
		challenges["decodedChk"] = challengeValue[2]
		challenges["udid"] = challengeValue[3]
		challenges["accountID"] = challengeValue[4]
		challenges["secondsLeft"] = challengeValue[5]
		queuedQuests = []

		for blocks in challengeValue[6:]:
			id_, type_, goal, reward, name = map(lambda x: int(x) if x.isdigit() else str(x), blocks.split(","))
			queuedQuests.append({
				"id": id_,
				"type": type_,
				"goal": goal,
				"reward": reward,
				"name": name
				})

		challenges["queuedQuests"] = queuedQuests

		return {
			"challenges": challenges,
			"hash": hashValue
		}

	@staticmethod
	def getGJCommentHistory(rawText: str, normalise: bool = True):
		'''
		Format:
	
		```py
		{
		    "comments": [
		        {
		            "content": {
		                "levelID": levelID,
		                "comment": comment,
		                "authorPlayerID": authorPlayerID,
		                "likes": likes,
		                "dislikes": dislikes,
		                "messageID": messageID,
		                "spam": spam,
		                "authorAccountID": authorAccountID,
		                "age": age,
		                "percent": percent,
		                "modBadge": modBadge,
		                "moderatorChatColor": moderatorChatColor
		            },
		            "sender": {
		                "userName": userName,
		                "icon": icon,
		                "playerColor": playerColor,
		                "playerColor2": playerColor2,
		                "iconType": iconType,
		                "glow": glow,
		                "accountID": accountID
		            }
		        }
		    ],
		    "pagination": {
		        "total": total,
		        "offset": offset,
		        "amount": amount
		    }
		}
		```
		'''	
		return Parse.getGJComments21(rawText, normalise)

	@staticmethod
	def getGJUsers20(rawText: str, normalise: bool = True):
		'''
		Format:
		
		```py
		{
		    "users": [
		        {
		            "userName": userName,
		            "userID": userID,
		            "stars": stars,
		            "demons": demons,
		            "ranking": ranking,
		            "accountHighlight": accountHighlight,
		            "creatorPoints": creatorPoints,
		            "iconID": iconID,
		            "color1": color1,
		            "color2": color2,
		            "secretCoins": secretCoins,
		            "iconType": iconType,
		            "special": special,
		            "accountID": accountID,
		            "userCoins": userCoins,
		            "messageState": messageState,
		            "friendsState": friendsState,
		            "youTube": youTube,
		            "accIcon": accIcon,
		            "accShip": accShip,
		            "accBall": accBall,
		            "accBird": accBird,
		            "accWave": accWave,
		            "accRobot": accRobot,
		            "accStreak": accStreak,
		            "accGlow": accGlow,
		            "isRegistered": isRegistered,
		            "globalRank": globalRank,
		            "friendState": friendState,
		            "messages": messages,
		            "friendRequests": friendRequests,
		            "newFriends": newFriends,
		            "newFriendRequest": newFriendRequest,
		            "age": age,
		            "accSpider": accSpider,
		            "twitter": twitter,
		            "twitch": twitch,
		            "diamonds": diamonds,
		            "accExplosion": accExplosion,
		            "modLevel": modLevel,
		            "commentHistoryState": commentHistoryState,
		            "color3": color3,
		            "moons": moons,
		            "accSwing": accSwing,
		            "accJetpack": accJetpack,
		            "demonBreakdown": {
		                "easyDemonCompletions": easyDemonCompletions,
		                "mediumDemonCompletions": mediumDemonCompletions,
		                "hardDemonCompletions": hardDemonCompletions,
		                "insaneDemonCompletions": insaneDemonCompletions,
		                "extremeDemonCompletions": extremeDemonCompletions,
		                "easyPlatformerDemonCompletions": easyPlatformerDemonCompletions,
		                "mediumPlatformerDemonCompletions": mediumPlatformerDemonCompletions,
		                "hardPlatformerDemonCompletions": hardPlatformerDemonCompletions,
		                "insanePlatformerDemonCompletions": insanePlatformerDemonCompletions,
		                "extremePlatformerDemonCompletions": extremePlatformerDemonCompletions,
		                "weeklyDemonCompletions": weeklyDemonCompletions,
		                "gauntletDemonCompletions": gauntletDemonCompletions
		            },
		            "classicLevelBreakdown": {
		                "autoCompletions": autoCompletions,
		                "easyCompletions": easyCompletions,
		                "normalCompletions": normalCompletions,
		                "hardCompletions": hardCompletions,
		                "harderCompletions": harderCompletions,
		                "insaneCompletions": insaneCompletions,
		                "dailyCompletions": dailyCompletions,
		                "gauntletCompletions": gauntletCompletions
		            },
		            "platformerLevelBreakdown": {
		                "autoPlatformerCompletions": autoPlatformerCompletions,
		                "easyPlatformerCompletions": easyPlatformerCompletions,
		                "normalPlatformerCompletions": normalPlatformerCompletions,
		                "hardPlatformerCompletions": hardPlatformerCompletions,
		                "harderPlatformerCompletions": harderPlatformerCompletions,
		                "insanePlatformerCompletions": insanePlatformerCompletions
		            }
		        },
		        ...
		    ],
		    "pagination": {
		        "total": total,
		        "offset": offset,
		        "amount": amount
		    }
		}
		```
		'''
		mainPart, paginationPart = rawText.rsplit("#", 1)
		pagination = Parse._parsePagination(paginationPart)
	
		userBlocks = mainPart.split("|")
	
		users = []
	
		for block in userBlocks:
			parsed = Parse._parseKeyValuePairs(block, splitter=":")
	
			if not parsed:
				continue
			
			if normalise is True:
				Parse._remap(parsed, 1)
	
			users.append(parsed)
	
		return {
			"users": users,
			"pagination": pagination
		}

	@staticmethod
	def getGJUserList20(rawText: str, normalise: bool = True):
		'''
		Format:
		
		```py
		{
		    "users": [
		        {
		            "userName": userName,
		            "userID": userID,
		            "stars": stars,
		            "demons": demons,
		            "ranking": ranking,
		            "accountHighlight": accountHighlight,
		            "creatorPoints": creatorPoints,
		            "iconID": iconID,
		            "color1": color1,
		            "color2": color2,
		            "secretCoins": secretCoins,
		            "iconType": iconType,
		            "special": special,
		            "accountID": accountID,
		            "userCoins": userCoins,
		            "messageState": messageState,
		            "friendsState": friendsState,
		            "youTube": youTube,
		            "accIcon": accIcon,
		            "accShip": accShip,
		            "accBall": accBall,
		            "accBird": accBird,
		            "accWave": accWave,
		            "accRobot": accRobot,
		            "accStreak": accStreak,
		            "accGlow": accGlow,
		            "isRegistered": isRegistered,
		            "globalRank": globalRank,
		            "friendState": friendState,
		            "messages": messages,
		            "friendRequests": friendRequests,
		            "newFriends": newFriends,
		            "newFriendRequest": newFriendRequest,
		            "age": age,
		            "accSpider": accSpider,
		            "twitter": twitter,
		            "twitch": twitch,
		            "diamonds": diamonds,
		            "accExplosion": accExplosion,
		            "modLevel": modLevel,
		            "commentHistoryState": commentHistoryState,
		            "color3": color3,
		            "moons": moons,
		            "accSwing": accSwing,
		            "accJetpack": accJetpack,
		            "demonBreakdown": {
		                "easyDemonCompletions": easyDemonCompletions,
		                "mediumDemonCompletions": mediumDemonCompletions,
		                "hardDemonCompletions": hardDemonCompletions,
		                "insaneDemonCompletions": insaneDemonCompletions,
		                "extremeDemonCompletions": extremeDemonCompletions,
		                "easyPlatformerDemonCompletions": easyPlatformerDemonCompletions,
		                "mediumPlatformerDemonCompletions": mediumPlatformerDemonCompletions,
		                "hardPlatformerDemonCompletions": hardPlatformerDemonCompletions,
		                "insanePlatformerDemonCompletions": insanePlatformerDemonCompletions,
		                "extremePlatformerDemonCompletions": extremePlatformerDemonCompletions,
		                "weeklyDemonCompletions": weeklyDemonCompletions,
		                "gauntletDemonCompletions": gauntletDemonCompletions
		            },
		            "classicLevelBreakdown": {
		                "autoCompletions": autoCompletions,
		                "easyCompletions": easyCompletions,
		                "normalCompletions": normalCompletions,
		                "hardCompletions": hardCompletions,
		                "harderCompletions": harderCompletions,
		                "insaneCompletions": insaneCompletions,
		                "dailyCompletions": dailyCompletions,
		                "gauntletCompletions": gauntletCompletions
		            },
		            "platformerLevelBreakdown": {
		                "autoPlatformerCompletions": autoPlatformerCompletions,
		                "easyPlatformerCompletions": easyPlatformerCompletions,
		                "normalPlatformerCompletions": normalPlatformerCompletions,
		                "hardPlatformerCompletions": hardPlatformerCompletions,
		                "harderPlatformerCompletions": harderPlatformerCompletions,
		                "insanePlatformerCompletions": insanePlatformerCompletions
		            }
		        },
		        ...
		    ]
		}
		```
		'''
		commentBlocks = rawText.split("|")
	
		users = []
		for block in commentBlocks:
			parsed = Parse._parseKeyValuePairs(block, splitter=":")
			if not parsed:
				continue

			if normalise is True:
				Parse._remap(parsed, 1)

			users.append(parsed)
	
		return {
			"users": users
		}

	@staticmethod
	def loginGJAccount(rawText: str):
		'''
		Format:
		
		```py
		{
		    "accountID": accountID,
		    "uuid": uuid
		}
		```
		'''
		data = rawText.split(",")

		return {
			"accountID": data[0],
			"uuid": data[1]
		}

	@staticmethod
	def getGJTopArtists(rawText: str, normalise: bool = True):
		'''
		Format:
		
		```py
		{
		    "artists": [
		        {
		            "ID": ID,
		            "name": name,
		            "artistID": artistID,
		            "artistName": artistName,
		            "size": size,
		            "videoID": videoID,
		            "youtubeURL": youtubeURL,
		            "isVerified": isVerified,
		            "songPriority": songPriority,
		            "link": link,
		            "nongEnum": nongEnum,
		            "extraArtistIDs": extraArtistIDs,
		            "new": new,
		            "newType": newType,
		            "extraArtistNames": extraArtistNames
		        }
		    ],
		    "pagination": {
		        "total": total,
		        "offset": offset,
		        "amount": amount
		    }
		}
		```
		'''	
		mainPart, paginationPart = rawText.rsplit("#", 1)
		pagination = Parse._parsePagination(paginationPart)
	
		artistBlocks = mainPart.split("|")
	
		artists = []
		for block in artistBlocks:
			parsed = Parse._parseKeyValuePairs(block, splitter=":")

			if not parsed:
				continue

			if normalise is True:
				Parse._remap(parsed, 9)

			artists.append(parsed)
	
		return {
			"artists": artists,
			"pagination": pagination
		}

	@staticmethod
	def syncGJAccountNew(rawText: str, normalise: bool = True):
		'''
		Format:
	
		```py
		{
		    "gameManager": gameManager,    # Decoded string
		    "levelManager": levelManager,  # Decoded string
		    "gameVersion": gameVersion,
		    "binaryVersion": binaryVersion,
		    "levels": {
		        levelID: stars,
		        ...
		    },
		    "mapPacks": [
		        {
		            "packID": packID,
		            "packName": packName,
		            "levels": [
		                levelID,
		                ...
		            ],
		            "stars": stars,
		            "coins": coins,
		            "difficulty": difficulty,
		            "textColor": {
		                "r": r,
		                "g": g,
		                "b": b
		            },
		            "barColor": {
		                "r": r,
		                "g": g,
		                "b": b
		            }
		        }
		    ]
		}
		```
		'''
		gameManager, levelManager, gameVersion, binaryVersion, levels, mapPacks = rawText.split(";")

		gameManager = Tools.Encryption.decodeString(gameManager, 17)
		levelManager = Tools.Encryption.decodeString(levelManager, 17)
		
		levels = Tools.Encryption.decodeString(levels, 18)
		mapPacks = Tools.Encryption.decodeString(mapPacks, 18)

		levels = Parse._parseKeyValuePairs(levels, splitter=",")

		mapBlocks = []
		for block in mapPacks.split("|"):
			parsed = Parse._parseKeyValuePairs(block, splitter=":")
			parsed["3"] = (
				[
					int(levelID)
					for levelID in parsed["3"].split(",")
				]
				if isinstance(parsed["3"], str)
				else [parsed["3"]]
			)
			r, g, b = map(int, parsed["7"].split(","))
			parsed["7"] = {
				"r": r,
				"g": g,
				"b": b
			}
			
			r, g, b = map(int, parsed["8"].split(","))
			parsed["8"] = {
				"r": r,
				"g": g,
				"b": b
			}

			mapBlocks.append(parsed)

		if normalise is True:
			for mapPack in mapBlocks:
				Parse._remap(mapPack, 11)

		return {
			"gameManager": gameManager,
			"levelManager": levelManager,
			"gameVersion": gameVersion,
			"binaryVersion": binaryVersion,
			"levels": levels,
			"mapPacks": mapBlocks
		}

class Tools:

	class Encryption:
		"""
		Tools related to encoding and decoding data
		"""
	
		@staticmethod
		def buildSaveData(gameManager, localLevels):
			manager = Tools.Encryption.encodeString(gameManager, 17)
			levels = Tools.Encryption.encodeString(localLevels, 17)
			return manager + ";" + levels
	
		@staticmethod
		def decodeString(data, type_: int) -> str:
			"""
			```
			- Type 1: Player Save Data
			- Type 2:  Player Messages
			- Type 3:  Vault Codes
			- Type 4:  Daily Challenges
			- Type 5:  Level Password
			Type 6:  Comment Integrity
			Type 7:  Account Password
			Type 8:  Level Leaderboard Integrity
			Type 9:  Level Integrity
			Type 10: Load Data
			Type 11: Multiplayer
			- Type 12: Music/SFX Library Secret
			Type 13: Rating Integrity
			- Type 14: Chest Rewards
			Type 15: Stat Submission Integrity
			- Type 16: Level Object Data
			- Type 17: Decoded Manager (syncGJAccountNew)
			- Type 18: Level / Map (syncGJAccountNew)
			```
			"""
			if type_ == 1:
				if isinstance(data, bytes):
					xored = Tools.xorCipher(data, 11)
				else:
					xored = Tools.xorCipher(data.encode("latin-1"), 11)
				decoded = base64.urlsafe_b64decode(xored)
				result = gzip.decompress(decoded).decode("latin-1")
				return result
	
			if type_ == 2:
				return Tools.xorCipher(
				Tools.b64DecodeUrlSafe(data),
				Tools.getXorKey(2)
				)
	
			elif type_ == 3:
				return Tools.xorCipher(
					Tools.b64DecodeUrlSafe(data),
					Tools.getXorKey(3)
				)[:-12]
	
			elif type_ == 4:
				return Tools.xorCipher(
					Tools.b64DecodeUrlSafe(data[5:]), Tools.getXorKey(4)
					)

			elif type_ == 5:
				return Tools.decodeLevelPassword(data)

			elif type_ == 12:
				return zlib.decompress(
					Tools.b64DecodeUrlSafeBytes(
						data.encode("latin-1")
						)
					).decode("latin-1")
	
			elif type_ == 14:
				return Tools.xorCipher(
					Tools.b64DecodeUrlSafe(data[5:]), Tools.getXorKey(14)
					)
	
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
							Tools.b64DecodeUrlSafeBytes(data.encode())
							).decode()
			
					except Exception:
						continue
				return ""
	
			if type_ == 17:
				result = data.encode("latin-1")
				b64Decoded = Tools.b64DecodeUrlSafeBytes(result)
				result = gzip.decompress(b64Decoded)
				return result.decode("latin-1")
	
			if type_ == 18:
				resultData = data[20:-20].encode("latin1")
				resultData = Tools.b64DecodeUrlSafeBytes(resultData)
				result = zlib.decompress(resultData).decode()
				return result
	
			else: return data
	
		@staticmethod
		def encodeString(data: str, type_: int, useGzip: bool = True) -> str:
			"""
			```
			- Type 1: Player Save Data
			- Type 2:  Player Messages
			- Type 3:  Vault Codes
			- Type 4:  Daily Challenges
			- Type 5:  Level Password
			Type 6:  Comment Integrity
			Type 7:  Account Password
			Type 8:  Level Leaderboard Integrity
			Type 9:  Level Integrity
			Type 10: Load Data
			Type 11: Multiplayer
			- Type 12: Music/SFX Library Secret
			Type 13: Rating Integrity
			- Type 14: Chest Rewards
			Type 15: Stat Submission Integrity
			- Type 16: Level Object Data
			- Type 17: Decoded Manager (syncGJAccountNew)
			- Type 18: Level / Map (syncGJAccountNew)
			```
			"""
			if type_ == 1:
				raw = data.encode("latin-1")
				compressed = gzip.compress(raw)
				b64 = Tools.b64EncodeUrlSafeBytes(compressed)
				xored = Tools.xorCipher(b64, 11)
				return xored.decode("latin-1")
	
			if type_ == 2:
				return Tools.b64EncodeUrlSafe(
				Tools.xorCipher(
					data,
					Tools.getXorKey(2))
				)
	
			elif type_ == 3:
				return Tools.b64EncodeUrlSafe(
					Tools.xorCipher(
					data + Tools.getSalt(8),
					Tools.getXorKey(3))
				)
			elif type_ == 4:
				encoded = Tools.b64EncodeUrlSafe(
					Tools.xorCipher(
						data,
						Tools.getXorKey(4)
					)
				)
				return Tools.generateRs(5) + encoded
			
			elif type_ == 5:
				return Tools.encodeLevelPassword(data)

			elif type_ == 12:
				return Tools.b64EncodeUrlSafeBytes(
					zlib.compress(
						data.encode("latin-1")
						)
					).decode("latin-1")
	
			elif type_ == 14:
				encoded = Tools.b64EncodeUrlSafe(
					Tools.xorCipher(
						data,
						Tools.getXorKey(14)
					)
				)
				return Tools.generateRs(5) + encoded
	
			elif type_ == 16:
				data2 = data.encode()
				if useGzip:
					buf = io.BytesIO()
					with gzip.GzipFile(fileobj=buf, mode="wb", mtime=0) as f:
						f.write(data2)
					compressed = buf.getvalue()
				else:
					compressed = zlib.compress(data2)[2:-4]
				return Tools.b64EncodeUrlSafeBytes(compressed).decode()
	
			elif type_ == 17:
				raw = data.encode("latin-1")
				buf = io.BytesIO()
				with gzip.GzipFile(fileobj=buf, mode="wb", mtime=0) as f:
					f.write(raw)
			
				compressed = buf.getvalue()
				b64 = Tools.b64EncodeUrlSafeBytes(compressed)
				return b64.decode("latin-1")
	
			elif type_ == 18:
				compressed = zlib.compress(data.encode())
				b64 = Tools.b64EncodeUrlSafeBytes(compressed).decode()
				return Tools.generateRs(20) + b64 + Tools.generateRs(20)
	
			else: return data
	
	class Hashes:
	
		@staticmethod
		def hashGetGJLevels(levelRows: Sequence[dict | Sequence]) -> str:
			"""
			Per-level segments: first digit of level ID, last digit, stars, coin count,
			1 if coins verified else 0. Salt xI25fpAapCQg; result is SHA-1 hex.
			"""
			salt = Tools.getSalt(1)
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
			salt = Tools.getSalt(1)
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
			salt = Tools.getSalt(1)
			pw = Tools.Hashes.normalizePasswordForDownloadHash(password)
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
			salt = Tools.getSalt(1)
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
			salt = Tools.getSalt(1)
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
			salt = Tools.getSalt(6)
			return hashlib.sha1((undecodedResponse[5:] + salt).encode()).hexdigest()
	
		@staticmethod
		def hashGetGJRewards(undecodedResponse: str) -> str:
			salt = Tools.getSalt(7)
			return hashlib.sha1((undecodedResponse[5:] + salt).encode()).hexdigest()

	@staticmethod
	def b64EncodeUrlSafe(data: str) -> str:
		return base64.urlsafe_b64encode(data.encode()).decode()
	
	@staticmethod
	def b64DecodeUrlSafe(b64: str) -> str:
		return base64.urlsafe_b64decode(b64).decode()
	
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
			with open(f"{name}.{ext}", "w", encoding="utf-8") as file:
				file.write(response)
		else:
			with open(f"{name}.{ext}", "w", encoding="utf-8") as file:
				file.write(str(response))
	
	@staticmethod
	def makeReq(url: str, data: dict):
		response = requests.post(url, data, headers={"User-Agent": ""}, verify=False)
		if response.status_code != 200:
			raise RuntimeError("Could not reach server")
		return response
	
	@staticmethod
	def checkResponse(response: str) -> bool:
		if re.fullmatch(r"-\d+", response):
			return False
		return True
	
	@staticmethod
	def xorCipher(data: Any, key: Any) -> Any:
		if isinstance(data, str):
			if isinstance(key, str):
				resultChars = []
				keyLength = len(key)
	
				for i, ch in enumerate(data):
					byteVal = ord(ch)
					xKey = ord(key[i % keyLength])
					resultChars.append(chr(byteVal ^ xKey))
		
				return "".join(resultChars)
			else:
				raise ValueError("Cannot perform cyclic xor using an integer key")
		elif isinstance(data, bytes):
			if isinstance(key, int):
				if key != 11:
					raise ValueError("Only integer key supported is 11")
				return bytes(b ^ key for b in data)
			elif isinstance(key, str):
				raise ValueError("Only integer keys supported for bytes input")
			else:
				if not key:
					raise ValueError("Key must not be empty")
	
				raise ValueError("Invalid key type")
		else:
			raise ValueError("Invalid data type")
	
	
	@staticmethod
	def genChk(keyIndex: int, values: Sequence[int | str] | None = None, saltIndex: int = 1) -> str:
		"""
		Keys:
		```
		1:  Key 11: Player Save Data
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
		Salts:
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
		salt: str = Tools.getSalt(saltIndex)
		key: int | str = Tools.getXorKey(keyIndex)

		allValues = list(values) if values is not None else []
		allValues.append(salt)
	
		string = "".join(map(str, allValues))
		hashed = hashlib.sha1(string.encode()).hexdigest()
	
		xored = Tools.xorCipher(hashed, key)
		chk = Tools.b64EncodeUrlSafe(xored)
	
		return chk
	
	@staticmethod
	def getObjectIDs(objectString: str) -> list:
		"""
		Returns all object IDs in an object string such that it's length evaluates to the object count
		"""
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
		return objectIds

	@staticmethod
	def getCoinCount(objectString: str) -> int:
		"""
		Counts the amount of coins in object data
		"""
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
	def _generateClassicLeaderboardSeed(
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
	def _generateLeaderboardRandom(hasPlatformerSeed: bool = False) -> int:
		_leaderboardRandState = int(time.time()) & 0x7FFFFFFF
		if not hasattr(_leaderboardRandState, "state"):
			_leaderboardRandState = int(time.time()) & 0x7FFFFFFF
	
		_leaderboardRandState = (
			_leaderboardRandState * 214013 + 2531011
		) & 0x7FFFFFFF
	
		value = (_leaderboardRandState >> 16) & 0x7FFF
	
		if hasPlatformerSeed:
			value += 2000
	
		return value

	@staticmethod
	def _generatePlatformerHash(bestTime, bestPoints):
		number = (((bestTime + 7890) % 34567) * 601 + ((abs(bestPoints) + 3456) % 78901) * 967 + 94819) % 94433
		return ((number ^ number >> 16) * 829) % 77849
	
	@staticmethod
	def getXorKey(index: int) -> int | str:
		"""
		```
		1:  Key 11: Player Save Data
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
	def generateGjp2(password: str) -> str:
		salt = Tools.getSalt(9)
		return hashlib.sha1((password + salt).encode()).hexdigest()
	
	
	
	@staticmethod
	def crackGjp2(gjp2: str) -> str | None:
		"""
		Downloads rockyou.txt on first run.
		Checks the gjp2 against every password in the list.
		"""
		ROCKYOU_URL = "https://github.com/brannondorsey/naive-hashcat/releases/download/data/rockyou.txt"
		ROCKYOU_PATH = os.path.join(os.path.dirname(__file__), "rockyou.txt")
		SALT = "mI29fmAnxgTs"
	
		def ensureRockyou():
			if not os.path.isfile(ROCKYOU_PATH):
				ssl._create_default_https_context = ssl._create_unverified_context
				urllib.request.urlretrieve(ROCKYOU_URL, ROCKYOU_PATH)
				ssl._create_default_https_context = ssl.create_default_context
	
		def generateGjp2(password: str, saltBytes: bytes) -> str:
			return hashlib.sha1(password.encode() + saltBytes).hexdigest()
	
		# Prepare
		ensureRockyou()
		targetHash = gjp2.strip()
		saltBytes = SALT.encode()
	
		# Search
		with open(ROCKYOU_PATH, encoding="utf-8", errors="ignore") as f:
			for line in f:
				password = line.rstrip("\n\r")
	
				if generateGjp2(password, saltBytes) == targetHash:
					return password
	
		return None
	
	@staticmethod
	def encodeGjp(password: str) -> str:
		xored = Tools.xorCipher(password, Tools.getXorKey(7))
		b = base64.b64encode(xored.encode()).decode()
		return b.replace("+", "-").replace("/", "_").rstrip("=")
	
	@staticmethod
	def decodeGjp(gjp: str) -> str:
		padded = gjp + "=" * (-len(gjp) % 4)
		s = padded.replace("-", "+").replace("_", "/")
		raw = base64.b64decode(s.encode()).decode()
		return Tools.xorCipher(raw, Tools.getXorKey(7))

	@staticmethod
	def encodeLevelPassword(plain: str) -> str:
		if plain in ("", "0", "(none)", "(free copy)", "(error)"):
			return "0"
		xored = Tools.xorCipher("1" + plain, Tools.getXorKey(5))
		return Tools.b64EncodeUrlSafe(xored)

	@staticmethod
	def decodeLevelPassword(encoded: int | str) -> str:
		encoded = str(encoded).strip()
		if encoded in ("", "0"):
			return "(none)"

		try:
			if encoded.isdigit():
				return encoded

			padded = encoded + ("=" * (-len(encoded) % 4))
			raw = Tools.b64DecodeUrlSafe(padded)
			decoded = Tools.xorCipher(raw, Tools.getXorKey(5))[1:]

			if decoded and decoded[0] == "\x01":
				decoded = decoded[1:]
			decoded = decoded.lstrip("0")
			if decoded == "":
				return "(free copy)"

			if decoded in ("(none)", "(free copy)", "(error)"):
				return decoded

			return decoded

		except Exception:
			return "(error)"
	
	@staticmethod
	def generateRs(length: int = 10) -> str:
		alphabet = string.ascii_letters + string.digits
		return "".join(random.choices(alphabet, k=length))
	
	@staticmethod
	def generateRn(length: int | None = None) -> int:
		numLength = length if length else random.randint(3,5)
		return int("".join(random.choices(string.digits, k=numLength)))
	
	@staticmethod
	def generateUuid(parts: Sequence[int] = (8, 4, 4, 4, 10)) -> str:
		"""
		Legacy uuid generator, use player ID in requests
		"""
		return "-".join(map(Tools.generateRs, parts))
	
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
	def _generateCdnExpires(offsetSeconds: int = 3600) -> int:
		return int(time.time()) + offsetSeconds
	
	@staticmethod
	def _generateCdnToken(endpoint: str, expires: int) -> str:
		payload = f"8501f9c2-75ba-4230-8188-51037c4da102{endpoint}{expires}"
		digestAscii = hashlib.md5(payload.encode()).hexdigest()
		return Tools.b64EncodeUrlSafe(digestAscii)
	
	@staticmethod
	def _sampleStringForUploadSeed(data: str, charCount: int = 50) -> str:
		if len(data) < charCount:
			return data
		step = len(data) // charCount
		return data[::step][:charCount]
	
	@staticmethod
	def _generateLevelUploadSeed2(levelString: str) -> str:
		sample = Tools._sampleStringForUploadSeed(levelString, 50)
		return Tools.genChk(9, [sample], 1)
	
	@staticmethod
	def _generateListSeed2(length: int = 5) -> str:
		alphabet = string.ascii_letters + string.digits
		return "".join(random.choices(alphabet, k=length))
	
	@staticmethod
	def _generateListUploadSeed(listLevels: str, accountId: int, seed2: str) -> str:
		sample = Tools._sampleStringForUploadSeed(listLevels, 50)
		digest = hashlib.sha1(f"{sample}{accountId}".encode()).hexdigest()
		return Tools.b64EncodeUrlSafe(Tools.xorCipher(digest, seed2))
	
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
		prefix = Tools._randomClientTokenPrefix(5)
		num = str(random.randint(minDigits, maxDigits))
		xored = Tools.xorCipher(num, Tools.getXorKey(4))
		if urlSafeB64:
			return prefix + Tools.b64EncodeUrlSafe(xored)
		return prefix + base64.b64encode(xored.encode()).decode()
	
	@staticmethod
	def generateChestMenuChk(
		minDigits: int = 10_000,
		maxDigits: int = 999_999
	) -> str:
		prefix = Tools._randomClientTokenPrefix(5)
		num = str(random.randint(minDigits, maxDigits))
		xored = Tools.xorCipher(num, Tools.getXorKey(14))
		return prefix + Tools.b64EncodeUrlSafe(xored)
	
	@staticmethod
	def generateWraithRewardChk(
		minDigits: int = 10_000,
		maxDigits: int = 1_000_000
	) -> str:
		prefix = Tools._randomClientTokenPrefix(5)
		num = str(random.randint(minDigits, maxDigits))
		xored = Tools.xorCipher(num, Tools.getXorKey(14))
		return prefix + base64.b64encode(xored.encode()).decode()
	
	@staticmethod
	def genChkDownloadLevel(
		levelId: int,
		inc: int,
		rs: str,
		accountId: int,
		udid: str,
		uuid: int
	) -> str:
		return Tools.genChk(9, [levelId, inc, rs, accountId, udid, uuid], 1)
	
	@staticmethod
	def genChkRateStars(
		levelId: int,
		stars: int,
		rs: str,
		accountId: int,
		udid: str,
		uuid: int
	) -> str:
		return Tools.genChk(13, [levelId, stars, rs, accountId, udid, uuid], 3)
	
	@staticmethod
	def genChkLikeItem(
		special: int,
		itemId: int,
		like: int,
		type_: int,
		rs: str,
		accountId: int,
		udid: str,
		uuid: int
	) -> str:
		return Tools.genChk(
			13, [special, itemId, like, type_, rs, accountId, udid, uuid], 3
		)
	
	@staticmethod
	def genChkLeaderboard(values: List[Union[int, str]]) -> str:
		return Tools.genChk(8, values, 5)
	
	@staticmethod
	def genChkLevelComment(
		userName: str,
		commentB64: str,
		levelId: int,
		percent: int ,
		commentType: int = 0
	) -> str:
		return Tools.genChk(
			6, [userName, commentB64, levelId, percent, commentType], 2
		)
	
	@staticmethod
	def encodeLeaderboardProgressString(differences: Sequence[int]) -> str:
		s = ",".join(str(d) for d in differences)
		xored = Tools.xorCipher(s, Tools.getXorKey(9))
		return Tools.b64EncodeUrlSafe(xored)
	
	@staticmethod
	def decodeLeaderboardProgressString(encoded: str) -> list[int]:
		raw = Tools.xorCipher(Tools.b64DecodeUrlSafe(encoded), Tools.getXorKey(9))
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
		decoded = Tools.xorCipher(
			Tools.b64DecodeUrlSafe(payload),
			Tools.getXorKey(xorKeyIndex)
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
		
def backupGJAccountNew(
	accountID: int,
	gjp2: str,
	saveData: str,
	uuid: int,
	gameVersion: int = 22,
	binaryVersion: int = 47,
	udid: str | None = None,
	dvs: int | None = None
) -> str:
	"""
	accountID: The player's account ID (not to be confused with user ID). Used for authorization
	gjp2: The player's account password, encoded with GJP2. Used for authorization
	saveData: The save data for CCGameManager.dat compressed with gzip, then a semicolon ; and the save data for CCLocalLevels.dat compressed with gzip
	uuid: The player's user ID
	gameVersion: A number representing the game's version. The current value is 22 for 2.2
	binaryVersion: A number representing the game's small version. The current value is 47 for 2.2081 on PC and 48 for 2.2082 on mobile
	udid: The player's UDID (Unique Device Identifier). Used to identify unregistered users
	dvs: Platform type, iOS = 1, Android = 2, Windows = 3, macOS = 8
	"""
	secret = Tools.getSecret(2)

	if udid is None:
		udid = Tools.generateUdid()

	data: dict[str, str | int] = {
		"accountID": accountID,
		"gjp2": gjp2,
		"saveData": saveData,
		"gameVersion": gameVersion,
		"binaryVersion": binaryVersion,
		"udid": udid,
		"uuid": uuid,
		"secret": secret
	}

	if dvs is not None:
		data["dvs"] = dvs
	
	response = Tools.makeReq("http://www.robtopgames.org/database/accounts/backupGJAccountNew.php", data)
	
	if not Tools.checkResponse(response.text):
		print(f"backupGJAccountNew Failed: {response.text}")
	
	return response.text

def loginGJAccount(
	userName: str,
	gjp2: str,
	udid: str | None = None,
	sID: str | None = None
) -> str:
	"""
	userName: The username of the account the player is trying to log into
	gjp2: The password of the account the player is trying to log into, encoded with GJP2
	udid: The player's UDID (Unique Device Identifier). Used to identify unregistered users
	sID: The player's Steam ID
	"""
	secret = Tools.getSecret(2)
	
	if udid is None:
		udid = Tools.generateUdid()

	data: dict[str, str | int] = {
		"udid": udid,
		"userName": userName,
		"gjp2": gjp2,
		"secret": secret
	}

	if sID is not None:
		data["sID"] = sID

	response = Tools.makeReq(
		"http://www.boomlings.com/database/accounts/loginGJAccount.php",
		data
	)

	if not Tools.checkResponse(response.text):
		print(f"loginGJAccount Failed: {response.text}")
	return response.text

def registerGJAccount(
	userName: str,
	password: str,
	email: str
) -> str:
	"""
	userName: The username of the account to create
	password: The password of the account to create
	email: The email of the account to create
	"""
	secret = Tools.getSecret(2)
	
	data: dict[str, str | int] = {
		"userName": userName,
		"password": password,
		"email": email,
		"secret": secret
	}
	response = Tools.makeReq(
		"http://www.boomlings.com/database/accounts/registerGJAccount.php",
		data
	)
	if not Tools.checkResponse(response.text):
		print(f"registerGJAccount Failed: {response.text}")
	return response.text

def syncGJAccountNew(
	accountID: int,
	gjp2: str,
	gameVersion: int | None = None,
	binaryVersion: int | None = None,
	udid: str | None = None,
	uuid: int | None = None,
	dvs: int | None = None,
) -> str:
	"""
	accountID: The player's account ID (not to be confused with user ID). Used for authorization
	gjp2: The player's account password, encoded with GJP2. Used for authorization
	gameVersion: A number representing the game's version. The current value is 22 for 2.2
	binaryVersion: A number representing the game's small version. The current value is 47 for 2.2081 on PC and 48 for 2.2082 on mobile
	udid: The player's UDID (Unique Device Identifier). Used to identify unregistered users
	uuid: The player's user ID
	dvs: Platform type, iOS = 1, Android = 2, Windows = 3, macOS = 8
	"""
	secret = Tools.getSecret(2)
	
	data: dict[str, str | int] = {
		"accountID": accountID,
		"gjp2": gjp2,
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

	if dvs is not None:
		data["dvs"] = dvs

	response = Tools.makeReq(
		"http://www.robtopgames.org/database/accounts/syncGJAccountNew.php",
		data
	)

	if not Tools.checkResponse(response.text):
		print(f"syncGJAccountNew Failed: {response.text}")

	return response.text

def updateGJAccSettings20(
	accountID: int,
	gjp2: str,
	mS: int | None = None,
	frS: int | None = None,
	cS: int | None = None,
	yt: str | None = None,
	twitter: str | None = None,
	twitch: str | None = None,
	instagram: str | None = None,
	tiktok: str | None = None,
	discord: str | None = None,
	custom: str | None = None
) -> str:
	"""
	accountID: The player's account ID (not to be confused with user ID). Used for authorization
	gjp2: The player's account password, encoded with GJP2. Used for authorization
	mS: Who the user allows messages from: 0 for anyone, 1 for just friends, and 2 for no one
	frS: Who the user allows friend requests from: 0 for anyone, and 1 for no one
	cS: Who the user allows to view their comments: 0 for anyone, 1 for just friends, and 2 for only themselves
	yt: The end of the link to the user's youtube channel, after the /channel/. e.g. UCZoN2WLAooS6uhREa9Cgpwg
	twitter: The user's twitter handle
	twitch: The user's twitch username
	instagram: The user's Instagram username
	tiktok: The user's TikTok handle
	discord: The user's Discord handle
	custom: The user's custom one-time authentication token
	"""
	secret = Tools.getSecret(2)
	
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

	if instagram is not None:
		data["instagram"] = instagram

	if tiktok is not None:
		data["tiktok"] = tiktok

	if discord is not None:
		data["discord"] = discord

	if custom is not None:
		data["custom"] = custom

	response = Tools.makeReq(
		"http://www.boomlings.com/database/updateGJAccSettings20.php",
		data
	)

	if not Tools.checkResponse(response.text):
		print(f"updateGJAccSettings20 Failed: {response.text}")

	return response.text
		
def getGJScores20(
	stat: Literal[0, 1, 2, 3] | None = None,
	accountID: int | None = None,
	gjp2: str | None = None,
	type_: Literal["top", "relative", "friends", "creators"] | None = None,
	count: int | None = None,
	gameVersion: int | None = None,
	binaryVersion: int | None = None,
	udid: str | None = None,
	uuid: int | None = None,
	dvs: int | None = None
) -> str:
	"""
	stat: The user statistic to use when ordering top, relative and friends leaderboards. 0 = stars, 1 = moons, 2 = demons, 3 = coins, defaults to 0
	accountID: 	The player's account ID (not to be confused with user ID). Used for authorization
	gjp2: The player's account password, encoded with GJP2. Used for authorization
	type_: Can be top, relative, friends, or creators. If left out it defaults to top
	count: Returns the amount of players specified. Limited to 100
	gameVersion: A number representing the game's version. The current value is 22 for 2.2
	binaryVersion: A number representing the game's small version. The current value is 47 for 2.2081 on PC and 48 for 2.2082 on mobile
	udid: The player's UDID (Unique Device Identifier). Used to identify unregistered users
	uuid: The player's user ID
	dvs: Platform type, iOS = 1, Android = 2, Windows = 3, macOS = 8
	"""
	secret = Tools.getSecret(1)
	
	data: dict[str, str | int] = {
		"secret": secret
	}
	
	if stat is not None:
		data["stat"] = stat
	
	if gameVersion is not None:
		data["gameVersion"] = gameVersion
	
	if binaryVersion is not None:
		data["binaryVersion"] = binaryVersion
	
	if accountID is not None:
		data["accountID"] = accountID
	
	if gjp2 is not None:
		data["gjp2"] = gjp2
	
	if type_ is not None:
		data["type"] = type_
	
	if count is not None:
		# Hard cap at 100 (server-side limit)
		data["count"] = min(count, 100)
	
	if udid is not None:
		data["udid"] = udid
	
	if uuid is not None:
		data["uuid"] = uuid
	
	if dvs is not None:
		data["dvs"] = dvs
	
	response = Tools.makeReq(
		"http://www.boomlings.com/database/getGJScores20.php",
		data
	)
	
	if not Tools.checkResponse(response.text):
		print(f"getGJScores20 Failed: {response.text}")
	
	return response.text

def getGJUserInfo20(
	targetAccountID: int,
	gameVersion: int | None = None,
	binaryVersion: int | None = None,
	accountID: int | None = None,
	gjp2: str | None = None,
	udid: str | None = None,
	uuid: int | None = None,
	dvs: int | None = None
	) -> str:
	"""
	targetAccountID: The account ID of the person you want the info of
	gameVersion: A number representing the game's version. The current value is 22 for 2.2
	binaryVersion: A number representing the game's small version. The current value is 47 for 2.2081 on PC and 48 for 2.2082 on mobile
	accountID: The player's account ID (not to be confused with user ID). Used for authorization
	gjp2: The player's account password, encoded with GJP2. Used for authorization
	udid: The player's UDID (Unique Device Identifier). Used to identify unregistered users
	uuid: The player's user ID
	dvs: Platform type, iOS = 1, Android = 2, Windows = 3, macOS = 8
	"""
	secret = Tools.getSecret(1)
	
	data: dict[str, str | int] = {
		"targetAccountID": targetAccountID,
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
	
	if dvs is not None:
		data["dvs"] = dvs
	
	response = Tools.makeReq(
		"http://www.boomlings.com/database/getGJUserInfo20.php",
		data
	)
	
	if not Tools.checkResponse(response.text):
		print(f"getGJUserInfo20 Failed: {response.text}")
	
	return response.text

def getGJUsers20(
	gameVersion: int | None = None,
	binaryVersion: int | None = None,
	str_: str | None = None,
	page: int | None = None,
	total: int | None = None,
	accountID: int | None = None,
	gjp2: str | None = None,
	dvs: int | None = None
	) -> str:
	"""
	gameVersion: A number representing the game's version. The current value is 22 for 2.2
	binaryVersion: A number representing the game's small version. The current value is 47 for 2.2081 on PC and 48 for 2.2082 on mobile
	str_: The name or user ID of the user you want to search for
	page: The page of users you want. Redundant as it only returns 1 user
	total: Likely the cached total page count
	accountID: The requesting account ID, if logged in
	gjp2: The player's account password, encoded with GJP2. Used for authorization
	dvs: Platform type, iOS = 1, Android = 2, Windows = 3, macOS = 8
	"""
	secret = Tools.getSecret(1)
	
	data: dict[str, str | int] = {
		"secret": secret
	}
	
	if gameVersion is not None:
		data["gameVersion"] = gameVersion
	
	if binaryVersion is not None:
		data["binaryVersion"] = binaryVersion
	
	if str_ is not None:
		data["str"] = str_
	
	if page is not None:
		data["page"] = page
	
	if total is not None:
		data["total"] = total
	
	if accountID is not None:
		data["accountID"] = accountID
	
	if gjp2 is not None:
		data["gjp2"] = gjp2
	
	if dvs is not None:
		data["dvs"] = dvs
	
	response = Tools.makeReq(
		"http://www.boomlings.com/database/getGJUsers20.php",
		data
	)
	
	if not Tools.checkResponse(response.text):
		print(f"getGJUsers20 Failed: {response.text}")
	
	return response.text

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
	dinfoe: int,
	sinfo: str,
	sinfod: int,
	sinfog: int,
	sinfoe: int,
	gameVersion: int | None = None,
	binaryVersion: int | None = None,
	udid: str | None = None,
	uuid: int | None = None,
	dvs: int | None = None,
	userName: str | None = None,
	color1: int | None = None,
	color2: int | None = None,
	color3: int | None = None,
	special: int | None = None,
	seed: str | None = None
) -> str:
	"""
	accountID: The player's account ID (not to be confused with user ID). Used for authorization
	gjp2: The player's account password, encoded with GJP2. Used for authorization
	stars: 	The amount of stars the user has
	moons: The amount of moons the user has
	demons: The amount of demons the user has, including official levels
	diamonds: The amount of diamonds the user has
	icon: Which icon the iconType has selected, for example if iconType is 0 (cube), then it's the selected cube
	iconType: Which gamemode the player has last selected when changing their icons, 0 for cube, 1 for ship, 2 for ball, 3 for ufo, 4 for wave, 5 for robot, 6 for spider
	coins: The amount of secret coins the user has
	userCoins: The amount of user coins the user has
	accIcon: The ID of the user's selected icon
	accShip: The ID of the user's selected ship
	accBall: The ID of the user's selected ball
	accBird: The ID of the user's selected UFO
	accDart: The ID of the user's selected wave
	accRobot: The ID of the user's selected robot
	accGlow: Whether the user has glow enabled
	accSpider: The ID of the user's selected spider
	accExplosion: The ID of the user's selected death effect
	accSwing: The ID of the user's selected swing
	accJetpack: The ID of the user's selected jetpack
	dinfo: List of all completed demons (level IDs separated by ,). Does not include official, weekly, gauntlet and event levels. Not sent if empty
	dinfow: Amount of completed weeklies. Sent only together with dinfo
	dinfog: Amount of completed gauntlet demons. Sent only together with dinfo
	dinfoe: Amount of completed event demons. Sent only together with dinfo
	sinfo: 	List of counts of completed levels of each non-demon difficulty, separately for classic and platformer levels. Includes official levels. Format: autoClassic,easyClassic,normalClassic,hardClassic,harderClassic,insaneClassic,autoPlatformer,easyPlatformer,normalPlatformer,hardPlatformer,harderPlatformer,insanePlatformer
	sinfod: Amount of completed dailies
	sinfog: Amount of completed gauntlet non-demon levels
	sinfoe: Amount of completed event non-demon levels
	gameVersion: A number representing the game's version. The current value is 22 for 2.2
	binaryVersion: A number representing the game's small version. The current value is 47 for 2.2081 on PC and 48 for 2.2082 on mobile
	udid: The player's UDID (Unique Device Identifier). Used to identify unregistered users
	uuid: The player's user ID
	dvs: Platform type, iOS = 1, Android = 2, Windows = 3, macOS = 8
	userName: The username of the player
	color1: Color 1 of the player. Defaults to the default primary color when left out
	color2: Color 2 of the player. Defaults to the default secondary color when left out
	color3: Glow color of the player. Defaults to secondary color when left out
	special: Glow (2 if enabled)
	seed: A random set of 10 numbers and letters in A-Za-z0-9, auto generated if left out
	"""
	secret = Tools.getSecret(1)
	
	if seed is None:
		import random
		chars = "1234567890qwertyuiopasdfghjklzxcvbnmQWERTYUIOPASDFGHJKLZXCVBNM"
		seed = "".join(random.sample(chars, 10))
	
	seed2 = Tools.genChk(
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
		"dinfoe": dinfoe,
		"sinfo": sinfo,
		"sinfod": sinfod,
		"sinfog": sinfog,
		"sinfoe": sinfoe,
		"seed": seed,
		"seed2": seed2,
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

	if dvs is not None:
		data["dvs"] = dvs	

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
	
	response = Tools.makeReq(
		"http://www.boomlings.com/database/updateGJUserScore22.php",
		data
	)
	
	if not Tools.checkResponse(response.text):
		print(f"updateGJUserScore22 Failed: {response.text}")
	
	return response.text
		
def deleteGJLevelUser20(
	accountID: int,
	gjp2: str,
	levelID: int,
	gameVersion: int | None = None,
	binaryVersion: int | None = None,
	udid: str | None = None,
	uuid: int | None = None,
	dvs: int | None = None
	) -> str:
	"""
	accountID: The player's account ID (not to be confused with user ID). Used for authorization
	gjp2: The player's account password, encoded with GJP2. Used for authorization
	levelID: The level ID to remove from the user's list
	gameVersion: A number representing the game's version. The current value is 22 for 2.2
	binaryVersion: A number representing the game's small version. The current value is 47 for 2.2081 on PC and 48 for 2.2082 on mobile
	udid: The player's UDID (Unique Device Identifier). Used to identify unregistered users
	uuid: The player's user ID
	dvs: Platform type, iOS = 1, Android = 2, Windows = 3, macOS = 8
	"""
	secret = Tools.getSecret(2)
	
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
	
	if udid is not None:
		data["udid"] = udid
	
	if uuid is not None:
		data["uuid"] = uuid

	if dvs is not None:
		data["dvs"] = dvs	
	
	response = Tools.makeReq(
		"http://www.boomlings.com/database/deleteGJLevelUser20.php",
		data
	)
	
	if not Tools.checkResponse(response.text):
		print(f"deleteGJLevelUser20 Failed: {response.text}")
	
	return response.text

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
	password: int,
	twoPlayer: int,
	songID: int,
	requestedStars: int,
	ldm: int,
	levelString: str,
	original: int | None = None,
	auto: int | None = None,
	unlisted: int | None = None,
	seed2: str | None = None,
	objects: int | None = None,
	coins: int | None = None,
	binaryVersion: int | None = None,
	udid: str | None = None,
	uuid: int | None = None,
	wt: int | None = None,
	wt2: int | None = None,
	seed: str | None = None,
	extraString: str | None = None,
	levelInfo: str | None = None,
	dvs: int | None = None,
	ts: int | None = None,
	lrs: str | None = None
) -> str:
	"""
	gameVersion: A number representing the game's version. The current value is 22 for 2.2
	accountID: The player's account ID (not to be confused with user ID). Used for authorization
	gjp2: The player's account password, encoded with GJP2. Used for authorization
	userName: The uploader's username
	levelID: The ID of the level if updating to a newer version, otherwise 0
	levelName: The name of the level
	levelDesc: Description in plaintext
	levelVersion: The version number of the level
	levelLength: 0 to 4 = Tiny to XL, 5 = Platformer
	audioTrack: Main level song ID, 0 if songID is used (Stereo Madness = 0)
	password: The level's copy password. Set to 0 for no copy or 1 for free copy. Other valid values consist of 1 followed by the password - either 4 or 6 digits. Ignored since binaryVersion=39
	twoPlayer: Set to 1 if the level utilizes two player mode
	songID: The ID of the custom song used in the level. Set to 0 if an official song is used
	requestedStars: The requested star rating for the level. The number is not limited to 10
	ldm: Whether the level uses high detail objects
	levelString: The actual level data. Must be gzip compressed and then converted to URL-safe base64
	original: The ID of the original level if the level was copied, otherwise 0
	auto: Whether the player has jumped during verification
	unlisted: 0 = public, 1 = friends only, 2 = unlisted, 0 by default
	seed2: Upload seed2 value; auto-generated if omitted
	objects: Number of objects in the level, auto-detected if omitted
	coins: Number of coins in the level, auto-detected if omitted
	binaryVersion: A number representing the game's small version. The current value is 47 for 2.2081 on PC and 48 for 2.2082 on mobile
	udid: The player's UDID (Unique Device Identifier). Used to identify unregistered users
	uuid: The player's user ID
	wt: The amount of time spent in the editor of a level (local copy)
	wt2: The amount of time spent in the editor of a level (previous copies)
	seed: A random string
	extraString: Capacity string used to save the cost of memory re-allocation when rendering levels
	levelInfo: pre-2.208 lrs
	dvs: Platform type, iOS = 1, Android = 2, Windows = 3, macOS = 8
	ts: The amount of 240 TPS steps the verification attempt took
	lrs: The replay string of the verification attempt, for leaderboard mods
	"""
	secret = Tools.getSecret(1)
	if seed2 is None:
		seed2 = Tools._generateLevelUploadSeed2(levelString)
	
	if original is None:
		original = 0

	if auto is None:
		auto = 0

	if unlisted is None:
		unlisted = 0

	if objects is None:
		objectString = Tools.Encryption.decodeString(levelString, 16)
		objects = len(Tools.getObjectIDs(objectString))

	if coins is None:
		objectString = Tools.Encryption.decodeString(levelString, 16)
		coins = Tools.getCoinCount(objectString)

	data: dict[str, str | int] = {
		"gameVersion": gameVersion,
		"accountID": accountID,
		"gjp2": gjp2,
		"userName": userName,
		"levelID": levelID,
		"levelName": levelName,
		"levelDesc": Tools.b64EncodeUrlSafe(levelDesc),
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

	if udid is not None:
		data["udid"] = udid
	
	if uuid is not None:
		data["uuid"] = uuid
	
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

	if dvs is not None:
		data["dvs"] = dvs

	if ts is not None:
		data["ts"] = ts

	if lrs is not None:
		data["lrs"] = lrs
	
	response = Tools.makeReq(
		"http://www.boomlings.com/database/uploadGJLevel21.php",
		data
	)
	
	if not Tools.checkResponse(response.text):
		print(f"uploadGJLevel21 Failed: {response.text}")
	
	return response.text

def updateGJDesc20(
	accountID: int,
	gjp2: str,
	levelID: int,
	levelDesc: str,
	gameVersion: int | None = None,
	binaryVersion: int | None = None,
) -> str:
	"""
	accountID: The player's account ID (not to be confused with user ID). Used for authorization
	gjp2: The player's account password, encoded with GJP2. Used for authorization
	levelID: The level ID whose description is being updated
	levelDesc: The new description text
	gameVersion: A number representing the game's version. The current value is 22 for 2.2
	binaryVersion: A number representing the game's small version. The current value is 47 for 2.2081 on PC and 48 for 2.2082 on mobile
	"""
	secret = Tools.getSecret(1)
	
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
	
	response = Tools.makeReq(
		"http://www.boomlings.com/database/updateGJDesc20.php",
		data
	)
	
	if not Tools.checkResponse(response.text):
		print(f"updateGJDesc20 Failed: {response.text}")
	
	return response.text

def suggestGJStars(
	accountID: int,
	gjp2: str,
	levelID: int,
	stars: int,
	feature: int,
	gameVersion: int,
	binaryVersion: int,
	udid: str | None = None,
	uuid: int | None = None,
	dvs: int | None = None
) -> str:
	"""
	accountID: The player's account ID (not to be confused with user ID). Used for authorization
	gjp2: The player's account password, encoded with GJP2. Used for authorization
	levelID: The ID of the level
	stars: How many stars that are requested
	feature: 0 for star rate, 1 for feature, 2 for epic, 3 for legendary, 4 for mythic
	gameVersion: A number representing the game's version. The current value is 22 for 2.2
	binaryVersion: A number representing the game's small version. The current value is 47 for 2.2081 on PC and 48 for 2.2082 on mobile
	udid: The player's UDID (Unique Device Identifier). Used to identify unregistered users
	uuid: The player's user ID
	dvs: Platform type, iOS = 1, Android = 2, Windows = 3, macOS = 8
	"""
	secret = Tools.getSecret(4)
	
	data: dict[str, str | int] = {
		"accountID": accountID,
		"gjp2": gjp2,
		"levelID": levelID,
		"stars": stars,
		"feature": feature,
		"gameVersion": gameVersion,
		"binaryVersion": binaryVersion,
		"secret": secret
	}

	if udid is not None:
		data["udid"] = udid
	
	if uuid is not None:
		data["uuid"] = uuid

	if dvs is not None:
		data["dvs"] = dvs
	
	response = Tools.makeReq(
		"http://www.boomlings.com/database/suggestGJStars20.php",
		data
	)
	
	if not Tools.checkResponse(response.text):
		print(f"suggestGJStars Failed: {response.text}")
	
	return response.text

def reportGJLevel(levelID: int | None = None) -> str:
	"""
	levelID: The ID of the level being reported
	"""
	secret = Tools.getSecret(1)
	
	data: dict[str, str | int] = {
		"secret": secret
	}
	
	if levelID is not None:
		data["levelID"] = levelID

	response = Tools.makeReq(
		"http://www.boomlings.com/database/reportGJLevel.php",
		data
	)

	if not Tools.checkResponse(response.text):
		print(f"reportGJLevel Failed: {response.text}")

	return response.text

def rateGJStars211(
	accountID: int,
	gjp2: str,
	levelID: int,
	stars: int,
	uuid: int,
	rs: str | None = None,
	udid: str | None = None,
	chk: str | None = None,
	gameVersion: int | None = None,
	binaryVersion: int | None = None,
	dvs: int | None = None
) -> str:
	"""
	accountID: The player's account ID (not to be confused with user ID). Used for authorization
	gjp2: The player's account password, encoded with GJP2. Used for authorization
	levelID: The ID of the level receiving the star suggestion
	stars: The amount of stars being suggested
	udid: The player's UDID (Unique Device Identifier). Used to identify unregistered users
	rs: 10 randomly generated characters from [A-Za-z0-9]
	uuid: The player's user ID
	chk: A string computed for authentication, auto generated if omitted
	gameVersion: A number representing the game's version. The current value is 22 for 2.2
	binaryVersion: A number representing the game's small version. The current value is 47 for 2.2081 on PC and 48 for 2.2082 on mobile
	dvs: Platform type, iOS = 1, Android = 2, Windows = 3, macOS = 8
	"""
	secret = Tools.getSecret(1)

	if rs is None:
		rs = Tools.generateRs()

	if udid is None:
		udid = Tools.generateUdid()

	if chk is None:
		chk = Tools.genChkRateStars(
			levelID, stars, rs, accountID, udid, uuid
		)

	data: dict[str, str | int] = {
		"accountID": accountID,
		"gjp2": gjp2,
		"levelID": levelID,
		"stars": stars,
		"uuid": uuid,
		"udid": udid,
		"rs": rs,
		"chk": chk,
		"secret": secret
	}
	
	if gameVersion is not None:
		data["gameVersion"] = gameVersion
	
	if binaryVersion is not None:
		data["binaryVersion"] = binaryVersion

	if dvs is not None:
		data["dvs"] = dvs
	
	response = Tools.makeReq(
		"http://www.boomlings.com/database/rateGJStars211.php",
		data
	)
	
	if not Tools.checkResponse(response.text):
		print(f"rateGJStars211 Failed: {response.text}")
	
	return response.text

def rateGJDemon21(
	accountID: int,
	gjp2: str,
	levelID: int,
	rating: int,
	gameVersion: int,
	binaryVersion: int,
	udid: str | None = None,
	uuid: int | None = None,
	dvs: int | None = None
) -> str:
	"""
	gameVersion: A number representing the game's version. The current value is 22 for 2.2
	binaryVersion: A number representing the game's small version. The current value is 47 for 2.2081 on PC and 48 for 2.2082 on mobile
	accountID: The player's account ID (not to be confused with user ID). Used for authorization
	gjp2: The player's account password, encoded with GJP2. Used for authorization
	levelID: The ID of the demon being rated
	rating: 1 for Easy Demon, 2 for Medium Demon, 3 for Hard Demon, 4 for Insane Demon and 5 for Extreme Demon
	udid: The player's UDID (Unique Device Identifier). Used to identify unregistered users
	uuid: The player's user ID
	dvs: Platform type, iOS = 1, Android = 2, Windows = 3, macOS = 8
	"""
	secret = Tools.getSecret(4)
	
	data: dict[str, str | int] = {
		"gameVersion": gameVersion,
		"binaryVersion": binaryVersion,
		"accountID": accountID,
		"gjp2": gjp2,
		"levelID": levelID,
		"rating": rating,
		"secret": secret
	}

	if udid is not None:
		data["udid"] = udid
	
	if uuid is not None:
		data["uuid"] = uuid

	if dvs is not None:
		data["dvs"] = dvs
	
	response = Tools.makeReq(
		"http://www.boomlings.com/database/rateGJDemon21.php",
		data
	)
	
	if not Tools.checkResponse(response.text):
		print(f"rateGJDemon21 Failed: {response.text}")
	
	return response.text

def getGJMapPacks21(
	accountID: int | None = None,
	gjp2: str | None = None,
	page: int | None = None,
	gameVersion: int | None = None,
	binaryVersion: int | None = None,
	udid: str | None = None,
	uuid: int | None = None,
	dvs: int | None = None
) -> str:
	"""
	accountID: The player's account ID (not to be confused with user ID). Used for authorization
	gjp2: The player's account password, encoded with GJP2. Used for authorization
	page: Denotes which page of map packs you want to retrieve, starting with 0
	gameVersion: A number representing the game's version. The current value is 22 for 2.2
	binaryVersion: A number representing the game's small version. The current value is 47 for 2.2081 on PC and 48 for 2.2082 on mobile
	udid: The player's UDID (Unique Device Identifier). Used to identify unregistered users
	uuid: The player's user ID
	dvs: Platform type, iOS = 1, Android = 2, Windows = 3, macOS = 8
	"""
	secret = Tools.getSecret(1)
	
	data: dict[str, str | int] = {
		"secret": secret
	}

	if accountID is not None:
		data["accountID"] = accountID
	
	if gjp2 is not None:
		data["gjp2"] = gjp2
	
	if page is not None:
		data["page"] = page

	if gameVersion is not None:
		data["gameVersion"] = gameVersion
	
	if binaryVersion is not None:
		data["binaryVersion"] = binaryVersion
	
	if udid is not None:
		data["udid"] = udid
	
	if uuid is not None:
		data["uuid"] = uuid
	
	if dvs is not None:
		data["dvs"] = dvs
	
	response = Tools.makeReq(
		"http://www.boomlings.com/database/getGJMapPacks21.php",
		data
	)
	
	if not Tools.checkResponse(response.text):
		print(f"getGJMapPacks21 Failed: {response.text}")
	
	return response.text

def getGJGauntlets21(
	accountID: int | None = None,
	gjp2: str | None = None,
	gameVersion: int | None = None,
	binaryVersion: int | None = None,
	special: int | None = None,
	udid: str | None = None,
	uuid: int | None = None,
	dvs: int | None = None,
	vkey: int | None = None
) -> str:
	"""
	gameVersion: A number representing the game's version. The current value is 22 for 2.2
	binaryVersion: A number representing the game's small version. The current value is 47 for 2.2081 on PC and 48 for 2.2082 on mobile
	special: 1 (fetches the 2.2 gauntlets)
	udid: The player's UDID (Unique Device Identifier). Used to identify unregistered users
	uuid: The player's user ID
	dvs: Platform type, iOS = 1, Android = 2, Windows = 3, macOS = 8
	accountID: The player's account ID (not to be confused with user ID). Used for authorization
	gjp2: The player's account password, encoded with GJP2. Used for authorization
	vkey: Optional version check key
	"""
	secret = Tools.getSecret(1)
	
	data: dict[str, str | int] = {
		"secret": secret
	}
	
	if accountID is not None:
		data["accountID"] = accountID
	
	if gjp2 is not None:
		data["gjp2"] = gjp2

	if gameVersion is not None:
		data["gameVersion"] = gameVersion
	
	if binaryVersion is not None:
		data["binaryVersion"] = binaryVersion
	
	if special is not None:
		data["special"] = special
	
	if udid is not None:
		data["udid"] = udid
	
	if uuid is not None:
		data["uuid"] = uuid
	
	if dvs is not None:
		data["dvs"] = dvs
	
	if vkey is not None:
		data["vkey"] = vkey
	
	response = Tools.makeReq(
		"http://www.boomlings.com/database/getGJGauntlets21.php",
		data
	)
	
	if not Tools.checkResponse(response.text):
		print(f"getGJGauntlets21 Failed: {response.text}")
	
	return response.text

def getGJDailyLevel(
	accountID: int | None = None,
	gjp2: str | None = None,
	weekly: int | None = None,
	type_: int | None = None,
	gameVersion: int | None = None,
	binaryVersion: int | None = None,
	chk: str | bool | None = None,
	udid: str | None = None,
	uuid: int | None = None,
	dvs: int | None = None
) -> str:
	"""
	accountID: The player's account ID (not to be confused with user ID). Used for authorization
	gjp2: The player's account password, encoded with GJP2. Used for authorization
	weekly: 0 for daily, 1 for weekly. Defaults to 0 if not sent. This parameter is outdated since 2.207
	type_: 0 for daily, 1 for weekly, 2 for event level
	gameVersion: A number representing the game's version. The current value is 22 for 2.2
	binaryVersion: A number representing the game's small version. The current value is 47 for 2.2081 on PC and 48 for 2.2082 on mobile
	chk: A string computed for authentication, set to True to auto generate
	udid: The player's UDID (Unique Device Identifier). Used to identify unregistered users
	uuid: The player's user ID
	dvs: Platform type, iOS = 1, Android = 2, Windows = 3, macOS = 8
	"""
	secret = Tools.getSecret(1)
	
	data: dict[str, str | int] = {
		"secret": secret
	}
	
	if accountID is not None:
		data["accountID"] = accountID
	
	if gjp2 is not None:
		data["gjp2"] = gjp2
	
	if weekly is not None:
		data["weekly"] = weekly
	
	if type_ is not None:
		data["type"] = type_

	if gameVersion is not None:
		data["gameVersion"] = gameVersion
	
	if binaryVersion is not None:
		data["binaryVersion"] = binaryVersion

	if chk is True:
		data["chk"] = Tools.generateChestMenuChk()
	elif chk is not None:
		data["chk"] = chk
	
	if udid is not None:
		data["udid"] = udid
	
	if uuid is not None:
		data["uuid"] = uuid
	
	if dvs is not None:
		data["dvs"] = dvs
	
	response = Tools.makeReq(
		"http://www.boomlings.com/database/getGJDailyLevel.php",
		data
	)
	
	if not Tools.checkResponse(response.text):
		print(f"getGJDailyLevel Failed: {response.text}")
	
	return response.text

def downloadGJLevel22(
	levelID: int,
	accountID: int | None = None,
	gjp2: str | None = None,
	gameVersion: int | None = None,
	binaryVersion: int | None = None,
	udid: str | None = None,
	uuid: int | None = None,
	inc: Literal[0, 1] | None = None,
	extras: int | None = None,
	rs: str | None = None,
	chk: tuple[int, Literal[0, 1], str, int, str, int] | None = None
) -> str:
	"""
	levelID: The ID of the level to download. Use -1 for the daily level, -2 for the weekly and -3 for the event level
	accountID: The player's account ID (not to be confused with user ID). Used for authorization
	gjp2: The player's account password, encoded with GJP2. Used for authorization
	gameVersion: A number representing the game's version. The current value is 22 for 2.2
	binaryVersion: A number representing the game's small version. The current value is 47 for 2.2081 on PC and 48 for 2.2082 on mobile
	udid: The player's UDID (Unique Device Identifier). Used to identify unregistered users
	uuid: The player's user ID
	inc: Whether the amount of downloads should be incremented on the level (requires proper authentication)
	extras: Used to return some extra data when set to 1, but was disabled sometime in 2022
	rs: 10 randomly generated characters from [A-Za-z0-9]
	chk: A string computed for authentication, pass in a tuple containing (levelID, inc, rs, accountID, udid, uuid) to generate
	"""
	secret = Tools.getSecret(1)
	
	data: dict[str, str | int] = {
		"levelID": levelID,
		"secret": secret
	}

	if accountID is not None:
		data["accountID"] = accountID
	
	if gjp2 is not None:
		data["gjp2"] = gjp2

	if gameVersion is not None:
		data["gameVersion"] = gameVersion
	
	if binaryVersion is not None:
		data["binaryVersion"] = binaryVersion
	
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
		levelID, inc, rs, accountID, udid, uuid = chk
		data["chk"] = Tools.genChkDownloadLevel(levelID, inc, rs, accountID, udid, uuid)
	
	response = Tools.makeReq(
		"http://www.boomlings.com/database/downloadGJLevel22.php",
		data
	)
	
	if not Tools.checkResponse(response.text):
		print(f"downloadGJLevel22 Failed: {response.text}")
	
	return response.text

def getGJLevels21(
	str_: str | int | None = None,
	type_: int | None = None,
	page: int | None = None,
	total: int | None = None,
	gjp2: str | None = None,
	accountID: int | None = None,
	diff: int | None = None,
	demonFilter: int | None = None,
	len_: int | str | None = None,
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
	gameVersion: int | None = None,
	binaryVersion: int | None = None,
	udid: str | None = None,
	uuid: int | None = None
) -> str:
	"""
	str_: Search query, user ID, or comma-separated list of level IDs depending on type_
	type_: Search type, defaults to most liked. Valid values are:
	```markdown
	| Type | Description                                                                      |
	| :--: | -------------------------------------------------------------------------------- |
	|  0   | Search query (used when opening the original level)                              |
	|  1   | Most downloaded                                                                  |
	|  2   | Most liked                                                                       |
	|  3   | Trending                                                                         |
	|  4   | Recent                                                                           |
	|  5   | User's levels, uses str as the user ID                                           |
	|  6   | Featured                                                                         |
	|  7   | Magic                                                                            |
	|  8   | Moderator sent levels                                                            |
	|  10  | List of levels, uses str as a comma separated list of level IDs                  |
	|  11  | Awarded                                                                          |
	|  12  | Followed (see followed parameter)                                                |
	|  13  | Friends (login required)                                                         |
	|  15  | Most liked in GD World                                                           |
	|  16  | Hall of fame                                                                     |
	|  17  | Featured in GD World                                                             |
	|  18  | Unknown (always empty, perhaps robtop only?)                                     |
	|  19  | Unknown (same as type 10 but this type has pagination and no star-rate filter)   |
	|  21  | Daily history                                                                    |
	|  22  | Weekly history                                                                   |
	|  23  | Event history                                                                    |
	|  24  | Reported levels (Elder Moderator only)                                           |
	|  25  | Level list, uses str as the list ID                                              |
	|  26  | Local level list (same as type 19 but can return up to 100 levels)               |
	|  27  | Sent                                                                             |
	|  28  | GD Lite weekly levels                                                            |
	|  29  | GD Lite bonus levels (platformer)                                                |
	```
	page: Which page to request. Defaults to 0
	total: Probably the cached total number of levels, default is 0
	gjp2: The player's account password, encoded with GJP2. Used for authorization
	accountID: The player's account ID (not to be confused with user ID). Used for authorization
	diff: Comma-separated list of difficulty values. - = None, -1 = N/A, -2 = Demons (see demonFilter), -3 = Auto, 1 to 5 = Easy to Insane
	demonFilter: Selects which demon difficulty to search. Will search all demon types if not sent. 1 to 5 = Easy Demon to Extreme Demon
	len_: Length filter, 0 = Any, 0 to 4 = Tiny to XL, 5 = Platformer
	uncompleted: Uncompleted filter, either 0 or 1
	onlyCompleted: Completed filter, either 0 or 1
	completedLevels: Comma separated list of completed level IDs surrounded by ()
	featured: Featured filter, either 0 or 1
	original: Original filter, either 0 or 1
	twoPlayer: Two Player Mode filter, either 0 or 1
	coins: Coins filter, either 0 or 1
	epic: Epic filter, either 1 or not sent
	legendary: Mythic filter, either 1 or not sent (swapped with mythic)
	mythic: Legendary filter, either 1 or not sent (swapped with legendary)
	noStar: Unrated filter, either 1 or not sent
	star: Rated filter, either 1 or not sent
	song: Official (or custom) song ID, not sent when off (Stereo Madness = 1)
	customSong: Whether the song is a Newgrounds song. Either 1 or not sent
	followed: Comma-separated list of followed account IDs, used for type 12 queries
	local: 1 to request "My Online Levels" when using type 5 with a sender user ID
	gameVersion: A number representing the game's version. The current value is 22 for 2.2
	binaryVersion: A number representing the game's small version. The current value is 47 for 2.2081 on PC and 48 for 2.2082 on mobile
	udid: The player's UDID (Unique Device Identifier). Used to identify unregistered users
	uuid: The player's user ID
	"""
	secret = Tools.getSecret(1)
	
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
	
	if gjp2 is not None:
		data["gjp2"] = gjp2
	
	if accountID is not None:
		data["accountID"] = accountID
	
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
	
	response = Tools.makeReq(
		"http://www.boomlings.com/database/getGJLevels21.php",
		data
	)
	
	if not Tools.checkResponse(response.text):
		print(f"getGJLevels21 Failed: {response.text}")
	
	return response.text

def getGJLevelScores211(
	accountID: int,
	gjp2: str,
	levelID: int,
	gameVersion: int | None = None,
	binaryVersion: int | None = None,
	time: int | None = None,
	points: int | None = None,
	plat: int | None = None,
	percent: int | None = None,
	type_: int | None = None,
	mode: int | None = None,
	udid: str | None = None,
	uuid: int | None = None,
	dvs: int | None = None,
	s1: int | None = None,
	s2: int | None = None,
	s3: int | None = None,
	s4: tuple[int, int, int, bool] | None = None,
	s5: bool | None = None,
	s6: str | None = None,
	s7: bool | None = None,
	s8: int | None = None,
	s9: int | None = None,
	s10: int | None = None,
	s11: int | None = None,
	s12: bool | Literal[0] | None = None,
	s13: int | None = None,
	s14: int | None = None,
	s15: bool | Literal[0] | None = None,
	s16: str | None = None,
	s17: str | None = None,
	s18: int | None = None,
	s19: bool | Literal[0] | None = None,
	s20: int | None = None,
	chk: tuple[int, int, int, int, int, int, bool] | None = None,
) -> str:
	"""
	accountID: The player's account ID (not to be confused with user ID). Used for authorization
	gjp2: The player's account password, encoded with GJP2. Used for authorization
	levelID: The ID of the level or list. Negative if it's a list ID
	gameVersion: A number representing the game's version. The current value is 22 for 2.2
	binaryVersion: A number representing the game's small version. The current value is 47 for 2.2081 on PC and 48 for 2.2082 on mobile
	time: Time in milliseconds if the user completed the level, otherwise 0
	points: Always 0
	plat: Always 0
	percent: If left out, the leaderboard will be fetched without updating your score
	type_: 0 for Friends, 1 for Top, 2 for Week. Defaults to 0 if left out
	mode: Always 0
	udid: The player's UDID (Unique Device Identifier). Used to identify unregistered users
	uuid: The player's user ID
	dvs: Platform type, iOS = 1, Android = 2, Windows = 3, macOS = 8
	s1: User's attempts
	s2: User's clicks
	s3: User's attempt time in seconds
	s4: level seed, pass in a tuple containing (jumps, percent, seconds, hasPlayed)
	s5: Random number, Set to True to include
	s6: List of PB differences (For example from 0 to 50, then 69, it would be 50,19)
	s7: Randomly Generated 10 character string, set to True to include
	s8: Attempt count
	s9: The amount of coins the user got
	s10: Same as timelyID
	s11: 0 if level has not been completed, otherwise, amount of ticks on the best time attempt
	s12: 0 if level has not been completed, otherwise True
	s13: Unknown value, starts at 1171520
	s14: 0 if level has not been completed, otherwise, amount of clicks on the best time attempt
	s15: 0 if level has not been completed, otherwise True
	s16: Seemingly always empty
	s17: Seemingly always empty
	s18: 0 if level has not been completed, otherwise the amount of collected coins on the best time attempt
	s19: 0 if level has not been completed, otherwise True
	s20: The level version
	chk: Pass in a tuple containing (percent, jumps, attempts, coins, timelyID, seconds, hasPlayed), also include s6 and s7 in the parameters for chk to generate

	attempts: Total level attempts
	coins: The number of coins collected
	timelyID: The ordinal number of the daily/weekly, 0 otherwise
	jumps: Jumps in the current attempt
	seconds: Duration of attempt
	hasPlayed: ALways True
	"""
	secret = Tools.getSecret(1)

	
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

	if udid is not None:
		data["udid"] = udid

	if uuid is not None:
		data["uuid"] = uuid

	if dvs is not None:
		data["dvs"] = dvs
	
	if s1 is not None:
		data["s1"] = s1 + 8354
	
	if s2 is not None:
		data["s2"] = s2 + 3991
	
	if s3 is not None:
		data["s3"] = s3 + 4085
	
	if isinstance(s4, tuple):
		jumps, percent, seconds, hasPlayed = s4
		data["s4"] = Tools._generateClassicLeaderboardSeed(jumps, percent, seconds, hasPlayed)
	
	if s5 is True:
		data["s5"] = Tools._generateLeaderboardRandom(False)
	
	if s6 is not None:
		key = Tools.getXorKey(9)
		value = Tools.b64EncodeUrlSafe(Tools.xorCipher(s6, key))
		s6, data["s6"] = value, value
	
	if s7 is True:
		data["s7"] = Tools.generateRs()

	if s8 is not None:
		data["s8"] = s8

	if s9 is not None:
		data["s9"] = s9 + 5819
	
	if s10 is not None:
		data["s10"] = s10
	
	if s11 is not None:
		if s11 != 0:
			s11 += 46533
		data["s11"] = s11
	
	if s12 is not None:
		data["s12"] = 25645 if s12 is True else 0
	
	if s13 is not None:
		if s13 < 1171520:
			s13 = 1171520
		data["s13"] = s13
	
	if s14 is not None:
		if s14 != 0:
			s14 += 7684
		data["s14"] = s14
	
	if s15 is not None:
		data["s15"] = 3453 if s15 is True else 0
	
	if s16 is not None:
		data["s16"] = s16
	
	if s17 is not None:
		data["s17"] = s17
	
	if s18 is not None:
		if s18 != 0:
			s18 += 6433
		data["s18"] = s18
	
	if s19 is not None:
		data["s19"] = 6323 if s19 is True else 0

	if s20 is not None:
		data["s20"] = s20

	if (s6 is not None and
		s7 is not None and
		isinstance(chk, list)):
		percent, jumps, attempts, coins, timelyID, seconds, hasPlayed = chk
		seed = Tools._generateClassicLeaderboardSeed(jumps, percent, seconds, hasPlayed)
		data["chk"] = Tools.genChk(8, [accountID, levelID, percent, jumps, attempts, seed, s6, 1, coins, timelyID, data["s7"]], 5)
	
	response = Tools.makeReq(
		"http://www.boomlings.com/database/getGJLevelScores211.php",
		data
	)

	if not Tools.checkResponse(response.text):
		print(f"getGJLevelScores211 Failed: {response.text}")
	
	return response.text

def getGJLevelScoresPlat(
	accountID: int,
	gjp2: str,
	levelID: int,
	gameVersion: int | None = None,
	binaryVersion: int | None = None,
	time: int | None = None,
	points: int | None = None,
	plat: int | None = None,
	percent: int | None = None,
	type_: int | None = None,
	mode: int | None = None,
	udid: str | None = None,
	uuid: int | None = None,
	dvs: int | None = None,
	s1: int | None = None,
	s2: int | None = None,
	s3: int | None = None,
	s4: tuple[int, int, int, bool] | None = None,
	s5: bool | None = None,
	s6: str | None = None,
	s7: bool | None = None,
	s8: int | None = None,
	s9: int | None = None,
	s10: int | None = None,
	s11: int | None = None,
	s12: bool | Literal[0] | None = None,
	s13: int | None = None,
	s14: int | None = None,
	s15: bool | Literal[0] | None = None,
	s16: str | None = None,
	s17: str | None = None,
	s18: int | None = None,
	s19: bool | Literal[0] | None = None,
	s20: int | None = None,
	chk: tuple[int, int, int, int, int, int, bool] | None = None,
) -> str:
	"""
	accountID: The player's account ID (not to be confused with user ID). Used for authorization
	gjp2: The player's account password, encoded with GJP2. Used for authorization
	levelID: The ID of the level or list. Negative if it's a list ID
	gameVersion: A number representing the game's version. The current value is 22 for 2.2
	binaryVersion: A number representing the game's small version. The current value is 47 for 2.2081 on PC and 48 for 2.2082 on mobile
	time: Time in milliseconds if the user completed the level, otherwise 0
	points: The amount of points the user has
	plat: Always 1
	percent: If left out, the leaderboard will be fetched without updating your score
	type_: 0 for Friends, 1 for Top, 2 for Week. Defaults to 0 if left out
	mode: 0 for Time, 1 for Points
	udid: The player's UDID (Unique Device Identifier). Used to identify unregistered users
	uuid: The player's user ID
	dvs: Platform type, iOS = 1, Android = 2, Windows = 3, macOS = 8
	s1: User's attempts
	s2: User's clicks
	s3: User's attempt time in seconds
	s4: level seed, pass in a tuple containing (jumps, percent, seconds, hasPlayed)
	s5: Random number, Set to True to include
	s6: List of PB differences (For example from 0 to 50, then 69, it would be 50,19)
	s7: Randomly Generated 10 character string, set to True to include
	s8: Attempt count
	s9: The amount of coins the user got
	s10: Same as timelyID
	s11: 0 if level has not been completed, otherwise, amount of ticks on the best time attempt
	s12: 0 if level has not been completed, otherwise True
	s13: Unknown value, starts at 1171520
	s14: 0 if level has not been completed, otherwise, amount of clicks on the best time attempt
	s15: 0 if level has not been completed, otherwise True
	s16: Seemingly always empty
	s17: Seemingly always empty
	s18: 0 if level has not been completed, otherwise the amount of collected coins on the best time attempt
	s19: 0 if level has not been completed, otherwise True
	s20: The level version
	chk: Pass in a tuple containing (percent, jumps, attempts, coins, timelyID, seconds, hasPlayed), also include s6 and s7 in the parameters for chk to generate

	attempts: Total level attempts
	coins: The number of coins collected
	timelyID: The ordinal number of the daily/weekly, 0 otherwise
	jumps: Jumps in the current attempt
	seconds: Duration of attempt
	hasPlayed: ALways True
	"""
	secret = Tools.getSecret(1)

	
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

	if udid is not None:
		data["udid"] = udid

	if uuid is not None:
		data["uuid"] = uuid

	if dvs is not None:
		data["dvs"] = dvs
	
	if s1 is not None:
		data["s1"] = s1 + 8354
	
	if s2 is not None:
		data["s2"] = s2 + 3991
	
	if s3 is not None:
		data["s3"] = s3 + 4085
	
	if isinstance(s4, tuple):
		jumps, percent, seconds, hasPlayed = s4
		data["s4"] = Tools._generateClassicLeaderboardSeed(jumps, percent, seconds, hasPlayed)
	
	if s5 is True:
		data["s5"] = Tools._generateLeaderboardRandom(False)
	
	if s6 is not None:
		key = Tools.getXorKey(9)
		value = Tools.b64EncodeUrlSafe(Tools.xorCipher(s6, key))
		s6, data["s6"] = value, value
	
	if s7 is True:
		data["s7"] = Tools.generateRs()

	if s8 is not None:
		data["s8"] = s8

	if s9 is not None:
		data["s9"] = s9 + 5819
	
	if s10 is not None:
		data["s10"] = s10
	
	if s11 is not None:
		if s11 != 0:
			s11 += 46533
		data["s11"] = s11
	
	if s12 is not None:
		data["s12"] = 25645 if s12 is True else 0
	
	if s13 is not None:
		if s13 < 1171520:
			s13 = 1171520
		data["s13"] = s13
	
	if s14 is not None:
		if s14 != 0:
			s14 += 7684
		data["s14"] = s14
	
	if s15 is not None:
		data["s15"] = 3453 if s15 is True else 0
	
	if s16 is not None:
		data["s16"] = s16
	
	if s17 is not None:
		data["s17"] = s17
	
	if s18 is not None:
		if s18 != 0:
			s18 += 6433
		data["s18"] = s18
	
	if s19 is not None:
		data["s19"] = 6323 if s19 is True else 0

	if s20 is not None:
		data["s20"] = s20

	if (s6 is not None and
		s7 is not None and
		isinstance(chk, list)):
		percent, jumps, attempts, coins, timelyID, seconds, hasPlayed = chk
		seed = Tools._generateClassicLeaderboardSeed(jumps, percent, seconds, hasPlayed)
		data["chk"] = Tools.genChk(8, [accountID, levelID, percent, jumps, attempts, seed, s6, 1, coins, timelyID, data["s7"]], 5)
	
	response = Tools.makeReq(
		"http://www.boomlings.com/database/getGJLevelScoresPlat.php",
		data
	)
	
	if not Tools.checkResponse(response.text):
		print(f"getGJLevelScoresPlat Failed: {response.text}")
	
	return response.text
		
def getGJComments21(
	levelID: int,
	page: int,
	accountID: int | None = None,
	gjp2: str | None = None,
	mode: int | None = None,
	total: int | None = None,
	count: int | None = None,
	gameVersion: int | None = None,
	binaryVersion: int | None = None,
	udid: str | None = None,
	uuid: int | None = None,
	dvs: int | None = None
) -> str:
	"""
	levelID: The ID of the level or list. Negative if it's a list ID
	page: Which page of comments you want to see
	accountID: The player's account ID (not to be confused with user ID). Used for authorization
	gjp2: The player's account password, encoded with GJP2. Used for authorization
	mode: Set to 0 for most recent, and 1 for most liked
	total: Probably the cached total number of comments, default is 0
	count: Number of comments to fetch. Defaults to 10, but doubles if "More Comments" is enabled or in compact view (stacking)
	gameVersion: A number representing the game's version. The current value is 22 for 2.2
	binaryVersion: A number representing the game's small version. The current value is 47 for 2.2081 on PC and 48 for 2.2082 on mobile
	udid: The player's UDID (Unique Device Identifier). Used to identify unregistered users
	uuid: The player's user ID
	dvs: Platform type, iOS = 1, Android = 2, Windows = 3, macOS = 8
	"""
	secret = Tools.getSecret(1)
	
	data: dict[str, str | int] = {
		"levelID": levelID,
		"page": page,
		"secret": secret
	}

	if accountID is not None:
		data["accountID"] = accountID
	
	if gjp2 is not None:
		data["gjp2"] = gjp2
	
	if mode is not None:
		data["mode"] = mode
	
	if total is not None:
		data["total"] = total
	
	if count is not None:
		data["count"] = count

	if gameVersion is not None:
		data["gameVersion"] = gameVersion
	
	if binaryVersion is not None:
		data["binaryVersion"] = binaryVersion

	if udid is not None:
		data["udid"] = udid
	
	if uuid is not None:
		data["uuid"] = uuid
	
	if dvs is not None:
		data["dvs"] = dvs
	
	response = Tools.makeReq(
		"http://www.boomlings.com/database/getGJComments21.php",
		data
	)
	
	if not Tools.checkResponse(response.text):
		print(f"getGJComments21 Failed: {response.text}")
	
	return response.text

def getGJCommentHistory(
	userID: int,
	page: int,
	gjp2: str | None = None,
	accountID: int | None = None,
	gameVersion: int | None = None,
	binaryVersion: int | None = None,
	mode: int | None = None,
	total: int | None = None,
	count: int | None = None,
	udid: str | None = None,
	uuid: int | None = None,
	dvs: int | None = None
) -> str:
	"""
	userID: The user ID of the target user. This is different from the account ID
	page: Which page of comments you want to see
	accountID: The player's account ID (not to be confused with user ID). Used for authorization
	gjp2: The player's account password, encoded with GJP2. Used for authorization
	gameVersion: A number representing the game's version. The current value is 22 for 2.2
	binaryVersion: A number representing the game's small version. The current value is 47 for 2.2081 on PC and 48 for 2.2082 on mobile
	mode: Set to 0 for most recent, and 1 for most liked
	total: Probably the cached total number of comments, default is 0
	count: The number of comments you want to get. 20 in normal view, 40 in compact view. Capped at 100
	udid: The player's UDID (Unique Device Identifier). Used to identify unregistered users
	uuid: The player's user ID
	dvs: Platform type, iOS = 1, Android = 2, Windows = 3, macOS = 8
	"""
	secret = Tools.getSecret(1)
	
	data: dict[str, str | int] = {
		"userID": userID,
		"page": page,
		"secret": secret
	}
	
	if gjp2 is not None:
		data["gjp2"] = gjp2
	
	if accountID is not None:
		data["accountID"] = accountID
	
	if gameVersion is not None:
		data["gameVersion"] = gameVersion
	
	if binaryVersion is not None:
		data["binaryVersion"] = binaryVersion
	
	if mode is not None:
		data["mode"] = mode
	
	if total is not None:
		data["total"] = total
	
	if count is not None:
		data["count"] = count
	
	if udid is not None:
		data["udid"] = udid
	
	if uuid is not None:
		data["uuid"] = uuid
	
	if dvs is not None:
		data["dvs"] = dvs
	
	response = Tools.makeReq(
		"http://www.boomlings.com/database/getGJCommentHistory.php",
		data
	)
	
	if not Tools.checkResponse(response.text):
		print(f"getGJCommentHistory Failed: {response.text}")
	
	return response.text

def getGJAccountComments20(
	accountID: int,
	page: int,
	gjp2: str | None = None,
	gameVersion: int | None = None,
	binaryVersion: int | None = None,
	total: int | None = None,
	count: int | None = None,
	udid: str | None = None,
	uuid: int | None = None,
	dvs: int | None = None
) -> str:
	"""
	accountID: The account ID of the player whose comments you're getting
	page: Which page of comments you want to see
	gjp2: The player's account password, encoded with GJP2. Used for authorization
	gameVersion: A number representing the game's version. The current value is 22 for 2.2
	binaryVersion: A number representing the game's small version. The current value is 47 for 2.2081 on PC and 48 for 2.2082 on mobile
	total: Probably the cached total number of account comments, default is 0
	count: Amount of account comments that will be returned. Max 20, default 10
	udid: The player's UDID (Unique Device Identifier). Used to identify unregistered users
	uuid: The player's user ID
	dvs: Platform type, iOS = 1, Android = 2, Windows = 3, macOS = 8
	"""
	secret = Tools.getSecret(1)
	
	data: dict[str, str | int] = {
		"accountID": accountID,
		"page": page,
		"secret": secret
	}

	if gjp2 is not None:
		data["gjp2"] = gjp2

	if gameVersion is not None:
		data["gameVersion"] = gameVersion
	
	if binaryVersion is not None:
		data["binaryVersion"] = binaryVersion
	
	if total is not None:
		data["total"] = total
	
	if count is not None:
		data["count"] = count
	
	if udid is not None:
		data["udid"] = udid
	
	if uuid is not None:
		data["uuid"] = uuid
	
	if dvs is not None:
		data["dvs"] = dvs
	
	response = Tools.makeReq(
		"http://www.boomlings.com/database/getGJAccountComments20.php",
		data
	)
	
	if not Tools.checkResponse(response.text):
		print(f"getGJAccountComments20 Failed: {response.text}")
	
	return response.text

def uploadGJAccComment20(
	accountID: int,
	gjp2: str,
	comment: str,
	gameVersion: int | None = None,
	binaryVersion: int | None = None,
	cType: int | None = None,
	userName: str | None = None,
	chk: tuple[str, str] | None = None,
	udid: str | None = None,
	uuid: int | None = None,
	dvs: int | None = None
) -> str:
	"""
	accountID: The player's account ID (not to be confused with user ID). Used for authorization
	gjp2: The player's account password, encoded with GJP2. Used for authorization
	comment: The comment's text in plaintext
	gameVersion: A number representing the game's version. The current value is 22 for 2.2
	binaryVersion: A number representing the game's small version. The current value is 47 for 2.2081 on PC and 48 for 2.2082 on mobile
	cType: The comment type. 0 for level (unused), 1 for account
	userName: The name of the user
	chk: The comment chk, pass in a tuple containing (Username, Comment Content)
	udid: The player's UDID (Unique Device Identifier). Used to identify unregistered users
	uuid: The player's user ID
	dvs: Platform type, iOS = 1, Android = 2, Windows = 3, macOS = 8
	"""
	secret = Tools.getSecret(1)
	
	commentB64 = Tools.b64EncodeUrlSafe(comment)
	
	data: dict[str, str | int] = {
		"accountID": accountID,
		"gjp2": gjp2,
		"comment": commentB64,
		"secret": secret
	}

	if gameVersion is not None:
		data["gameVersion"] = gameVersion
	
	if binaryVersion is not None:
		data["binaryVersion"] = binaryVersion
	
	if cType is not None:
		data["cType"] = cType
	
	if userName is not None:
		data["userName"] = userName
	
	if chk is not None:
		chkList = list(chk)
		data["chk"] = Tools.genChk(6, list((*chkList, 0, 0, 1)), 2)
	
	if udid is not None:
		data["udid"] = udid
	
	if uuid is not None:
		data["uuid"] = uuid
	
	if dvs is not None:
		data["dvs"] = dvs
	
	response = Tools.makeReq(
		"http://www.boomlings.com/database/uploadGJAccComment20.php",
		data
	)
	
	if not Tools.checkResponse(response.text):
		print(f"uploadGJAccComment20 Failed: {response.text}")
	
	return response.text

def deleteGJAccComment20(
	accountID: int,
	targetAccountID: int,
	gjp2: str,
	commentID: int,
	gameVersion: int | None = None,
	binaryVersion: int | None = None,
	udid: str | None = None,
	uuid: int | None = None,
	dvs: int | None = None,
	cType: int | None = None
	) -> str:
	"""
	accountID: The player's account ID (not to be confused with user ID). Used for authorization
	targetAccountID: Account ID of the comment author
	gjp2: The player's account password, encoded with GJP2. Used for authorization
	commentID: The ID of the comment being deleted (Returned by uploadGJAccComment20)
	gameVersion: A number representing the game's version. The current value is 22 for 2.2
	binaryVersion: A number representing the game's small version. The current value is 47 for 2.2081 on PC and 48 for 2.2082 on mobile
	udid: The player's UDID (Unique Device Identifier). Used to identify unregistered users
	uuid: The player's user ID
	dvs: Platform type, iOS = 1, Android = 2, Windows = 3, macOS = 8
	cType: The comment type. 0 for level (unused), 1 for account
	"""
	secret = Tools.getSecret(1)
	
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
	
	if udid is not None:
		data["udid"] = udid
	
	if uuid is not None:
		data["uuid"] = uuid
	
	if dvs is not None:
		data["dvs"] = dvs
	
	if cType is not None:
		data["cType"] = cType
	
	response = Tools.makeReq(
		"http://www.boomlings.com/database/deleteGJAccComment20.php",
		data
	)
	
	if not Tools.checkResponse(response.text):
		print(f"deleteGJAccComment20 Failed: {response.text}")
	
	return response.text

def uploadGJComment21(
	accountID: int,
	gjp2: str,
	userName: str,
	comment: str,
	levelID: int,
	percent: int,
	gameVersion: int | None = None,
	binaryVersion: int | None = None,
	udid: str | None = None,
	uuid: int | None = None,
	dvs: int | None = None,
	chk: str | None = None
) -> str:
	"""
	accountID: The player's account ID (not to be confused with user ID). Used for authorization
	gjp2: The player's account password, encoded with GJP2. Used for authorization
	userName: The commenter's username
	comment: The comment in plaintext
	levelID: The ID of the level to comment on. If commenting on a list, the ID should be negative
	percent: The level percentage shown on the comment as an integer. Only sent if percentage is not 0
	gameVersion: A number representing the game's version. The current value is 22 for 2.2
	binaryVersion: A number representing the game's small version. The current value is 47 for 2.2081 on PC and 48 for 2.2082 on mobile
	udid: The player's UDID (Unique Device Identifier). Used to identify unregistered users
	uuid: The player's user ID
	dvs: Platform type, iOS = 1, Android = 2, Windows = 3, macOS = 8
	chk: Comment chk, auto generated if omitted
	"""
	secret = Tools.getSecret(1)
	commentB64 = Tools.b64EncodeUrlSafe(comment)
	if chk is None:
		chk = Tools.genChkLevelComment(
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
	
	if udid is not None:
		data["udid"] = udid
	
	if uuid is not None:
		data["uuid"] = uuid
	
	if dvs is not None:
		data["dvs"] = dvs
	
	response = Tools.makeReq(
		"http://www.boomlings.com/database/uploadGJComment21.php", 
		data
	)
	
	if not Tools.checkResponse(response.text):
		print(f"uploadGJComment21 Failed: {response.text}")
	
	return response.text

def deleteGJComment20(
	accountID: int,
	gjp2: str,
	commentID: int,
	levelID: int,
	gameVersion: int | None = None,
	binaryVersion: int | None = None,
	udid: str | None = None,
	uuid: int | None = None,
	dvs: int | None = None
) -> str:
	"""
	accountID: Account ID of the user deleting the comment
	gjp2: The player's account password, encoded with GJP2. Used for authorization
	commentID: ID of the comment
	levelID: ID of the level the comment is on
	gameVersion: A number representing the game's version. The current value is 22 for 2.2
	binaryVersion: A number representing the game's small version. The current value is 47 for 2.2081 on PC and 48 for 2.2082 on mobile
	udid: The player's UDID (Unique Device Identifier). Used to identify unregistered users
	uuid: The player's user ID
	dvs: Platform type, iOS = 1, Android = 2, Windows = 3, macOS = 8
	"""
	secret = Tools.getSecret(1)
	
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
	
	if udid is not None:
		data["udid"] = udid
	
	if uuid is not None:
		data["uuid"] = uuid
	
	if dvs is not None:
		data["dvs"] = dvs
	
	response = Tools.makeReq(
		"http://www.boomlings.com/database/deleteGJComment20.php",
		data
	)
	
	if not Tools.checkResponse(response.text):
		print(f"deleteGJComment20 Failed: {response.text}")
	
	return response.text
		
def uploadGJLevelList(
	gameVersion: int,
	accountID: int,
	gjp2: str,
	listID: int,
	listName: str,
	listDesc: str,
	original: int,
	difficulty: int,
	unlisted: int,
	listLevels: str,
	listVersion: int = 0,
	seed: str | None = None,
	seed2: str | None = None,
	binaryVersion: int | None = None,
	udid: str | None = None,
	uuid: int | None = None,
	dvs: int | None = None
) -> str:
	"""
	gameVersion: A number representing the game's version. The current value is 22 for 2.2
	accountID: Account ID of the user deleting the comment
	gjp2: The player's account password, encoded with GJP2. Used for authorization
	listID: The ID of the list if updating to a newer version, otherwise 0
	listName: The name of the list, in plaintext
	listDesc: The description of the list in plaintext
	original: The ID of the original list if the list was copied, otherwise 0
	difficulty: The list's difficulty face. -1 is N/A, and then it's 0-10 where 0 is Auto and 10 is Extreme Demon
	unlisted: Set to 2 if the list should be unlisted, and to 1 if the list should be unlisted and only viewable by friends
	listLevels: All level IDs included in the list, separated by 
	listVersion: Always 0
	seed: A chk required for authentication, auto generated if omitted
	seed2: 5 randomly generated characters from [A-Za-z0-9]
	binaryVersion: A number representing the game's small version. The current value is 47 for 2.2081 on PC and 48 for 2.2082 on mobile
	udid: The player's UDID (Unique Device Identifier). Used to identify unregistered users
	uuid: The player's user ID
	dvs: Platform type, iOS = 1, Android = 2, Windows = 3, macOS = 8
	"""
	secret = Tools.getSecret(1)
	if seed2 is None:
		seed2 = Tools._generateListSeed2()
	if seed is None:
		seed = Tools._generateListUploadSeed(listLevels, accountID, seed2)
	
	data: dict[str, str | int] = {
		"gameVersion": gameVersion,
		"accountID": accountID,
		"gjp2": gjp2,
		"listID": listID,
		"listName": listName,
		"listDesc": Tools.b64EncodeUrlSafe(listDesc),
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

	if udid is not None:
		data["udid"] = udid
	
	if uuid is not None:
		data["uuid"] = uuid
	
	if dvs is not None:
		data["dvs"] = dvs
	
	response = Tools.makeReq(
		"http://www.boomlings.com/database/uploadGJLevelList.php",
		data
	)
	
	if not Tools.checkResponse(response.text):
		print(f"uploadGJLevelList Failed: {response.text}")
	
	return response.text

def getGJLevelLists(
	gameVersion: int | None = None,
	binaryVersion: int | None = None,
	type_: int | None = None,
	str_: str | int | None = None,
	page: int | None = None,
	accountID: int | None = None,
	gjp2: str | None = None,
	diff: int | None = None,
	demonFilter: int | None = None,
	star: int | None = None,
	followed: str | None = None,
	udid: str | None = None,
	uuid: int | None = None,
	dvs: int | None = None
) -> str:
	"""
	gameVersion: A number representing the game's version. The current value is 22 for 2.2
	binaryVersion: A number representing the game's small version. The current value is 47 for 2.2081 on PC and 48 for 2.2082 on mobile
	type_: Search type, defaults to most liked, types are as follows:
	```markdown
	| Type | Description                                      |
	| :--: | ---------------------------------------------- |
	|  0   | Search query                                   |
	|  1   | Most downloaded                                |
	|  2   | Most liked                                     |
	|  3   | Trending                                       |
	|  4   | Recent                                         |
	|  5   | User's lists, uses `str` as the **account ID** |
	|  6   | Lists button                                   |
	|  7   | Magic (returns the same levels as most liked)  |
	|  11  | Awarded                                        |
	|  12  | Followed (see `followed` parameter)            |
	|  13  | Friends (login required)                       |
	|  27  | Sent lists                                     |
	```
	str_: Search query, user ID or level list depending on type
	page: Which page to request, defaults to 0
	accountID: Account ID of the user deleting the comment
	gjp2: The player's account password, encoded with GJP2. Used for authorization
	diff: Comma-separated list of difficulty values. - = None, -1 = N/A, -2 = Demons (see demonFilter), -3 = Auto, 1 to 5 = Easy to Insane
	demonFilter: Selects which demon difficulty to search. Will search all demon types if not sent. 1 to 5 = Easy Demon to Extreme Demon
	star: Rated filter, either 1 or not sent
	followed: Comma separated list of the followed user IDs
	udid: The player's UDID (Unique Device Identifier). Used to identify unregistered users
	uuid: The player's user ID
	dvs: Platform type, iOS = 1, Android = 2, Windows = 3, macOS = 8
	"""
	secret = Tools.getSecret(1)
	
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
	
	if accountID is not None:
		data["accountID"] = accountID

	if gjp2 is not None:
		data["gjp2"] = gjp2
	
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

	if dvs is not None:
		data["dvs"] = dvs
	
	response = Tools.makeReq(
		"http://www.boomlings.com/database/getGJLevelLists.php",
		data
	)
	
	if not Tools.checkResponse(response.text):
		print(f"getGJLevelLists Failed: {response.text}")
	
	return response.text

def deleteGJLevelList(
	accountID: int,
	gjp2: str,
	listID: int,
	uuid: int,
	gameVersion: int | None = None,
	binaryVersion: int | None = None,
	udid: str | None = None,
	dvs: int | None = None
) -> str:
	"""
	accountID: The player's account ID (not to be confused with user ID). Used for authorization
	gjp2: The player's account password, encoded with GJP2. Used for authorization
	listID: The level list ID to delete
	udid: The player's UDID (Unique Device Identifier). Used to identify unregistered users
	gameVersion: A number representing the game's version. The current value is 22 for 2.2
	binaryVersion: A number representing the game's small version. The current value is 47 for 2.2081 on PC and 48 for 2.2082 on mobile
	uuid: The player's user ID
	dvs: Platform type, iOS = 1, Android = 2, Windows = 3, macOS = 8
	"""
	secret = Tools.getSecret(3)

	if udid is None:
		udid = Tools.generateUdid()
	
	data: dict[str, str | int] = {
		"accountID": accountID,
		"gjp2": gjp2,
		"listID": listID,
		"uuid": uuid,
		"udid": udid,
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

	if dvs is not None:
		data["dvs"] = dvs

	response = Tools.makeReq(
		"http://www.boomlings.com/database/deleteGJLevelList.php",
		data
	)
	
	if not Tools.checkResponse(response.text):
		print(f"deleteGJLevelList Failed: {response.text}")
	
	return response.text
		
def getSaveData(
	gameVersion: int | None = None,
	binaryVersion: int | None = None,
) -> str:
	"""
	gameVersion: A number representing the game's version. The current value is 22 for 2.2
	binaryVersion: A number representing the game's small version. The current value is 47 for 2.2081 on PC and 48 for 2.2082 on mobile
	"""
	secret = Tools.getSecret(1)
	
	data: dict[str, str | int] = {
		"secret": secret
	}
	
	if gameVersion is not None:
		data["gameVersion"] = gameVersion
	
	if binaryVersion is not None:
		data["binaryVersion"] = binaryVersion
	
	response = Tools.makeReq(
		"http://www.boomlings.com/database/getSaveData.php",
		data
	)
	
	if not Tools.checkResponse(response.text):
		print(f"getSaveData Failed: {response.text}")
	
	return response.text

def getAccountURL(accountID: int, type_: int) -> str:
	"""
	accountID: The player's account ID (not to be confused with user ID). Used for authorization
	type_: Used to decide which endpoint is used after the data server is found. 1 = backup data, 2 = sync data
	"""
	secret = Tools.getSecret(1)
	
	data: dict[str, str | int] = {
		"accountID": accountID,
		"type": type_,
		"secret": secret
	}
	
	response = Tools.makeReq(
		"http://www.boomlings.com/database/getAccountURL.php",
		data
	)
	
	if not Tools.checkResponse(response.text):
		print(f"getAccountURL Failed: {response.text}")
	
	return response.text

def likeGJItem211(
	itemID: int,
	type_: int,
	gameVersion: int | None = None,
	binaryVersion: int | None = None,
	accountID: int | None = None,
	gjp2: str | None = None,
	udid: str | None = None,
	uuid: int | None = None,
	rs: str | None = None,
	special: int | None = None,
	like: int | None = None,
	chk: tuple[int, int, int, int, str, int, str, int] | None = None
) -> str:
	"""
	itemID: The ID of the level, comment, or account comment
	type_: 1 for level, 2 for level comment, 3 for account comment, 4 for list
	gameVersion: A number representing the game's version. The current value is 22 for 2.2
	binaryVersion: A number representing the game's small version. The current value is 47 for 2.2081 on PC and 48 for 2.2082 on mobile
	accountID: The player's account ID (not to be confused with user ID). Used for authorization
	gjp2: The player's account password, encoded with GJP2. Used for authorization
	udid: The player's UDID (Unique Device Identifier). Used to identify unregistered users
	uuid: The player's user ID
	rs: 10 randomly generated characters
	special: (Level/List = 0, comment = Level/List ID, profile post = accountID)
	like: (0 = dislike, 1 = like)
	chk: Rate chk, pass in a tuple containing (special, itemID, likeVal, type_, rs, accountID, udid, uuid) to generate
	
	For likes to go through, it's recommended to provide:
	```
	itemID
	type_
	udid
	uuid
	accountID
	gjp2
	like
	```
	"""
	secret = Tools.getSecret(1)
	likeVal = 1 if like is None else like
	
	if rs is None:
		rs = Tools.generateRs()
	
	data: dict[str, str | int] = {
		"itemID": itemID,
		"type": type_,
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
	
	if rs is not None:
		data["rs"] = rs

	if special is not None:
		data["special"] = special

	if like is not None:
		data["like"] = like
	
	if chk is not None:
		special, itemID, likeVal, type_, rs, accountID, udid, uuid = chk
		data["chk"] = Tools.genChkLikeItem(
			special, itemID, likeVal, type_, rs, accountID, udid, uuid
		)
	
	response = Tools.makeReq(
		"http://www.boomlings.com/database/likeGJItem211.php",
		data
	)
	
	if not Tools.checkResponse(response.text):
		print(f"likeGJItem211 Failed: {response.text}")
	
	return response.text

def requestUserAccess(
	accountID: int,
	gjp2: str,
	gameVersion: int | None = None,
	binaryVersion: int | None = None,
	udid: str | None = None,
	uuid: int | None = None,
	dvs: int | None = None
) -> str:
	"""
	accountID: The player's account ID (not to be confused with user ID). Used for authorization
	gjp2: The player's account password, encoded with GJP2. Used for authorization
	gameVersion: A number representing the game's version. The current value is 22 for 2.2
	binaryVersion: A number representing the game's small version. The current value is 47 for 2.2081 on PC and 48 for 2.2082 on mobile
	udid: The player's UDID (Unique Device Identifier). Used to identify unregistered users
	uuid: The player's user ID
	dvs: Platform type, iOS = 1, Android = 2, Windows = 3, macOS = 8
	"""
	secret = Tools.getSecret(1)
	
	data: dict[str, str | int] = {
		"accountID": accountID,
		"gjp2": gjp2,
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

	if dvs is not None:
		data["dvs"] = dvs

	response = Tools.makeReq(
		"http://www.boomlings.com/database/requestUserAccess.php",
		data
	)
	
	if not Tools.checkResponse(response.text):
		print(f"requestUserAccess Failed: {response.text}")
	
	return response.text

def restoreGJItems(udid: str) -> str:
	"""
	This endpoint no longer exists. This is kept for historical reasons.
	udid: The player's UDID (Unique Device Identifier). Used to identify unregistered users, can be replaced with anything
	"""
	secret = Tools.getSecret(1)
	
	data: dict[str, str | int] = {
		"udid": udid,
		"secret": secret
	}
	
	response = Tools.makeReq(
		"http://www.boomlings.com/database/restoreGJItems.php",
		data
	)
	
	if not Tools.checkResponse(response.text):
		print(f"restoreGJItems Failed: {response.text}")
	
	return response.text

def getTop1000() -> str:
	"""
	This endpoint returns an HTML document containing a table with the following columns:
	Rank, AccountID, Username, Stars, Diamonds, Demons, UserCoins, Coins.
	"""
	response = requests.get(
		"http://www.boomlings.com/database/accounts/getTop1000.php",
		headers={"User-Agent": ""}
	)
	
	return response.text
		
def getGJSecretReward(
	udid: str | None = None,
	rewardKey: str | None = None,
	chk: str | None = None,
	gameVersion: int | None = None,
	binaryVersion: int | None = None,
	accountID: int | None = None,
	gjp2: str | None = None,
	uuid: int | None = None,
	dvs: int | None = None
) -> str:
	"""
	udid: The player's UDID (Unique Device Identifier). Used to identify unregistered users
	rewardKey: The input reward key string
	chk: Optional precomputed reward checksum
	gameVersion: A number representing the game's version. The current value is 22 for 2.2
	binaryVersion: A number representing the game's small version. The current value is 47 for 2.2081 on PC and 48 for 2.2082 on mobile
	accountID: The player's account ID (not to be confused with user ID). Used for authorization
	gjp2: The player's account password, encoded with GJP2. Used for authorization
	uuid: The player's user ID
	dvs: Platform type, iOS = 1, Android = 2, Windows = 3, macOS = 8
	"""
	secret = Tools.getSecret(1)
	
	if chk is None:
		chk = Tools.generateWraithRewardChk()
	
	if udid is None:
		udid = Tools.generateUdid()
	
	data: dict[str, str | int] = {
		"udid": udid,
		"chk": chk,
		"secret": secret
	}
	
	if rewardKey is not None:
		data["rewardKey"] = rewardKey

	if gameVersion is not None:
		data["gameVersion"] = gameVersion
	
	if binaryVersion is not None:
		data["binaryVersion"] = binaryVersion
	
	if accountID is not None:
		data["accountID"] = accountID
	
	if gjp2 is not None:
		data["gjp2"] = gjp2
	
	if uuid is not None:
		data["uuid"] = uuid
	
	if dvs is not None:
		data["dvs"] = dvs
	
	response = Tools.makeReq(
		"http://www.boomlings.com/database/getGJSecretReward.php",
		data
	)
	
	if not Tools.checkResponse(response.text):
		print(f"getGJSecretReward Failed: {response.text}")
	
	return response.text

def getGJRewards(
	accountID: int | None = None,
	gjp2: str | None = None,
	udid: str | None = None,
	rewardType: int | None = None,
	chk: str | None = None,
	gameVersion: int | None = None,
	binaryVersion: int | None = None,
	uuid: int | None = None,
	r1: int | bool | None = None,
	r2: int | bool | None = None
) -> str:
	"""
	Note: While the request can technically succeed with no parameters, it is highly recommended to include accountID and gjp2\n
	accountID: The player's account ID (not to be confused with user ID). Used for authorization
	gjp2: The player's account password, encoded with GJP2. Used for authorization
	udid: The player's UDID (Unique Device Identifier). Used to identify unregistered users
	rewardType: 0 for getting info about the chests, 1 to get a new small chest, 2 to get a new large chest. Defaults to 0 if left out
	chk: Rewards CHK using the chest rewards key, auto-generated of omitted
	gameVersion: A number representing the game's version. The current value is 22 for 2.2
	binaryVersion: A number representing the game's small version. The current value is 47 for 2.2081 on PC and 48 for 2.2082 on mobile
	uuid: The player's user ID
	r1: A random 3-5 digit number, set to True to auto-generate
	r2: A random 3-5 digit number, set to True to auto-generate
	"""
	secret = Tools.getSecret(1)
	if chk is None:
		chk = Tools.generateChestMenuChk()
		
	data: dict[str, str | int] = {
		"chk": chk,
		"secret": secret
	}
	
	if r1 is True:
		data["r1"] = Tools.generateRn()
	elif isinstance(r1, int):
		data["r1"] = r1

	if r2 is True:
		data["r2"] = Tools.generateRn()
	elif isinstance(r2, int):
		data["r2"] = r2

	if udid is not None:
		data["udid"] = udid
	else:
		data["udid"] = Tools.generateUdid()

	if accountID is not None:
		data["accountID"] = accountID

	if gjp2 is not None:
		data["gjp2"] = gjp2
	
	if gameVersion is not None:
		data["gameVersion"] = gameVersion
	
	if binaryVersion is not None:
		data["binaryVersion"] = binaryVersion
	
	if uuid is not None:
		data["uuid"] = uuid
	
	if rewardType is not None:
		data["rewardType"] = rewardType
	
	if r1 is not None:
		data["r1"] = r1
	
	if r2 is not None:
		data["r2"] = r2
	
	response = Tools.makeReq(
		"http://www.boomlings.com/database/getGJRewards.php",
		data
	)
	
	if not Tools.checkResponse(response.text):
		print(f"getGJRewards Failed: {response.text}")
	
	return response.text

def getGJChallenges(
	udid: str | None = None,
	chk: str | None = None,
	gameVersion: int | None = None,
	binaryVersion: int | None = None,
	accountID: int | None = None,
	gjp2: str | None = None,
	uuid: int | None = None,
	world: int | None = None,
	dvs: int | None = None
) -> str:
	"""
	udid: The player's UDID (Unique Device Identifier). Used to identify unregistered users
	chk: The challenge checksum for the request
	gameVersion: A number representing the game's version. The current value is 22 for 2.2
	binaryVersion: A number representing the game's small version. The current value is 47 for 2.2081 on PC and 48 for 2.2082 on mobile
	accountID: The player's account ID (not to be confused with user ID). Used for authorization
	gjp2: The player's account password, encoded with GJP2. Used for authorization
	uuid: The player's user ID
	world: Optional world ID for the challenge list
	dvs: Platform type, iOS = 1, Android = 2, Windows = 3, macOS = 8
	"""
	secret = Tools.getSecret(1)
	if chk is None:
		chk = Tools.generateQuestChk()
	
	data: dict[str, str | int] = {
		"chk": chk,
		"secret": secret
	}
	
	if udid is not None:
		data["udid"] = udid
	else:
		data["udid"] = Tools.generateUdid()
	
	if gameVersion is not None:
		data["gameVersion"] = gameVersion
	
	if binaryVersion is not None:
		data["binaryVersion"] = binaryVersion
	
	if accountID is not None:
		data["accountID"] = accountID
	
	if gjp2 is not None:
		data["gjp2"] = gjp2
	
	if uuid is not None:
		data["uuid"] = uuid
	
	if world is not None:
		data["world"] = world
	
	if dvs is not None:
		data["dvs"] = dvs
	
	response = Tools.makeReq(
		"http://www.boomlings.com/database/getGJChallenges.php",
		data
	)
	
	if not Tools.checkResponse(response.text):
		print(f"getGJChallenges Failed: {response.text}")
	
	return response.text
		
def getGJMessages20(
	accountID: int,
	gjp2: str,
	gameVersion: int | None = None,
	binaryVersion: int | None = None,
	page: int | None = None,
	total: int | None = None,
	getSent: int | None = None,
	dvs: int | None = None,
	udid: str | None = None,
	uuid: int | None = None
) -> str:
	"""
	accountID: The player's account ID (not to be confused with user ID). Used for authorization
	gjp2: The player's account password, encoded with GJP2. Used for authorization
	gameVersion: A number representing the game's version. The current value is 22 for 2.2
	binaryVersion: A number representing the game's small version. The current value is 47 for 2.2081 on PC and 48 for 2.2082 on mobile
	page: The message page number
	total: Cached total message count
	getSent: 1 to fetch sent messages instead of received ones
	dvs: Platform type, iOS = 1, Android = 2, Windows = 3, macOS = 8
	udid: The player's UDID (Unique Device Identifier). Used to identify unregistered users
	uuid: The player's user ID
	"""
	secret = Tools.getSecret(1)
	
	data: dict[str, str | int] = {
		"accountID": accountID,
		"gjp2": gjp2,
		"secret": secret
	}
	
	if gameVersion is not None:
		data["gameVersion"] = gameVersion
	
	if binaryVersion is not None:
		data["binaryVersion"] = binaryVersion
	
	if page is not None:
		data["page"] = page
	
	if total is not None:
		data["total"] = total
	
	if getSent is not None:
		data["getSent"] = getSent
	
	if dvs is not None:
		data["dvs"] = dvs
	
	if udid is not None:
		data["udid"] = udid
	
	if uuid is not None:
		data["uuid"] = uuid
	
	response = Tools.makeReq(
		"http://www.boomlings.com/database/getGJMessages20.php",
		data
	)
	
	if not Tools.checkResponse(response.text):
		print(f"getGJMessages20 Failed: {response.text}")
	
	return response.text

def downloadGJMessage20(
	accountID: int,
	gjp2: str,
	messageID: int,
	gameVersion: int | None = None,
	binaryVersion: int | None = None,
	dvs: int | None = None,
	udid: str | None = None,
	uuid: int | None = None
) -> str:
	"""
	accountID: The player's account ID (not to be confused with user ID). Used for authorization
	gjp2: The player's account password, encoded with GJP2. Used for authorization
	messageID: The message ID to fetch
	gameVersion: A number representing the game's version. The current value is 22 for 2.2
	binaryVersion: A number representing the game's small version. The current value is 47 for 2.2081 on PC and 48 for 2.2082 on mobile
	dvs: Platform type, iOS = 1, Android = 2, Windows = 3, macOS = 8
	udid: The player's UDID (Unique Device Identifier). Used to identify unregistered users
	uuid: The player's user ID
	"""
	secret = Tools.getSecret(1)
	
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
	
	if dvs is not None:
		data["dvs"] = dvs
	
	if udid is not None:
		data["udid"] = udid
	
	if uuid is not None:
		data["uuid"] = uuid
	
	response = Tools.makeReq(
		"http://www.boomlings.com/database/downloadGJMessage20.php",
		data
	)
	
	if not Tools.checkResponse(response.text):
		print(f"downloadGJMessage20 Failed: {response.text}")
	
	return response.text

def uploadGJMessage20(
	accountID: int,
	gjp2: str,
	toAccountID: int,
	subject: str,
	body: str,
	gameVersion: int | None = None,
	binaryVersion: int | None = None,
	dvs: int | None = None,
	udid: str | None = None,
	uuid: int | None = None
) -> str:
	"""
	accountID: The player's account ID (not to be confused with user ID). Used for authorization
	gjp2: The player's account password, encoded with GJP2. Used for authorization
	toAccountID: The recipient account ID
	subject: The message subject, sent base64 URL-safe encoded
	body: The message body, sent base64 URL-safe encoded
	gameVersion: A number representing the game's version. The current value is 22 for 2.2
	binaryVersion: A number representing the game's small version. The current value is 47 for 2.2081 on PC and 48 for 2.2082 on mobile
	dvs: Platform type, iOS = 1, Android = 2, Windows = 3, macOS = 8
	udid: The player's UDID (Unique Device Identifier). Used to identify unregistered users
	uuid: The player's user ID
	"""
	secret = Tools.getSecret(1)
	
	data: dict[str, str | int] = {
		"accountID": accountID,
		"gjp2": gjp2,
		"toAccountID": toAccountID,
		"subject": Tools.b64EncodeUrlSafe(subject),
		"body": Tools.b64EncodeUrlSafe(body),
		"secret": secret
	}
	
	if gameVersion is not None:
		data["gameVersion"] = gameVersion
	
	if binaryVersion is not None:
		data["binaryVersion"] = binaryVersion
	
	if dvs is not None:
		data["dvs"] = dvs
	
	if udid is not None:
		data["udid"] = udid
	
	if uuid is not None:
		data["uuid"] = uuid
	
	response = Tools.makeReq(
		"http://www.boomlings.com/database/uploadGJMessage20.php",
		data
	)
	
	if not Tools.checkResponse(response.text):
		print(f"uploadGJMessage20 Failed: {response.text}")
	
	return response.text

def deleteGJMessages20(
	accountID: int,
	gjp2: str,
	messageID: int,
	gameVersion: int | None = None,
	binaryVersion: int | None = None,
	isSender: int | None = None,
	dvs: int | None = None,
	udid: str | None = None,
	uuid: int | None = None
) -> str:
	"""
	accountID: The player's account ID (not to be confused with user ID). Used for authorization
	gjp2: The player's account password, encoded with GJP2. Used for authorization
	messageID: The message ID to delete
	gameVersion: A number representing the game's version. The current value is 22 for 2.2
	binaryVersion: A number representing the game's small version. The current value is 47 for 2.2081 on PC and 48 for 2.2082 on mobile
	isSender: 1 if the actor is the sender of the message
	dvs: Platform type, iOS = 1, Android = 2, Windows = 3, macOS = 8
	udid: The player's UDID (Unique Device Identifier). Used to identify unregistered users
	uuid: The player's user ID
	"""
	secret = Tools.getSecret(1)
	
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
	
	if isSender is not None:
		data["isSender"] = isSender
	
	if dvs is not None:
		data["dvs"] = dvs
	
	if udid is not None:
		data["udid"] = udid
	
	if uuid is not None:
		data["uuid"] = uuid
	
	response = Tools.makeReq(
		"http://www.boomlings.com/database/deleteGJMessages20.php",
		data
	)
	
	if not Tools.checkResponse(response.text):
		print(f"deleteGJMessages20 Failed: {response.text}")
	
	return response.text

def getGJFriendRequests20(
	accountID: int,
	gjp2: str,
	gameVersion: int | None = None,
	binaryVersion: int | None = None,
	page: int | None = None,
	total: int | None = None,
	getSent: int | None = None,
	dvs: int | None = None,
	udid: str | None = None,
	uuid: int | None = None
) -> str:
	"""
	accountID: The player's account ID (not to be confused with user ID). Used for authorization
	gjp2: The player's account password, encoded with GJP2. Used for authorization
	gameVersion: A number representing the game's version. The current value is 22 for 2.2
	binaryVersion: A number representing the game's small version. The current value is 47 for 2.2081 on PC and 48 for 2.2082 on mobile
	page: The request page number
	total: Cached total count of friend requests
	getSent: 1 to fetch sent requests instead of received requests
	dvs: Platform type, iOS = 1, Android = 2, Windows = 3, macOS = 8
	udid: The player's UDID (Unique Device Identifier). Used to identify unregistered users
	uuid: The player's user ID
	"""
	secret = Tools.getSecret(1)
	
	data: dict[str, str | int] = {
		"accountID": accountID,
		"gjp2": gjp2,
		"secret": secret
	}
	
	if gameVersion is not None:
		data["gameVersion"] = gameVersion
	
	if binaryVersion is not None:
		data["binaryVersion"] = binaryVersion
	
	if page is not None:
		data["page"] = page
	
	if total is not None:
		data["total"] = total
	
	if getSent is not None:
		data["getSent"] = getSent
	
	if dvs is not None:
		data["dvs"] = dvs
	
	if udid is not None:
		data["udid"] = udid
	
	if uuid is not None:
		data["uuid"] = uuid
	
	response = Tools.makeReq(
		"http://www.boomlings.com/database/getGJFriendRequests20.php",
		data
	)
	
	if not Tools.checkResponse(response.text):
		print(f"getGJFriendRequests20 Failed: {response.text}")
	
	return response.text

def uploadFriendRequest20(
	accountID: int,
	toAccountID: int,
	gjp2: str,
	gameVersion: int | None = None,
	binaryVersion: int | None = None,
	dvs: int | None = None,
	udid: str | None = None,
	uuid: int | None = None
) -> str:
	"""
	accountID: The player's account ID (not to be confused with user ID). Used for authorization
	toAccountID: The recipient account ID
	gjp2: The player's account password, encoded with GJP2. Used for authorization
	gameVersion: A number representing the game's version. The current value is 22 for 2.2
	binaryVersion: A number representing the game's small version. The current value is 47 for 2.2081 on PC and 48 for 2.2082 on mobile
	dvs: Platform type, iOS = 1, Android = 2, Windows = 3, macOS = 8
	udid: The player's UDID (Unique Device Identifier). Used to identify unregistered users
	uuid: The player's user ID
	"""
	secret = Tools.getSecret(1)
	
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
	
	if dvs is not None:
		data["dvs"] = dvs
	
	if udid is not None:
		data["udid"] = udid
	
	if uuid is not None:
		data["uuid"] = uuid
	
	response = Tools.makeReq(
		"http://www.boomlings.com/database/uploadFriendRequest20.php",
		data
	)
	
	if not Tools.checkResponse(response.text):
		print(f"uploadFriendRequest20 Failed: {response.text}")
	
	return response.text

def deleteGJFriendRequests20(
	accountID: int,
	gjp2: str,
	targetAccountID: int,
	gameVersion: int | None = None,
	binaryVersion: int | None = None,
	accounts: str | None = None,
	isSender: int | None = None,
	dvs: int | None = None,
	udid: str | None = None,
	uuid: int | None = None
) -> str:
	"""
	accountID: The player's account ID (not to be confused with user ID). Used for authorization
	gjp2: The player's account password, encoded with GJP2. Used for authorization
	targetAccountID: The accountID of the player you are declining the friend request or 0 if multiple requests are being declined
	gameVersion: A number representing the game's version. The current value is 22 for 2.2
	binaryVersion: A number representing the game's small version. The current value is 47 for 2.2081 on PC and 48 for 2.2082 on mobile
	accounts: Account IDs seperated by , for players whose requests are being declined. Sent only if there are multiple requests being declined
	isSender: 1 if the player is the sender of the friend request(s) to the target account(s)
	dvs: Platform type, iOS = 1, Android = 2, Windows = 3, macOS = 8
	udid: The player's UDID (Unique Device Identifier). Used to identify unregistered users
	uuid: The player's user ID
	"""
	secret = Tools.getSecret(1)
	
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
	
	if accounts is not None:
		data["accounts"] = accounts
	
	if isSender is not None:
		data["isSender"] = isSender
	
	if dvs is not None:
		data["dvs"] = dvs
	
	if udid is not None:
		data["udid"] = udid
	
	if uuid is not None:
		data["uuid"] = uuid
	
	response = Tools.makeReq(
		"http://www.boomlings.com/database/deleteGJFriendRequests20.php",
		data
	)
	
	if not Tools.checkResponse(response.text):
		print(f"deleteGJFriendRequests20 Failed: {response.text}")
	
	return response.text

def acceptGJFriendRequest20(
	accountID: int,
	targetAccountID: int,
	gjp2: str,
	gameVersion: int | None = None,
	binaryVersion: int | None = None,
	requestID: int | None = None,
	dvs: int | None = None,
	udid: str | None = None,
	uuid: int | None = None
) -> str:
	"""
	accountID: The player's account ID (not to be confused with user ID). Used for authorization
	targetAccountID: The other account involved in the request
	gjp2: The player's account password, encoded with GJP2. Used for authorization
	gameVersion: A number representing the game's version. The current value is 22 for 2.2
	binaryVersion: A number representing the game's small version. The current value is 47 for 2.2081 on PC and 48 for 2.2082 on mobile
	requestID: The ID of the friend request being accepted
	dvs: Platform type, iOS = 1, Android = 2, Windows = 3, macOS = 8
	udid: The player's UDID (Unique Device Identifier). Used to identify unregistered users
	uuid: The player's user ID
	"""
	secret = Tools.getSecret(1)
	
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
	
	if requestID is not None:
		data["requestID"] = requestID
	
	if dvs is not None:
		data["dvs"] = dvs
	
	if udid is not None:
		data["udid"] = udid
	
	if uuid is not None:
		data["uuid"] = uuid
	
	response = Tools.makeReq(
		"http://www.boomlings.com/database/acceptGJFriendRequest20.php",
		data
	)
	
	if not Tools.checkResponse(response.text):
		print(f"acceptGJFriendRequest20 Failed: {response.text}")
	
	return response.text

def readGJFriendRequest20(
	accountID: int,
	gjp2: str,
	requestID: int,
	gameVersion: int | None = None,
	binaryVersion: int | None = None,
	dvs: int | None = None,
	udid: str | None = None,
	uuid: int | None = None
) -> str:
	"""
	accountID: The player's account ID (not to be confused with user ID). Used for authorization
	gjp2: The player's account password, encoded with GJP2. Used for authorization
	requestID: The ID of the received friend request
	gameVersion: A number representing the game's version. The current value is 22 for 2.2
	binaryVersion: A number representing the game's small version. The current value is 47 for 2.2081 on PC and 48 for 2.2082 on mobile
	dvs: Platform type, iOS = 1, Android = 2, Windows = 3, macOS = 8
	udid: The player's UDID (Unique Device Identifier). Used to identify unregistered users
	uuid: The player's user ID
	"""
	secret = Tools.getSecret(1)
	
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
	
	if dvs is not None:
		data["dvs"] = dvs
	
	if udid is not None:
		data["udid"] = udid
	
	if uuid is not None:
		data["uuid"] = uuid
	
	response = Tools.makeReq(
		"http://www.boomlings.com/database/readGJFriendRequest20.php",
		data
	)
	
	if not Tools.checkResponse(response.text):
		print(f"readGJFriendRequest20 Failed: {response.text}")
	
	return response.text

def removeGJFriend20(
	accountID: int,
	gjp2: str,
	targetAccountID: int,
	gameVersion: int | None = None,
	binaryVersion: int | None = None,
	dvs: int | None = None,
	udid: str | None = None,
	uuid: int | None = None
) -> str:
	"""
	accountID: The player's account ID (not to be confused with user ID). Used for authorization
	gjp2: The player's account password, encoded with GJP2. Used for authorization
	targetAccountID: The friend account ID being removed
	gameVersion: A number representing the game's version. The current value is 22 for 2.2
	binaryVersion: A number representing the game's small version. The current value is 47 for 2.2081 on PC and 48 for 2.2082 on mobile
	dvs: Platform type, iOS = 1, Android = 2, Windows = 3, macOS = 8
	udid: The player's UDID (Unique Device Identifier). Used to identify unregistered users
	uuid: The player's user ID
	"""
	secret = Tools.getSecret(1)
	
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
	
	if dvs is not None:
		data["dvs"] = dvs
	
	if udid is not None:
		data["udid"] = udid
	
	if uuid is not None:
		data["uuid"] = uuid
	
	response = Tools.makeReq(
		"http://www.boomlings.com/database/removeGJFriend20.php",
		data
	)
	
	if not Tools.checkResponse(response.text):
		print(f"removeGJFriend20 Failed: {response.text}")
	
	return response.text

def blockGJUser20(
	accountID: int,
	gjp2: str,
	targetAccountID: int,
	gameVersion: int | None = None,
	binaryVersion: int | None = None,
	dvs: int | None = None,
	udid: str | None = None,
	uuid: int | None = None
) -> str:
	"""
	accountID: The player's account ID (not to be confused with user ID). Used for authorization
	gjp2: The player's account password, encoded with GJP2. Used for authorization
	targetAccountID: The account ID of the person being blocked
	gameVersion: A number representing the game's version. The current value is 22 for 2.2
	binaryVersion: A number representing the game's small version. The current value is 47 for 2.2081 on PC and 48 for 2.2082 on mobile
	dvs: Platform type, iOS = 1, Android = 2, Windows = 3, macOS = 8
	udid: The player's UDID (Unique Device Identifier). Used to identify unregistered users
	uuid: The player's user ID
	"""
	secret = Tools.getSecret(1)
	
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
	
	if dvs is not None:
		data["dvs"] = dvs
	
	if udid is not None:
		data["udid"] = udid
	
	if uuid is not None:
		data["uuid"] = uuid
	
	response = Tools.makeReq(
		"http://www.boomlings.com/database/blockGJUser20.php",
		data
	)
	
	if not Tools.checkResponse(response.text):
		print(f"blockGJUser20 Failed: {response.text}")
	
	return response.text

def unblockGJUser20(
	accountID: int,
	gjp2: str,
	targetAccountID: int,
	gameVersion: int | None = None,
	binaryVersion: int | None = None,
	dvs: int | None = None,
	udid: str | None = None,
	uuid: int | None = None
) -> str:
	"""
	accountID: The player's account ID (not to be confused with user ID). Used for authorization
	gjp2: The player's account password, encoded with GJP2. Used for authorization
	targetAccountID: The account ID of the person getting unblocked
	gameVersion: A number representing the game's version. The current value is 22 for 2.2
	binaryVersion: A number representing the game's small version. The current value is 47 for 2.2081 on PC and 48 for 2.2082 on mobile
	dvs: Platform type, iOS = 1, Android = 2, Windows = 3, macOS = 8
	udid: The player's UDID (Unique Device Identifier). Used to identify unregistered users
	uuid: The player's user ID
	"""
	secret = Tools.getSecret(1)
	
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
	
	if dvs is not None:
		data["dvs"] = dvs
	
	if udid is not None:
		data["udid"] = udid
	
	if uuid is not None:
		data["uuid"] = uuid
	
	response = Tools.makeReq(
		"http://www.boomlings.com/database/unblockGJUser20.php",
		data
	)
	
	if not Tools.checkResponse(response.text):
		print(f"unblockGJUser20 Failed: {response.text}")
	
	return response.text

def getGJUserList20(
	accountID: int,
	gjp2: str,
	gameVersion: int | None = None,
	binaryVersion: int | None = None,
	type_: int | None = None,
	dvs: int | None = None,
	udid: str | None = None,
	uuid: int | None = None
) -> str:
	"""
	accountID: The player's account ID (not to be confused with user ID). Used for authorization
	gjp2: gjp2: The player's account password, encoded with GJP2. Used for authorization
	gameVersion: A number representing the game's version. The current value is 22 for 2.2
	binaryVersion: A number representing the game's small version. The current value is 47 for 2.2081 on PC and 48 for 2.2082 on mobile
	type_: 0 for friends, 1 for blocklist. Defaults to 0 if left out
	dvs: Platform type, iOS = 1, Android = 2, Windows = 3, macOS = 8
	udid: The player's UDID (Unique Device Identifier). Used to identify unregistered users
	uuid: The player's user ID
	"""
	secret = Tools.getSecret(1)
	
	data: dict[str, str | int] = {
		"accountID": accountID,
		"gjp2": gjp2,
		"secret": secret
	}
	
	if gameVersion is not None:
		data["gameVersion"] = gameVersion
	
	if binaryVersion is not None:
		data["binaryVersion"] = binaryVersion
	
	if type_ is not None:
		data["type"] = type_
	
	if dvs is not None:
		data["dvs"] = dvs
	
	if udid is not None:
		data["udid"] = udid
	
	if uuid is not None:
		data["uuid"] = uuid
	
	response = Tools.makeReq(
		"http://www.boomlings.com/database/getGJUserList20.php",
		data
	)
	
	if not Tools.checkResponse(response.text):
		print(f"getGJUserList20 Failed: {response.text}")
	
	return response.text
		
def getGJSongInfo(
	songID: int,
	gameVersion: int | None = None,
	binaryVersion: int | None = None,
	accountID: int | None = None,
	gjp2: str | None = None,
	udid: str | None = None,
	uuid: int | None = None,
	dvs: int | None = None
) -> str:
	"""
	songID: The newgrounds ID of the song you want information about
	gameVersion: A number representing the game's version. The current value is 22 for 2.2
	binaryVersion: A number representing the game's small version. The current value is 47 for 2.2081 on PC and 48 for 2.2082 on mobile
	accountID: The player's account ID (not to be confused with user ID). Used for authorization
	gjp2: The player's account password, encoded with GJP2. Used for authorization
	udid: The player's UDID (Unique Device Identifier). Used to identify unregistered users
	uuid: The player's user ID
	dvs: Platform type, iOS = 1, Android = 2, Windows = 3, macOS = 8
	"""
	secret = Tools.getSecret(1)
	
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
	
	if dvs is not None:
		data["dvs"] = dvs
	
	response = Tools.makeReq(
		"http://www.boomlings.com/database/getGJSongInfo.php",
		data
	)
	
	if not Tools.checkResponse(response.text):
		print(f"getGJSongInfo Failed: {response.text}")
	
	return response.text

def getGJTopArtists(
	gameVersion: int | None = None,
	binaryVersion: int | None = None,
	page: int | None = None,
	total: int | None = None,
	dvs: int | None = None,
	udid: str | None = None,
	uuid: int | None = None
) -> str:
	"""
	gameVersion: A number representing the game's version. The current value is 22 for 2.2
	binaryVersion: A number representing the game's small version. The current value is 47 for 2.2081 on PC and 48 for 2.2082 on mobile
	page: Which page of the artists you want to see
	total: Cached total artist count
	dvs: Platform type, iOS = 1, Android = 2, Windows = 3, macOS = 8
	udid: The player's UDID (Unique Device Identifier). Used to identify unregistered users
	uuid: The player's user ID
	"""
	secret = Tools.getSecret(1)
	
	data: dict[str, str | int] = {
		"secret": secret
	}
	
	if gameVersion is not None:
		data["gameVersion"] = gameVersion
	
	if binaryVersion is not None:
		data["binaryVersion"] = binaryVersion
	
	if page is not None:
		data["page"] = page
	
	if total is not None:
		data["total"] = total
	
	if dvs is not None:
		data["dvs"] = dvs
	
	if udid is not None:
		data["udid"] = udid
	
	if uuid is not None:
		data["uuid"] = uuid
	
	response = Tools.makeReq(
		"http://www.boomlings.com/database/getGJTopArtists.php",
		data
	)
	
	if not Tools.checkResponse(response.text):
		print(f"getGJTopArtists Failed: {response.text}")
	
	return response.text

def testSong(songID: int) -> str:
	"""
	This endpoint no longer exists
	songID: The ID of the song on newgrounds
	"""
	response = requests.get(
		f"http://www.boomlings.com/database/testSong.php?songID={songID}",
		headers={"User-Agent": ""}
	)
	
	return response.text

def fetchMusicLibraryDat(
	useV2: bool = True,
	expires: int | None = None,
	token: str | None = None
) -> bytes:
	"""
	useV2: True to fetch the v2 music library file, False for the legacy file
	expires: Optional CDN expiry timestamp used when generating a signed token
	token: Optional CDN access token. If omitted and expires is provided, a token is generated automatically
	"""
	endpoint = (
		"/music/musiclibrary_02.dat" if useV2 else "/music/musiclibrary.dat"
	)
	url = "https://geometrydashfiles.b-cdn.net" + endpoint
	params: dict[str, str | int] = {}
	if expires is not None:
		params["expires"] = expires
	if token is None and expires is not None:
		token = Tools._generateCdnToken(endpoint, expires)
	if token is not None:
		params["token"] = token
	
	response = requests.get(
		url,
		params=params or None,
		headers={"User-Agent": ""}
	)
	return response.content

def fetchSfxLibraryDat(
	expires: int | None = None,
	token: str | None = None
) -> bytes:
	"""
	expires: Optional CDN expiry timestamp used when generating a signed token
	token: Optional CDN access token. If omitted and expires is provided, a token is generated automatically
	"""
	endpoint = "/sfx/sfxlibrary.dat"
	url = "https://geometrydashfiles.b-cdn.net" + endpoint
	params: dict[str, str | int] = {}
	if expires is not None:
		params["expires"] = expires
	if token is None and expires is not None:
		token = Tools._generateCdnToken(endpoint, expires)
	if token is not None:
		params["token"] = token
	
	response = requests.get(
		url,
		params=params or None,
		headers={"User-Agent": ""}
	)
	
	return response.content

def joinMPLobby(
	accountID: int,
	gjp2: str,
	gameID: int,
	lastCommentID: int,
	gameVersion: int | None = None,
	binaryVersion: int | None = None,
) -> str:
	"""
	accountID: The player's account ID (not to be confused with user ID). Used for authorization
	gjp2: The player's account password, encoded with GJP2. Used for authorization
	gameID: The ID of the multiplayer lobby
	lastCommentID: Your last multiplayer comment ID. It's unknown what the initial value is
	gameVersion: A number representing the game's version. The current value is 22 for 2.2
	binaryVersion: A number representing the game's small version. The current value is 47 for 2.2081 on PC and 48 for 2.2082 on mobile
	"""
	secret = Tools.getSecret(2)
	
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
	
	response = Tools.makeReq(
		"https://www.geometrydash.com/database/joinMPLobby.php",
		data
	)
	
	if not Tools.checkResponse(response.text):
		print(f"joinMPLobby Failed: {response.text}")
	
	return response.text

def exitMPLobby(
	accountID: int,
	gjp2: str,
	gameID: int,
	gameVersion: int | None = None,
	binaryVersion: int | None = None,
) -> str:
	"""
	accountID: The player's account ID (not to be confused with user ID). Used for authorization
	gjp2: The player's account password, encoded with GJP2. Used for authorization
	gameID: The ID of the multiplayer lobby
	gameVersion: A number representing the game's version. The current value is 22 for 2.2
	binaryVersion: A number representing the game's small version. The current value is 47 for 2.2081 on PC and 48 for 2.2082 on mobile
	"""
	secret = Tools.getSecret(2)
	
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
	
	response = Tools.makeReq(
		"https://www.geometrydash.com/database/exitMPLobby.php",
		data
	)
	
	if not Tools.checkResponse(response.text):
		print(f"exitMPLobby Failed: {response.text}")
	
	return response.text

def uploadMPComment(
	accountID: int,
	gjp2: str,
	comment: str,
	gameID: int,
	extra: str | None = None,
	chk: str | None = None,
	gameVersion: int | None = None,
	binaryVersion: int | None = None,
) -> str:
	"""
	accountID: The player's account ID (not to be confused with user ID). Used for authorization
	gjp2: The player's account password, encoded with GJP2. Used for authorization
	comment: The comment text, sent base64 URL-safe encoded
	gameID: The ID of the multiplayer lobby
	extra: Optional random or extra payload value used in checksum generation
	chk: Optional precomputed lobby comment checksum
	gameVersion: A number representing the game's version. The current value is 22 for 2.2
	binaryVersion: A number representing the game's small version. The current value is 47 for 2.2081 on PC and 48 for 2.2082 on mobile
	"""
	secret = Tools.getSecret(2)
	if extra is None:
		extra = Tools.generateRs()

	if chk is None:
		chk = Tools.genChk(11, [accountID, comment, gameID, extra], 1)

	comment = Tools.b64EncodeUrlSafe(comment)

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
	
	response = Tools.makeReq(
		"https://www.geometrydash.com/database/uploadMPComment.php",
		data
	)
	
	if not Tools.checkResponse(response.text):
		print(f"uploadMPComment Failed: {response.text}")
	
	return response.text
