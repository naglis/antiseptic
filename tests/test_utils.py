#!/usr/bin/env python

"""
test_utils
----------------------------------

tests for `antiseptic.utils` module.
"""

import unittest

from antiseptic.utils import split_rev


class TestSplitRev(unittest.TestCase):

    def test_simple(self):
        date, rev = split_rev('123456780')
        self.assertEqual(date, 12345678)
        self.assertEqual(rev, 0)

    def test_non_digit_raises_ValueError(self):
        with self.assertRaises(ValueError):
            _, _ = split_rev('12345678a')


if __name__ == '__main__':
    unittest.main()
