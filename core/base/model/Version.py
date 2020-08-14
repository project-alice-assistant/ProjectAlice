from __future__ import annotations

from dataclasses import dataclass

import re


@dataclass(order=True)
class Version:
	mainVersion: int = 0
	updateVersion: int = 0
	hotfix: int = 0
	# use of release instead of master since release > rc > b > a
	releaseType: str = 'release'
	releaseNumber: int = 1


	@property
	def isVersionNumber(self):
		return self > Version(0, 0, 0, '', 0)


	def __str__(self):
		if self.releaseType == 'release':
			return f'{self.mainVersion}.{self.updateVersion}.{self.hotfix}'
		else:
			return f'{self.mainVersion}.{self.updateVersion}.{self.hotfix}-{self.releaseType}{self.releaseNumber}'


	@classmethod
	def fromString(cls, versionString: str) -> Version:
		versionMatch = re.search(
			r'(?P<mainVersion>\d+)\.(?P<updateVersion>\d+)(?:\.(?P<hotfix>\d+))?(?:-(?P<releaseType>a|b|rc)(?P<releaseNumber>\d+)?)?',
			str(versionString))

		# when the string is no version set the version to the lowest possible value
		if not versionMatch:
			return cls(0, 0, 0, '', 0)

		return cls(
			int(versionMatch.group('mainVersion')),
			int(versionMatch.group('updateVersion')),
			int(versionMatch.group('hotfix') or 0),
			versionMatch.group('releaseType') or 'release',
			int(versionMatch.group('releaseNumber') or 1))
