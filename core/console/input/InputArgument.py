# -*- coding: utf-8 -*-


#
# InputArgument is a command line argument
#
class InputArgument:

	REQUIRED = 1
	OPTIONAL = 2
	ARRAY = 4

	def __init__(self, name, mode = None, description = '', default = None):
		self.mode = mode

		if not mode:
			self.mode = self.OPTIONAL

		self.setDefault(default)
		self.name = name
		self.description = description
		self.default = ''

	def getDescription(self):
		return self.description

	def getDefault(self):
		return self.default

	def getName(self):
		return self.name

	def isRequired(self):
		return self.mode == self.REQUIRED & self.mode

	def isArray(self):
		return self.mode == self.ARRAY & self.mode

	def setDefault(self, definition):
		if self.mode == self.REQUIRED and definition is not None:
			raise ValueError('Cannot set a default value except for OPTIONNAL mode')

		if self.isArray():
			if definition is None:
				definition = list()
			elif type(definition) != list:
				raise ValueError('A default value for an array argument must be an array.')

		self.default = definition


	def __str__(self):
		return '([{}] name={}, description={})'.format(self.__class__.__name__, self.name, self.description)
