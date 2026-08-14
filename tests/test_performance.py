"""performance.py의 성능 측정과 보너스를 확인합니다."""


import unittest

from mac import make_pattern
from performance import average_mac_time, compare_2d_and_1d, measure_sizes


class PerformanceTest(unittest.TestCase):

    def test_average_time_is_not_negative(self):
        pattern = make_pattern(3, "Cross")
        average_ms = average_mac_time(pattern, pattern, 10)

        self.assertGreaterEqual(average_ms, 0)

    def test_measurement_has_four_sizes(self):
        results = measure_sizes(10)
        sizes = [result["size"] for result in results]

        self.assertEqual(sizes, [3, 5, 13, 25])

    def test_operation_count_is_n_squared(self):
        results = measure_sizes(10)

        for result in results:
            self.assertEqual(result["operations"], result["size"] ** 2)

    def test_bonus_scores_are_same(self):
        result = compare_2d_and_1d(13, 10)

        self.assertEqual(result["score_2d"], result["score_1d"])


if __name__ == "__main__":
    unittest.main()
