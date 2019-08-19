# -*- coding: utf-8 -*-

import re

#
# Tools
#

WORD_RE = re.compile(r'\w+')
WORD2_RE = re.compile(r'[^\w]')

def toArray(object):
	tmp_array = list()

	for key in object:
		tmp_array.append(object[key])

	return tmp_array

def isInt(str):
	try:
		int(str)
		return True
	except ValueError:
		return False


def indexOf(needle, heystack):
	try:
		return heystack.index(needle)
	except ValueError:
		return -1

def ucfirst(str, tolower = False):
	str += ''
	f = str[0].upper()
	if tolower:
		return f + str[1:].lower()
	return f + str[1:]

def _capitalizeMatch(m):
	w = m.group(0)
	if not w[0].isupper():
		return w[0].upper() + w[1:]
	return w

def _capitalizeWords(s):
	w = WORD_RE.sub(_capitalizeMatch, s)
	w = WORD2_RE.sub("", w)
	return w

def camelCase(word, useUCfirst = False):
	word = word.replace('/', ' ').replace('_', ' ').replace('-', ' ').replace('.', ' ')
	word = _capitalizeWords(word)
	word = word.replace(' ', '')

	return ucfirst(word) if useUCfirst else word
