#  Copyright (c) 2021
#
#  This file, test_Version.py, is part of Project Alice.
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
#  Last modified: 2021.04.13 at 12:56:50 CEST

import unittest

from ProjectAlice.core.base.model.Version import Version


class TestVersion(unittest.TestCase):

	def test_fromString(self):
		self.assertEqual(Version.fromString('1.2.3-a4'), Version(1, 2, 3, 'a', 4))
		self.assertEqual(Version.fromString('1.2.3'), Version(1, 2, 3, 'release', 1))
		self.assertEqual(Version.fromString('1.2'), Version(1, 2, 0, 'release', 1))
		self.assertEqual(Version.fromString('test'), Version(0, 0, 0, '', 0))
		self.assertFalse(Version.fromString('test').isVersionNumber)
		self.assertTrue(Version.fromString('1.2').isVersionNumber)

	def test_stringConversion(self):
		self.assertEqual(str(Version(1, 2, 0, 'release', 1)), '1.2.0')
		self.assertEqual(str(Version(1, 2, 0, 'a', 3)), '1.2.0-a3')

	def test_comparison(self):
		self.assertTrue(
			Version(1, 0, 0, 'release', 1) > Version(1, 0, 0, 'rc', 1) > Version(1, 0, 0, 'b', 1) > Version(1, 0, 0, 'a', 1) > Version(0, 9, 0, 'release', 1)
		)


if __name__ == "__main__":
	unittest.main()
