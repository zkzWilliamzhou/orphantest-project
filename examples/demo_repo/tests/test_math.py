import unittest


class TestMath(unittest.TestCase):
    def test_add(self):
        self.assertEqual(1 + 1, 2)

    def test_multiply(self):
        self.assertEqual(3 * 4, 12)
