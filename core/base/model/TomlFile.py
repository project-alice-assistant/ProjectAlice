from pathlib import Path
from textwrap import dedent
from typing import Any, Dict, Union, ValuesView

import re


class TomlFile:

	SECTION_PATTERN = re.compile('^\[(?P<sectionName>.+)\]$')
	CONFIG_PATTERN = re.compile('^(#)?( )?(?P<configName>.+)?( )=?( )(?P<configValue>.*)')

	def __init__(self, path: Path):
		super().__init__()

		self._path = path
		self._data = dict()
		self._load()


	def _load(self):
		if not self._path.exists():
			self._path.touch()

		with self._path.open() as f:
			# noinspection PyTypeChecker
			section: Section = None
			for line in f:
				match = re.match(self.SECTION_PATTERN, line)
				if match:
					section = Section(match.group('sectionName'))
					self._data[section.name] = section
					continue

				match = re.match(self.CONFIG_PATTERN, line)
				if match and section is not None:
					section.addConfig(key=match.group('configName'), value=match.group('configValue'), commented=line.startswith('#'))
					continue

				if line.startswith('##') and section is not None:
					section.addComment(Comment(line))


	def __iter__(self):
		return iter(self._data)


	def __str__(self):
		response = f'[Toml file with {len(self._data)} sections]\n'
		for sec in self._data.values():
			response += f'{sec}\n'

		return response


	def __getitem__(self, item: str) -> dict:
		if item in self._data:
			return self._data[item]

		section = Section(item)
		self._data[section.name] = section
		return section


	def __setitem__(self, key: str, value: dict):
		if not isinstance(value, dict):
			raise ValueError

		if key in self._data:
			self._data[key] = value
			return

		section = Section(key)
		self._data[section.name] = section
		for key, val in value.items():
			section.addConfig(key=key, value=val, commented=False)


	def __delitem__(self, key: str):
		if key in self._data:
			self._data.pop(key)


	def __contains__(self, item) -> bool:
		return item in self._data


class Comment:

	def __init__(self, comment: str):
		self.comment = comment.strip()


class Section(dict):

	def __init__(self, name: str):
		super().__init__()
		self.name = name
		self.data: Dict[str, Union[Comment, Config]] = dict()
		self._comments = 0


	def __len__(self) -> int:
		return len(self.data)


	def __iter__(self):
		return iter(self.data)


	def __setitem__(self, key: str, value: Any):
		self.data[key] = Config(key, value)


	def __getitem__(self, key: str) -> Any:
		return self.data[key]


	def __delitem__(self, key: str):
		self.data.pop(key)


	def __contains__(self, item) -> bool:
		return item in self.data


	def __repr__(self) -> dict:
		return self.data


	def __str__(self):
		response = f'* Section "{self.name}" with {len(self.data) - self._comments} configurations:\n'
		for conf in self.data.values():
			if isinstance(conf, Comment):
				continue

			response += f' - {conf.name} = {conf.value} | Commented: {conf.commented}\n'
		return dedent(response)


	def values(self) -> ValuesView:
		return self.data.values()


	def addComment(self, comment: Comment):
		self._comments += 1
		self.data[f'comment_{self._comments}'] = comment


	def addConfig(self, key: str, value: Any, commented: bool):
		config = Config(key, value, commented)
		self.data[config.name] = config


class Config:

	def __init__(self, key: str, value: Any, commented: bool = False):
		self.name = key
		self.commented = commented

		try:
			self.value = eval(value.replace('true', 'True').replace('false', 'False'))
		except Exception:
			self.value = value


	def commentOut(self):
		self.commented = True


	def uncomment(self):
		self.commented = False


	def __str__(self) -> str:
		return str(self.value)


	def __repr__(self) -> str:
		return self.value


	def __getitem__(self, item):
		if isinstance(self.value, list) or isinstance(self.value, dict):
			return self.value[item]

		return self.value


if __name__ == '__main__':
	t = TomlFile(Path('../../../system/snips/snips.toml'))


	t['lol'] = {'rofl': 'lmfao'}

	print(t)
