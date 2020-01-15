import unittest

from core.base.model.Version import Version

class TestVersion(unittest.TestCase):

	def test_fromString(self):
		self.assertEqual(Version.fromString('1.2.3-a4'), Version(1, 2, 3, 'a', 4))
		self.assertEqual(Version.fromString('1.2.3'), Version(1, 2, 3, 'release', 1))
		self.assertEqual(Version.fromString('1.2'), Version(1, 2, 0, 'release', 1))
		self.assertEqual(Version.fromString('test'), Version(0, 0, 0, '', 0))
		self.assertFalse(Version.fromString('test').isVersionNumber)
		self.assertTrue(Version.fromString('1.2').isVersionNumber)

	def test_stringConvertsion(self):
		self.assertEqual(str(Version(1, 2, 0, 'release', 1)), '1.2.0')
		self.assertEqual(str(Version(1, 2, 0, 'a', 3)), '1.2.0-a3')

	def test_comparison(self):
		self.assertTrue(
			Version(1, 0, 0, 'release', 1) > Version(1, 0, 0, 'rc', 1) > Version(1, 0, 0, 'b', 1) > Version(1, 0, 0, 'a', 1) > Version(0, 9, 0, 'release', 1)
		)


if __name__ == "__main__":
	unittest.main()
