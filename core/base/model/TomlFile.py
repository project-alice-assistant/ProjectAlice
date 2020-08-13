from __future__ import annotations

import json
import re
import subprocess
import tempfile
from pathlib import Path
from textwrap import dedent
from typing import Any, Dict, ItemsView, Optional, Union, ValuesView

from core.base.model.ProjectAliceObject import ProjectAliceObject


class TomlFile(ProjectAliceObject):

	SECTION_PATTERN = re.compile(r'^\[(?P<sectionName>.+)]$')
	CONFIG_PATTERN = re.compile(r'^(#)?( )?(?P<configName>.+)?( )=?( )(?P<configValue>.*)')

	def __init__(self, path: Path):
		super().__init__()

		self._path = path
		self._data = dict()
		self._loaded = False


	@classmethod
	def loadToml(cls, path: Path, createIfNotExists: bool = False) -> Optional[TomlFile]:
		if not path.exists() and not createIfNotExists:
			return None
		elif not path.exists():
			path.touch()

		instance = cls(path)
		instance._load()
		return instance


	def _load(self):
		with self._path.open() as f:
			# noinspection PyTypeChecker
			section: Optional[Section] = None
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

				if not line.strip() and section is not None:
					section.addEmptiness()
		self._loaded = True


	def dump(self, withComments: bool = True, otherPath: Path = None, keepOtherPath: bool = False) -> dict:
		path = otherPath or self._path
		self._path = otherPath if otherPath and keepOtherPath else path
		writePath = self._path

		try:
			test = tempfile.TemporaryFile(dir=path)
			test.close()
		except Exception:
			writePath = Path(writePath.stem).with_suffix('.toml')

		with writePath.open('w+') as f:
			for sectionName, section in self._data.items():

				f.write(f'[{sectionName}]\n')

				for dataName, data in section.items():
					if isinstance(data, Comment):
						if withComments:
							f.write(f'{data}\n')
					else:
						if isinstance(data, Emptiness):
							f.write('\n')
							continue

						if isinstance(data, Config) and data.commented and not withComments:
							continue

						value = data.value
						if isinstance(value, str):
							value = f'"{value}"'
						elif isinstance(value, bool):
							value = 'true' if value else 'false'

						f.write(f'{"#" if data.commented else ""}{data.name} = {json.dumps(value) if isinstance(value, list) else value}\n')

		if self._path != writePath:
			subprocess.run(['sudo', 'mv', writePath, self._path])

		return self._data


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

		self.addEmptinessIfNeeded()
		section = Section(item)
		self._data[section.name] = section
		return section


	def __setitem__(self, key: str, value: dict):
		if not isinstance(value, dict):
			raise ValueError

		if key in self._data:
			section = self._data[key]
		else:
			self.addEmptinessIfNeeded()
			section = Section(key)
			self._data[section.name] = section

		for key, val in value.items():
			section.addConfig(key=key, value=val, commented=False)


	def addEmptinessIfNeeded(self):
		"""
		Add a space between the last existing section and a new one
		"""
		if self._loaded:
			try:
				self._data[list(self._data)[-1]].addEmptiness()
			except Exception:
				# No need to add new emptiness
				pass


	def __delitem__(self, key: str):
		if key in self._data:
			del self._data[key]


	def __contains__(self, item) -> bool:
		return item in self._data


	def values(self) -> ValuesView:
		return self._data.values()


	def items(self) -> ItemsView:
		return self._data.items()


	def get(self, key, default: Any) -> Any:
		return self._data.get(key, default)


class Comment:

	def __init__(self, comment: str):
		self.comment = comment.strip()


	def __repr__(self):
		return self.comment


	def __str__(self):
		return self.comment


class Section(dict):

	def __init__(self, name: str):
		super().__init__()
		self.name = name
		self.data: Dict[str, Union[Comment, Config, Emptiness]] = dict()
		self._comments = 0
		self._whites = 0


	def __len__(self) -> int:
		return len(self.data)


	def __iter__(self):
		return iter(self.data)


	def __setitem__(self, key: str, value: Any):
		if key in self.data:
			self.data[key].value = value
			self.data[key].uncomment()
		else:
			self.data[key] = Config(key, value)


	def __getitem__(self, key: str) -> Any:
		if key in self.data:
			return self.data[key].value

		return ''


	def __delitem__(self, key: str):
		self.data[key].commentOut()


	def __contains__(self, item) -> bool:
		return item in self.data


	def __repr__(self) -> dict:
		return self.data


	def __str__(self):
		response = f'* Section "{self.name}" with {len(self.data) - self._comments} configurations:\n'
		for conf in self.data.values():
			if isinstance(conf, Comment) or isinstance(conf, Emptiness):
				continue

			response += f' - {conf.name} = {conf.value} | Commented: {conf.commented}\n'
		return dedent(response)


	def values(self) -> ValuesView:
		return self.data.values()


	def items(self) -> ItemsView:
		return self.data.items()


	# noinspection PyMethodOverriding
	def get(self, key, default: Any) -> Any:
		return self.data.get(key, default)


	def addComment(self, comment: Comment):
		self._comments += 1
		self.data[f'comment_{self._comments}'] = comment


	def addConfig(self, key: str, value: Any, commented: bool):
		config = Config(key, value, commented)
		self.data[config.name] = config


	def addEmptiness(self):
		self._whites += 1
		self.data[f'whites_{self._whites}'] = Emptiness()


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
		return self.value


	def __repr__(self) -> str:
		return self.value


	def __getitem__(self, item) -> Any:
		if isinstance(self.value, list) or isinstance(self.value, dict):
			return self.value[item]

		return self.value


class Emptiness:

	def __str__(self) -> str:
		return '\n'


	def __repr__(self) -> str:
		return '\n'
