import sys
import traceback

from colorama import Fore, init
from core.console import Command

# TODO ????
init()

from core.console.input.ArgvInput import ArgvInput
from core.console.input.ArrayInput import ArrayInput
from core.console.command.HelpCommand import HelpCommand
from core.console.command.ListCommand import ListCommand
from core.console.input.InputArgument import InputArgument
from core.console.input.InputDefinition import InputDefinition
from core.console.input.InputOption import InputOption


class ConsoleApplication:
	"""
	ConsoleApplication
	"""

	def __init__(self, name: str, version: int):
		self._name = name
		self._version = version
		self._verbosity = 0
		self._commands = dict()
		self._running = None
		self._needHelp = False
		self._definition = self.getDefaultInputDefinition()

		for command in self.getDefaultCommands():
			self.add(command)


	@property
	def definition(self) -> InputDefinition:
		return self._definition


	@staticmethod
	def getDefaultInputDefinition() -> InputDefinition:
		return InputDefinition([
			InputArgument(name='command', mode=InputArgument.Mode.REQUIRED, description='The command to execute'),
			InputOption(name='--help', shortcut='-h', mode=InputOption.Mode.NONE, description='Display this help message.'),
			InputOption(name='--verbose', shortcut='-v', mode=InputOption.Mode.NONE, description='Increase the verbosity of messages'),
			InputOption(name='--version', shortcut='-V', mode=InputOption.Mode.NONE, description='Display this application version.'),
			InputOption(name='--no-interaction', shortcut='-n', mode=InputOption.Mode.NONE, description='Do not ask any interactive question.')
		])


	@staticmethod
	def getDefaultCommands() -> list:
		return [ListCommand(), HelpCommand()]

	@property
	def commands(self) -> dict:
		return self._commands


	def add(self, command: Command) -> Command:
		command.application = self

		if not command.isEnabled():
			command.application = None
			return

		if command.definition is None:
			raise ValueError('Command class {} is not correctly initialized. You probably forgot to call the parent constructor.'.format(command.__class__.__name__))

		self.commands[command.name] = command

		return command


	def addCommands(self, commands: list):
		for command in commands:
			self.add(command)


	def has(self, name: str) -> bool:
		return name in self.commands


	@property
	def verbosity(self) -> int:
		return self._verbosity


	@verbosity.setter
	def verbosity(self, level: int):
		self._verbosity = level


	@staticmethod
	def getCommandName(inputt: ArgvInput) -> str:
		return inputt.getFirstArgument()

	@property
	def name(self) -> str:
		return self._name

	@name.setter
	def name(self, name: str):
		self._name = name

	@property
	def version(self) -> int:
		return self._version


	@version.setter
	def version(self, version: int):
		self._version = version


	def getLongVersion(self) -> str:
		versionMessage = 'AliceConsole'

		if self.name is not None:
			versionMessage = self.name

		if self._version is not None:
			versionMessage += ' version ' + str(self._version)

		return versionMessage


	# TODO doRun() doesn't raise any exceptions
	def run(self, inputt: ArgvInput = None) -> int:
		if inputt is None:
			inputt = ArgvInput()

		self.configureIO(inputt)

		try:
			exitCode = self.doRun(inputt)
		except ValueError as ve:
			exitCode = 400
			print(Fore.YELLOW + '[Error]' + Fore.RESET + ' Error with code {}'.format(exitCode))
			print(Fore.YELLOW + '[Error]' + Fore.RESET + ' Message {}'.format(ve))

			if self._verbosity > 0:
				print(traceback.format_exc())
				sys.exit(exitCode)
			else:
				sys.exit(exitCode)

		except Exception as e:
			exitCode = 500
			print(Fore.RED + '[Exception]' + Fore.RESET + ' Error with code {}'.format(exitCode))
			print(Fore.RED + '[Exception]' + Fore.RESET + ' Message {}'.format(e))
			# print('\n Message: ' + str(self.running.getSynopsis()))

			if self._verbosity > 0:
				print(traceback.format_exc())
				sys.exit(exitCode)
			else:
				sys.exit(exitCode)

		return exitCode


	def configureIO(self, inputt: ArgvInput):
		if inputt.hasParameterOption(['--no-interaction', '-n']):
			inputt.setInteractive(False)

		if inputt.hasParameterOption(['--verbose', '-v']):
			self.verbosity = 1


	def doRun(self, inputt: ArgvInput) -> int:
		if inputt.hasParameterOption(['--version', '-V']):
			print(self.getLongVersion())
			return 0

		name = self.getCommandName(inputt)

		if inputt.hasParameterOption(['--help', '-h']):
			if name is None:
				name = 'help'
				inputt = ArrayInput(parameters={'command': 'help'})
			else:
				self._needHelp = True

		if name is None:
			name = 'list'
			inputt = ArrayInput(parameters={"command": name})

		command = self.find(name)
		self._running = command
		exitCode = self.doRunCommand(command=command, inputt=inputt)
		self._running = None

		return exitCode


	@staticmethod
	def doRunCommand(command: Command, inputt: ArgvInput):
		return command.run(inputt)


	def find(self, name: str):
		return self.get(name)


	def get(self, name: str) -> Command:
		if name not in self.commands or self.commands[name] is None:
			raise ValueError('The command \'{}\' does not exist.'.format(name))

		command = self.commands[name]

		if self._needHelp:
			self._needHelp = False
			helpCommand = self.get('help')
			helpCommand.setCommand(command)
			return helpCommand

		return command
