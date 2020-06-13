from flask import jsonify, render_template, request, send_from_directory
from flask_classful import route

from core.interface.model.View import View


class MyHomeView(View):
	route_base = '/myhome/'


	def index(self):
		return render_template(template_name_or_list='myHome.html',
		                       langData=self._langData,
		                       aliceSettings=self.ConfigManager.aliceConfigurations)


	### Location API
	@route('/Location/<path:_id>/getSettings', methods=['POST'])
	def getLocationSettings(self, _id: str):
		try:
			_id = int(_id)
			return jsonify(self.LocationManager.getSettings(_id))
		except Exception as e:
			self.logError(f'Failed loading settings: {e}')
			return jsonify(sucess=False)


	@route('/Location/<path:_id>/deleteSynonym', methods=['POST'])
	def deleteLocationSynonym(self, _id: str):
		try:
			_id = int(_id)
			req_data = request.form.to_dict()
			self.logInfo(f'trying to delete {req_data} for {_id}')
			return jsonify(self.LocationManager.deleteLocationSynonym(_id, req_data['value']))
		except Exception as e:
			self.logError(f'Failed deleting synonym: {e}')
			return jsonify(sucess=False)


	@route('/Location/<path:_id>/addSynonym', methods=['POST'])
	def addLocationSynonym(self, _id: str):
		# todo check duplicates (with other rooms as well!)
		try:
			_id = int(_id)
			req_data = request.form.to_dict()
			self.logInfo(f'trying to add {req_data} for {_id}')
			return jsonify(self.LocationManager.addLocationSynonym(_id, req_data['value']))
		except Exception as e:
			self.logError(f'Failed adding synonym: {e}')
			return jsonify(sucess=False)


	# TODO Consider using PUT method?
	@route('/Location/0/add', methods=['POST'])
	def addLocation(self):
		try:
			req_data = request.form.to_dict()
			return jsonify(id=self.LocationManager.addNewLocation(req_data['name']).id)
		except Exception as e:
			return jsonify(error=str(e))


	# TODO consider using DELETE method?
	@route('/Location/<path:_id>/delete', methods=['POST'])
	def deleteLocation(self, _id: str):
		_id = int(_id)
		return jsonify(self.LocationManager.deleteLocation(_id))


	### Device Type API
	@route('/deviceType_static/<path:filename>')
	def deviceType_static(self, filename: str):
		parent, fileType, filename = filename.split('/')
		self.logInfo(f'../../skills/{parent}/device/{fileType}/{filename}')
		return send_from_directory(f'{self.WebInterfaceManager.app.root_path}/../../skills/{parent}/device/{fileType}/', filename)


	@route('/DeviceType/getList')
	def deviceType_getList(self):
		res = [{'skill': devobs.skill, 'deviceType': devobs.name, 'id': _id} for _id, devobs in self.DeviceManager.deviceTypes.items()]
		return jsonify(res)


	### Device API
	@route('/Device/0/add', methods=['POST'])
	def addDevice(self):
		try:
			req_data = request.form.to_dict()
			device = self.DeviceManager.addNewDevice(deviceTypeId=int(req_data['deviceTypeID']), locationId=int(req_data['locationID']))
			if not device:
				raise Exception(f'Device creation failed - please see log')
			deviceType = device.getDeviceType()
			return {'id': device.id, 'skill': deviceType.skill, 'deviceType': deviceType.name}
		except Exception as e:
			self.logError(f'Failed adding device: {e}')
			return jsonify(error=str(e))


	# TODO consider using DELETE method?
	@route('/Device/<path:_id>/delete', methods=['POST'])
	def deleteDevice(self, _id: int):
		try:
			_id = int(_id)
			self.DeviceManager.deleteDeviceID(deviceId=_id)
			return jsonify(success=True)
		except Exception as e:
			self.logError(f'Failed deleting device: {e}')
			return jsonify(success=False)


	@route('/Device/<path:_id>/getSettings/<path:roomid>', methods=['POST'])
	def getDeviceRoomSettings(self, _id: str, roomid: str):
		try:
			_id = int(_id)
			roomid = int(roomid)
			if roomid == 0:
				# todo get generic settings
				pass
			else:
				# todo get room dependent settings
				pass
		except Exception as e:
			self.logError(f'Failed getting device settings: {e}')


	#TODO consider using UPDATE method?
	@route('/Device/<path:_id>/saveSettings/<path:roomid>', methods=['POST'])
	def saveDeviceRoomSettings(self, _id: str, roomid: str):
		try:
			_id = int(_id)
			roomid = int(roomid)
			if roomid == 0:
				# todo get generic settings
				pass
			else:
				# todo get room dependent settings
				pass
		except Exception as e:
			self.logError(f'Failed saving device settings: {e}')


	@route('/Device/<path:_id>/toggle', methods=['POST'])
	def toggleDevice(self, _id: str):
		try:
			self.logInfo(f'Toggling device id {_id}')
			_id = int(_id)
			self.DeviceManager.getDeviceById(_id).toggle()
			return jsonify(success=True)
		except Exception as e:
			self.logError(f'Failed toggling device Link: {e}')
			return jsonify(success=False)


	@route('/Device/<path:_id>/addLink/<path:roomid>', methods=['POST'])
	def addDeviceLink(self, _id: str, roomid: str):
		try:
			_id = int(_id)
			roomid = int(roomid)
			if roomid == 0:
				raise Exception('No valid room ID supplied')
			else:
				self.DeviceManager.addLink(deviceId=id, locationId=roomid)
			return jsonify(success=True)
		except Exception as e:
			self.logError(f'Failed adding room/device Link: {e}')
			return jsonify(success=False)


	@route('/Device/u/<path:uid>/icon', methods=['GET'])
	def getIconUID(self, uid: str):
		return self.getIcon(id=self.DeviceManager.devUIDtoID())


	@route('/Device/<path:_id>/icon', methods=['GET'])
	def getIcon(self, _id: str):
		try:
			_id = int(_id)
			device = self.DeviceManager.getDeviceById(_id)
			return send_from_directory(f'{self.WebInterfaceManager.app.root_path}/../../skills/{device.skill}/device/img/', device.getIcon())
		except Exception as e:
			self.logError(f'Failed loading icon: {e}')
			return send_from_directory(f'{self.WebInterfaceManager.app.root_path}/../static/css/images/', 'error.png')


	@route('/Device/<path:_id>/deleteLink/<path:roomid>', methods=['POST'])
	def deleteDeviceLink(self, _id: str, roomid: str):
		try:
			_id = int(_id)
			locationID = int(roomid)
			if locationID == 0:
				raise Exception('No valid room id supplied')
			else:
				linkID = self.DeviceManager.getLink(_id, locationID)
				self.DeviceManager.deleteLink(_id=linkID)
		except Exception as e:
			self.logError(f'Failed deleting room/device Link: {e}')


	@route('/Device/<path:_id>/pair', methods=['POST'])
	def pairDevice(self, _id: str):
		try:
			_id = int(_id)
			device = self.DeviceManager.getDeviceById(_id)
			device.getDeviceType().discover(device=device, uid=self.DeviceManager.getFreeUID())
			return jsonify(success=True)
		except Exception as e:
			self.logError(f'Failed pairing device: {e}')
			return jsonify(error=str(e))


	### general myHome API
	@route('/load/')
	def load(self) -> str:
		result = dict()
		for _id, loc in self.LocationManager.locations.items():
			result[_id] = loc.asJson()
		return jsonify(result)


	@route('/save/', methods=['POST'])
	def save(self):
		try:
			tmp = request.get_json()
			# save to DB
			self.LocationManager.updateLocations(tmp)

			return jsonify(success=True)
		except Exception as e:
			self.logError(f'Failed saving house map: {e}')
			return jsonify(success=False)
