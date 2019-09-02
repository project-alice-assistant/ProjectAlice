# -*- coding: utf-8 -*-


from core.console.Tools import isInt, toArray


#
# InputDefinition is a collection of InputArgument and InputOption
#
class InputDefinition:

	def __init__(self, definition=None):
		if definition is None:
			definition = list()

		self.arguments = dict()
		self.requiredCount = 0
		self.hasAnArrayArgument = False
		self.hasOptional = False
		self.options = dict()
		self.shortcuts = dict()
		self.setDefinition(definition)


	def setDefinition(self, definition):
		_arguments = dict()
		options = dict()
		cpt = 0

		if definition:
			for item in definition:
				if item.__class__.__name__ == 'InputOption':
					options[cpt] = item
				else:
					_arguments[cpt] = item

				cpt += 1

		self.setArguments(_arguments)
		self.setOptions(options)


	def setArguments(self, _arguments):
		self.arguments = dict()
		self.requiredCount = 0
		self.hasOptional = False
		self.hasAnArrayArgument = False
		self.addArguments(_arguments)


	def addArguments(self, _arguments):
		if _arguments:
			for index, argument in _arguments.items():
				self.addArgument(argument)


	def addArgument(self, argument):
		if argument.getName() in self.arguments and self.arguments[argument.getName()]:
			raise ValueError('An argument with name {} already exists.'.format(str(argument.getName())))

		if self.hasAnArrayArgument:
			raise ValueError('Cannot add an argument after an array argument.')

		if argument.isRequired() and self.hasOptional:
			raise ValueError('Cannot add a required argument after an optional one.')

		if argument.isArray():
			self.hasAnArrayArgument = True

		if argument.isRequired():
			self.requiredCount += 1
		else:
			self.hasOptional = True

		self.arguments[argument.getName()] = argument


	def getArgument(self, name):
		if not self.hasArgument(name):
			raise ValueError('The {} argument does not exist.'.format(str(name)))

		_arguments = None

		if isInt(name):
			_arguments = toArray(self.arguments)
		else:
			_arguments = self.arguments

		return _arguments[name]


	def hasArgument(self, name):
		_arguments = self.arguments

		if isInt(name):
			_arguments = toArray(self.arguments)
			return name < len(_arguments)

		return name in _arguments


	def getArguments(self):
		return self.arguments


	def getArgumentCount(self):
		if self.hasAnArrayArgument:
			return 20000000  # Any huge number
		else:
			return len(self.arguments)


	def getArgumentRequiredCount(self):
		return self.requiredCount


	def getArgumentDefaults(self):
		values = list()

		for index, argument in self.arguments.items():
			values[argument.getName()] = argument.getDefault()

		return values


	def setOptions(self, options):
		self.options = dict()
		self.shortcuts = dict()
		self.addOptions(options)


	def addOptions(self, options):
		for index, option in options.items():
			self.addOption(option)


	def addOption(self, option):
		if option.getName() in self.options and self.options[option.getName()]:
			raise ValueError('An option named {} already exists.'.format(str(option.getName())))

		if option.getShortcut():
			for shortcut in option.getShortcut().split('|'):
				if shortcut in self.shortcuts:
					raise ValueError('An option with shortcut -{} already exists.'.format(str(shortcut)))

		self.options[option.getName()] = option

		if option.getShortcut():
			for shortcut in option.getShortcut().split('|'):
				self.shortcuts[shortcut] = option.getName()


	def getOption(self, name):
		if not self.hasOption(name):
			raise ValueError('The --{} option does not exist.'.format(str(name)))

		return self.options[name]


	def hasOption(self, name):
		return name in self.options


	def getOptions(self):
		return self.options


	def hasShortcut(self, name):
		return name in self.shortcuts


	def getOptionForShortcut(self, shortcut):
		return self.getOption(self.shortcutToName(shortcut))


	def getOptionDefaults(self):
		values = list()

		for index, option in self.options.items():
			values[option.getName()] = option.getDefault()
		return values


	def shortcutToName(self, shortcut):
		if shortcut not in self.shortcuts or not self.shortcuts[shortcut]:
			raise ValueError('The -{} option does not exist.'.format(str(shortcut)))

		return self.shortcuts[shortcut]


	def getSynopsis(self):
		elements = list()

		for index, option in self.getOptions().items():
			if option.getShortcut():
				shortcut = '-{}|'.format(option.getShortcut())
			else:
				shortcut = ''

			out = '['

			if option.isValueRequired():
				out += str(shortcut) + '--' + str(option.getName()) + '="..."'
			elif option.isValueOptional():
				out += str(shortcut) + '--' + str(option.getName()) + '[="..."]'
			else:
				out += str(shortcut) + '--' + str(option.getName())

			out += ']'

			elements.append(out)

		for index, argument in self.getArguments().items():
			out = ''

			if argument.isRequired():
				out += argument.getName()
				if argument.isArray():
					out += '1'
			else:
				out += '[' + str(argument.getName()) + ']'

				if argument.isArray():
					out += '1'

			elements.append(out)

			if argument.isArray():
				elements.append('... [' + str(argument.getName()) + 'N]')

		return ' '.join(elements)


	def __str__(self):
		return '([{}] arguments={}, options={}, shortcuts={})'.format(
			self.__class__.__name__, self.arguments, self.options, self.shortcuts
		)
