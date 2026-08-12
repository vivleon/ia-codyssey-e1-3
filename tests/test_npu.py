"""행렬, MAC, 라벨, epsilon 정책 단위 테스트."""

import unittest
from unittest.mock import patch

from npu import (
    Matrix,
    MatrixError,
    WARMUP_REPEATS,
    benchmark_mac,
    compare_scores,
    generate_pattern,
    mac_score,
    normalize_label,
)


class MatrixTest(unittest.TestCase):
    def test_reads_and_writes_position(self) -> None:
        matrix = Matrix([[1, 2], [3, 4]])
        matrix.set(0, 1, 9)

        self.assertEqual(matrix.get(0, 1), 9.0)
        copied = matrix.to_rows()
        copied[0][1] = -1
        self.assertEqual(matrix.get(0, 1), 9.0)

    def test_rejects_non_square_matrix(self) -> None:
        with self.assertRaises(MatrixError):
            Matrix([[1, 2], [3]])

    def test_rejects_non_numeric_value(self) -> None:
        with self.assertRaises(MatrixError):
            Matrix([[1, "two"], [3, 4]])


class NpuOperationTest(unittest.TestCase):
    def test_mac_score_for_cross_and_x(self) -> None:
        cross = generate_pattern(3, "Cross")
        x_pattern = generate_pattern(3, "X")

        self.assertEqual(mac_score(cross, cross), 5.0)
        self.assertEqual(mac_score(cross, x_pattern), 1.0)

    def test_mac_rejects_size_mismatch(self) -> None:
        with self.assertRaises(MatrixError):
            mac_score(generate_pattern(3, "Cross"), generate_pattern(5, "Cross"))

    def test_normalizes_required_labels(self) -> None:
        self.assertEqual(normalize_label("+"), "Cross")
        self.assertEqual(normalize_label("cross"), "Cross")
        self.assertEqual(normalize_label(" x "), "X")

    def test_epsilon_turns_near_equal_scores_into_undecided(self) -> None:
        self.assertEqual(
            compare_scores(0.9, 0.9 - 1e-12, epsilon=1e-9),
            "UNDECIDED",
        )
        self.assertEqual(compare_scores(5.0, 1.0), "A")
        self.assertEqual(compare_scores(1.0, 5.0), "B")

    def test_benchmark_warms_up_before_measured_repeats(self) -> None:
        matrix = Matrix([[1]])
        events = []

        def record_score(*_args) -> float:
            events.append("score")
            return 1.0

        timer_values = iter((100, 500))

        def record_timer() -> int:
            events.append("timer")
            return next(timer_values)

        with patch("npu.mac_score", side_effect=record_score), patch(
            "npu.perf_counter_ns", side_effect=record_timer
        ):
            average_ms = benchmark_mac(matrix, matrix, repeats=4)

        self.assertEqual(
            events,
            ["score"] * WARMUP_REPEATS
            + ["timer"]
            + ["score"] * 4
            + ["timer"],
        )
        self.assertAlmostEqual(average_ms, 0.0001)


if __name__ == "__main__":
    unittest.main()
