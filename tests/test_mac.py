"""mac.py의 기본 계산을 확인합니다."""


import unittest

from mac import (
    calculate_mac,
    calculate_mac_1d,
    check_matrix,
    choose_winner,
    flatten_matrix,
    make_pattern,
    normalize_label,
)


class MacTest(unittest.TestCase):

    def test_cross_mac_score_is_five(self):
        cross = [
            [0, 1, 0],
            [1, 1, 1],
            [0, 1, 0],
        ]

        self.assertEqual(calculate_mac(cross, cross), 5)

    def test_cross_and_x_score_is_one(self):
        cross = make_pattern(3, "Cross")
        x_pattern = make_pattern(3, "X")

        self.assertEqual(calculate_mac(cross, x_pattern), 1)

    def test_different_sizes_raise_error(self):
        with self.assertRaises(ValueError):
            calculate_mac([[1]], [[1, 0], [0, 1]])

    def test_non_square_matrix_raises_error(self):
        with self.assertRaises(ValueError):
            check_matrix([[1, 0, 1], [0, 1, 0]])

    def test_label_plus_becomes_cross(self):
        self.assertEqual(normalize_label("+"), "Cross")

    def test_label_cross_becomes_cross(self):
        self.assertEqual(normalize_label(" cross "), "Cross")

    def test_label_x_becomes_x(self):
        self.assertEqual(normalize_label("X"), "X")

    def test_unknown_label_raises_error(self):
        with self.assertRaises(ValueError):
            normalize_label("circle")

    def test_larger_score_wins(self):
        self.assertEqual(choose_winner(5, 1), "A")
        self.assertEqual(choose_winner(1, 5), "B")

    def test_tiny_difference_is_undecided(self):
        self.assertEqual(choose_winner(0.9, 0.8999999999999999), "UNDECIDED")

    def test_make_cross_pattern(self):
        expected = [
            [0, 1, 0],
            [1, 1, 1],
            [0, 1, 0],
        ]

        self.assertEqual(make_pattern(3, "Cross"), expected)

    def test_make_x_pattern(self):
        expected = [
            [1, 0, 1],
            [0, 1, 0],
            [1, 0, 1],
        ]

        self.assertEqual(make_pattern(3, "X"), expected)

    def test_flatten_matrix(self):
        self.assertEqual(flatten_matrix([[1, 2], [3, 4]]), [1, 2, 3, 4])

    def test_1d_and_2d_scores_are_same(self):
        pattern = make_pattern(5, "Cross")
        flat_pattern = flatten_matrix(pattern)

        score_2d = calculate_mac(pattern, pattern)
        score_1d = calculate_mac_1d(flat_pattern, flat_pattern)

        self.assertEqual(score_2d, score_1d)


if __name__ == "__main__":
    unittest.main()
