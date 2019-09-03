from core.commons import commons


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
			for argument in _arguments.values():
				self.addArgument(argument)


	def addArgument(self, argument):
		if self.arguments.get(argument.name):
			raise ValueError('An argument with name {} already exists.'.format(str(argument.name)))

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

		self.arguments[argument.name] = argument


	def getArgument(self, name):
		if not self.hasArgument(name):
			raise ValueError('The {} argument does not exist.'.format(str(name)))

		_arguments = list(self.arguments.values()) if commons.isInt(name) else self.arguments

		return _arguments[name]


	def hasArgument(self, name):
		if commons.isInt(name):
			return name < len(self.arguments)

		return name in self.arguments


	def getArguments(self):
		return self.arguments


	def getArgumentCount(self):
		return len(self.arguments) if not self.hasAnArrayArgument else 20000000  # Any huge number


	def getArgumentRequiredCount(self):
		return self.requiredCount


	def getArgumentDefaults(self):
		return {x.name: x.getDefault for x in self.arguments.values()}


	def setOptions(self, options):
		self.options = dict()
		self.shortcuts = dict()
		self.addOptions(options)


	def addOptions(self, options):
		for option in options.values():
			self.addOption(option)


	def addOption(self, option):
		if option.name in self.options and self.options[option.name]:
			raise ValueError('An option named {} already exists.'.format(str(option.name)))

		if option.getShortcut():
			for shortcut in option.getShortcut().split('|'):
				if shortcut in self.shortcuts:
					raise ValueError('An option with shortcut -{} already exists.'.format(str(shortcut)))

		self.options[option.name] = option

		if option.getShortcut():
			for shortcut in option.getShortcut().split('|'):
				self.shortcuts[shortcut] = option.name


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
		return {x.name: x.getDefault for x in self.options.values()}


	def shortcutToName(self, shortcut):
		if shortcut not in self.shortcuts or not self.shortcuts[shortcut]:
			raise ValueError('The -{} option does not exist.'.format(str(shortcut)))

		return self.shortcuts[shortcut]


	def getSynopsis(self):
		elements = list()

		for option in self.getOptions().values():
			shortcut = '-{}|'.format(option.getShortcut()) if option.getShortcut() else ''

			if option.isValueRequired():
				out = '[{}--{}="..."]'
			elif option.isValueOptional():
				out = '[{}--{}[="..."]]'
			else:
				out = '[{}--{}]'

			elements.append(out.format(shortcut, option.name))

		for argument in self.getArguments().values():
			out = '[{}]'
			if not argument.isRequired():
				out = '{}'

			if argument.isArray():
				out += '1'

			elements.append(out.format(argument.name))

			if argument.isArray():
				elements.append('... [{}N]'.format(argument.name))

		return ' '.join(elements)


	def __str__(self):
		return '([{}] arguments={}, options={}, shortcuts={})'.format(
			self.__class__.__name__, self.arguments, self.options, self.shortcuts
		)
