from __future__ import annotations

import re

class Version(str):

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
				'hotfix': int(matches.group('hotfix')) if matches.group('hotfix') else 0,
				'releaseType': matches.group('releaseType') or 'master',
				'releaseNumber': int(matches.group('releaseNumber')) if matches.group('releaseNumber') else 1
			}
			self._isVersionNumber = True
		except AttributeError:
			self._isVersionNumber = False
			self._infos = {
				'mainVersion'  : 0,
				'updateVersion': 0,
				'hotfix'       : 0,
				'releaseType'  : '',
				'releaseNumber': 0
			}
		
		# master gets z so it has a higher value than any other release type
		releaseMathing = 'z' if self._infos['releaseType'] == 'master' else self._infos['releaseType']
		self.versionMatching = f'{self._infos["mainVersion"]}{self._infos["updateVersion"]}{self._infos["hotfix"]}{releaseMathing}{self._infos["releaseNumber"]}'


	def __gt__(self, other: Version) -> bool:
		return self.versionMatching > other.versionMatching


	def __lt__(self, other: Version) -> bool:
		return not self.__eq__(other) and not self.__gt__(other)


	def __eq__(self, other: Version) -> bool:
		return self.versionMatching == other.versionMatching


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
