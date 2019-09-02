import re

WORD_RE = re.compile(r'\w+')
WORD2_RE = re.compile(r'[^\w]')


def capitalizeMatch(m):
	w = m.group(0)

	if not w[0].isupper():
		return w[0].upper() + w[1:]

	return w


def capitalizeWords(s):
	w = WORD_RE.sub(capitalizeMatch, s)

	w = WORD2_RE.sub("", w)

	return w


def skillNameToCamelCase(skillName):
	skillName = skillName.replace('/', ' ').replace('_', ' ').replace('-', ' ')
	skillName = capitalizeWords(skillName)
	skillName = skillName.replace(' ', '')

	return skillName
