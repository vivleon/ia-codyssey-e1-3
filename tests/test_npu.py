"""npu.py의 기본 계산 테스트.

테스트는 ``입력 준비 → 함수 실행 → 기대 결과 확인`` 순서로 읽으면 된다.
각 테스트는 MAC 계산의 한 가지 규칙만 작게 확인한다.
"""

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
        # 올바른 2×2 행렬은 한 변의 길이 2를 반환해야 한다.
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
        # 손으로 계산 가능한 2×2 예제로 MAC 결과를 검증한다.
        pattern = [[1, 0], [0, 1]]
        cross_filter = [[0, 1], [1, 0]]
        x_filter = [[1, 0], [0, 1]]
        self.assertEqual(mac_score(pattern, cross_filter), 0)
        self.assertEqual(mac_score(pattern, x_filter), 2)

    def test_mac_rejects_different_sizes(self):
        with self.assertRaises(ValueError):
            mac_score([[1]], [[1, 0], [0, 1]])

    def test_near_tie_is_undecided(self):
        # 1e-12 차이는 기본 epsilon 1e-9보다 작으므로 동점이다.
        self.assertEqual(compare_scores(1.0, 1.0 + 1e-12), "UNDECIDED")

    def test_larger_score_wins(self):
        self.assertEqual(compare_scores(5, 1), "A")
        self.assertEqual(compare_scores(1, 5), "B")

    def test_measure_time_returns_number(self):
        # 실행 시간은 환경마다 다르므로 정확한 값 대신 0 이상인지 확인한다.
        pattern = [[1, 0], [0, 1]]
        self.assertGreaterEqual(measure_mac_time(pattern, pattern, 10), 0)

    def test_make_pattern(self):
        self.assertEqual(len(make_pattern(5, "Cross")), 5)
        self.assertEqual(len(make_pattern(13, "X")), 13)


if __name__ == "__main__":
    unittest.main()
