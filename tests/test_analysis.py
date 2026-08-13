"""analysis.py의 JSON 분석 테스트."""

import unittest
from pathlib import Path

from analysis import (
    analyze_dataset,
    extract_size,
    load_json_file,
    measure_sizes,
    summarize,
)


DATA_FILE = Path(__file__).parents[1] / "data.json"


class AnalysisTest(unittest.TestCase):
    def test_extract_size(self):
        self.assertEqual(extract_size("size_13_2"), 13)

    def test_reject_wrong_key(self):
        with self.assertRaises(ValueError):
            extract_size("pattern_13_2")

    def test_attached_data_result(self):
        results = analyze_dataset(load_json_file(DATA_FILE))
        summary = summarize(results)
        self.assertEqual(summary["total"], 6)
        self.assertEqual(summary["passed"], 3)
        self.assertEqual(summary["failed"], 3)

    def test_undecided_counts_as_failure(self):
        data = {
            "filters": {
                "size_1": {"cross": [[1.0]], "x": [[1.0]]}
            },
            "patterns": {
                "size_1_1": {"input": [[1.0]], "expected": "+"}
            },
        }
        result = analyze_dataset(data)[0]
        self.assertEqual(result["predicted"], "UNDECIDED")
        self.assertFalse(result["passed"])

    def test_bad_case_does_not_stop_other_cases(self):
        data = {
            "filters": {
                "size_1": {"cross": [[1]], "x": [[0]]}
            },
            "patterns": {
                "wrong_key": {"input": [[1]], "expected": "+"},
                "size_1_1": {"input": [[1]], "expected": "+"},
            },
        }
        results = analyze_dataset(data)
        self.assertEqual(results[0]["predicted"], "ERROR")
        self.assertTrue(results[1]["passed"])

    def test_missing_filter_group_is_case_error(self):
        data = {
            "filters": {},
            "patterns": {
                "size_1_1": {"input": [[1]], "expected": "+"}
            },
        }
        result = analyze_dataset(data)[0]
        self.assertIn("size_1", result["reason"])

    def test_unknown_label_is_case_error(self):
        data = {
            "filters": {
                "size_1": {"cross": [[1]], "x": [[0]]}
            },
            "patterns": {
                "size_1_1": {"input": [[1]], "expected": "triangle"}
            },
        }
        result = analyze_dataset(data)[0]
        self.assertEqual(result["predicted"], "ERROR")

    def test_performance_has_n_squared(self):
        performance = measure_sizes((3, 5), repeats=10)
        self.assertEqual(performance[0]["operations"], 9)
        self.assertEqual(performance[1]["operations"], 25)


if __name__ == "__main__":
    unittest.main()
