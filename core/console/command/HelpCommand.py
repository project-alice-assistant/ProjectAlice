from core.console.Command import Command
from core.console.input.InputArgument import InputArgument


#
# HelpCommand provides help for a given command
#
class HelpCommand(Command):

	def __init__(self):
		self.command = None

		super().__init__('HelpCommand')


	def create(self):
		self.setName('help')
		self.setDescription('Displays help for a command')
		self.setDefinition([InputArgument(name='command_name', mode=InputArgument.OPTIONAL, description='The command name', default='help')])
		self.setHelp('> The %command.name% command displays help for a given command:\n'
					 '  <fg:magenta>%command.full_name%<fg:reset> <fg:cyan>list<fg:reset>\n\n'
					 '  To display the list of available commands, please use the list command.')


	def setCommand(self, command):
		self.command = command

		return self


	def execute(self, inputt):
		if self.command is None:
			self.command = self.application().find(inputt.getArgument('command_name'))

		self.nl()
		self.write(self.command.getProcessedHelp())
		self.command = None
