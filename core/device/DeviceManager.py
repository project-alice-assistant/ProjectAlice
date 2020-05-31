import json
import socket
import sqlite3
import threading
import time
import uuid
from pathlib import Path
from typing import Dict, List, Optional

import esptool
import requests
import serial
from esptool import ESPLoader
from paho.mqtt.client import MQTTMessage
from random import shuffle
from serial.tools import list_ports

from core.base.model.Manager import Manager
from core.commons import constants
from core.device.model.Device import Device
from core.device.model.DeviceType import DeviceType
from core.device.model.DeviceLink import DeviceLink
from core.device.model.Location import Location
from core.device.model.TasmotaConfigs import TasmotaConfigs
from core.dialog.model.DialogSession import DialogSession


class DeviceManager(Manager):
#todo remove all room: string - replace with locationID

	DB_DEVICE = 'devices'
	DB_LINKS = 'deviceLinks'
	DB_TYPES = 'deviceTypes'
	DATABASE = {
		DB_DEVICE: [
			'id INTEGER PRIMARY KEY',
			'typeID INTEGER NOT NULL',
			'uid TEXT',
			'locationID INTEGER NOT NULL',
			'name TEXT',
			'display TEXT',
			'devSettings TEXT'
		],
		DB_LINKS: [
			'id INTEGER PRIMARY KEY',
			'deviceID INTEGER NOT NULL',
			'locationID INTEGER NOT NULL',
			'locSettings TEXT'
		],
		DB_TYPES: [
			'id INTEGER PRIMARY KEY',
			'skill TEXT NOT NULL',
			'name TEXT NOT NULL',
			'devSettings TEXT',
			'locSettings TEXT'
		]
	}
	SAT_TYPE = 'device_AliceSatellite'


	def __init__(self):
		super().__init__(databaseSchema=self.DATABASE)

		self._devices: Dict[int, Device] = dict()
		self._deviceLinks: Dict[int, DeviceLink] = dict()
		#self._idToUID: Dict[int, str] = dict() #todo maybe relevant for faster access?
		self._deviceTypes: Dict[int, DeviceType] = dict()
		self._broadcastFlag = threading.Event()

		self._flashThread = None

		self._heartbeats = dict()
		self._heartbeatsCheckTimer = None
		self._heartbeatTimer = None


	def onStart(self):
		super().onStart()

		self.loadDevices()
		#self.loadLinks()

		self.logInfo(f'Loaded **{len(self._devices)}** device', plural='device')


	@property
	def devices(self) -> Dict[int, Device]:
		return self._devices


	def onBooted(self):
		self.MqttManager.publish(topic='projectalice/devices/coreReconnection')

		if self._devices:
			self._heartbeatsCheckTimer = self.ThreadManager.newTimer(interval=3, func=self.checkHeartbeats)
			self._heartbeatTimer = self.ThreadManager.newTimer(interval=2, func=self.sendHeartbeat)


	def onStop(self):
		super().onStop()
		self.MqttManager.publish(topic='projectalice/devices/coreDisconnection')


	def onDeviceStatus(self, session) -> bool:
		device = self.getDeviceByUID(uid=session.payload['uid'])
		device.onDeviceStatus()


	def deviceMessage(self, message: MQTTMessage) -> DialogSession:
		return self.DialogManager.newTempSession(message=message)


	def loadDevices(self):
		for row in self.databaseFetch(tableName=self.DB_DEVICE, method='all'):
			# to dict!
			self._devices[row['id']] = Device(row)


	# noinspection SqlResolve
	def isUIDAvailable(self, uid: str) -> bool:
		try:
			count = self.databaseFetch(tableName='devices', query='SELECT COUNT() FROM :__table__ WHERE uid = :uid', values={'uid': uid})[0]
			return count <= 0
		except sqlite3.OperationalError as e:
			self.logWarning(f"Couldn't check device from database: {e}")
			return False


	# noinspection SqlResolve
	def addNewDevice(self, deviceTypeID: int, locationID: int = None, uid: str = None) -> Device:
		# get or create location from different inputs
		try:
			location = self.LocationManager.getLocation(id=locationID)

			self.assertDeviceTypeAllowedAtLocation(locationID=location.id, typeID=deviceTypeID)

			values = {'typeID': deviceTypeID, 'uid': uid, 'locationID': location.id, 'display': "{}"}
			values['id'] = self.databaseInsert(tableName=self.DB_DEVICE, values=values)

			self._devices[values['id']] = Device(data=values)
			return self._devices[values['id']]
		except Exception as e:
			self.logWarning(f"Couldn't insert device in database: {e}")
			return None


	def devUIDtoID(self, UID: str) -> int:
		for id, dev in self.devices.items():
			if dev.uid == UID:
				return id


	def devIDtoUID(self, ID: int) -> str:
		return self.devices[ID].uid


	def deleteDeviceID(self, deviceID: int):
		self.devices.pop(deviceID)
		self.DatabaseManager.delete(tableName=self.DB_DEVICE, callerName=self.name, values={"id": deviceID})
		self.DatabaseManager.delete(tableName=self.DB_LINKS, callerName=self.name, values={"id": deviceID})


	def getDeviceType(self, id: int):
		return self.deviceTypes.get(id, None)


	def getDeviceTypeByName(self, name: str) -> DeviceType:
		for device in self.deviceTypes.values():
			if device.name == name:
				return device
		return None


	def getDeviceTypesForSkill(self, skillName: str) -> Dict[int, DeviceType]:
		return {id: deviceType for id, deviceType in self.deviceTypes.items() if deviceType.skill == skillName}


	def removeDeviceTypesForSkill(self,skillName: str):
		for id, deviceType in self.getDeviceTypesForSkill(skillName):
			self.deviceTypes.pop(id, None)


	def addDeviceTypes(self, deviceTypes: Dict):
		self.deviceTypes.update(deviceTypes)


	def removeDeviceType(self, id: int):
		self.DatabaseManager.delete(
			tableName=self.DB_TYPES,
			callerName=self.name,
			values={
				'id': id
			}
		)
		self._deviceTypes.pop(id)

	def getLink(self, deviceID, int, locationID: int):
		pass



	def addLink(self, id: int, locationid: int):
		device = self.getDeviceByID(id)
		deviceType = device.getDeviceType()
		if not deviceType.multiRoom():
			raise Exception(f'Device type {deviceType.name} can\'t be linked to other rooms')

		#todo get device/room specific settings
		locSettings = []
		values = {'id' : id, 'locationid': locationid, 'locSettings': locSettings}
		self.databaseInsert(tableName=self.DB_LINKS, query='INSERT INTO :__table__ (deviceID, locationID, locSettings) VALUES (:id, :locationid, locSettings)', values=values)

	def deleteLink(self, id: int):
		pass

	def deleteDeviceUID(self, deviceUID: str):
		self.deleteDeviceID(deviceID=self.devUIDtoID(UID=deviceUID))


	def _getFreeUID(self, base: str = '') -> str:
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


	def deviceConnecting(self, uid: str) -> Optional[Device]:
		device = self.getDeviceByUID(uid)
		if not device:
			self.logWarning(f'A device with uid **{uid}** tried to connect but is unknown')
			return None

		if not device.connected:
			device.connected = True
			self.broadcast(method=constants.EVENT_DEVICE_CONNECTING, exceptions=[self.name], propagateToSkills=True)
			self.MqttManager.publish('projectalice/devices/updated', payload={'id': device.id, 'type': 'status'})

		self._heartbeats[uid] = time.time() + 5
		if not self._heartbeatsCheckTimer:
			self._heartbeatsCheckTimer = self.ThreadManager.newTimer(interval=3, func=self.checkHeartbeats)

		return device


	def deviceDisconnecting(self, uid: str):
		self._heartbeats.pop(uid, None)

		device = self.getDeviceByUID(uid)

		if not device:
			return

		if device.connected:
			self.logInfo(f'Device with uid **{uid}** disconnected')
			device.connected = False
			self.broadcast(method=constants.EVENT_DEVICE_DISCONNECTING, exceptions=[self.name], propagateToSkills=True)
			self.MqttManager.publish('projectalice/devices/updated', payload={'id': device.id, 'type': 'status'})


