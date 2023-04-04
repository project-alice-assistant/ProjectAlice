#  Copyright (c) 2021
#
#  This file, MyHomeApi.py, is part of Project Alice.
#
#  Project Alice is free software: you can redistribute it and/or modify
#  it under the terms of the GNU General Public License as published by
#  the Free Software Foundation, either version 3 of the License, or
#  (at your option) any later version.
#
#  This program is distributed in the hope that it will be useful,
#  but WITHOUT ANY WARRANTY; without even the implied warranty of
#  MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#  GNU General Public License for more details.
#
#  You should have received a copy of the GNU General Public License
#  along with this program.  If not, see <https://www.gnu.org/licenses/>
#
#  Last modified: 2021.04.13 at 12:56:49 CEST
import time
from flask import Response, jsonify, make_response, request, send_from_directory
from flask_classful import route
from pathlib import Path
from typing import Optional, Union
from werkzeug.datastructures import FileStorage

from core.commons import constants
from core.device.model.Device import Device
from core.device.model.DeviceType import DeviceType
from core.util.Decorators import ApiAuthenticated
from core.webApi.model.Api import Api


class MyHomeApi(Api):
	route_base = f'/api/{Api.version()}/myHome/'


	def __init__(self):
		super().__init__()


	# noinspection PyMethodMayBeStatic
	def fileCheck(self) -> Optional[FileStorage]:
		if 'newTile' not in request.files:
			return None
		else:
			ffile = request.files['newTile']
			if not ffile.filename:
				return None
			if not '.' in ffile.filename or ffile.filename.rsplit('.', 1)[1].lower() != 'png':
				return None
			return ffile


	@route('/', methods=['GET'])
	def getData(self) -> Response:
		try:
			return jsonify(data={
				'locations'    : {location.id: location.toDict() for location in self.LocationManager.locations.values()},
				'constructions': {construction.id: construction.toDict() for construction in self.LocationManager.constructions.values()},
				'furnitures'   : {furniture.id: furniture.toDict() for furniture in self.LocationManager.furnitures.values()},
				'devices'      : {device.id: device.toDict() for device in self.DeviceManager.devices.values()},
				'links'        : {link.id: link.toDict() for link in self.DeviceManager.deviceLinks.values()}
			})
		except:
			return jsonify(success=False)


	@route('/locations/<location>/', methods=['GET'])
	@ApiAuthenticated
	def getLocation(self, location: Union[int, str]) -> Response:
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
	def addLocation(self) -> Response:
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
	def addFurniture(self) -> Response:
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
	def addConstruction(self) -> Response:
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
	def updateLocation(self, locationId: str) -> Response:
		try:
			return jsonify(success=self.LocationManager.updateLocation(int(locationId), request.json).toDict())
		except Exception as e:
			self.logError(f'Failed saving location {e}')
			return jsonify(success=False)


	@route('/furniture/<furnitureId>/', methods=['PATCH'])
	@ApiAuthenticated
	def updateFurniture(self, furnitureId: str) -> Response:
		try:
			return jsonify(success=self.LocationManager.updateFurniture(int(furnitureId), request.json).toDict())
		except Exception as e:
			self.logError(f'Failed saving furniture {e}')
			return jsonify(success=False)


	@route('/constructions/<constructionId>/', methods=['PATCH'])
	@ApiAuthenticated
	def updateConstruction(self, constructionId: str) -> Response:
		try:
			return jsonify(success=self.LocationManager.updateConstruction(int(constructionId), request.json).toDict())
		except Exception as e:
			self.logError(f'Failed saving construction {e}')
			return jsonify(success=False)


	@route('/devices/<deviceId>/', methods=['PATCH'])
	@ApiAuthenticated
	def updateDevice(self, deviceId: str) -> Response:
		try:
			device = self.DeviceManager.updateDeviceSettings(int(deviceId), request.json)
			return jsonify(success=True, device=device.toDict(), links={link.id: link.toDict() for link in device.getLinks().values()})
		except Exception as e:
			self.logError(f'Failed saving device: {e}')
			return jsonify(success=False)


	@route('/locations/<locationId>/', methods=['DELETE'])
	@ApiAuthenticated
	def deleteLocation(self, locationId: str) -> Response:
		"""
		Delete requested location and any associated furniture or constructions, providing it is NOT
		LocationId number 1. (the default and required location) .
		"""
		if int(locationId) == 1:
			self.logWarning('Cannot delete location id 1')
			return jsonify(success=False, message="Cannot delete location id 1")

		try:
			self.LocationManager.deleteLocation(int(locationId))
			return jsonify(success=True)
		except Exception as e:
			self.logError(f'Failed deleting location {e}')
			return jsonify(success=False)


	@route('/furniture/<furnitureId>/', methods=['DELETE'])
	@ApiAuthenticated
	def deleteFurniture(self, furnitureId: str) -> Response:
		try:
			self.LocationManager.deleteFurniture(int(furnitureId))
			return jsonify(success=True)
		except Exception as e:
			self.logError(f'Failed deleting furniture {e}')
			return jsonify(success=False)


	@route('/constructions/<constructionId>/', methods=['DELETE'])
	@ApiAuthenticated
	def deleteConstruction(self, constructionId: str) -> Response:
		try:
			self.LocationManager.deleteConstruction(int(constructionId))
			return jsonify(success=True)
		except Exception as e:
			self.logError(f'Failed deleting construction {e}')
			return jsonify(success=False)


	@route('/devices/<deviceId>/', methods=['DELETE'])
	@ApiAuthenticated
	def deleteDevice(self, deviceId: str) -> Response:
		try:
			self.DeviceManager.deleteDevice(deviceId=int(deviceId))
			return jsonify(success=True)
		except Exception as e:
			self.logError(f'Failed deleting device {e}')
			return jsonify(success=False)


	@route('/locations/floors/', methods=['GET'])
	def getFloorsList(self) -> Response:
		try:
			return jsonify(data=[image.stem for image in Path(self.Commons.rootDir(), 'core/webApi/static/images/floors/').glob(f'*{constants.PNG_EXT}')])
		except:
			return jsonify(success=False)


	@route('/furniture/tiles/', methods=['GET'])
	def getFurnitureList(self) -> Response:
		try:
			return jsonify(data=[image.stem for image in Path(self.Commons.rootDir(), 'core/webApi/static/images/furniture/').glob(f'*{constants.PNG_EXT}')])
		except:
			return jsonify(success=False)


	@route('/constructions/tiles/', methods=['GET'])
	def getConstructionList(self) -> Response:
		try:
			return jsonify(data=[image.stem for image in Path(self.Commons.rootDir(), 'core/webApi/static/images/constructions/').glob(f'*{constants.PNG_EXT}')])
		except:
			return jsonify(success=False)


	@route('/locations/floors/<imageId>.png', methods=['GET'])
	def getFloor(self, imageId: str) -> Response:
		try:
			return send_from_directory('static/images/floors', f'{imageId}{constants.PNG_EXT}')
		except:
			return jsonify(success=False)


	# noinspection PyMethodMayBeStatic
	def incompatibleFile(self) -> Response:
		return jsonify(success=False, message='Incompatible file')


	@route('/locations/floor/', methods=['PUT'])
	@ApiAuthenticated
	def addFloorTile(self) -> Response:
		try:
			ffile = self.fileCheck()
			if not ffile:
				return self.incompatibleFile()
			else:
				ffile.save(f'{self.Commons.rootDir()}/core/webApi/static/images/floors/0000_{int(time.time())}.png')
				return jsonify(success=True)
		except Exception as e:
			self.logError('Error saving new floor tile:', str(e))
			return jsonify(success=False, message=str(e))


	@route('/furniture/<imageId>.png', methods=['GET'])
	def getFurniture(self, imageId: str) -> Response:
		try:
			return send_from_directory('static/images/furniture', f'{imageId}{constants.PNG_EXT}')
		except:
			return jsonify(success=False)


	@route('/locations/furniture/', methods=['PUT'])
	@ApiAuthenticated
	def addFurnitureTile(self) -> Response:
		# noinspection DuplicatedCode
		try:
			ffile = self.fileCheck()
			if not ffile:
				return self.incompatibleFile()
			else:
				ffile.save(f'{self.Commons.rootDir()}/core/webApi/static/images/furniture/0000_{int(time.time())}.png')
				return jsonify(success=True)
		except Exception as e:
			return jsonify(success=False, message=str(e))


	@route('/constructions/<imageId>.png', methods=['GET'])
	def getConstruction(self, imageId: str) -> Response:
		try:
			return send_from_directory('static/images/constructions', f'{imageId}{constants.PNG_EXT}')
		except:
			return jsonify(success=False)


	@route('/locations/construction/', methods=['PUT'])
	@ApiAuthenticated
	def addConstructionTile(self) -> Response:
		# noinspection DuplicatedCode
		try:
			ffile = self.fileCheck()
			if not ffile:
				return self.incompatibleFile()
			else:
				ffile.save(f'{self.Commons.rootDir()}/core/webApi/static/images/constructions/0000_{int(time.time())}.png')
				return jsonify(success=True)
		except Exception as e:
			return jsonify(success=False, message=str(e))


	# noinspection PyUnusedLocal
	@route('/devices/<deviceId>/<etag>/device.png', methods=['GET'])
	def getDeviceIcon(self, deviceId: str, etag: str) -> Response:
		"""
		Returns the icon of a device.
		:param deviceId:
		:param etag: Is only used by the browser caching mechanisms
		:return:
		"""
		ffile = None
		try:
			device: Device = self.DeviceManager.getDevice(deviceId=int(deviceId))
			if not device:
				raise Exception('Device not found - maybe not yet loaded (Alice Startup?)')
			ffile = device.getDeviceIcon()
			response = make_response(send_from_directory(ffile.parent, f'{ffile.name}'))
			response.headers.add('Access-Control-Allow-Headers', 'x-etag')
			response.headers.add('x-etag', device.etag)
			return response
		except Exception as e:
			self.logError(f'{e}')
			self.logError(f'Failed to retrieve icon for device id **{deviceId}** ({ffile if ffile else "error while getting filename"}) :{e}')  # NOSONAR
			ffile = Path(self.Commons.rootDir(), 'core/webApi/static/images/missing-icon.png')
			return send_from_directory(ffile.parent, f'{ffile.stem}{constants.PNG_EXT}')


	@route('/devices/', methods=['PUT'])
	@ApiAuthenticated
	def addDevice(self) -> Response:
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
	def addDeviceLink(self) -> Response:
		"""
		 API method for creating a device link from a given deviceId to a targetLocation
		:return: json object with success value and the created link or message containing an error message
		"""
		try:
			link = self.DeviceManager.addDeviceLink(targetLocation=request.json.get('targetLocation'), deviceId=request.json.get('deviceId'))
			if link:
				return jsonify(success=True, link=link.toDict())
			else:
				raise Exception('Failed adding device with unknown error.')
		except Exception as e:
			self.logError(f'Failed adding new device link {e}')
			return jsonify(success=False, message=str(e))


	@route('/deviceLinks/', methods=['DELETE'])
	@ApiAuthenticated
	def removeDeviceLink(self) -> Response:
		"""
		API method for deleting an existing device link to a location
		:return: success value and error message
		"""
		try:
			self.DeviceManager.deleteDeviceLinks(deviceId=request.json.get('deviceId'), targetLocationId=request.json.get('targetLocation'))
			return jsonify(success=True)
		except Exception as e:
			self.logError(f'Failed deleting device link {e}')
			return jsonify(success=False, message=str(e))


	@route('/devices/<deviceId>/onClick/', methods=['GET'])
	@ApiAuthenticated
	def deviceClick(self, deviceId: str) -> Response:
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
	def getDeviceTypes(self) -> Response:
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
	def getDeviceTypeIcon(self, skillName: str, deviceType: str) -> Response:
		try:
			dType: DeviceType = self.DeviceManager.getDeviceType(skillName=skillName, deviceType=deviceType)
			ffile = dType.getDeviceTypeIcon()
			return send_from_directory(ffile.parent, f'{ffile.stem}{constants.PNG_EXT}')
		except Exception as e:
			self.logError(f'Failed retrieving device type icon {e}')
			ffile = Path(self.Commons.rootDir(), 'core/webApi/static/images/missing-icon.png')
			return send_from_directory(ffile.parent, f'{ffile.stem}{constants.PNG_EXT}')


	@route('/devices/<deviceId>/reply/', methods=['POST'])
	@ApiAuthenticated
	def deviceReply(self, deviceId: str) -> Response:
		try:
			self.DeviceManager.getDevice(deviceId=int(deviceId)).onDeviceUIReply(request.json)
			return jsonify(success=True)
		except Exception as e:
			self.logError(f'Cannot return device type list {e}')
			return jsonify(success=False, message=f'Device not found {e}')
