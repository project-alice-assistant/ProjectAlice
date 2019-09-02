class Slot(object):
	def __init__(self, data):
		self._slotName = data['slotName']
		self._entity = data['entity']
		self._rawValue = data['rawValue']
		self._value = data['value']
		self._range = data['range']

	@property
	def slotName(self):
		return self._slotName

	@property
	def entity(self):
		return self._entity

	@property
	def rawValue(self):
		return self._rawValue

	@property
	def value(self):
		return self._value

	@property
	def range(self):
		return self._range