## Heartbeats
	def onDeviceHeartbeat(self, uid: str, siteId: str = None):
		device = self.getDeviceByUID(uid=uid)
		if siteId:
			location = self.LocationManager.getLocation(siteID=siteId)

		if not device:
			self.logWarning(f'Device with uid **{uid}** does not exist')
			return

		if location and not device.isInLocation(location):
			self.logWarning(f'Device with uid **{uid}** is not matching its defined room (received **{siteId.replace(" ", "_").lower()}** but required **{device.getMainLocation().getSaveName()}**')
			return

		device.connected = True
		self._heartbeats[uid] = time.time()


	def checkHeartbeats(self):
		now = time.time()
		for uid, lastTime in self._heartbeats.copy().items():
			if now - 5 > lastTime:
				self.logWarning(f'Device with uid **{uid}** has not given a signal since 5 seconds or more')
				self._heartbeats.pop(uid)
				device = self.getDeviceByUID(uid)
				if device:
					device.connected = False
					self.publish('projectalice/devices/updated', payload={'id': device.id, 'type': 'status'})

		self._heartbeatsCheckTimer = self.ThreadManager.newTimer(interval=3, func=self.checkHeartbeats)


	def sendHeartbeat(self):
		self.MqttManager.publish(
			topic=constants.TOPIC_CORE_HEARTBEAT
		)

		self._heartbeatTimer = self.ThreadManager.newTimer(interval=2, func=self.sendHeartbeat)

