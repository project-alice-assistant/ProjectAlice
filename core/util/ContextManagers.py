from contextlib import contextmanager

from core.ProjectAliceExceptions import OfflineError
from core.base.SuperManager import SuperManager


@contextmanager
def Online(): #NOSONAR
	internetManager = SuperManager.getInstance().internetManager
	if internetManager.online:
		try:
			yield
		except:
			if not internetManager.checkOnlineState():
				raise
			else:
				yield

	raise OfflineError
