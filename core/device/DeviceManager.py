import os
import socket
import sqlite3
import threading
import time
import uuid
from random import shuffle
from typing import Optional

import esptool # type: ignore
import requests
from esptool import ESPLoader # type: ignore
from paho.mqtt.client import MQTTMessage # type: ignore
from serial import Serial # type: ignore
from serial.tools import list_ports # type: ignore

from core.base.SuperManager import SuperManager
from core.base.model.Manager import Manager
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


	def __init__(self):
		super().__init__(self.NAME, self.DATABASE)

		self._devices           = dict()
		self._broadcastRoom     = ''
		self._broadcastFlag     = threading.Event()

		self._broadcastPort     = None
		self._broadcastTimer    = None

		self._flashThread       = None

		self._listenPort        = None

		self._broadcastSocket   = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
		self._broadcastSocket.setsockopt(socket.SOL_SOCKET, socket.SO_BROADCAST, 1)
		self._broadcastSocket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)

		self._listenSocket      = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
		self._listenSocket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
		self._listenSocket.settimeout(2)


	def onStart(self):
		super().onStart()

		self._broadcastPort = int(self.ConfigManager.getAliceConfigByName('newDeviceBroadcastPort'))  # Default 12354
		self._listenPort = self._broadcastPort + 1

		self._listenSocket.bind(('', self._listenPort))

		self.loadDevices()
		self.logInfo(f'- Loaded {len(self._devices)} devices')


	@property
	def broadcastRoom(self) -> str:
		return self._broadcastRoom


	def onBooted(self):
		self.MqttManager.publish(topic='projectalice/devices/coreReconnection')


	def onStop(self):
		super().onStop()
		self.stopBroadcasting()
		self._broadcastSocket.close()
		self.MqttManager.publish(topic='projectalice/devices/coreDisconnection')


	def onMessage(self, message: MQTTMessage) -> Optional[DialogSession]:
		if not 'projectalice/devices/' in message.topic:
			return None

		return self.DialogSessionManager.addTempSession(sessionId=uuid.uuid4(), message=message)


	def loadDevices(self):
		for row in self.databaseFetch(tableName='devices', query='SELECT * FROM :__table__', method='all'):
			self._devices[row['uid']] = Device(row)


	# noinspection SqlResolve
	def isUIDAvailable(self, uid: str) -> bool:
		try:
			count = self.databaseFetch(tableName='devices', query='SELECT COUNT() FROM :__table__ WHERE uid = :uid', values={'uid': uid})[0]
			return count <= 0
		except sqlite3.OperationalError as e:
			self.logWarning(f"Couldn't check device from database: {e}")
			return False


	def isBusy(self) -> bool:
		return self.ThreadManager.isThreadAlive('broadcast')


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
			self.logWarning(f"Couldn't insert device in database: {e}")
			return False


	def startTasmotaFlashingProcess(self, room: str, espType: str, session: DialogSession) -> bool:
		self.ThreadManager.doLater(interval=0.5, func=self.MqttManager.endDialog, args=[session.sessionId, self.TalkManager.randomTalk('connectESPForFlashing', module='AliceCore')])

		self._broadcastFlag.set()
		if os.path.isfile('sonoff.bin'):
			os.remove('sonoff.bin')

		try:
			req = requests.get('https://github.com/arendst/Sonoff-Tasmota/releases/download/v6.5.0/sonoff.bin')
			with open('sonoff.bin', 'wb') as file:
				file.write(req.content)
				self.logInfo('Downloaded sonoff.bin')
		except Exception as e:
			self.logError(f'Something went wrong downloading sonoff.bin: {e}')
			self._broadcastFlag.clear()
			return False

		self.ThreadManager.newThread(name='flashThread', target=self.doFlashTasmota, args=[room, espType, session.siteId])
		return True


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


	def doFlashTasmota(self, room: str, espType: str, siteId: str):
		port = self.findUSBPort(timeout=60)
		if port:
			self.MqttManager.say(text=self.TalkManager.randomTalk('usbDeviceFound', module='AliceCore'), client=siteId)
			try:
				mac = ESPLoader.detect_chip(port=port, baud=115200).read_mac()
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
				self.logError(f'Something went wrong flashing esp device: {e}')
				self.MqttManager.say(text=self.TalkManager.randomTalk('espFailed', module='AliceCore'), client=siteId)
				self._broadcastFlag.clear()
				return
		else:
			self.MqttManager.say(text=self.TalkManager.randomTalk('noESPFound', module='AliceCore'), client=siteId)
			self._broadcastFlag.clear()
			return

		self.logInfo('Tasmota flash done')
		self.MqttManager.say(text=self.TalkManager.randomTalk('espFlashedUnplugReplug', module='AliceCore'), client=siteId)
		found = self.findUSBPort(timeout = 60)
		if found:
			self.MqttManager.say(text=self.TalkManager.randomTalk('espFoundReadyForConf', module='AliceCore'), client=siteId)
			time.sleep(10)
			uid = self._getFreeUID(mac)
			tasmotaConfigs = TasmotaConfigs(deviceType=espType, uid=uid)
			confs = tasmotaConfigs.getBacklogConfigs(room)
			if not confs:
				self.logError('Something went wrong getting tasmota configuration')
				self.MqttManager.say(text=self.TalkManager.randomTalk('espFailed', module='AliceCore'), client=siteId)
			else:
				serial = Serial()
				serial.baudrate = 115200
				serial.port = port
				serial.open()

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
							serial.write(piece.encode())
							self.logInfo('Sent {}'.format(piece.replace('\r\n', '')))
							time.sleep(0.5)

						time.sleep(group['waitAfter'])

					serial.close()
					self.logInfo('Tasmota flashing and configuring done')
					self.MqttManager.say(text=self.TalkManager.randomTalk('espFlashingDone', module='AliceCore'), client=siteId)
					self.addNewDevice(espType, room, uid)
					self._broadcastFlag.clear()

				except Exception as e:
					self.logError(f'Something went wrong writting configuration to esp device: {e}')
					self.MqttManager.say(text=self.TalkManager.randomTalk('espFailed', module='AliceCore'), client=siteId)
					self._broadcastFlag.clear()
					serial.close()
		else:
			self.MqttManager.say(text=self.TalkManager.randomTalk('espFailed', module='AliceCore'), client=siteId)
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

		self.logInfo(f'Started broadcasting on {self._broadcastPort} for new device addition. Attributed uid: {uid}')
		self._listenSocket.listen(2)
		self.ThreadManager.newThread(name='broadcast', target=self.broadcast, args=[room, uid, siteId])

		self._broadcastTimer = self.ThreadManager.newTimer(interval=300, func=self.stopBroadcasting)

		self.ModuleManager.broadcast(method = 'onBroadcastingForNewDeviceStart')
		return True


	def stopBroadcasting(self):
		self.logInfo('Stopped broadcasting for new devices')
		self._broadcastFlag.clear()

		if self._broadcastTimer:
			self._broadcastTimer.cancel()

		self._broadcastRoom = ''
		self.ModuleManager.broadcast(method='onBroadcastingForNewDeviceStop')


	def broadcast(self, room: str, uid: str, replyOnSiteId: str):
		self._broadcastFlag.set()
		while self._broadcastFlag.isSet():
			self._broadcastSocket.sendto(bytes(f'{commons.getLocalIp()}:{self._listenPort}:{room}:{uid}', encoding='utf8'), ('<broadcast>', self._broadcastPort))
			try:
				sock, address = self._listenSocket.accept()
				sock.settimeout(None)
				answer = sock.recv(1024).decode()

				deviceIp = answer.split(':')[0]
				deviceType = answer.split(':')[1]

				if deviceType.lower() == 'alicesatellite':
					for satellite in self.getDevicesByRoom(room):
						if satellite.deviceType.lower() == 'alicesatellite':
							self.logWarning('Cannot have more than one Alice module per room, aborting')
							self.MqttManager.say(text = self.TalkManager.randomTalk('maxOneAlicePerRoom', module='system'), client=replyOnSiteId)
							answer = 'nok'
							break

				if answer != 'nok':
					if self.addNewDevice(deviceType, room, uid):
						self.logInfo(f'New device with uid {uid} successfully added')
						self.MqttManager.say(text = self.TalkManager.randomTalk('newDeviceAdditionSuccess', module='system'), client=replyOnSiteId)
						answer = 'ok'
					else:
						self.logInfo('Failed adding new device')
						self.MqttManager.say(text = self.TalkManager.randomTalk('newDeviceAdditionFailed', module='system'), client=replyOnSiteId)
						answer = 'nok'

					if deviceType.lower() == 'alicesatellite':
						self.ThreadManager.doLater(interval=5, func=self.WakewordManager.uploadToNewDevice, args=[uid])

				self._broadcastSocket.sendto(bytes(answer, encoding='utf8'), (deviceIp, self._broadcastPort))
				self.stopBroadcasting()
			except socket.timeout:
				self.logInfo('No device query received')


	def deviceConnecting(self, uid: str) -> Optional[Device]:
		if uid not in self._devices:
			self.logWarning(f'A device with uid {uid} tried to connect but is unknown')
			return None

		if not self._devices[uid].connected:
			self._devices[uid].connected = True
			SuperManager.getInstance().broadcast('onDeviceConnecting', exceptions=[self.name])
			self.ModuleManager.broadcast('onDeviceConnecting')

		return self._devices[uid]


	def deviceDisconnecting(self, uid: str):
		if uid not in self._devices:
			return False

		if self._devices[uid].connected:
			self._devices[uid].connected = False
			SuperManager.getInstance().broadcast('onDeviceDisconnecting', exceptions=[self.name])
			self.ModuleManager.broadcast('onDeviceDisconnecting')


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
		for device in self._devices.values():
			if device.deviceType == deviceType:
				if connectedOnly:
					if device.connected:
						deviceList.append(device)
				else:
					deviceList.append(device)

		return deviceList


	def getDeviceByUID(self, uid: str) -> Device:
		return self._devices.get(uid, None)
