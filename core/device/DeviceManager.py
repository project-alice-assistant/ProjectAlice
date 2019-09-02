import os
import socket
import sqlite3
import threading
import time
import uuid
from random import shuffle
from typing import Optional

import esptool
import requests
from esptool import ESPLoader
from paho.mqtt.client import MQTTMessage
from serial import Serial
from serial.tools import list_ports

import core.base.Managers as managers
from core.base.Manager import Manager
from core.commons import commons
from core.device.model.Device import Device
from core.device.model.TasmotaConfigs import TasmotaConfigs
from core.dialog.model.DialogSession import DialogSession


class DeviceManager(Manager):

	NAME = 'DeviceManager'

	DATABASE = {
		'devices': [
			'id INTEGER PRIMARY KEY',
			'type TEXT NOT NULL',
			'uid TEXT NOT NULL',
			'room TEXT NOT NULL',
			'name TEXT'
		]
	}


	def __init__(self, mainClass):
		super().__init__(mainClass, self.NAME, self.DATABASE)
		managers.DeviceManager = self

		self._devices = dict()
		self._broadcastRoom = ''
		self._broadcastFlag = threading.Event()

		self._broadcastPort = int(managers.ConfigManager.getAliceConfigByName('newDeviceBroadcastPort')) # Default 12354
		self._broadcastTimer = None

		self._flashThread = None

		self._listenPort = self._broadcastPort + 1

		self._broadcastSocket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
		self._broadcastSocket.setsockopt(socket.SOL_SOCKET, socket.SO_BROADCAST, 1)
		self._broadcastSocket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)

		self._listenSocket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
		self._listenSocket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
		self._listenSocket.settimeout(2)
		self._listenSocket.bind(('', self._listenPort))


	@property
	def broadcastRoom(self) -> str:
		return self._broadcastRoom


	def onStart(self):
		if not super().onStart():
			self._logger.error('[{}] Failed to start'.format(self.name))
			return

		self.loadDevices()
		self._logger.info('- Loaded {} devices'.format(len(self._devices)))


	def onBooted(self):
		managers.MqttServer.publish(topic='projectalice/devices/coreReconnection')


	def onStop(self):
		super().onStop()
		self.stopBroadcasting()
		self._broadcastSocket.close()
		managers.MqttServer.publish(topic='projectalice/devices/coreDisconnection')


	@staticmethod
	def onMessage(message: MQTTMessage) -> Optional[DialogSession]:
		if not 'projectalice/devices/' in message.topic:
			return None

		return managers.DialogSessionManager.addTempSession(sessionId = uuid.uuid4(), message = message)


	def loadDevices(self):
		for row in self.databaseFetch(tableName='devices', query='SELECT * FROM :__table__', method='all'):
			self._devices[row['uid']] = Device(row)


	# noinspection SqlResolve
	def isUIDAvailable(self, uid: str) -> bool:
		try:
			count = self.databaseFetch(tableName='devices', query='SELECT COUNT() FROM :__table__ WHERE uid = :uid', values={'uid': uid})[0]
			return count <= 0
		except sqlite3.OperationalError as e:
			self._logger.warning("[{}] Couldn't check device from database: {}".format(self.name, e))
			return False


	@staticmethod
	def isBusy():
		return managers.ThreadManager.isThreadAlive('broadcast')


	@property
	def broadcastFlag(self) -> threading.Event:
		return self._broadcastFlag


	# noinspection SqlResolve
	def addNewDevice(self, ttype: str, room: str = None, uid: str = None) -> bool:
		if not room:
			room = self._broadcastRoom
		if not uid:
			uid = self._getFreeUID()

		try:
			values = {'type': ttype, 'uid': uid, 'room': room}
			values['id'] = self.databaseInsert(tableName='devices', query='INSERT INTO :__table__ (type, uid, room) VALUES (:type, :uid, :room)', values=values)
			d = Device(values, True)
			self._devices[uid] = d
			return True
		except Exception as e:
			self._logger.warning("[{}] Couldn't insert device in database: {}".format(self.name, e))
			return False


	def startTasmotaFlashingProcess(self, room: str, espType: str, session: DialogSession) -> bool:
		managers.ThreadManager.doLater(interval=0.5, func = managers.MqttServer.endTalk, args = [session.sessionId, managers.TalkManager.randomTalk('connectESPForFlashing', module = 'AliceCore')])

		self._broadcastFlag.set()
		if os.path.isfile('sonoff.bin'):
			os.remove('sonoff.bin')

		try:
			req = requests.get('https://github.com/arendst/Sonoff-Tasmota/releases/download/v6.5.0/sonoff.bin')
			with open('sonoff.bin', 'wb') as file:
				file.write(req.content)
				self._logger.info('[{}] Downloaded sonoff.bin'.format(self.name))
		except Exception as e:
			self._logger.error('[{}] Something went wrong downloading sonoff.bin: {}'.format(self.name, e))
			self._broadcastFlag.clear()
			return False

		managers.ThreadManager.newThread(name='flashThread', target=self.doFlashTasmota, args=[room, espType, session.siteId])
		return True


	def findUSBPort(self, timeout: int) -> str:
		oldPorts = list()
		scanPresent = True
		found = False
		port = ''
		tries = 0
		self._logger.info('[{}] Looking for USB device for the next {} seconds'.format(self.name, timeout))
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
				self._logger.info('[{}] USB device disconnected'.format(self._name))
				oldPorts = list()
				scanPresent = True
			else:
				changes = [port for port in newPorts if port not in oldPorts]
				if changes:
					port = changes[0]
					self._logger.info('[{}] Found usb device on {}'.format(self._name, port))
					return port

			time.sleep(0.5)

		return port


	def doFlashTasmota(self, room: str, espType: str, siteId: str):
		port = self.findUSBPort(timeout = 60)
		if port:
			managers.MqttServer.say(text=managers.TalkManager.randomTalk('usbDeviceFound', module = 'AliceCore'), client=siteId)
			try:
				mac = ESPLoader.detect_chip(port = port, baud = 115200).read_mac()
				mac = '%s' % (':'.join(map(lambda x: '%02x' % x, mac)))
				cmd = list()
				cmd.append('--port')
				cmd.append(port)
				cmd.append('--baud')
				cmd.append('115200')
				cmd.append('--after')
				cmd.append('no_reset')
				cmd.append('write_flash')
				cmd.append('--flash_mode')
				cmd.append('dout')
				cmd.append('0x00000')
				cmd.append('sonoff.bin')
				cmd.append('--erase-all')
				esptool.main(cmd)
			except Exception as e:
				self._logger.error('[{}] Something went wrong flashing esp device: {}'.format(self.name, e))
				managers.MqttServer.say(text=managers.TalkManager.randomTalk('espFailed', module = 'AliceCore'), client=siteId)
				self._broadcastFlag.clear()
				return
		else:
			managers.MqttServer.say(text=managers.TalkManager.randomTalk('noESPFound', module = 'AliceCore'), client=siteId)
			self._broadcastFlag.clear()
			return

		self._logger.info('[{}] Tasmota flash done'.format(self.name))
		managers.MqttServer.say(text=managers.TalkManager.randomTalk('espFlashedUnplugReplug', module = 'AliceCore'), client=siteId)
		found = self.findUSBPort(timeout = 60)
		if found:
			managers.MqttServer.say(text=managers.TalkManager.randomTalk('espFoundReadyForConf', module = 'AliceCore'), client=siteId)
			time.sleep(10)
			uid = self._getFreeUID(mac)
			tasmotaConfigs = TasmotaConfigs(deviceType = espType, uid = uid)
			confs = tasmotaConfigs.getBacklogConfigs(room)
			if not confs:
				self._logger.error('[{}] Something went wrong getting tasmota configuration'.format(self.name))
				managers.MqttServer.say(text=managers.TalkManager.randomTalk('espFailed', module = 'AliceCore'), client=siteId)
			else:
				serial = Serial()
				serial.baudrate = 115200
				serial.port = port
				serial.open()

				try:
					for group in confs:
						cmd = ';'.join(group['cmds'])
						if len(group['cmds']) > 1:
							cmd = 'Backlog {}'.format(cmd)

						arr = list()
						if len(cmd) > 50:
							while len(cmd) > 50:
								arr.append(cmd[:50])
								cmd = cmd[50:]
							arr.append('{}\r\n'.format(cmd))
						else:
							arr.append('{}\r\n'.format(cmd))

						for piece in arr:
							serial.write(piece.encode())
							self._logger.info('[{}] Sent {}'.format(self.name, piece.replace('\r\n', '')))
							time.sleep(0.5)

						time.sleep(group['waitAfter'])

					serial.close()
					self._logger.info('[{}] Tasmota flashing and configuring done'.format(self.name))
					managers.MqttServer.say(text=managers.TalkManager.randomTalk('espFlashingDone', module = 'AliceCore'), client=siteId)
					self.addNewDevice(espType, room, uid)
					self._broadcastFlag.clear()

				except Exception as e:
					self._logger.error('[{}] Something went wrong writting configuration to esp device: {}'.format(self.name, e))
					managers.MqttServer.say(text=managers.TalkManager.randomTalk('espFailed', module = 'AliceCore'), client=siteId)
					self._broadcastFlag.clear()
					serial.close()
		else:
			managers.MqttServer.say(text=managers.TalkManager.randomTalk('espFailed', module = 'AliceCore'), client=siteId)
			self._broadcastFlag.clear()
			return


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
				l = list(base)
				shuffle(l)
				uid = ''.join(l)

		return uid


	def startBroadcastingForNewDevice(self, room: str, siteId: str, uid: str = '') -> bool:
		if self.isBusy():
			return False

		self._broadcastRoom = commons.cleanRoomNameToSiteId(room)

		if not uid:
			uid = self._getFreeUID()

		self._logger.info('[{}] Started broadcasting on {} for new device addition. Attributed uid: {}'.format(self.name, self._broadcastPort, uid))
		self._listenSocket.listen(2)
		managers.ThreadManager.newThread(name='broadcast', target=self.broadcast, args=[room, uid, siteId])

		self._broadcastTimer = managers.ThreadManager.newTimer(interval = 300, func = self.stopBroadcasting)

		managers.ModuleManager.broadcast(method = 'onBroadcastingForNewDeviceStart')
		return True


	def stopBroadcasting(self):
		self._logger.info('Stopped broadcasting for new devices')
		self._broadcastFlag.clear()

		if self._broadcastTimer:
			self._broadcastTimer.cancel()

		self._broadcastRoom = ''
		managers.ModuleManager.broadcast(method='onBroadcastingForNewDeviceStop')


	def broadcast(self, room: str, uid: str, replyOnSiteId: str):
		self._broadcastFlag.set()
		while self._broadcastFlag.isSet():
			self._broadcastSocket.sendto(bytes('{}:{}:{}:{}'.format(commons.getLocalIp(), self._listenPort, room, uid), encoding='utf8'), ('<broadcast>', self._broadcastPort))
			try:
				sock, address = self._listenSocket.accept()
				sock.settimeout(None)
				answer = sock.recv(1024).decode()

				deviceIp = answer.split(':')[0]
				deviceType = answer.split(':')[1]

				if deviceType.lower() == 'alicesatellite':
					for satellite in self.getDevicesByRoom(room):
						if satellite.deviceType.lower() == 'alicesatellite':
							self._logger.warning('[{}] Cannot have more than one Alice module per room, aborting'.format(self.name))
							managers.MqttServer.say(text = managers.TalkManager.randomTalk('maxOneAlicePerRoom', module = 'system'), client = replyOnSiteId)
							answer = 'nok'
							break

				if answer != 'nok':
					if self.addNewDevice(deviceType, room, uid):
						self._logger.info('[{}] New device with uid {} successfully added'.format(self.name, uid))
						managers.MqttServer.say(text = managers.TalkManager.randomTalk('newDeviceAdditionSuccess', module = 'system'), client = replyOnSiteId)
						answer = 'ok'
					else:
						self._logger.info('[{}] Failed adding new device'.format(self.name))
						managers.MqttServer.say(text = managers.TalkManager.randomTalk('newDeviceAdditionFailed', module = 'system'), client = replyOnSiteId)
						answer = 'nok'

					if deviceType.lower() == 'alicesatellite':
						managers.ThreadManager.doLater(interval=5, func=managers.WakewordManager.uploadToNewDevice, args=[uid])

				self._broadcastSocket.sendto(bytes(answer, encoding='utf8'), (deviceIp, self._broadcastPort))
				self.stopBroadcasting()
			except socket.timeout:
				pass


	def deviceConnecting(self, uid: str) -> Optional[Device]:
		if uid not in self._devices:
			self._logger.warning('[{}] A device with uid {} tried to connect but is unknown'.format(self.name, uid))
			return None

		if not self._devices[uid].connected:
			self._devices[uid].connected = True
			managers.broadcast('onDeviceConnecting', exceptions=[self.name])
			managers.ModuleManager.broadcast('onDeviceConnecting')

		return self._devices[uid]


	def deviceDisconnecting(self, uid: str):
		if uid not in self._devices:
			return False

		if self._devices[uid].connected:
			self._devices[uid].connected = False
			managers.broadcast('onDeviceDisconnecting', exceptions=[self.name])
			managers.ModuleManager.broadcast('onDeviceDisconnecting')


	def getDevicesByRoom(self, room: str, connectedOnly: bool = False) -> list:
		deviceList = list()
		for uid, device in self._devices.items():
			if device.room.lower() == room.lower():
				if connectedOnly:
					if device.connected:
						deviceList.append(device)
				else:
					deviceList.append(device)
		return deviceList


	def getDevicesByType(self, deviceType: str, connectedOnly: bool = False) -> list:
		deviceList = list()
		for uid, device in self._devices.items():
			if device.deviceType == deviceType:
				if connectedOnly:
					if device.connected:
						deviceList.append(device)
				else:
					deviceList.append(device)

		return deviceList


	def getDeviceByUID(self, uid: str) -> Device:
		return self._devices.get(uid, None)
