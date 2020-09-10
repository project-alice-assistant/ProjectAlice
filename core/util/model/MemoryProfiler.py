from pympler import classtracker, muppy, summary, tracker

from core.base.model.ProjectAliceObject import ProjectAliceObject


class MemoryProfiler:

	def __init__(self):
		self._tracker = tracker.SummaryTracker()
		self._aliceTracker = classtracker.ClassTracker()
		self._aliceTracker.track_class(ProjectAliceObject)


	def dump(self):
		allObjects = muppy.get_objects()
		summ = summary.summarize(allObjects)

		print('----- Objects summary -----')
		summary.print_(summ)

		print('----- ProjectAliceObject tracker -----')
		self._aliceTracker.create_snapshot()
		self._aliceTracker.stats.print_summary()

		if self._tracker:
			print('----- Evolution over time -----')
			self._tracker.print_diff()

		self._tracker = tracker.SummaryTracker()
