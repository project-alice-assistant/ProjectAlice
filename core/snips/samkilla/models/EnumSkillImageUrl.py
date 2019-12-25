import os

from core.snips.samkilla.models.Singleton import Singleton

DEFAULT_RESOURCE = 'default-bundle.svg'


class EnumSkillImageUrl(Singleton):
	default = DEFAULT_RESOURCE
	air = 'bundle-air.svg'
	assistant = 'bundle-assistant.svg'
	bank = 'bundle-bank.svg'
	battery = 'bundle-battery.svg'
	bluetooth = 'bundle-bluetooth.svg'
	box = 'bundle-box.svg'
	calculator = 'bundle-calculator.svg'
	calendar = 'bundle-calendar.svg'
	camera = 'bundle-camera.svg'
	car = 'bundle-car.svg'
	coffee = 'bundle-coffee.svg'
	direction = 'bundle-direction.svg'
	drink = 'bundle-drink.svg'
	film = 'bundle-film.svg'
	folder = 'bundle-folder.svg'
	games = 'bundle-games.svg'
	headphones = 'bundle-headphones.svg'
	home = 'bundle-home.svg'
	key = 'bundle-key.svg'
	lamp = 'bundle-lamp.svg'
	lights = 'bundle-lights.svg'
	location = 'bundle-location.svg'
	lock = 'bundle-lock.svg'
	map = 'bundle-map.svg'
	medicine = 'bundle-medicine.svg'
	microphone = 'bundle-microphone.svg'
	monitor = 'bundle-monitor.svg'
	movie = 'bundle-movie.svg'
	music = 'bundle-music.svg'
	plant = 'bundle-plant.svg'
	radio = 'bundle-radio.svg'
	rain = 'bundle-rain.svg'
	recording = 'bundle-recording.svg'
	restart = 'bundle-restart.svg'
	security = 'bundle-security.svg'
	settings = 'bundle-settings.svg'
	shutdown = 'bundle-shutdown.svg'
	sport = 'bundle-sport.svg'
	spotify = 'bundle-spotify.svg'
	star = 'bundle-star.svg'
	store = 'bundle-store.svg'
	sun = 'bundle-sun.svg'
	temperature = 'bundle-temperature.svg'
	time = 'bundle-time.svg'
	timer = 'bundle-timer.svg'
	transport = 'bundle-transport.svg'
	vynil = 'bundle-vynil.svg'
	wallet = 'bundle-wallet.svg'
	weather = 'bundle-weather.svg'
	wind = 'bundle-wind.svg'
	yoga = 'bundle-yoga.svg'


	def __init__(self):
		Singleton.__init__(self, 'EnumSkillImageUrl')


	def getResourceFileByAttr(self, attrName: str) -> str:
		return getattr(self, attrName)


	@staticmethod
	def getImageUrl(urlPrefix: str, enumImageUrlKey: str = DEFAULT_RESOURCE):
		return f'{urlPrefix}/images/bundles/{enumImageUrlKey}'


	@staticmethod
	def urlToResourceKey(url: str) -> str:
		return os.path.basename(url).replace('.svg', '').replace('bundle', '').replace('-', '')
