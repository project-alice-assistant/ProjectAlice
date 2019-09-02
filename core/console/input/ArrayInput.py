# -*- coding: utf-8 -*-

from core.console.Tools import indexOf
from core.console.Tools import isInt
from core.console.input.Input import Input


#
# ArrayInput is a set of inputs as Array
#
class ArrayInput(Input):

	def __init__(self, parameters, definition=None):
		self.parameters = parameters

		super().__init__(definition)


	def getFirstArgument(self):
		for key, value in self.parameters.items():
			if key and '-' == key[0]:
				continue

			return value


	def hasParameterOption(self, values):
		for k, v in self.parameters.items():
			if not isInt(k):
				v = k

			if indexOf(v, values) >= 0:
				return True

		return False


	def getParameterOption(self, values, cdef):
		for k, v in self.parameters.items():
			if not isInt(k) and indexOf(v, values) >= 0:
				return True
			elif indexOf(v, values) >= 0:
				return v

		return cdef


	def parse(self):
		for key, value in self.parameters.items():
			if indexOf('--', key) >= 0:
				self.addLongOption(key[2:], value)
			elif '-' == key[0]:
				self.addShortOption(key[1:], value)
			else:
				self.addArgument(key, value)


	def addShortOption(self, shortcut, value):
		if not self.definition.hasShortcut(shortcut):
			raise ValueError('The -{} option does not exist.'.format(str(shortcut)))

		self.addLongOption(self.definition.getOptionForShortcut(shortcut).getName(), value)


	def addLongOption(self, name, value):
		if not self.definition.hasOption(name):
			raise ValueError('The -{} option does not exist.'.format(str(name)))

		option = self.definition.getOption(name)

		if value is None:
			if option.isValueRequired():
				raise ValueError('The -{} option requires a value.'.format(str(name)))

			value = option.getDefault() if option.isValueOptional() else True

		self.options[name] = value


	def addArgument(self, name, value):
		if not self.definition.hasArgument(name):
			raise ValueError('The {} argument does not exist.'.format(str(name)))

		self.arguments[name] = value


	def __str__(self):
		params = list()

		for k, v in self.parameters.items():
			if '-' == k[0]:
				params.append('{}{}'.format(k, ('{}{}'.format('=', self.escapeToken(v)) if '' != v else '')))
			else:
				params.append(self.escapeToken(v))

		return ' '.join(params)
