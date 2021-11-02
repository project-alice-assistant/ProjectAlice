#  Copyright (c) 2021
#
#  This file, MemoryProfiler.py, is part of Project Alice.
#
#  Project Alice is free software: you can redistribute it and/or modify
#  it under the terms of the GNU General Public License as published by
#  the Free Software Foundation, either version 3 of the License, or
#  (at your option) any later version.
#
#  This program is distributed in the hope that it will be useful,
#  but WITHOUT ANY WARRANTY; without even the implied warranty of
#  MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#  GNU General Public License for more details.
#
#  You should have received a copy of the GNU General Public License
#  along with this program.  If not, see <https://www.gnu.org/licenses/>
#
#  Last modified: 2021.04.13 at 12:56:48 CEST

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
