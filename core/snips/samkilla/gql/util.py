# -*- coding: utf-8 -*-

def gql(query, replaceMap=None):
	query = query.replace("\n", " ").replace("\t", " ").replace('"', '__QUOTES__')

	if replaceMap:
		for toReplaceStr in replaceMap:
			query = query.replace("${" + toReplaceStr + "}", replaceMap[toReplaceStr])

	return query