## base
	def getDeviceTypeBySkillRAW(self, skill: str):
		data = self.DatabaseManager.fetch(
			tableName=self.DB_TYPES,
			query='SELECT * FROM :__table__ WHERE skill = :skill',
			callerName=self.name,
			values={'skill': skill},
			method='all'
		)
		return {d['name']: {'id': d['id'], 'name': d['name'], 'skill': d['skill']} for d in data}


	def updateDevice(self,device: dict):
		self.getDeviceByID(device['id']).display = device['display']
		self.DatabaseManager.update(tableName=self.DB_DEVICE,
		                            callerName=self.name,
		                            values={'display': device['display']},
		                            row=('id', device['id']))


	def assertDeviceTypeAllowedAtLocation(self, typeID: int, locationID: int):
		# check max allowed per Location
		deviceType = self.getDeviceType(typeID)
		# check if another instance of this device is allowed
		if deviceType.totalDeviceLimit > 0:
			if deviceType.totalDeviceLimit <= self.DeviceManager.getDevicesByTypeID(deviceTypeID=typeID):
				raise Exception(f'Maximum limit of devices from this device type reached')
		#todo self.MqttManager.say(text=self.TalkManager.randomTalk('maxOneAlicePerRoom', skill='system'), client=replyOnSiteId)

		# check if there are aleady too many of this device type in the location
		if deviceType.perLocationLimit > 0:
			if deviceType.perLocationLimit <= self.LocationManager.getDevicesByLocation(locationID=locationID,deviceTypeID=typeID):
				raise Exception(f'Maximum limit of devices in this location already reached')
		#todo self.MqttManager.say(text=self.TalkManager.randomTalk('maxOneAlicePerRoom', skill='system'), client=replyOnSiteId)


	@property
	def deviceTypes(self) -> dict:
		return self._deviceTypes


	def getDevicesByLocation(self, locationID: int, connectedOnly: bool = False, deviceTypeID: int = None) -> List[Device]:
		return [device for device in self._devices.values() if device.locationID == locationID
		        and (not connectedOnly or device.connected)
		        and (not deviceTypeID or device.deviceTypeID == deviceTypeID)]


	def getDevicesByType(self, deviceType: str, connectedOnly: bool = False) -> List[Device]:
		deviceTypeObj = self.getDeviceTypeByName(deviceType)
		if deviceTypeObj:
			return [x for x in self._devices.values() if x.deviceTypeID == deviceTypeObj.id and (not connectedOnly or x.connected)]
		return list()


	def getDevicesByTypeID(self, deviceTypeID: int, connectedOnly: bool = False) -> List[Device]:
		return [x for x in self._devices.values() if x.deviceTypeID == deviceTypeID and (not connectedOnly or x.connected)]


	def getDeviceLinksByType(self, deviceType: int, connectedOnly: bool = False) -> List[Device]:
		return [x for x in self._deviceLinks.values() if x.deviceTypeID == deviceType and (not connectedOnly or x.connected)]


	def getDeviceByUID(self, uid: str) -> Optional[Device]:
		return self._devices.get(self.devUIDtoID(uid), None)


	def getDeviceByID(self, id: int) -> Optional[Device]:
		return self._devices.get(id, None)


