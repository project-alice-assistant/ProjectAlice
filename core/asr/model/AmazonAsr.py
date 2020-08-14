from core.asr.model.Asr import Asr

try:
	from boto3 import client
except:
	pass # Auto installed



class AmazonAsr(Asr):

	NAME = 'Amazon Asr'
	DEPENDENCIES = {
		'system': [],
		'pip'   : {
			'boto3==1.13.19'
		}
	}

	def __init__(self):
		super().__init__()
		self._capableOfArbitraryCapture = True
		self._isOnlineASR = True

		self._client: client = None


	def onStart(self):
		super().onStart()
		self._client = client(
			'transcribe',
			region_name=self.ConfigManager.getAliceConfigByName('awsRegion'),
			aws_access_key_id=self.ConfigManager.getAliceConfigByName('awsAccessKey'),
			aws_secret_access_key=self.ConfigManager.getAliceConfigByName('awsSecretKey')
		)
