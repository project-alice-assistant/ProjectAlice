import re
import sys

from core.commons import commons
from core.console.input.Input import Input


class ArgvInput(Input):
	"""
	ArgvInput is a set of inputs as a argv command line
	"""


	def __init__(self, argv=None, definition=None, standalone=False):
		self.tokens = None
		self.parsed = None
		self.standalone = standalone

		if not argv:
			argv = sys.argv[1:]

		# Unshift the command name:
		# if len(argv) != 0:
		# 	argv.pop(0)

		self.tokens = argv

		super().__init__(definition=definition)


	def setTokens(self, tokens):
		self.tokens = tokens


	def parse(self):
		parseOptions = True
		self.parsed = self.tokens.copy()

		token = None

		if self.parsed:
			token = self.parsed.pop(0)

		while token is not None:
			if parseOptions and token == '':
				self.parseArgument(token)
			elif parseOptions and token == '--':
				parseOptions = False
			elif parseOptions and not commons.indexOf('--', token):
				self.parseLongOption(token)
			elif parseOptions and '-' == token[0] and '-' != token:
				self.parseShortOption(token)
			else:
				self.parseArgument(token)

			try:
				token = self.parsed.pop(0)
			except:
				break


	def parseShortOption(self, token):
		name = token[1:]

		if len(name) > 1:
			if self.definition.hasShortcut(name[0]) and self.definition.getOptionForShortcut(name[0]).acceptValue():
				self.addShortOption(name[0], name[1:])
			else:
				self.parseShortOptionSet(name)

		else:
			self.addShortOption(name, None)


	def parseShortOptionSet(self, name):
		length = len(name)

		for i in range(0, length):
			if not self.definition.hasShortcut(name[i]):
				raise ValueError('The -{} option does not exist.'.format(name[i]))

			option = self.definition.getOptionForShortcut(name[i])

			if option.acceptValue():
				self.addLongOption(option.name, None if i == length - 1 else name[i + 1:])
				break
			else:
				self.addLongOption(option.name, None)


	def parseLongOption(self, token):
		name = token[2:]
		pos = commons.indexOf('=', name)

		if pos != -1:
			self.addLongOption(name[0:pos], name[pos + 1:])
		else:
			self.addLongOption(name, None)


	def parseArgument(self, token):
		c = len(self.arguments)

		if self.definition.hasArgument(c):
			arg = self.definition.getArgument(c)

			if arg.isArray():
				self.arguments[arg.name] = [token]
			else:
				self.arguments[arg.name] = token

		elif self.definition.hasArgument(c - 1) and self.definition.getArgument(c - 1).isArray():
			arg = self.definition.getArgument(c - 1)

			if arg.name not in self.arguments or self.arguments[arg.name] is None:
				self.arguments[arg.name] = list()

			self.arguments[arg.name].append(token)
		else:
			if not self.standalone:
				raise ValueError('Too many arguments.')


	def addShortOption(self, shortcut, value):

		if not self.definition.hasShortcut(shortcut):
			raise ValueError('The -{} option does not exist.'.format(shortcut))

		self.addLongOption(self.definition.getOptionForShortcut(shortcut).name, value)


	def addLongOption(self, name, value):

		if not self.definition.hasOption(name):
			raise ValueError('The --{} option does not exist.'.format(name))

		option = self.definition.getOption(name)

		if value is not None and not option.acceptValue():
			raise ValueError('The --{} option does not accept a value : {}'.format(name, value))

		if value is None and option.acceptValue() and self.parsed:
			nekst = self.parsed.pop(0)

			if not nekst.startswith('-'):
				value = nekst
			else:
				self.parsed.insert(0, nekst)

		if value is None:
			if option.isValueRequired():
				raise ValueError('The --{} option requires a value.'.format(name))

			if not option.isArray():
				if option.isValueOptional():
					value = option.getDefault()
				else:
					value = True

		if option.isArray():
			if not self.options.get(name):
				self.options[name] = list()

			self.options[name].append(value)
		else:
			self.options[name] = value


	def getFirstArgument(self):
		for token in self.tokens:
			if not token.startswith('-'):
				return token


	def hasParameterOption(self, values):

		for token in self.tokens:
			for value in values:
				if token == value or 0 == commons.indexOf(value + '=', token):
					return True

		return False


	def getParameterOption(self, values, definition):

		tokens = self.tokens.copy()
		token = None

		if tokens:
			token = tokens.pop(0)

		if token:
			for value in values:
				if token == value or 0 == commons.indexOf(value + '=', token):
					pos = commons.indexOf('=', token)

					if pos:
						return token[pos + 1:]

			# weird
			# if len(tokens) != 0:
			# 	token = tokens.pop(0)

			return tokens.pop(0)

		return definition


	def __str__(self):
		tokens = list()

		for token in self.tokens:

			reg = re.compile(r'^(-[^=]+=)(.+)')
			match = reg.match(token)

			if match:
				return match[1] + self.escapeToken(match[2])

			if token and token[0] != '-':
				return self.escapeToken(token)

			tokens.append(token)

		return ' '.join(tokens)
