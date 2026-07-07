from typing import Any, Literal
import requests
from pprint import pprint


def normaliseResults(data: dict[str, Any]) -> dict[str, Any]:
	keys = [
		"ID",
		"Name",
		"Username",
		"CP",
		"Description",
		"Size",
		"OriginalID",
		"rCoins",
		"sCoins",
		"Version",
		"Length",
		"EditorTime",
		"EditorCTime",
		"RequestedRating",
		"TwoPlayer",
		"ObjectCount",
		"PlayerID",
	]

	data["results"] = [
		dict(zip(keys, result))
		for result in data.get("results", [])
	]

	return data

def makeRequest(
	user: str,
	password: str,
	levelID: int | None = None,
	name: str | None = None,
	username: str | None = None,
	description: str | None = None,
	songID: int | None = None,
	originalID: int | None = None,
	version: int | None = None,
	length: str | None = None,
	rcoins: int | None = None,
	scoins: int | None = None,
	minEditorTime: int | None = None,
	maxEditorTime: int | None = None,
	editorCTime: int | None = None,
	requestedRating: int | None = None,
	twoPlayer: bool | None = None,
	minObjectCount: int | None = None,
	maxObjectCount: int | None = None,
	playerID: int | None = None,
	minCP: int | None = None,
	maxCP: int | None = None,
	minSize: int | None = None,
	maxSize: int | None = None,
	sortBy: Literal["ID", "CreatorPoints", "Size"] | None = None,
	sortOrder: Literal["asc", "desc"] | None = None,
	searchMode: Literal["contains", "exclusive"] | None = None,
	caseSensitive: Literal["sensitive", "insensitive"] | None = None,
	pageSize: int | None = None,
	page: int | None = None,
) -> Any:

	lengthParam = length.title() if length is not None else None

	sortByParam = sortBy
	if sortByParam is not None:
		sortByMap = {
			"id": "ID",
			"creatorpoints": "CreatorPoints",
			"size": "Size",
		}
		sortByParam = sortByMap.get(
			sortByParam.replace("_", "").replace(" ", "").lower(),
			sortByParam,
		)

	sortOrderParam = sortOrder.lower() if sortOrder is not None else "desc"
	searchModeParam = searchMode.lower() if searchMode is not None else "contains"
	caseSensitiveParam = (
		caseSensitive.lower() if caseSensitive is not None else "insensitive"
	)

	twoPlayerParam = (
		"Yes"
		if twoPlayer is True
		else "No"
		if twoPlayer is False
		else None
	)

	if page is None:
		page = 1

	if pageSize is None:
		pageSize = 10

	if sortBy is None:
		sortByParam = "ID"

	if sortOrder is None:
		sortOrder = "desc"

	if searchMode is None:
		searchMode  = "contains"

	if caseSensitive is None:
		caseSensitive = "insensitive"

	params = {
		"level_id": levelID,
		"name": name,
		"username": username,
		"description": description,
		"song_id": songID,
		"original_id": originalID,
		"version": version,
		"length": lengthParam,
		"rcoins": rcoins,
		"scoins": scoins,
		"min_editor_time": minEditorTime,
		"max_editor_time": maxEditorTime,
		"editor_ctime": editorCTime,
		"requested_rating": requestedRating,
		"two_player": twoPlayerParam,
		"min_object_count": minObjectCount,
		"max_object_count": maxObjectCount,
		"player_id": playerID,
		"min_cp": minCP,
		"max_cp": maxCP,
		"min_size": minSize,
		"max_size": maxSize,
		"sort_by": sortByParam,
		"sort_order": sortOrderParam,
		"search_mode": searchModeParam,
		"case_sensitive": caseSensitiveParam,
		"page_size": pageSize,
		"page": page,
	}

	params = {
		key: "" if value is None else value
		for key, value in params.items()
	}

	response = requests.get(
		"https://unlisted.ryder7223.hrsn.dev/api/search",
		params=params,
		auth=(user, password)
	)

	response.raise_for_status()
	data = response.json()
	return normaliseResults(data)
