from contextlib import contextmanager

from core.base.SuperManager import SuperManager
from core.ProjectAliceExceptions import OfflineError


@contextmanager
def Online():
	internetManager = SuperManager.getInstance().internetManager
	if internetManager.online:
		try:
			yield
		except:
			if internetManager.checkOnlineState():
				raise
	raise OfflineError
