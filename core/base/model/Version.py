from __future__ import annotations
import attr
import re

@attr.s(slots=True, frozen=True)
class Version:
	mainVersion = attr.ib(default=0, converter=int)
	updateVersion = attr.ib(default=0, converter=int)
	hotfix = attr.ib(default=0, converter=int)
	# use of release instead of master since release > rc > b > a
	releaseType = attr.ib(default='release', converter=attr.converters.default_if_none('release'))
	releaseNumber  = attr.ib(default=1, converter=lambda x: int(x) if x else 1)
	version: str = attr.ib(init=False)
	@version.default
	def _combineVersions(self):
		return f'{self.mainVersion}.{self.updateVersion}.{self.hotfix}-{self.releaseType}{self.releaseNumber}'

	isVersionNumber: bool = attr.ib(init=False)
	@isVersionNumber.default
	def _isVersionNumber(self):
		return self.version != '0.0.0-0'
	
	def __str__(self):
		return self.version.rstrip('-release1')
	
	@classmethod
	def fromString(cls, versionString: str) -> Version:
		versionMatch = re.search(
			'(?P<mainVersion>\d+)\.(?P<updateVersion>\d+)(?:\.(?P<hotfix>\d+))?(?:-(?P<releaseType>a|b|rc)(?P<releaseNumber>\d+)?)?',
			str(versionString))
		return cls(*versionMatch.groups()) if versionMatch else cls(0, 0, 0, '', 0)
