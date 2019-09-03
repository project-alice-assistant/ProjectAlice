def gql(query: str, replaceMap: dict = None) -> str:
	query = query.replace("\n", ' ').replace("\t", ' ').replace('"', '__QUOTES__')

	if replaceMap:
		for toReplaceStr in replaceMap:
			query = query.replace('${' + toReplaceStr + '}', replaceMap[toReplaceStr])

	return query
