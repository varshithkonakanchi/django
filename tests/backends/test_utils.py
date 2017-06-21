"""Tests for django.db.backends.utils"""
from decimal import Decimal, Rounded

from django.db.backends.utils import format_number, truncate_name
from django.test import SimpleTestCase


class TestUtils(SimpleTestCase):

    def test_truncate_name(self):
        self.assertEqual(truncate_name('some_table', 10), 'some_table')
        self.assertEqual(truncate_name('some_long_table', 10), 'some_la38a')
        self.assertEqual(truncate_name('some_long_table', 10, 3), 'some_loa38')
        self.assertEqual(truncate_name('some_long_table'), 'some_long_table')
        # "user"."table" syntax
        self.assertEqual(truncate_name('username"."some_table', 10), 'username"."some_table')
        self.assertEqual(truncate_name('username"."some_long_table', 10), 'username"."some_la38a')
        self.assertEqual(truncate_name('username"."some_long_table', 10, 3), 'username"."some_loa38')

    def test_format_number(self):
        def equal(value, max_d, places, result):
            self.assertEqual(format_number(Decimal(value), max_d, places), result)

        equal('0', 12, 3, '0.000')
        equal('0', 12, 8, '0.00000000')
        equal('1', 12, 9, '1.000000000')
        equal('0.00000000', 12, 8, '0.00000000')
        equal('0.000000004', 12, 8, '0.00000000')
        equal('0.000000008', 12, 8, '0.00000001')
        equal('0.000000000000000000999', 10, 8, '0.00000000')
        equal('0.1234567890', 12, 10, '0.1234567890')
        equal('0.1234567890', 12, 9, '0.123456789')
        equal('0.1234567890', 12, 8, '0.12345679')
        equal('0.1234567890', 12, 5, '0.12346')
        equal('0.1234567890', 12, 3, '0.123')
        equal('0.1234567890', 12, 1, '0.1')
        equal('0.1234567890', 12, 0, '0')
        equal('0.1234567890', None, 0, '0')
        equal('1234567890.1234567890', None, 0, '1234567890')
        equal('1234567890.1234567890', None, 2, '1234567890.12')
        equal('0.1234', 5, None, '0.1234')
        equal('123.12', 5, None, '123.12')

        with self.assertRaises(Rounded):
            equal('0.1234567890', 5, None, '0.12346')
        with self.assertRaises(Rounded):
            equal('1234567890.1234', 5, None, '1234600000')
