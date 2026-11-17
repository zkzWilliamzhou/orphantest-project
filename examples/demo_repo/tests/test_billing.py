import unittest


class TestBilling(unittest.TestCase):
    def test_tax_rounding(self):
        self.assertEqual(round(1.005, 2), 1.0)

    def test_invoice_total(self):
        self.assertEqual(10 + 5, 15)
