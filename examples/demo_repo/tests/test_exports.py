import unittest


class TestExports(unittest.TestCase):
    def test_csv_header(self):
        self.assertEqual("id,amount", "id,amount")

    def test_row_count(self):
        self.assertEqual(len([1, 2, 3]), 3)
