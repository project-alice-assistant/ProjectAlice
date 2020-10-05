from pympler import classtracker, muppy, summary, tracker

from core.base.model.ProjectAliceObject import ProjectAliceObject


class MemoryProfiler(ProjectAliceObject):

	def __init__(self):
		super().__init__()
		self._tracker = None
		self._aliceTracker = None


	def start(self):
		self._tracker = tracker.SummaryTracker()
		self._aliceTracker = classtracker.ClassTracker()
		self._aliceTracker.track_class(ProjectAliceObject)


	def dump(self):
		allObjects = muppy.get_objects()
		summ = summary.summarize(allObjects)

		self.logDebug('----- Objects summary -----')
		for line in summary.format_(summ, limit=15, sort='size', order='descending'):
			self.logDebug(line)

		if self._aliceTracker:
			self.logDebug('----- ProjectAliceObject tracker -----')
			self._aliceTracker.create_snapshot()
			self._aliceTracker.stats.print_summary()

		if self._tracker:
			self.logDebug('----- Evolution over time -----')
			for line in summary.format_(self._tracker.diff()):
				self.logDebug(line)

			self._tracker = tracker.SummaryTracker()
