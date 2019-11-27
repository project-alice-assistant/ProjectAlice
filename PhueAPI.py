from __future__ import annotations

import json
import time
from dataclasses import dataclass
from json import JSONDecodeError
from pathlib import Path
from typing import Optional

import requests
from requests import RequestException, Response


class UnauthorizedUser(Exception): pass
class LinkButtonNotPressed(Exception): pass
class IPNotPhueBridge(Exception): pass
class SelectorError(Exception): pass
class NoSuchLight(Exception): pass
class LightNotReachable(Exception): pass


class Bridge:

	def __init__(self, ip: str = None, deviceName: str = 'phuepython', username: str = None, confFile: Path = Path('phueAPI.json')):
		self._ip = ip
		self._deviceName = deviceName
		self._confFile = confFile
		self._username = username
		self._connected = False

		self._groups = dict()
		self._lights = dict()

		conf = self.loadConfigFileData()
		if conf:
			if ip and ip != conf['ip']:
				self._confFile.unlink()
			elif not ip:
				self._ip = conf['ip']

			if username and username != conf['ip']:
				self._confFile.unlink()
			elif not username:
				self._username = conf['username']

	@property
	def lights(self) -> dict:
		return self._lights


	def light(self, lightId: int = None, lightName: str = None) -> Light:
		if lightId is None and lightName is None:
			raise SelectorError('Cannot get light without id and/or name')

		if lightId is None:
			for light in self._lights.values():
				if light.name == lightName:
					return light
			raise NoSuchLight
		else:
			if lightId not in self._lights:
				raise NoSuchLight
			return self._lights[lightId]


	@property
	def connected(self) -> bool:
		return self._connected


	def loadConfigFileData(self) -> Optional[dict]:
		try:
			if not self._confFile.exists():
				return None

			with self._confFile.open() as fp:
				return json.load(fp)
		except Exception as e:
			print(f'Error opening config file: {e}')
			return None


	def saveConfigFile(self):
		try:
			self._confFile.write_text(json.dumps({'ip': self._ip, 'username': self._username}))
		except Exception as e:
			print(f'Error saving config file: {e}')
			return None


	def connect(self, autodiscover: bool = True) -> bool:
		try:
			if not self._ip and autodiscover:
				self.autodiscover()

			if not self._username:
				raise UnauthorizedUser

			req = self.sendRequest(url=f'/{self._username}')
			answer = req.json()
			if self.errorReturned(answer):
				raise UnauthorizedUser

			self._connected = True
		except OSError as e:
			print(f'Bridge connection error: {e}')
			return False
		except UnauthorizedUser:
			raise
		except Exception as e:
			print(f'Something went wrong connecting to the bridge: {e}')
			return False

		try:
			self.loadDevices()
		except Exception as e:
			print(f'Something went wrong loading devices assigned to the bridge: {e}')

		return True


	def register(self, saveConnection: bool = True) -> bool:
		try:
			req = self.sendRequest(data={'devicetype': f'phueAPI#{self._deviceName}'}, method='POST')
			answer = req.json()
			if self.errorReturned(answer):
				raise LinkButtonNotPressed
			elif self.successReturned(answer):
				if saveConnection:
					self._username = answer[0]['success']['username']
					self.saveConfigFile()
				return True
			else:
				raise Exception('Unsupported answer from bridge while registering')
		except LinkButtonNotPressed:
			raise
		except Exception as e:
			print(f'Bridge register failed: {e}')
			return False


	@staticmethod
	def isPhueBridge(ip) -> bool:
		try:
			req = requests.get(f'http://{ip}/api/config', timeout=2)
			data = req.json()
			if 'swversion' in data and 'bridgeid' in data:
				return True

			return False
		except Exception:
			return False


	def sendAuthRequest(self, url: str, data: dict = None, method: str = 'GET', silent: bool = False) -> Response:
		if self._username not in url:
			url = f'/{self._username}{"/" if not url.startswith("/") else ""}{url}'
		return self.sendRequest(url=url, data=data, method=method, silent=silent)


	def sendRequest(self, url: str = None, data: dict = None, method: str = 'GET', silent: bool = False) -> Response:
		data = data or dict()
		url = url or '/api'
		if not url.startswith('/api'):
			url = f'/api{"/" if not url.startswith("/") else ""}{url}'

		try:
			req = requests.request(method=method, url=f'http://{self._ip}{url}', data=json.dumps(data), timeout=2)
			return req
		except Exception as e:
			if not silent:
				print(f'API request error: {e}')
			raise


	def autodiscover(self):
		print('Trying to autodiscover the bridge on the network')
		try:
			request = requests.get('https://www.meethue.com/api/nupnp')
			print('Obtained a list of potential devices')
			for device in request.json():
				print(f'Testing {device["internalipaddress"]}')
				if self.isPhueBridge(device['internalipaddress']):
					self._ip = device['internalipaddress']
					self.saveConfigFile()
					print(f'Found bridge at {self._ip}')
					break
		except (RequestException, JSONDecodeError):
			print('Something went wrong trying to discover the bridge on your network')


	def loadDevices(self):
		req = self.sendAuthRequest(url='/groups')
		answer = req.json()
		for groupId, data in answer.items():
			if 'class' in data:
				data['clazz'] = data.pop('class')
			groupId = int(groupId)
			group = Group(**data)
			group.init(groupId, self)
			self._groups[groupId] = group

		req = self.sendAuthRequest(url='/lights')
		answer = req.json()
		for lightId, data in answer.items():
			lightId = int(lightId)
			light = Light(**data)
			light.init(lightId, self)
			self._lights[lightId] = light


	@staticmethod
	def errorReturned(answer: dict) -> bool:
		return isinstance(answer, list) and 'error' in answer[0]


	@staticmethod
	def successReturned(answer: dict) -> bool:
		return isinstance(answer, list) and 'success' in answer[0]


