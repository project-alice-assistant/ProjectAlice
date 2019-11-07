from __future__ import annotations

import re

from core.base.model.ProjectAliceObject import ProjectAliceObject


class Version(str, ProjectAliceObject):

	VERSION_PARSER_REGEX = re.compile('(?P<mainVersion>\d+)\.(?P<updateVersion>\d+)(\.(?P<hotfix>\d+))?(-(?P<releaseType>a|b|rc)(?P<releaseNumber>\d+)?)?')

	def __new__(cls, value, *args, **kwargs):
		return super().__new__(cls, value)


	def __init__(self, versionString: str):
		super().__init__()
		self._string = versionString
		matches = self.VERSION_PARSER_REGEX.search(versionString)

		if not matches:
			self._isVersionNumber = False
		else:
			self._isVersionNumber = True
			self._infos = {
				'mainVersion': int(matches.group('mainVersion')),
				'updateVersion': int(matches.group('updateVersion')),
				'hotfix': -1 if not matches.group('hotfix') else int(matches.group('hotfix')),
				'releaseType': matches.group('releaseType') or 'master',
				'releaseNumber': 1 if not matches.group('releaseNumber') else int(matches.group('releaseNumber'))
			}
			self.isOldVersioning()


	def __gt__(self, other: Version) -> bool:
		if self.__eq__(other) or self.isOldVersioning():
			return False

		if other.isOldVersioning():
			return True

		if self._infos['mainVersion'] > other.infos['mainVersion']:
			# 2.0.0 > 1.0.0
			return True

		elif self._infos['mainVersion'] == other.infos['mainVersion'] and \
				self._infos['updateVersion'] > other.infos['updateVersion']:
			# 2.1.0 > 2.0.0
			return True

		elif self._infos['mainVersion'] == other.infos['mainVersion'] and \
				self._infos['updateVersion'] == other.infos['updateVersion'] and \
				self._infos['hotfix'] > other.infos['hotfix']:
			# 2.1.1 > 2.1.0
			return True

		else:
			if self._infos['releaseType'] in ('a', 'b', 'rc') and other.infos['releaseType'] == 'master':
				# 2.1.1-a < 2.1.1
				return False
			elif self._infos['releaseType'] == 'b' and other.infos['releaseType'] == 'a':
				# 2.1.1-b > 2.1.1-a
				return True
			elif self._infos['releaseType'] == 'rc' and other.infos['releaseType'] in ('a', 'b'):
				# 2.1.1-rc > 2.1.1-b
				return True
			elif self._infos['releaseType'] == 'master' and other.infos['releaseType'] in ('a', 'b', 'rc'):
				# 2.1.1 > 2.1.1-b
				return True
			elif self._infos['releaseType'] == other.infos['releaseType']:
				# 2.1.1-b2 > 2.1.1-b1
				return self._infos['releaseNumber'] > other.infos['releaseNumber']

		return False


	def __lt__(self, other: Version) -> bool:
		if self.__eq__(other):
			return False

		return not self.__gt__(other)


	def __eq__(self, other: Version) -> bool:
		return self._infos == other.infos


	def __ne__(self, other: Version) -> bool:
		return not self.__eq__(other)


	def __ge__(self, other: Version) -> bool:
		return self.__eq__(other) or self.__gt__(other)


	def __le__(self, other: Version) -> bool:
		return self.__eq__(other) or not self.__gt__(other)


	def __repr__(self):
		return f'{self.infos["mainVersion"]}.{self.infos["updateVersion"]}.{self.infos["hotfix"]}-{self.infos["releaseType"]}{self.infos["releaseNumber"]}'


	def isOldVersioning(self) -> bool:
		if self._infos['hotfix'] == -1:
			self.logWarning(f'Use of deprecated version number: {self._string}. Please use 3 digits format: x.x.x(-[a/b/rc]x)')
			return True
		return False


	@property
	def string(self) -> str:
		return self._string


	@property
	def infos(self) -> dict:
		return self._infos


	@property
	def isVersionNumber(self) -> bool:
		return self._isVersionNumber
