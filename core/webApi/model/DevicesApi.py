from flask import jsonify, request
from flask_classful import route

from core.util.Decorators import ApiAuthenticated
from core.webApi.model.Api import Api


class DevicesApi(Api):
	route_base = f'/api/{Api.version()}/devices/'


	@route('/<uid>/hello/', methods=['GET'])
	def hello(self, uid: str) -> dict:
		try:
			device = self.DeviceManager.getDevice(uid=uid)
			if not device:
				return jsonify(success=True, reply='unknownDevice')
			else:
				self.DeviceManager.deviceConnecting(uid)
				return jsonify(success=True, deviceId=device.id)

		except Exception as e:
			self.logError(f'Error for device Hello {e}')
			return jsonify(success=False, message=str(e))


	@route('/<uid>/bye/', methods=['GET'])
	def bye(self, uid: str) -> dict:
		try:
			device = self.DeviceManager.getDevice(uid=uid)
			if not device:
				return jsonify(success=True, reply='unknownDevice')
			else:
				self.DeviceManager.deviceDisconnecting(uid)
				return jsonify(success=True)

		except Exception as e:
			self.logError(f'Error for device Bye {e}')
			return jsonify(success=False, message=str(e))


	@route('/<uid>/', methods=['PUT'])
	@ApiAuthenticated
	def addDevice(self, uid: str) -> dict:
		try:
			device = self.DeviceManager.addNewDevice(
				deviceType=request.json.get('deviceType'),
				skillName=request.json.get('skillName'),
				locationId=request.json.get('locationId', None),
				uid=uid,
				abilities=request.json.get('abilities', None),
				displaySettings=request.json.get('displaySettings', None),
				deviceParam=request.json.get('deviceParam', None),
				displayName=request.json.get('displayName', None),
				noChecks=False
			)
			if device:
				return jsonify(success=True, device=device.toDict())
			else:
				raise Exception('Device creation failed')
		except Exception as e:
			self.logError(f'Error adding new device {e}')
			return jsonify(success=False, message=str(e))
