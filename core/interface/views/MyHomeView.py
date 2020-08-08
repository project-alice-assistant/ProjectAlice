import json

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
	@route('/Location/<path:_id>/getSettings', methods=['GET'])
	def getLocationSettings(self, _id: str):
		try:
			_id = int(_id)
			return jsonify(self.LocationManager.getSettings(_id))
		except Exception as e:
			self.logError(f'Failed loading settings: {e}')
			return jsonify(success=False)


	@route('/Location/<path:_id>/deleteSynonym', methods=['POST'])
	def deleteLocationSynonym(self, _id: str):
		try:
			_id = int(_id)
			data = request.form.to_dict()
			self.logInfo(f'Deleting {data} for {_id}')
			return jsonify(self.LocationManager.deleteLocationSynonym(_id, data['value']))
		except Exception as e:
			self.logError(f'Failed deleting synonym: {e}')
			return jsonify(success=False)


	@route('/Location/<path:_id>/addSynonym', methods=['POST'])
	def addLocationSynonym(self, _id: str):
		try:
			_id = int(_id)
			data = request.form.to_dict()
			self.logInfo(f'Adding {data} for {_id}')
			self.LocationManager.addLocationSynonym(_id, data['value'])
			return jsonify(success=True)
		except Exception as e:
			self.logError(f'Failed adding synonym: {e}')
			return jsonify(success=False, error=str(e))


	# TODO Consider using PUT method?
	@route('/Location/0/add', methods=['POST'])
	def addLocation(self):
		try:
			data = request.form.to_dict()
			return jsonify(id=self.LocationManager.addNewLocation(data['name']).id)
		except Exception as e:
			return jsonify(success=False, error=str(e))


	# TODO consider using DELETE method?
	@route('/Location/<path:_id>/delete', methods=['POST'])
	def deleteLocation(self, _id: str):
		_id = int(_id)
		return jsonify(self.LocationManager.deleteLocation(_id))


	### Device Type API
	@route('/deviceType_static/<path:filename>')
	def deviceType_static(self, filename: str):
		parent, fileType, filename = filename.split('/')
		return send_from_directory(f'{self.WebInterfaceManager.app.root_path}/../../skills/{parent}/device/{fileType}/', filename)


	@route('/DeviceType/getList')
	def deviceType_getList(self):
		res = [{'skill': devobs.skill, 'deviceType': devobs.name, 'id': _id} for _id, devobs in self.DeviceManager.deviceTypes.items()]
		return jsonify(res)


	### Device API
	@route('/Device/0/add', methods=['POST'])
	def addDevice(self):
		try:
			data = request.form.to_dict()
			device = self.DeviceManager.addNewDevice(deviceTypeId=int(data['deviceTypeID']), locationId=int(data['locationID']))
			if not device:
				raise Exception(f'Device creation failed - please see log')
			deviceType = device.getDeviceType()
			return {'id': device.id, 'skill': deviceType.skill, 'deviceType': deviceType.name}
		except Exception as e:
			self.logError(f'Failed adding device: {e}')
			return jsonify(success=False, error=str(e))


	@route('/Device/<path:_id>/changeLocation/<path:roomid>', methods=['POST'])
	def changeLocation(self, _id: str, roomid: str):
		try:
			_id = int(_id)
			device = self.DeviceManager.getDeviceById(_id=_id)
			roomid = int(roomid)
			if roomid == 0:
				return jsonify(success=False, error="No Location provided")
			else:
				self.DeviceManager.changeLocation(device=device, locationId=roomid)
				return jsonify(success=True)
		except Exception as e:
			self.logError(f'Failed changing location: {e}')


	# TODO consider using DELETE method? (will blow up jquery, because only get/post have shortcut methods)
	@route('/Device/<path:_id>/delete', methods=['POST'])
	def deleteDevice(self, _id: int):
		try:
			_id = int(_id)
			self.DeviceManager.deleteDeviceID(deviceId=_id)
			return jsonify(success=True)
		except Exception as e:
			self.logError(f'Failed deleting device: {e}')
			return jsonify(success=False, error=str(e))


	@route('/Device/<path:_id>/getSettings/<path:roomid>', methods=['GET'])
	def getDeviceSettings(self, _id: str, roomid: str):
		try:
			_id = int(_id)
			device = self.DeviceManager.getDeviceById(_id=_id)
			roomid = int(roomid)
			if roomid == 0:
				if not device.devSettings:
					device.devSettings = device.getDeviceType().DEV_SETTINGS.copy()
				return jsonify(device.devSettings)
			else:
				link = self.DeviceManager.getLink(deviceId=_id, locationId=roomid)
				return jsonify(link.locSettings)
		except Exception as e:
			self.logError(f'Failed getting device settings: {e}')


	#TODO consider using UPDATE method?
	@route('/Device/<path:_id>/saveSettings/<path:roomid>', methods=['POST'])
	def saveDeviceSettings(self, _id: str, roomid: str):
		try:
			confs = {key: value for key, value in request.form.items()}
			_id = int(_id)
			device = self.DeviceManager.getDeviceById(_id=_id)
			roomid = int(roomid)
			if roomid == 0:
				device.devSettings = confs
				device.saveDevSettings()
				return jsonify(success=True)

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
			custResult = self.DeviceManager.getDeviceById(_id).toggle()
			if custResult:
				return custResult
			return jsonify(success=True)
		except Exception as e:
			self.logError(f'Failed toggling device Link: {e}')
			return jsonify(success=False)


	@route('/Device/<path:_id>/getLinks', methods=['GET'])
	def getLinks(self, _id: str ):
		try:
			_id = int(_id)
			device = self.DeviceManager.getDeviceById(_id=_id)
			links = self.DeviceManager.getLinksForDevice(device=device)
			return json.dumps([link.asJson() for link in links])
		except Exception as e:
			self.logError(f'Error while loading Links: {e}')
			return jsonify(error=f'Error while loading Links: {e}')


	@route('/Device/<path:_id>/removeLink/<path:roomid>', methods=['POST'])
	def removeDeviceLink(self, _id: str, roomid: str):
		try:
			_id = int(_id)
			roomid = int(roomid)
			if roomid == 0:
				raise Exception('No valid room ID supplied')
			else:
				self.DeviceManager.deleteLink(deviceId=_id, locationId=roomid)
			return jsonify(success=True)
		except Exception as e:
			self.logError(f'Failed removing room/device Link: {e}')
			return jsonify(error=f'Failed removing room/device Link: {e}')


	@route('/Device/<path:_id>/addLink/<path:roomid>', methods=['POST'])
	def addDeviceLink(self, _id: str, roomid: str):
		try:
			_id = int(_id)
			roomid = int(roomid)
			if roomid == 0:
				raise Exception('No valid room ID supplied')
			else:
				self.DeviceManager.addLink(deviceId=_id, locationId=roomid)
			return jsonify(success=True)
		except Exception as e:
			self.logError(f'Failed adding room/device Link: {e}')
			return jsonify(error=f'Failed adding room/device Link: {e}')


	@route('/Device/u/<path:_uid>/icon', methods=['GET'])
	def getIconUID(self, _uid: str):
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
