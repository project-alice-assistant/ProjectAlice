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
		req_data = request.form.to_dict()
		return jsonify(self.LocationManager.addNewLocation(req_data['name']).id)


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


	@route('/deviceType/getList')
	def deviceType_getList(self):
		res = []
		for parentName, deviceList in self.SkillManager.deviceTypes.items():
			res.extend([{'skillName' : parentName, 'deviceType' : device} for device in deviceList])
		return jsonify(res)


### Device API
	@route('/Device/getList')
	def device_getList(self):
		self.logInfo(self.DeviceManager.devices)
		# uid, name, deviceType, room, lastContact, positioning
		# TODO this can't be the real way.....
		res = ""
		for d in self.DeviceManager.devices.values():
			res+=d.data
		return res

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


	@route('/Device/<path:id>/addLink/<path:roomid>', methods = ['POST'])
	def addDeviceLink(self, id: str, roomid: str):
		try:
			id = int(id)
			roomid = int(roomid)
			if roomid == 0:
				raise Exception('No valid room ID supplied')
			else:
				self.DeviceManager.addLink(id=id,roomid=roomid)
				pass
		except Exception as e:
			self.logError(f'Failed adding room/device Link: {e}')


	@route('/Device/<path:id>/deleteLink/<path:roomid>', methods = ['POST'])
	def deleteDeviceLink(self, id: str, roomid: str):
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
			self.logError(f'Failed deleting room/device Link: {e}')


### general myHome API
	@route('/load/')
	def load(self) -> str:
		result = dict()
		for id, loc in self.LocationManager._locations.items():
			result[id] = loc.asJson()
		return jsonify(result)


	def put(self):
		try:
			data = json.loads(request.form['data'])

			# save to DB
			self.LocationManager.updateLocations(data)

			return jsonify(success=True)
		except Exception as e:
			self.logError(f'Failed saving house map: {e}')
			return jsonify(success=False)
