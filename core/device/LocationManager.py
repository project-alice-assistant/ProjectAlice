class LocationManager(Manager):

	TABLE = 'locations'
	DATABASE =  {
		TABLE: [
			'id INTEGER PRIMARY KEY',
			'name TEXT',
			'synonyms TEXT',
			'coordinates TEXT'
		]
	}


	def __init__(self):
		super().__init__(databaseSchema=self.DATABASE)

		self._locations: Dict[str, Device] = dict()


	def onStart(self):
		super().onStart()

		self.loadLocations()
		self.logInfo(f'Loaded **{len(self._locations)}** room', plural='rooms')


	def loadLocations(self):
		for row in self.databaseFetch(tableName=TABLE, query='SELECT * FROM :__table__', method='all'):
			self._locations[row['id']] = Location(row)


	def addNewLocation(self, name: str = None) -> bool:
		values = {'name': name}
		values['id'] = self.databaseInsert(tableName='devices', query='INSERT INTO :__table__ (name, synonyms, coordinates) VALUES (:name, :synonyms, :coordinates)', values=values)
		self._locations[id] = Location(values)
		return True

	@app.route('/getLocations')
	def getLocations():
	    pass