@dataclass
class Group:
	name: str
	lights: list
	sensors: list
	type: str
	state: dict
	recycle: bool
	action: dict
	clazz: str = None
	stream: dict = None
	locations: dict = None
	id: int = None
	bridge: Bridge = None


	def init(self, groupId: int, bridgeInstance: Bridge):
		self.id = groupId
		self.bridge = bridgeInstance


@dataclass
class Light:
	state: dict
	swupdate: dict
	type: str
	name: str
	modelid: str
	manufacturername: str
	productname: str
	capabilities: dict
	config: dict
	uniqueid: str
	swversion: str
	swconfigid: str = ''
	productid: str = ''
	id: int = None
	bridge: Bridge = None


	def init(self, lightId: int, bridgeInstance: Bridge):
		self.id = lightId
		self.bridge = bridgeInstance


	def on(self):
		self.request(url=f'/{self.id}/state', method='PUT', data={'on': True})


	def off(self):
		self.request(url=f'/{self.id}/state', method='PUT', data={'on': False})


	def alert(self, state: str = 'lselect'):
		self.request(url=f'/{self.id}/state', method='PUT', data={'alert': state})


	def effect(self, effect: str = 'colorloop'):
		self.request(url=f'/{self.id}/state', method='PUT', data={'effect': effect})


	@property
	def brightness(self) -> int:
		return self.state['bri']


	@brightness.setter
	def brightness(self, brigthness: int):
		if brigthness == 0:
			self.off()
			self.state['bri'] = 0
			return

		brigthness = sorted((1, brigthness, 254))[1]

		self.state['bri'] = brigthness
		self.request(url=f'/{self.id}/state', method='PUT', data={'bri': brigthness})


	@property
	def saturation(self) -> int:
		return self.state['sat']


	@saturation.setter
	def saturation(self, saturation: int):
		saturation = sorted((1, saturation, 254))[1]

		self.state['sat'] = saturation
		self.request(url=f'/{self.id}/state', method='PUT', data={'sat': saturation})


	@property
	def hue(self) -> int:
		return self.state['hue']


	@hue.setter
	def hue(self, hue: int):
		hue = sorted((0, hue, 65535))[1]

		self.state['hue'] = hue
		self.request(url=f'/{self.id}/state', method='PUT', data={'hue': hue})


	@property
	def reachable(self) -> bool:
		return self.state['reachable']


	def delete(self):
		self.request(url=f'/{self.id}', method='DELETE')


	def request(self, url: str, data: dict = None, method: str = 'GET'):
		if not self.reachable:
			raise LightNotReachable

		self.bridge.sendAuthRequest(url=f'/lights{"/" if not url.startswith("/") else ""}{url}', method=method, data=data)


if __name__ == '__main__':
	bridge = Bridge()

	try:
		if bridge.connect():
			print('Connected to Philips Hue bridge')

			backup = bridge.light(12).brightness
			bridge.light(12).brightness = 100
			time.sleep(3)
			bridge.light(12).brightness = backup

	except UnauthorizedUser:
		try:
			bridge.register()
		except LinkButtonNotPressed:
			print('Please press your bridge button')
