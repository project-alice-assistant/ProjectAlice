import json
from pathlib import Path

from flask import jsonify, render_template, request, send_from_directory
from flask_classful import route

from core.interface.model.View import View
from main import exceptionListener


class MyHomeView(View):
	route_base = '/myhome/'

	def index(self):
		return render_template(template_name_or_list='myHome.html',
		                       langData=self._langData,
		                       aliceSettings=self.ConfigManager.aliceConfigurations)

### Location API
	@route('/Location/<path:id>/getSettings', methods = ['POST'])
	def getLocationSettings(self, id: str):
		try:
			id = int(id)
			return jsonify(self.LocationManager.getSettings(id))
		except Exception as e:
			self.logError(f'Failed loading settings: {e}')
			return jsonify(sucess=False)


	@route('/Location/<path:id>/deleteSynonym', methods = ['POST'])
	def deleteLocationSynonym(self, id: str):
		try:
			id = int(id)
			req_data = request.form.to_dict()
			self.logInfo(f'trying to delete {req_data} for {id}')
			return jsonify(self.LocationManager.deleteLocationSynonym(id, req_data['value']))
		except Exception as e:
			self.logError(f'Failed deleting synonym: {e}')
			return jsonify(sucess=False)

	@route('/Location/<path:id>/addSynonym', methods = ['POST'])
	def addLocationSynonym(self, id: str):
		#todo check duplicates (with other rooms as well!)
		try:
			id = int(id)
			req_data = request.form.to_dict()
			self.logInfo(f'trying to add {req_data} for {id}')
			return jsonify(self.LocationManager.addLocationSynonym(id, req_data['value']))
		except Exception as e:
			self.logError(f'Failed adding synonym: {e}')
			return jsonify(sucess=False)

	@route('/Location/0/add', methods = ['POST'])
	def addLocation(self):
		try:
			req_data = request.form.to_dict()
			return jsonify(id=self.LocationManager.addNewLocation(req_data['name']).id)
		except Exception as e:
			return jsonify(error=str(e))

	@route('/Location/<path:id>/delete', methods = ['POST'])
	def deleteLocation(self,id: str):
		id = int(id)
		return jsonify(self.LocationManager.deleteLocation(id))

### Device Type API
	@route('/deviceType_static/<path:filename>')
	def deviceType_static(self, filename: str):
		parent, fileType, filename = filename.split('/')
		self.logInfo(f'../../skills/{parent}/device/{fileType}/{filename}')
		return send_from_directory(f'{self.WebInterfaceManager.app.root_path}/../../skills/{parent}/device/{fileType}/', filename)


	@route('/DeviceType/getList')
	def deviceType_getList(self):
		res = [{'skill' : devobs.skill, 'deviceType' : devobs.name, 'id': id} for id, devobs in self.DeviceManager.deviceTypes.items()]
		return jsonify(res)


### Device API
	@route('/Device/0/add', methods=['POST'])
	def addDevice(self):
		try:
			req_data = request.form.to_dict()
			device = self.DeviceManager.addNewDevice(deviceTypeID=int(req_data['deviceTypeID']),locationID=int(req_data['locationID']))
			if not device:
				raise Exception(f'Device creation failed - please see log')
			deviceType = device.getDeviceType()
			return {'id': device.id, 'skill': deviceType.skill, 'deviceType': deviceType.name}
		except Exception as e:
			self.logError(f'Failed adding device: {e}')
			return jsonify(error=str(e))


	@route('/Device/<path:id>/delete', methods = ['POST'])
	def deleteDevice(self, id: int):
		try:
			id = int(id)
			self.DeviceManager.deleteDeviceID(deviceID=id)
			return jsonify(success=True)
		except Exception as e:
			self.logError(f'Failed deleting device: {e}')
			return jsonify(success=False)


	@route('/Device/<path:id>/getSettings/<path:roomid>', methods = ['POST'])
	def getDeviceRoomSettings(self, id: str, roomid: str):
		try:
			id = int(id)
			roomid = int(roomid)
			if roomid == 0:
				#todo get generic settings
				pass
			else:
				#todo get room dependent settings
				pass
		except Exception as e:
			self.logError(f'Failed getting device settings: {e}')


	@route('/Device/<path:id>/saveSettings/<path:roomid>', methods = ['POST'])
	def saveDeviceRoomSettings(self, id: str, roomid: str):
		try:
			id = int(id)
			roomid = int(roomid)
			if roomid == 0:
				#todo get generic settings
				pass
			else:
				#todo get room dependent settings
				pass
		except Exception as e:
			self.logError(f'Failed saving device settings: {e}')


	@route('/Device/<path:id>/toggle', methods = ['POST'])
	def toggleDevice(self):
		try:
			id = int(id)
			self.DeviceManager.getDeviceByID(id=id).toggle()
		except Exception as e:
			self.logError(f'Failed toggling device Link: {e}')


	@route('/Device/<path:id>/addLink/<path:roomid>', methods = ['POST'])
	def addDeviceLink(self, id: str, roomid: str):
		try:
			id = int(id)
			roomid = int(roomid)
			if roomid == 0:
				raise Exception('No valid room ID supplied')
			else:
				self.DeviceManager.addLink(id=id,roomid=roomid)
		except Exception as e:
			self.logError(f'Failed adding room/device Link: {e}')


	@route('/Device/<path:id>/deleteLink/<path:roomid>', methods = ['POST'])
	def deleteDeviceLink(self, id: str, roomid: str):
		try:
			id = int(id)
			roomid = int(roomid)
			if roomid == 0:
				raise Exception('No valid room ID supplied')
			else:
				linkID = self.DeviceManager.getLink(deviceID, locationID)
				self.DeviceManager.deleteLink(id=linkID)
		except Exception as e:
			self.logError(f'Failed deleting room/device Link: {e}')


	@route('/Device/<path:id>/pair', methods=['POST'])
	def pairDevice(self, id: str):
		try:
			id = int(id)
			device = self.DeviceManager.getDeviceByID(id=id)
			device.getDeviceType().discover(device=device)
			return jsonify(success=True)
		except Exception as e:
			self.logError(f'Failed pairing device: {e}')
			return jsonify(error=str(e))

	#todo send MQTT message out for changing the icon of a device
	# payload: image or link to image?
	# triggered by the deviceType class of the skills

### general myHome API
	@route('/load/')
	def load(self) -> str:
		result = dict()
		for id, loc in self.LocationManager._locations.items():
			result[id] = loc.asJson()
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
