#
# InputArgument is a command line argument
#
class InputArgument:
	class Mode(Flag):
		OPTIONAL = 0
		REQUIRED = auto()
		IS_ARRAY = auto()


	def __init__(self, name, mode=None, description='', default=None):
		try:
			self.mode = self.Mode(mode or self.Mode.Optional)
		except:
			raise ValueError('Argument mode {} is not valid.'.format(mode))

		self.setDefault(default)
		self._name = name
		self.description = description
		self.default = ''


	def getDescription(self):
		return self.description


	def getDefault(self):
		return self.default

	@property
	def name(self) -> str:
		return self._name


	def isRequired(self) -> bool:
		return bool(self.mode & self.Mode.REQUIRED)


	def isArray(self):
		return bool(self.mode & self.Mode.ARRAY)


	def setDefault(self, definition):
		if self.isRequired() and definition is not None:
			raise ValueError('Cannot set a default value except for OPTIONAL mode')

		if self.isArray():
			if definition is None:
				definition = list()
			elif not isinstance(definition, list):
				raise ValueError('A default value for an array argument must be an array.')

		self.default = definition


	def __str__(self):
		return '([{}] name={}, description={})'.format(self.__class__.__name__, self.name, self.description)
