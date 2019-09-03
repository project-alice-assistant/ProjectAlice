import re

from core.console.input.InputDefinition import InputDefinition


#
# Input is abstraction of a command input
#
class Input:

	def __init__(self, definition=None):
		self.arguments = dict()
		self.options = dict()
		self.interactive = True
		self.definition = None

		if definition is None:
			self.definition = InputDefinition()
		elif isinstance(definition, list):
			self.definition = InputDefinition(definition)
			self.bind(definition)
			self.validate()
		else:
			self.bind(definition)
			self.validate()


	def bind(self, definition):
		self.arguments = dict()
		self.options = dict()
		self.definition = definition
		self.parse()


	def parse(self):
		return True


	def validate(self):
		if len(self.arguments) < self.definition.getArgumentRequiredCount():
			raise ValueError('Not enough arguments.')


	def isInteractive(self):
		return self.interactive


	def setInteractive(self, interactive):
		self.interactive = interactive


	def getArguments(self):
		allArguments = self.definition.getArgumentDefaults()
		allArguments.update(self.arguments)
		return allArguments


	def getArgument(self, name):
		if not self.definition.hasArgument(name):
			raise ValueError('The {} argument does not exist.'.format(str(name)))

		return self.arguments.get(name) or self.definition.getArgument(name).getDefault()


	def getSynopsisBuffer(self):
		return self.definition


	def setArgument(self, name, value):
		if not self.definition.hasArgument(name):
			raise ValueError('The {} argument does not exist.'.format(str(name)))

		self.arguments[name] = value


	def hasArgument(self, name):
		return self.definition.hasArgument(name)


	def getOptions(self):
		allOptions = self.definition.getOptionDefaults()
		allOptions.update(self.options)
		return allOptions


	def getOption(self, name: str):
		if not self.definition.hasOption(name):
			raise ValueError('The {} option does not exist.'.format(name))

		return self.options.get(name) or self.definition.getOption(name).getDefault()


	def setOption(self, name: str, value):
		if not self.definition.hasOption(name):
			raise ValueError('The {} option does not exist.'.format(name))

		self.options[name] = value


	def hasOption(self, name):
		return self.definition.hasOption(name)


	def escapeToken(self, token):
		reg = re.compile(r'^[w-]+')
		result = reg.match(token)

		return token if result else self.escapeshellarg(token)


	@staticmethod
	def escapeshellargReplaceFunction(match):
		match = match.group()
		return match[0] + '\\\''


	def escapeshellarg(self, string):
		return re.sub(r'[^\\]\'', self.escapeshellargReplaceFunction, string)
