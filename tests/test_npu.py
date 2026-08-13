"""npu.py의 기본 계산 테스트."""

import unittest

from npu import (
    compare_scores,
    mac_score,
    make_pattern,
    measure_mac_time,
    normalize_label,
    validate_matrix,
)


class NpuTest(unittest.TestCase):
    def test_validate_square_matrix(self):
        self.assertEqual(validate_matrix([[1, 0], [0, 1]]), 2)

    def test_reject_non_square_matrix(self):
        with self.assertRaises(ValueError):
            validate_matrix([[1, 0], [1]])

    def test_reject_non_number(self):
        with self.assertRaises(ValueError):
            validate_matrix([[1, 0], [0, "x"]])

    def test_normalize_labels(self):
        self.assertEqual(normalize_label("+"), "Cross")
        self.assertEqual(normalize_label("cross"), "Cross")
        self.assertEqual(normalize_label("X"), "X")

    def test_mac_score(self):
        pattern = [[1, 0], [0, 1]]
        cross_filter = [[0, 1], [1, 0]]
        x_filter = [[1, 0], [0, 1]]
        self.assertEqual(mac_score(pattern, cross_filter), 0)
        self.assertEqual(mac_score(pattern, x_filter), 2)

    def test_mac_rejects_different_sizes(self):
        with self.assertRaises(ValueError):
            mac_score([[1]], [[1, 0], [0, 1]])

    def test_near_tie_is_undecided(self):
        self.assertEqual(compare_scores(1.0, 1.0 + 1e-12), "UNDECIDED")

    def test_larger_score_wins(self):
        self.assertEqual(compare_scores(5, 1), "A")
        self.assertEqual(compare_scores(1, 5), "B")

    def test_measure_time_returns_number(self):
        pattern = [[1, 0], [0, 1]]
        self.assertGreaterEqual(measure_mac_time(pattern, pattern, 10), 0)

    def test_make_pattern(self):
        self.assertEqual(len(make_pattern(5, "Cross")), 5)
        self.assertEqual(len(make_pattern(13, "X")), 13)


if __name__ == "__main__":
    unittest.main()