## todo move to tasmota skill
	@property
	def broadcastFlag(self) -> threading.Event:
		return self._broadcastFlag


	def doFlashTasmota(self, location: Location, espType: str, siteId: str):
		port = self.findUSBPort(timeout=60)
		if not port:
			self.MqttManager.say(text=self.TalkManager.randomTalk('noESPFound', skill='AliceCore'), client=siteId)
			self._broadcastFlag.clear()
			return

		self.MqttManager.say(text=self.TalkManager.randomTalk('usbDeviceFound', skill='AliceCore'), client=siteId)
		try:
			mac = ESPLoader.detect_chip(port=port, baud=115200).read_mac()
			mac = ':'.join([f'{x:02x}' for x in mac])
			cmd = [
				'--port', port,
				'--baud', '115200',
				'--after', 'no_reset', 'write_flash',
				'--flash_mode', 'dout', '0x00000', 'tasmota.bin',
				'--erase-all'
			]

			esptool.main(cmd)
		except Exception as e:
			self.logError(f'Something went wrong flashing esp device: {e}')
			self.MqttManager.say(text=self.TalkManager.randomTalk('espFailed', skill='AliceCore'), client=siteId)
			self._broadcastFlag.clear()
			return

		self.logInfo('Tasmota flash done')
		self.MqttManager.say(text=self.TalkManager.randomTalk('espFlashedUnplugReplug', skill='AliceCore'), client=siteId)
		found = self.findUSBPort(timeout=60)
		if found:
			self.MqttManager.say(text=self.TalkManager.randomTalk('espFoundReadyForConf', skill='AliceCore'), client=siteId)
			time.sleep(10)
			uid = self._getFreeUID(mac)
			tasmotaConfigs = TasmotaConfigs(deviceType=espType, uid=uid)
			confs = tasmotaConfigs.getBacklogConfigs(location.getSaveName())
			if not confs:
				self.logError('Something went wrong getting tasmota configuration')
				self.MqttManager.say(text=self.TalkManager.randomTalk('espFailed', skill='AliceCore'), client=siteId)
			else:
				ser = serial.Serial()
				ser.baudrate = 115200
				ser.port = port
				ser.open()

				try:
					for group in confs:
						cmd = ';'.join(group['cmds'])
						if len(group['cmds']) > 1:
							cmd = f'Backlog {cmd}'

						arr = list()
						if len(cmd) > 50:
							while len(cmd) > 50:
								arr.append(cmd[:50])
								cmd = cmd[50:]
							arr.append(f'{cmd}\r\n')
						else:
							arr.append(f'{cmd}\r\n')

						for piece in arr:
							ser.write(piece.encode())
							self.logInfo('Sent {}'.format(piece.replace('\r\n', '')))
							time.sleep(0.5)

						time.sleep(group['waitAfter'])

					ser.close()
					self.logInfo('Tasmota flashing and configuring done')
					self.MqttManager.say(text=self.TalkManager.randomTalk('espFlashingDone', skill='AliceCore'), client=siteId)

					#todo espType is not a valid input anymore: need a proper device type!
					self.addNewDevice(espType, locationID=location.id, uid=uid)
					self._broadcastFlag.clear()

				except Exception as e:
					self.logError(f'Something went wrong writting configuration to esp device: {e}')
					self.MqttManager.say(text=self.TalkManager.randomTalk('espFailed', skill='AliceCore'), client=siteId)
					self._broadcastFlag.clear()
					ser.close()
		else:
			self.MqttManager.say(text=self.TalkManager.randomTalk('espFailed', skill='AliceCore'), client=siteId)
			self._broadcastFlag.clear()


	def findUSBPort(self, timeout: int) -> str:
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
				# User disconnected a device
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

	# todo currently called from AliceCore - should be moved to a seperate skill or be handled with callbacks specified by skills
	def startTasmotaFlashingProcess(self, room: str, espType: str, session: DialogSession) -> bool:
		location = self.LocationManager.getLocationWithName(name=room)
		self.ThreadManager.doLater(interval=0.5, func=self.MqttManager.endDialog, args=[session.sessionId, self.TalkManager.randomTalk('connectESPForFlashing', skill='AliceCore')])

		self._broadcastFlag.set()

		binFile = Path('tasmota.bin')
		if binFile.exists():
			binFile.unlink()

		try:
			req = requests.get(f'https://github.com/arendst/Tasmota/releases/download/v8.2.0/tasmota.bin')
			with binFile.open('wb') as file:
				file.write(req.content)
				self.logInfo('Downloaded tasmota.bin')
		except Exception as e:
			self.logError(f'Something went wrong downloading tasmota.bin: {e}')
			self._broadcastFlag.clear()
			return False

		self.ThreadManager.newThread(name='flashThread', target=self.doFlashTasmota, args=[location, espType, session.siteId])
		return True
