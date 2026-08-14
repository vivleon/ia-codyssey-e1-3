"""json_mode.py의 데이터 분석을 확인합니다."""


import copy
import unittest
from pathlib import Path

from json_mode import (
    analyze_all,
    count_results,
    get_size_from_key,
    load_json,
)


DATA_FILE = Path(__file__).parents[1] / "data.json"


class JsonModeTest(unittest.TestCase):

    def test_load_json(self):
        data = load_json(DATA_FILE)

        self.assertIn("filters", data)
        self.assertIn("patterns", data)

    def test_get_size_from_key(self):
        self.assertEqual(get_size_from_key("size_13_2"), 13)

    def test_bad_pattern_key_raises_error(self):
        with self.assertRaises(ValueError):
            get_size_from_key("size13")

    def test_all_six_cases_are_analyzed(self):
        data = load_json(DATA_FILE)
        results = analyze_all(data)

        self.assertEqual(len(results), 6)

    def test_current_data_summary(self):
        data = load_json(DATA_FILE)
        results = analyze_all(data)
        summary = count_results(results)

        self.assertEqual(summary["total"], 6)
        self.assertEqual(summary["passed"], 3)
        self.assertEqual(summary["failed"], 3)

    def test_expected_labels_are_standardized(self):
        data = load_json(DATA_FILE)
        results = analyze_all(data)

        for result in results:
            self.assertIn(result["expected"], ["Cross", "X"])

    def test_bad_case_does_not_stop_next_case(self):
        data = load_json(DATA_FILE)
        broken_data = copy.deepcopy(data)
        broken_data["patterns"]["size_5_1"]["input"] = [[1]]

        results = analyze_all(broken_data)

        self.assertEqual(len(results), 6)
        self.assertEqual(results[0]["predicted"], "ERROR")
        self.assertNotEqual(results[1]["predicted"], "ERROR")

    def test_unknown_label_becomes_case_error(self):
        data = load_json(DATA_FILE)
        broken_data = copy.deepcopy(data)
        broken_data["patterns"]["size_5_1"]["expected"] = "circle"

        results = analyze_all(broken_data)

        self.assertEqual(results[0]["predicted"], "ERROR")
        self.assertIn("데이터/스키마 오류", results[0]["reason"])


if __name__ == "__main__":
    unittest.main()
