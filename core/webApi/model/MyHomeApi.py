from pathlib import Path
from typing import Union

from flask import jsonify, request, send_from_directory
from flask_classful import route

from core.commons import constants
from core.device.model.Device import Device
from core.device.model.DeviceType import DeviceType
from core.webApi.model.Api import Api
from core.util.Decorators import ApiAuthenticated


class MyHomeApi(Api):
	route_base = f'/api/{Api.version()}/myHome/'


	def __init__(self):
		super().__init__()


	@route('/', methods=['GET'])
	def getData(self):
		try:
			return jsonify(data={
				'locations': {location.id: location.toDict() for location in self.LocationManager.locations.values()},
				'constructions': {construction.id: construction.toDict() for construction in self.LocationManager.constructions.values()},
				'furnitures': {furniture.id: furniture.toDict() for furniture in self.LocationManager.furnitures.values()},
				'devices': {device.id: device.toDict() for device in self.DeviceManager.devices.values()},
				'links': {link.id: link.toDict() for link in self.DeviceManager.deviceLinks.values()}
			})
		except:
			return jsonify(success=False)


	@route('/locations/<location>/', methods=['GET'])
	@ApiAuthenticated
	def getLocation(self, location: Union[int, str]):
		try:
			try:
				locId = int(location)
				location = self.LocationManager.getLocation(locId=locId)
				return jsonify(success=True, location=location.toDict())

			except ValueError:
				location = self.LocationManager.getLocation(locationName=location, locationSynonym=location)
				if location:
					return jsonify(success=True, location=location.toDict())
				else:
					return jsonify(success=False, message=f'Location {location} could not be found')

		except Exception as e:
			self.logError(f'Something went wrong retrieving location {location} {e}')
			return jsonify(success=False, message=str(e))


	@route('/locations/', methods=['PUT'])
	@ApiAuthenticated
	def addLocation(self):
		try:
			location = self.LocationManager.addNewLocation(data=request.json)
			if location:
				return jsonify(location=location.toDict())
			else:
				return jsonify(success=False)
		except Exception as e:
			self.logError(f'Something went wrong creating a new location {e}')
			return jsonify(success=False)


	@route('/furniture/', methods=['PUT'])
	@ApiAuthenticated
	def addFurniture(self):
		try:
			furniture = self.LocationManager.addNewFurniture(data=request.json)
			if furniture:
				return jsonify(success=True, furniture=furniture.toDict())
			else:
				return jsonify(success=False, message='No Furniture could be added')
		except Exception as e:
			self.logError(f'Something went wrong creating a new furniture {e}')
			return jsonify(success=False, message=str(e))


	@route('/constructions/', methods=['PUT'])
	@ApiAuthenticated
	def addConstruction(self):
		try:
			construction = self.LocationManager.addNewConstruction(data=request.json)
			if construction:
				return jsonify(success=True, construction=construction.toDict())
			else:
				return jsonify(success=False, message='Construction could not be added')
		except Exception as e:
			self.logError(f'Something went wrong creating a new construction {e}')
			return jsonify(success=False, message=str(e))


	@route('/locations/<locationId>/', methods=['PATCH'])
	@ApiAuthenticated
	def updateLocation(self, locationId: str):
		try:
			return jsonify(success=self.LocationManager.updateLocation(int(locationId), request.json).toDict())
		except Exception as e:
			self.logError(f'Failed saving location {e}')
			return jsonify(success=False)


	@route('/furniture/<furnitureId>/', methods=['PATCH'])
	@ApiAuthenticated
	def updateFurniture(self, furnitureId: str):
		try:
			return jsonify(success=self.LocationManager.updateFurniture(int(furnitureId), request.json).toDict())
		except Exception as e:
			self.logError(f'Failed saving furniture {e}')
			return jsonify(success=False)


	@route('/constructions/<constructionId>/', methods=['PATCH'])
	@ApiAuthenticated
	def updateConstruction(self, constructionId: str):
		try:
			return jsonify(success=self.LocationManager.updateConstruction(int(constructionId), request.json).toDict())
		except Exception as e:
			self.logError(f'Failed saving construction {e}')
			return jsonify(success=False)


	@route('/devices/<deviceId>/', methods=['PATCH'])
	@ApiAuthenticated
	def updateDevice(self, deviceId: str):
		try:
			device = self.DeviceManager.updateDeviceSettings(int(deviceId), request.json)
			return jsonify(success=True, device=device.toDict(), links={link.id: link.toDict() for link in device.getLinks().values()})
		except Exception as e:
			self.logError(f'Failed saving device: {e}')
			return jsonify(success=False)


	@route('/locations/<locationId>/', methods=['DELETE'])
	@ApiAuthenticated
	def deleteLocation(self, locationId: str):
		"""
		Delete requested location and any associated furniture or constructions, providing it is NOT
		LocationId number 1. (the default and required location) .
		"""
		if int(locationId) == 1:
			self.logError('This is the default location, you are not able to delete it.')
			return jsonify(success=False)

		try:
			self.LocationManager.deleteLocation(int(locationId))
			return jsonify(success=True)
		except Exception as e:
			self.logError(f'Failed deleting location {e}')
			return jsonify(success=False)


	@route('/furniture/<furnitureId>/', methods=['DELETE'])
	@ApiAuthenticated
	def deleteFurniture(self, furnitureId: str):
		try:
			self.LocationManager.deleteFurniture(int(furnitureId))
			return jsonify(success=True)
		except Exception as e:
			self.logError(f'Failed deleting furniture {e}')
			return jsonify(success=False)


	@route('/constructions/<constructionId>/', methods=['DELETE'])
	@ApiAuthenticated
	def deleteConstruction(self, constructionId: str):
		try:
			self.LocationManager.deleteConstruction(int(constructionId))
			return jsonify(success=True)
		except Exception as e:
			self.logError(f'Failed deleting construction {e}')
			return jsonify(success=False)


	@route('/devices/<deviceId>/', methods=['DELETE'])
	@ApiAuthenticated
	def deleteDevice(self, deviceId: str):
		try:
			self.DeviceManager.deleteDevice(deviceId=int(deviceId))
			return jsonify(success=True)
		except Exception as e:
			self.logError(f'Failed deleting device {e}')
			return jsonify(success=False)


	@route('/locations/floors/', methods=['GET'])
	def getFloorsList(self):
		try:
			return jsonify(data=[image.stem for image in Path(self.Commons.rootDir(), 'core/webApi/static/images/floors/').glob(f'*{constants.PNG_EXT}')])
		except:
			return jsonify(success=False)


	@route('/furniture/tiles/', methods=['GET'])
	def getFurnitureList(self):
		try:
			return jsonify(data=[image.stem for image in Path(self.Commons.rootDir(), 'core/webApi/static/images/furniture/').glob(f'*{constants.PNG_EXT}')])
		except:
			return jsonify(success=False)


	@route('/constructions/tiles/', methods=['GET'])
	def getConstructionList(self):
		try:
			return jsonify(data=[image.stem for image in Path(self.Commons.rootDir(), 'core/webApi/static/images/constructions/').glob(f'*{constants.PNG_EXT}')])
		except:
			return jsonify(success=False)


	@route('/locations/floors/<imageId>.png', methods=['GET'])
	def getFloor(self, imageId: str):
		try:
			return send_from_directory('static/images/floors', f'{imageId}{constants.PNG_EXT}')
		except:
			return jsonify(success=False)


	@route('/furniture/<imageId>.png', methods=['GET'])
	def getFurniture(self, imageId: str):
		try:
			return send_from_directory('static/images/furniture', f'{imageId}{constants.PNG_EXT}')
		except:
			return jsonify(success=False)


	@route('/constructions/<imageId>.png', methods=['GET'])
	def getConstruction(self, imageId: str):
		try:
			return send_from_directory('static/images/constructions', f'{imageId}{constants.PNG_EXT}')
		except:
			return jsonify(success=False)


	@route('/devices/<deviceId>/<_rndStr>/device.png', methods=['GET'])
	def getDeviceIcon(self, _rndStr: str, deviceId: str):
		"""
		Returns the icon of a device.
		:param _rndStr: Is only used to bypass browser caching
		:param deviceId:
		:return:
		"""
		try:
			device: Device = self.DeviceManager.getDevice(deviceId=int(deviceId))
			file = device.getDeviceIcon()
			return send_from_directory(file.parent, f'{file.stem}{constants.PNG_EXT}')
		except Exception as e:
			self.logError(f'Failed to retrieve the ![yellow]("{device.displayName}") icon with path of ![yellow]("{file}") :{e}') #NOSONAR
			file = Path(self.Commons.rootDir(), 'core/webApi/static/images/missing-icon.png')
			return send_from_directory(file.parent, f'{file.stem}{constants.PNG_EXT}')


	@route('/devices/', methods=['PUT'])
	@ApiAuthenticated
	def addDevice(self):
		try:
			device = self.DeviceManager.addNewDeviceFromWebUI(data=request.json)
			if device:
				return jsonify(success=True, device=device.toDict(), link={link.id: link.toDict() for link in device.getLinks().values()})
			else:
				return jsonify(success=False, message='Failed adding Device!')
		except Exception as e:
			self.logError(f'Failed adding new device {e}')
			return jsonify(success=False, message=f'Failed adding new device {e}')


	@route('/deviceLinks/', methods=['PUT'])
	@ApiAuthenticated
	def addDeviceLink(self):
		"""
		 API method for creating a device link from a given deviceId to a targetLocation
		:return: json object with success value and the created link or message containing an error message
		"""
		try:
			link = self.DeviceManager.addDeviceLink(targetLocation=request.json.get('targetLocation'), deviceId=request.json.get('deviceId'))
			if link:
				return jsonify(success=True, link=link.toDict())
			else:
				raise Exception(f'Failed adding device with unknown error.')
		except Exception as e:
			self.logError(f'Failed adding new device link {e}')
			return jsonify(success=False, message=str(e))


	@route('/deviceLinks/', methods=['DELETE'])
	@ApiAuthenticated
	def removeDeviceLink(self):
		"""
		API method for deleting an existing device link to a location
		:return: success value and error mesasge
		"""
		try:
			self.DeviceManager.deleteDeviceLinks(deviceId=request.json.get('deviceId'), targetLocationId=request.json.get('targetLocation'))
			return jsonify(success=True)
		except Exception as e:
			self.logError(f'Failed deleting device link {e}')
			return jsonify(success=False, message=str(e))


	@route('/devices/<deviceId>/onClick/', methods=['GET'])
	@ApiAuthenticated
	def deviceClick(self, deviceId: str):
		try:
			device = self.DeviceManager.getDevice(deviceId=int(deviceId))
			if not device:
				raise Exception('No matching device found')

			ret = device.onUIClick()
			if not ret:
				raise Exception('Device did not return any ClickReaction')

			return jsonify(success=True, ret=ret)
		except Exception as e:
			self.logError(f'Failed device on click {e}')
			return jsonify(success=False, message=str(e))


	@route('/deviceTypes/', methods=['GET'])
	def getDeviceTypes(self):
		try:
			data = dict()
			for skillName, deviceType in self.DeviceManager.deviceTypes.items():
				data.setdefault(skillName, list())
				data[skillName] = [dType.toDict() for dType in deviceType.values()]

			return jsonify(types=data)
		except Exception as e:
			self.logError(f'Cannot return device type list {e}')
			return jsonify(success=False)


	@route('/deviceTypes/<skillName>/<deviceType>.png', methods=['GET'])
	def getDeviceTypeIcon(self, skillName: str, deviceType: str):
		try:
			dType: DeviceType = self.DeviceManager.getDeviceType(skillName=skillName, deviceType=deviceType)
			file = dType.getDeviceTypeIcon()
			return send_from_directory(file.parent, f'{file.stem}{constants.PNG_EXT}')
		except Exception as e:
			self.logError(f'Failed retrieving device type icon {e}')
			file = Path(self.Commons.rootDir(), 'core/webApi/static/images/missing-icon.png')
			return send_from_directory(file.parent, f'{file.stem}{constants.PNG_EXT}')


	@route('/devices/<deviceId>/reply/', methods=['POST'])
	@ApiAuthenticated
	def deviceReply(self, deviceId: str):
		try:
			self.DeviceManager.getDevice(deviceId=int(deviceId)).onDeviceUIReply(request.json)
			return jsonify(success=True)
		except Exception as e:
			self.logError(f'Cannot return device type list {e}')
			return jsonify(success=False, message=f'Device not found {e}')
