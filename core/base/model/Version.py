from __future__ import annotations
import attr
import re

@attr.s(slots=True, frozen=True, auto_attribs=True)
class Version:
	mainVersion: int = 0
	updateVersion: int = 0
	hotfix: int = 0
	# use of release instead of master since release > rc > b > a
	releaseType: str = 'release'
	releaseNumber: int  = 1


	@property
	def version(self):
		return f'{self.mainVersion}.{self.updateVersion}.{self.hotfix}-{self.releaseType}{self.releaseNumber}'


	@property
	def isVersionNumber(self):
		return self.version != '0.0.0-0'


	def __str__(self):
		return self.version.rstrip('-release1')


	@classmethod
	def fromString(cls, versionString: str) -> Version:
		versionMatch = re.search(
			'(?P<mainVersion>\d+)\.(?P<updateVersion>\d+)(?:\.(?P<hotfix>\d+))?(?:-(?P<releaseType>a|b|rc)(?P<releaseNumber>\d+)?)?',
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
