import importlib
import json
import socket
import threading
import time
import uuid
from random import shuffle
from typing import Dict, List, Optional, Union

from paho.mqtt.client import MQTTMessage
from serial.tools import list_ports

from core.base.model.Manager import Manager
from core.commons import constants
from core.device.model.Device import Device
from core.device.model.DeviceAbility import DeviceAbility
from core.device.model.DeviceException import DeviceTypeUndefined, MaxDeviceOfTypeReached, MaxDevicePerLocationReached
from core.device.model.DeviceLink import DeviceLink
from core.device.model.DeviceType import DeviceType
from core.device.model.Heartbeat import Heartbeat
from core.myHome.model.Location import Location
from core.dialog.model.DialogSession import DialogSession


class DeviceManager(Manager):
	DB_DEVICE = 'devices'
	DB_LINKS = 'deviceLinks'
	DATABASE = {
		DB_DEVICE: [
			'id INTEGER PRIMARY KEY',
			'uid TEXT',
			'parentLocation INTEGER NOT NULL',
			'typeName TEXT NOT NULL',
			'skillName TEXT NOT NULL',
			'settings TEXT',
			'displayName TEXT',
			'deviceParams TEXT'
		],
		DB_LINKS : [
			'id INTEGER PRIMARY KEY',
			'deviceId INTEGER NOT NULL',
			'targetLocation INTEGER NOT NULL',
			'settings TEXT'
		]
	}


	def __init__(self):
		super().__init__(databaseSchema=self.DATABASE)

		self._devices: Dict[int, Device] = dict()
		self._deviceLinks: Dict[int, DeviceLink] = dict()
		self._deviceTypes: Dict[str, Dict[str, DeviceType]] = dict()

		self._heartbeats = dict()
		self._heartbeatsCheckTimer = None
		self._heartbeat: Optional[Heartbeat] = None

		self._broadcastFlag = threading.Event()
		self._listenSocket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
		self._listenSocket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
		self._listenSocket.settimeout(2)
		self._broadcastSocket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
		self._broadcastSocket.setsockopt(socket.SOL_SOCKET, socket.SO_BROADCAST, 1)
		self._broadcastSocket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
		self._broadcastPort = int(self.ConfigManager.getAliceConfigByName('newDeviceBroadcastPort'))  # Default 12354
		self._listenPort = self._broadcastPort + 1
		self._listenSocket.bind(('', self._listenPort))
		self._broadcastTimer = None


	def onStart(self):
		super().onStart()
		self.loadDevices()
		self.loadLinks()

		# Create the default core device if needed. Cannot be done in AliceCore skill due to load sequence
		device = self.getMainDevice()
		if not device:
			device = self.addNewDevice(deviceType='AliceCore', skillName='AliceCore', locationId=1)
			if not device:
				self.logFatal('Core unit device creation failed, cannot continue')
				return

			self.logInfo('Created main unit device')
			self.ConfigManager.updateAliceConfiguration('uuid', device.uid)


		if self.ConfigManager.getAliceConfigByName('disableSound') and self.ConfigManager.getAliceConfigByName('disableCapture'):
			device.setAbilities([DeviceAbility.IS_CORE]) #Remove default abilities
		elif self.ConfigManager.getAliceConfigByName('disableSound'):
			device.setAbilities([DeviceAbility.IS_CORE, DeviceAbility.CAPTURE_SOUND])
		elif self.ConfigManager.getAliceConfigByName('disableCapture'):
			device.setAbilities([DeviceAbility.IS_CORE, DeviceAbility.PLAY_SOUND])

		self.logInfo(f'Loaded **{len(self._devices)}** device instance', plural='instance')


	def onBooted(self):
		super().onBooted()

		self.MqttManager.publish(topic=constants.TOPIC_CORE_RECONNECTION)
		self.getMainDevice().connected = True

		if self._devices:
			self.ThreadManager.newThread(name='checkHeartbeats', target=self.checkHeartbeats)

		self._heartbeat = Heartbeat(device=self.getMainDevice())


	def onStop(self):
		super().onStop()

		self._stopBroadcasting()
		self._broadcastSocket.close()

		if self._heartbeat:
			self._heartbeat.stopHeartBeat()
		self.MqttManager.publish(topic=constants.TOPIC_CORE_DISCONNECTION)


	def loadDevices(self):
		"""
		Loads devices from database
		:return: None
		"""
		for row in self.databaseFetch(tableName=self.DB_DEVICE, method='all'):
			try:
				data = self.Commons.dictFromRow(row)
				skillImport = importlib.import_module(f'skills.{data.get("skillName")}.devices.{data.get("typeName")}')
				klass = getattr(skillImport, data.get('typeName'))
				device = klass(data)
				self._devices[device.id] = device
			except Exception as e:
				self.logError(f"Couldn't create device instance: {e}")


	def loadLinks(self):
		"""
		Loads location links from database
		:return: None
		"""
		for row in self.databaseFetch(tableName=self.DB_LINKS, method='all'):
			self._deviceLinks[row['id']] = DeviceLink(row)


	def checkHeartbeats(self):
		"""
		Routine that checks all heartbeats and disconnects devices that haven't signaled their presence for hearbeatRate time
		:return: None
		"""
		now = time.time()
		for uid, lastTime in self._heartbeats.copy().items():
			device = self.getDevice(uid=uid)
			if not device:
				self._heartbeats.pop(uid)
			else:
				if now - device.deviceType.heartbeatRate > lastTime:
					self.logWarning(f'Device **{device.displayName}** has not given a signal since {device.deviceType.heartbeatRate} seconds or more')
					self._heartbeats.pop(uid)
					device.connected = False
					self.MqttManager.publish(constants.TOPIC_DEVICE_UPDATED, payload={'uid': device.uid, 'type': 'status'})

		self._heartbeatsCheckTimer = self.ThreadManager.newTimer(interval=3, func=self.checkHeartbeats)


	def getDevice(self, deviceId: int = None, uid: str = None) -> Optional[Device]:
		"""
		Returns a Device with the provided id or uid, if any
		:param deviceId: The device id
		:param uid: The device uid
		:return: Device instance if any or None
		"""
		if deviceId:
			return self._devices.get(deviceId, None)
		elif uid:
			for device in self._devices.values():
				if device.uid == uid:
					return device
		else:
			raise Exception('Cannot get a device without id or uid')


	def registerDeviceType(self, skillName: str, data: dict):
		"""
		Registers a new DeviceType. The device type can be generic or skill specific if class present in skill
		:param skillName: The skill name owning that device type
		:param data: The DeviceType data as a dict
		:return: None
		"""
		data.setdefault('skillName', skillName)
		if not data.get('deviceTypeName') or not data.get('skillName'):
			self.logError('Cannot register new device type without a type name and a skill name')
			return

		# Try to create the device type, if overriden by the user, else fallback to default generic type
		try:
			skillImport = importlib.import_module(f'skills.{skillName}.device.type.{data.get("deviceTypeName")}')
			klass = getattr(skillImport, data.get('deviceTypeName'))
			deviceType = klass(data)
		except:
			try:
				deviceType = DeviceType(data)
			except Exception as e:
				self.logError(f"Couldn't create device type: {e}")
				return

		self._deviceTypes.setdefault(skillName.lower(), dict())
		self._deviceTypes[skillName.lower()].setdefault(data['deviceTypeName'].lower(), deviceType)


	def getDevicesWithAbilities(self, abilites: List[DeviceAbility], connectedOnly: bool = True) -> List[Device]:
		"""
		Returns a list of Device instances having AT LEAST the provided abilities
		:param abilites: A list of DeviceAbility the device must have
		:param connectedOnly: Wheather or not the devices should be connected to bee returned
		:return: A list of Device instances
		"""
		ret = list()
		for device in self._devices.values():
			if connectedOnly and not device.connected:
				continue

			if device.hasAbilities(abilites):
				ret.append(device)

		return ret


	def getDevicesByType(self, deviceType: DeviceType, connectedOnly: bool = True) -> List[Device]:
		"""
		Returns a list of devices that are of the given type from the given skill
		:param connectedOnly: Include or not devices that are not connected
		:param deviceType: DeeviceType
		:return: list of Device instances
		"""

		ret = list()
		for device in self._devices.values():
			if connectedOnly and not device.connected:
				continue

			if device.deviceType == deviceType:
				ret.append(device)

		return ret


	def getDevicesByLocation(self, locationId: int, deviceType: DeviceType = None, abilities: List[DeviceAbility] = None, connectedOnly: bool = True) -> List[Device]:
		"""
		Returns a list of devices fitting thee locationId and the optional arguments
		:param locationId: the location Id, only mandatory argument
		:param deviceType: The device type that must be
		:param abilities: The abilities the device has to have
		:param connectedOnly: Wheather or not to return non connected devices
		:return: list of Device instances
		"""
		return self._filterDevices(locationId=locationId, deviceType=deviceType, abilities=abilities, connectedOnly=connectedOnly)


	def getDevicesBySkill(self, skillName: str, deviceType: DeviceType = None, abilities: List[DeviceAbility] = None, connectedOnly: bool = True) -> List[Device]:
		"""
		Returns a list of devices fitting the skill name and the optional arguments
		:param skillName: the location Id, only mandatory argument
		:param deviceType: The device type that must be
		:param abilities: The abilities the device has to have
		:param connectedOnly: Wheather or not to return non connected devices
		:return: list of Device instances
		"""
		return self._filterDevices(skillName=skillName, deviceType=deviceType, abilities=abilities, connectedOnly=connectedOnly)


	def _filterDevices(self, locationId: int = None, skillName: str = None, deviceType: DeviceType = None, abilities: List[DeviceAbility] = None, connectedOnly: bool = True) -> List[Device]:
		"""
		Returns a list of devices fitting the optional arguments
		:param locationId: the location Id, only mandatory argument
		:param skillName: the skill the device belongs to
		:param deviceType: The device type that must be
		:param abilities: The abilities the device has to have
		:param connectedOnly: Wheather or not to return non connected devices
		:return: list of Device instances
		"""

		ret = list()
		for device in self._devices.values():
			if (locationId and device.parentLocation != locationId)\
			    or (skillName and device.skillName != skillName)\
				or (deviceType and device.deviceType != deviceType)\
				or (connectedOnly and not device.connected)\
				or (abilities and not device.hasAbilities(abilities)):
				continue

			ret.append(device)

		return ret


	def getDeviceType(self, skillName: str, deviceType: str) -> Optional[DeviceType]:
		"""
		Returns the DeviceType instance for the skillname and devicetype
		:param skillName: The skill name
		:param deviceType: The device type string
		:return: Device instance
		"""
		return self.deviceTypes.get(skillName.lower(), dict()).get(deviceType.lower(), None)


	def getMainDevice(self) -> Optional[Device]:
		"""
		Returns the main device, the only one having the IS_CORE ability
		:return: Device instance
		"""
		devices = self.getDevicesWithAbilities(abilites=[DeviceAbility.IS_CORE], connectedOnly=False)
		if not devices:
			return None

		return devices[0]


	def addNewDeviceFromWebUI(self, data: Dict) -> Optional[Device]:
		return self.addNewDevice(
			deviceType=data['deviceType'],
			skillName=data['skillName'],
			locationId=data['parentLocation'],
			uid=-1,
			displaySettings=data['settings'],
			displayName=data.get('displayName', '')
		)


	def addNewDevice(self, deviceType: str, skillName: str, locationId: int = 0, uid: Union[str, int] = None, abilities: List[DeviceAbility] = None, displaySettings: Dict = None, displayName: str = None, noChecks: bool = False) -> Optional[Device]:
		"""
		Adds a new device to Alice. The device is immediately saved in DB
		:param deviceType: the type of device, defined by each skill
		:param skillName: the skill this device belongs to
		:param locationId: the location id where the device is placed
		:param uid: the device uid
		:param abilities: a list of abilities for this device
		:param displaySettings: a dict of display settings, for the UI
		:param displayName: the ui display name
		:param noChecks: if true, no condition checks will apply
		:return: A Device instance or None if something failed
		"""

		if not noChecks:
			dType: DeviceType = self.getDeviceType(skillName=skillName, deviceType=deviceType)
			if not dType:
				self.logError(f'Cannot add device **{deviceType}**, device type not found!')
				raise DeviceTypeUndefined(deviceType)

			if 0 < dType.totalDeviceLimit <= len(self.getDevicesByType(deviceType=dType, connectedOnly=False)):
				raise MaxDeviceOfTypeReached(dType.totalDeviceLimit)

			if 0 < dType.perLocationLimit <= len(self.getDevicesByLocation(locationId, deviceType=dType, connectedOnly=False)):
				raise MaxDevicePerLocationReached(dType.perLocationLimit)


		if not displaySettings:
			if locationId == 0:
				displaySettings = {
					'x': 50000,
					'y': 50000
				}
			else:
				displaySettings = {
					'x': 75,
					'y': 75
				}

		data = {
			'abilities'      : abilities,
			'displayName'    : displayName,
			'parentLocation' : locationId,
			'settings'       : displaySettings,
			'skillName'      : skillName,
			'typeName'       : deviceType,
			'uid'            : uid or str(uuid.uuid4())
		}

		device = Device(data)

		self._devices[device.id] = device
		return device


	@property
	def devices(self) -> Dict[int, Device]:
		return self._devices


	def updateDeviceDisplay(self, deviceId: int, data: dict) -> Optional[Device]:
		"""
		Updates the UI part of a device
		:param deviceId: The device id to update
		:param data: A dict of data to update
		:return: Device instance
		"""
		device = self.getDevice(deviceId=deviceId)
		if not device:
			raise Exception(f"Cannot update device, device with id **{deviceId}** doesn't exist")

		if 'parentLocation' in data and data['parentLocation'] != device.parentLocation:
			self.assertLocationChange(device=device, locationId=data['parentLocation'])

			self.deleteDeviceLinks(deviceUid=device.uid, targetLocationId=data['parentLocation'])
			device.parentLocation = data['parentLocation']

		if 'settings' in data:
			device.updateSettings(data['settings'])

		device.saveToDB()
		return device


	def assertLocationChange(self, device: Device, locationId: int) -> bool:
		"""
		Checks if the given device can be moved to another location
		if it is not possible, an exception is thrown
		:param device: Device instance
		:param locationId: int
		:return: bool
		"""
		loc = self.LocationManager.getLocation(locId=locationId)
		if not loc:
			raise Exception('Cannot change device location to a unexisting location')

		if 0 < device.deviceType.perLocationLimit <= len(self.getDevicesByLocation(locationId, deviceType=device.deviceType, connectedOnly=False)):
			raise Exception(f'Cannot move device **{device.displayName}** to new location, maximum per location limit reached')

		return True


	def deleteDevice(self, deviceId: int = None, deviceUid: str = None):
		"""
		called on deletion of a device
		Checks if deletion is allowed and deletes the device and its from the database
		:param deviceId:
		:param deviceUid:
		:return:
		"""
		# TODO unsub mqtt, clean links
		device = self.getDevice(deviceId=deviceId, uid=deviceUid)
		if not device:
			raise Exception(f'Device with uid {deviceUid} not found')
		elif device.hasAbilities([DeviceAbility.IS_CORE]):
			raise Exception(f'Cannot delete main unit')
		else:
			self.deleteDeviceLinks(deviceId=device.id)
			self._devices.pop(device.id)
			self.DatabaseManager.delete(tableName=self.DB_DEVICE, callerName=self.name, values={'id': device.id})


	def findUSBPort(self, timeout: int) -> str:
		"""
		This waits until a change is detected on the usb ports, meaning a device was plugged in
		Plugging a device out doesn't break the check, and only timeout or a detected plug in returns the port
		:param timeout: Seconds after which the function stops looking for a new device
		:return: The usb port detected or not
		"""
		oldPorts = list()
		scanPresent = True
		found = False
		tries = 0
		self.logInfo(f'Looking for USB device for the next {timeout} seconds')
		while not found:
			tries += 1
			if tries > timeout * 2:
				break

			newPorts = list()
			for port, desc, hwid in sorted(list_ports.comports()):
				if scanPresent:
					oldPorts.append(port)
				newPorts.append(port)

			scanPresent = False

			if len(newPorts) < len(oldPorts):
				self.logInfo('USB device disconnected')
				oldPorts = list()
				scanPresent = True
			else:
				changes = [port for port in newPorts if port not in oldPorts]
				if changes:
					port = changes[0]
					self.logInfo(f'Found usb device on {port}')
					return port

			time.sleep(0.5)

		return ''


	def isBusy(self) -> bool:
		"""
		The manager is busy if it's already broadcasting for a new device
		:return: boolean
		"""
		return self.ThreadManager.isThreadAlive('broadcast')


	def deviceConnecting(self, uid: str) -> Optional[Device]:
		"""
		Called upon connection of a new device.
		Sets status to connected and ensures the heartbeats are checked
		:param uid:
		:return: the device Object if known
		"""
		device = self.getDevice(uid=uid)
		if not device:
			self.logWarning(f'A device with uid **{uid}** tried to connect but is unknown')
			return None

		if not device.connected:
			device.connected = True
			self.broadcast(method=constants.EVENT_DEVICE_CONNECTING, exceptions=[self.name], propagateToSkills=True)
			self.MqttManager.publish(constants.TOPIC_DEVICE_UPDATED, payload={'uid': device.uid, 'type': 'status'})

		self._heartbeats[uid] = time.time() + 5
		if not self._heartbeatsCheckTimer:
			self._heartbeatsCheckTimer = self.ThreadManager.newTimer(interval=3, func=self.checkHeartbeats)

		return device


	def deviceDisconnecting(self, uid: str):
		"""
		Called when a device is disconnecting, removes the heartbeat  and sets status to disconnected
		:param uid:
		:return:
		"""
		self._heartbeats.pop(uid, None)

		device = self.getDevice(uid=uid)

		if not device:
			return

		if device.connected:
			self.logInfo(f'Device with uid **{uid}** disconnected')
			device.connected = False
			self.broadcast(method=constants.EVENT_DEVICE_DISCONNECTING, exceptions=[self.name], propagateToSkills=True)
			self.MqttManager.publish(constants.TOPIC_DEVICE_UPDATED, payload={'id': device.id, 'type': 'status'})


	@property
	def deviceTypes(self) -> dict:
		return self._deviceTypes


	def addDeviceLink(self, targetLocation: int, deviceId: int = None, deviceUid: str = None) -> Optional[DeviceLink]:
		"""
		Add a new device link, from deviceId or deviceUid to targetLocation
		:param targetLocation: int
		:param deviceId: int
		:param deviceUid: str
		:return:
		"""
		device = self.getDevice(deviceId=deviceId, uid=deviceUid)
		if not device:
			raise Exception('Unknown device requested for link.')

		if targetLocation <= 0:
			raise Exception('Cannot add a device link to no location')

		if device.linkedTo(targetLocation):
			raise Exception('This device is already linked to that location')

		data = {
			'deviceId': device.id,
			'targetLocation': targetLocation
		}

		link = DeviceLink(data)
		self._deviceLinks[link.id] = link
		return link


	def deleteDeviceLinks(self, linkId: int = None, deviceId: int = None, deviceUid: str = None, targetLocationId: int = None):
		"""
		Delete one or more device links.
		If link id is provided, deletes only one.
		If deviceId or Uid provided, deletes any link belonging to that device.
		If target location id provided, deletes any link to that location.
		If both device id or uid and target location provided, deletes any links from that device to that location
		:param linkId: int
		:param deviceId: int
		:param deviceUid: str
		:param targetLocationId: int
		:return:
		"""
		if linkId:
			self.DatabaseManager.delete(tableName=self.DB_LINKS, callerName=self.name, values={'id': linkId})
			self._deviceLinks.pop(linkId)

		elif deviceId or deviceUid:
			device = self.getDevice(deviceId=deviceId, uid=deviceUid)
			if not device:
				raise Exception(f'Deleting device link from parent device failed, parent device with id **{deviceId}** not found')

			delete = {'deviceId': device.id}

			# Case: if both device and location are known, delete specific entry
			if targetLocationId:
				delete['targetLocation'] = targetLocationId

			self.DatabaseManager.delete(tableName=self.DB_LINKS, callerName=self.name, values=delete)

			for link in self._deviceLinks.copy().values():
				if link.deviceId == device.id and (not targetLocationId or targetLocationId == link.targetLocation):
					self._deviceLinks.pop(link.id)

		elif targetLocationId:
			self.DatabaseManager.delete(tableName=self.DB_LINKS, callerName=self.name, values={'targetLocation': targetLocationId})

			for link in self._deviceLinks.copy().values():
				if link.targetLocation == targetLocationId:
					self._deviceLinks.pop(link.id)


	@property
	def deviceLinks(self) -> Dict[int, DeviceLink]:
		return self._deviceLinks


	def getDeviceTypesForSkill(self, skillName: str) -> Dict[str, DeviceType]:
		"""
		Return the list of device types a skill has registered
		:param skillName: str
		:return: Dict deviceTypeName:DeviceType
		"""
		return self._deviceTypes.get(skillName, dict())


	def removeDeviceTypesForSkill(self, skillName: str):
		"""
		Removes deviceTypes for the given skill
		:param skillName: str
		:return:
		"""
		self._deviceTypes.pop(skillName, None)


	@property
	def broadcastFlag(self) -> threading.Event:
		return self._broadcastFlag


	def startBroadcastingForNewDevice(self, device: Device, uid: str = '', replyOnDeviceUid: str = '') -> bool:
		"""
		Start broadcasting for a new device to join Alice's network
		:param device: The device instance that is supposed to join
		:param uid: The uid attributed to that device
		:param replyOnDeviceUid: Where Alice should announce the success or failure of the device addition
		:return: boolean
		"""
		if self.isBusy():
			return False

		if not uid:
			uid = str(uuid.uuid4())

		self.logInfo(f'Started broadcasting on {self._broadcastPort} for new device addition. Attributed uid: {device.uid}')
		self._listenSocket.listen(2)
		self.ThreadManager.newThread(name='broadcast', target=self._startBroadcast, args=[device, uid, replyOnDeviceUid])

		self._broadcastTimer = self.ThreadManager.newTimer(interval=300, func=self._stopBroadcasting)

		self.broadcast(method=constants.EVENT_BROADCASTING_FOR_NEW_DEVICE, exceptions=[self.name], propagateToSkills=True)
		return True


	def _startBroadcast(self, device: Device, uid: str, replyOnDeviceUid: str = ''):
		"""
		Starts the internal process of broadcasting for a new device
		:param device: the device class
		:param uid: the attributed uid
		:param replyOnDeviceUid: if provided,confirm on the device
		:return:
		"""
		self._broadcastFlag.set()
		while self._broadcastFlag.isSet():
			self._broadcastSocket.sendto(bytes(f'{self.Commons.getLocalIp()}:{self._listenPort}:{uid}', encoding='utf8'), ('<broadcast>', self._broadcastPort))
			try:
				sock, address = self._listenSocket.accept()
				sock.settimeout(None)
				answer = sock.recv(1024).decode()

				deviceIp = answer.split(':')[0]
				deviceType = answer.split(':')[1]

				if deviceType.lower() != device.deviceTypeName.lower():
					self.logWarning(f'Device with uid {uid} is not of correct type. Waiting on **{device.deviceTypeName}**, got **{deviceType}**')
					self._broadcastSocket.sendto(bytes('nok', encoding='utf8'), (deviceIp, self._broadcastPort))
					raise socket.timeout

				device.pairingDone(uid=uid)
				self.logInfo(f'Device with uid **{uid}** successfully paired')

				if replyOnDeviceUid:
					self.MqttManager.say(text=self.TalkManager.randomTalk('newDeviceAdditionSuccess', skill='system'), client=replyOnDeviceUid)

				#self.ThreadManager.doLater(interval=5, func=self.WakewordRecorder.uploadToNewDevice, args=[uid])

				self._broadcastSocket.sendto(bytes('ok', encoding='utf8'), (deviceIp, self._broadcastPort))
				self._stopBroadcasting()
			except socket.timeout:
				self.logInfo('No device query received')


	def _stopBroadcasting(self):
		"""
		Stops the new device discovery broadcast
		:return:
		"""
		if not self.isBusy():
			return

		self.logInfo('Stopped broadcasting for new devices')
		self._broadcastFlag.clear()
		self._broadcastTimer.cancel()
		self.broadcast(method=constants.EVENT_STOP_BROADCASTING_FOR_NEW_DEVICE, exceptions=[self.name], propagateToSkills=True)








































	def onDeviceStatus(self, session: DialogSession):
		device = self.getDevice(uid=session.payload['uid'])
		if device:
			device.onDeviceStatus(session)


	def deviceMessage(self, message: MQTTMessage) -> DialogSession:
		return self.DialogManager.newTempSession(message=message)


	def devUIDtoID(self, uid: str) -> int:
		for _id, dev in self.devices.items():
			if dev.uid == uid:
				return _id


	def devIDtoUID(self, _id: int) -> str:
		return self.devices[_id].uid


	def deleteDeviceID(self, deviceId: int):
		self.devices.pop(deviceId)
		self.DatabaseManager.delete(tableName=self.DB_DEVICE, callerName=self.name, values={"id": deviceId})
		self.DatabaseManager.delete(tableName=self.DB_LINKS, callerName=self.name, values={"id": deviceId})


	def addDeviceTypes(self, deviceTypes: Dict):
		self.deviceTypes.update(deviceTypes)


	def getLink(self, _id: int = None, deviceId: int = None, locationId: Union[list, int] = None) -> DeviceLink:
		if _id:
			return self._deviceLinks.get(_id, None)
		if not deviceId or not locationId:
			raise Exception('getLink: supply locationId or deviceID!')

		if not isinstance(locationId, List):
			locationId = [locationId]

		for link in self._deviceLinks.values():
			if link.deviceId == deviceId and link.locationId in locationId:
				return link





	def deleteDeviceUID(self, deviceUID: str):
		self.deleteDeviceID(deviceId=self.devUIDtoID(uid=deviceUID))


	def getFreeUID(self, base: str = '') -> str:
		"""
		Gets a free uid. A free uid is a uid not declared in database. If base is provided it will be used as a uid pattern
		:param base: str
		:return: str
		"""
		if not base:
			uid = str(uuid.uuid4())
		else:
			uid = base = base.replace(':', '').replace(' ', '')

		while not self.isUIDAvailable(uid):
			if not base:
				uid = str(uuid.uuid4())
			else:
				aList = list(base)
				shuffle(aList)
				uid = ''.join(aList)

		return uid


	def broadcastToDevices(self, topic: str, payload: dict = None, deviceType: DeviceType = None, location: Location = None, connectedOnly: bool = True):
		if not payload:
			payload = dict()

		for device in self._devices.values():
			if deviceType and device.getDeviceType() != deviceType:
				continue

			if location and device.isInLocation(location):
				continue

			if connectedOnly and not device.connected:
				continue

			payload.setdefault('uid', device.uid)
			payload.setdefault('siteId', device.siteId)

			self.MqttManager.publish(
				topic=topic,
				payload=json.dumps(payload)
			)





	## Heartbeats
	def onDeviceHeartbeat(self, uid: str, siteId: str = None):
		device = self.getDevice(uid=uid)

		if not device:
			self.logWarning(f'Device with uid **{uid}** does not exist')
			return

		device.connected = True
		self._heartbeats[uid] = time.time()


	def getDeviceLinksByType(self, deviceType: int, connectedOnly: bool = False) -> List[DeviceLink]:
		return [x for x in self._deviceLinks.values() if x.getDevice().deviceTypeId == deviceType and (not connectedOnly or x.getDevice().connected)]


	def getDeviceLinks(self, locationId: int, deviceTypeId: int = None, connectedOnly: bool = False, pairedOnly: bool = False) -> List[DeviceLink]:
		if locationId and not isinstance(locationId, List):
			locationId = [locationId]

		if deviceTypeId and not isinstance(deviceTypeId, List):
			deviceTypeId = [deviceTypeId]

		return [x for x in self._deviceLinks.values()
		        if (not locationId or x.locationId in locationId)
		        and x.getDevice()
		        and (not deviceTypeId or x.getDevice().deviceTypeId in deviceTypeId)
		        and (not connectedOnly or x.getDevice().connected)
		        and (not pairedOnly or x.getDevice().uid)]


	def getDeviceLinksForSession(self, session: DialogSession, skill: str, noneIsEverywhere: bool = False):
		#get all relevant deviceTypes
		devTypes = self.DeviceManager.getDeviceTypesForSkill(skillName=skill)
		devTypeIds = [dev for dev in devTypes] # keys in dict are Ids

		#get all required locations
		locations = self.LocationManager.getLocationsForSession(sess=session, noneIsEverywhere=noneIsEverywhere)
		locationIds = [loc.id for loc in locations]

		return self.DeviceManager.getDeviceLinks(deviceTypeId=devTypeIds, locationId=locationIds)


	@staticmethod
	def groupDeviceLinksByDevice(links: List[DeviceLink]) -> Dict[int, DeviceLink]:
		# group links by device
		devGrouped = dict()
		for link in links:
			devGrouped.setdefault(link.deviceId,[]).append(link)
		return devGrouped





	def getDeviceById(self, _id: int) -> Optional[Device]:
		return self._devices.get(_id, None)


	def getDeviceByName(self, name: str):
		return next((dev for dev in self._devices.values() if dev.displayName == name), None)


	def getLinksForDevice(self, device: Device) -> List[DeviceLink]:
		return [link for link in self._deviceLinks.values() if link.deviceId == device.id]


	## generic helper for finding a new USB device

