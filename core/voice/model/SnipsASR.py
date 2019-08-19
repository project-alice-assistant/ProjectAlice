# -*- coding: utf-8 -*-
from core.voice.model.ASR import ASR


class SnipsASR(ASR):

	def __init__(self):
		super().__init__()
		pass

	def isCapableOfArbitraryCapture(self):
		return False
