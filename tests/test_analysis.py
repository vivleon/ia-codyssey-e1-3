"""JSON 스키마, 케이스 격리, 성능 결과 테스트."""

import unittest
from pathlib import Path
from unittest.mock import patch

from analysis import (
    DataAnalysisError,
    FILTER_KEYS,
    analyze_dataset,
    analyze_file,
    load_json_file,
    measure_sizes,
)


PROJECT_ROOT = Path(__file__).resolve().parents[1]


class DatasetAnalysisTest(unittest.TestCase):
    def test_attached_dataset_has_expected_dynamic_summary(self) -> None:
        report = analyze_file(PROJECT_ROOT / "data.json")

        self.assertEqual(report.total_count, 6)
        self.assertEqual(report.passed_count, 3)
        self.assertEqual(report.failed_count, 3)
        self.assertEqual(
            [result.identifier for result in report.failures],
            ["size_5_1", "size_13_2", "size_25_1"],
        )
        self.assertTrue(
            all(result.predicted == "UNDECIDED" for result in report.failures)
        )

    def test_size_mismatch_fails_only_that_case(self) -> None:
        data = {
            "filters": {
                "size_3": {
                    "cross": [[1, 0, 1], [0, 1, 0], [1, 0, 1]],
                    "x": [[1, 0, 1], [0, 1, 0], [1, 0, 1]],
                }
            },
            "patterns": {
                "size_3_1": {
                    "input": [[1, 0], [0, 1]],
                    "expected": "x",
                }
            },
        }

        report = analyze_dataset(data)

        self.assertEqual(report.failed_count, 1)
        self.assertEqual(report.results[0].predicted, "ERROR")
        self.assertIn("크기", report.results[0].reason)

    def test_invalid_pattern_key_is_reported_without_crash(self) -> None:
        report = analyze_dataset(
            {
                "filters": {},
                "patterns": {
                    "wrong-key": {"input": [[1]], "expected": "+"},
                },
            }
        )
        self.assertEqual(report.results[0].predicted, "ERROR")
        self.assertIn("size_{N}_{idx}", report.results[0].reason)

    def test_missing_filter_group_suggests_required_json_key(self) -> None:
        report = analyze_dataset(
            {
                "filters": {},
                "patterns": {
                    "size_1_1": {"input": [[1]], "expected": "+"},
                },
            }
        )

        reason = report.results[0].reason
        self.assertIn("size_1 필터 객체가 없습니다", reason)
        self.assertIn("filters에 size_1 키", reason)
        self.assertIn("cross/x", reason)

    def test_normalized_filter_alias_collision_is_reported(self) -> None:
        report = analyze_dataset(
            {
                "filters": {
                    "size_1": {
                        "cross": [[1]],
                        "+": [[1]],
                        "x": [[0]],
                    }
                },
                "patterns": {
                    "size_1_1": {"input": [[1]], "expected": "+"},
                },
            }
        )

        self.assertIn("Cross 필터가 중복되었습니다", report.results[0].reason)

    def test_filter_key_hints_have_one_key_per_standard_label(self) -> None:
        self.assertEqual(FILTER_KEYS, {"Cross": "cross", "X": "x"})

    def test_unsupported_expected_label_is_isolated_to_case(self) -> None:
        report = analyze_dataset(
            {
                "filters": {},
                "patterns": {
                    "size_1_1": {"input": [[1]], "expected": "triangle"},
                },
            }
        )

        result = report.results[0]
        self.assertEqual(result.expected, None)
        self.assertEqual(result.predicted, "ERROR")
        self.assertIn("지원하지 않는 라벨입니다: 'triangle'", result.reason)

    def test_missing_file_has_clear_error(self) -> None:
        with self.assertRaises(DataAnalysisError):
            load_json_file(PROJECT_ROOT / "missing-data.json")

    def test_performance_rows_include_n_squared_operations(self) -> None:
        rows = measure_sizes(sizes=(3, 5), repeats=10)
        self.assertEqual([row.operations for row in rows], [9, 25])
        self.assertTrue(all(row.average_ms >= 0 for row in rows))

    def test_equal_scores_are_undecided_and_counted_as_failure(self) -> None:
        report = analyze_dataset(
            {
                "filters": {
                    "size_1": {
                        "cross": [[1]],
                        "x": [[1]],
                    }
                },
                "patterns": {
                    "size_1_1": {
                        "input": [[1]],
                        "expected": "+",
                    }
                },
            }
        )

        result = report.results[0]
        self.assertEqual(result.predicted, "UNDECIDED")
        self.assertFalse(result.passed)
        self.assertEqual(report.failed_count, 1)
        self.assertIn("epsilon", result.reason)

    def test_measure_sizes_passes_custom_repeat_count_to_benchmark(self) -> None:
        with patch("analysis.benchmark_mac", return_value=0.125) as benchmark:
            rows = measure_sizes(sizes=(3, 5), repeats=37)

        self.assertEqual([row.repeats for row in rows], [37, 37])
        self.assertEqual([row.average_ms for row in rows], [0.125, 0.125])
        self.assertEqual([call.args[2] for call in benchmark.call_args_list], [37, 37])


if __name__ == "__main__":
    unittest.main()
