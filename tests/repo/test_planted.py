"""TEMPORARY (FND-032, step 12): a test that fails on Windows only."""

import sys
import unittest


class PlantedTest(unittest.TestCase):
    def test_fails_on_windows_only(self) -> None:
        self.assertNotEqual(sys.platform, "win32")


if __name__ == "__main__":
    unittest.main()
