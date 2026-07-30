"""JSON 스키마, 케이스 격리, 성능 결과 테스트."""

import unittest
from pathlib import Path

from analysis import (
    DataAnalysisError,
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

    def test_missing_file_has_clear_error(self) -> None:
        with self.assertRaises(DataAnalysisError):
            load_json_file(PROJECT_ROOT / "missing-data.json")

    def test_performance_rows_include_n_squared_operations(self) -> None:
        rows = measure_sizes(sizes=(3, 5), repeats=10)
        self.assertEqual([row.operations for row in rows], [9, 25])
        self.assertTrue(all(row.average_ms >= 0 for row in rows))


if __name__ == "__main__":
    unittest.main()
