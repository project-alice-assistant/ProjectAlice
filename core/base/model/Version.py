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

		matches = self.VERSION_PARSER_REGEX.search(str(versionString))
		try:
			self._infos = {
				'mainVersion': int(matches.group('mainVersion')),
				'updateVersion': int(matches.group('updateVersion')),
				'hotfix': 0 if not matches.group('hotfix') else int(matches.group('hotfix')),
				'releaseType': matches.group('releaseType') or 'master',
				'releaseNumber': 1 if not matches.group('releaseNumber') else int(matches.group('releaseNumber'))
			}
			self._isVersionNumber = True
		except AttributeError:
			self._isVersionNumber = False
			self._infos = {
				'mainVersion': 0,
				'updateVersion': 0,
				'hotfix': 0,
				'releaseType': '',
				'releaseNumber': 0
			}
		self._version = f'{self.mainVersion}.{self.updateVersion}.{self.hotfix}'


	def __gt__(self, other: Version) -> bool:
		if self.__eq__(other):
			return False

		# 2.1.1 > 1.2.1 > 1.1.2
		if self._version != other._version:
			return self._version > other._version

		# 2.1.1 > 2.1.1-rc > 2.1.1-b > 2.1.1-a
		if self._infos['releaseType'] != other.infos['releaseType']:
			return self._infos['releaseType'] == 'master' \
				or self._infos['releaseType'] > other.infos['releaseType']

		# 2.1.1-b2 > 2.1.1-b1
		return self._infos['releaseNumber'] > other.infos['releaseNumber']


	def __lt__(self, other: Version) -> bool:
		return not self.__eq__(other) and not self.__gt__(other)


	def __eq__(self, other: Version) -> bool:
		return self._infos == other.infos


	def __ne__(self, other: Version) -> bool:
		return not self.__eq__(other)


	def __ge__(self, other: Version) -> bool:
		return self.__eq__(other) or self.__gt__(other)


	def __le__(self, other: Version) -> bool:
		return self.__eq__(other) or not self.__gt__(other)


	def __repr__(self):
		return self._string


	@property
	def string(self) -> str:
		return self._string


	@property
	def infos(self) -> dict:
		return self._infos


	@property
	def isVersionNumber(self) -> bool:
		return self._isVersionNumber
