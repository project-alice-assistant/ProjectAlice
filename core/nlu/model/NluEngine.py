from pathlib import Path

from core.base.model.ProjectAliceObject import ProjectAliceObject


class NluEngine(ProjectAliceObject):
	NAME = ''


	def __init__(self):
		super().__init__()


	def start(self):
		self.logInfo(f'Starting {self.NAME}')


	def stop(self):
		self.logInfo(f'Stopping {self.NAME}')


	def train(self):
		self.logInfo(f'Training {self.NAME}')


	def convertDialogTemplate(self, file: Path):
		self.logFatal(f'NLU Engine {self.NAME} is missing implementation of "convertDialogTemplate"')
