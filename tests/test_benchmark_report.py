"""반복 벤치마크의 통계·메모리 리포트 테스트."""

import unittest
from unittest.mock import patch

from benchmark_report import collect_benchmark


class BenchmarkReportTest(unittest.TestCase):
    def test_collects_mean_median_and_population_stdev(self) -> None:
        samples = [1.0, 2.0, 6.0]

        with patch("benchmark_report.benchmark_mac", side_effect=samples):
            report = collect_benchmark(size=3, repeats=10, groups=3)

        self.assertEqual(report["operations_per_mac"], 9)
        self.assertEqual(report["repeats_per_group"], 10)
        self.assertEqual(report["samples_ms"], samples)
        self.assertEqual(report["mean_ms"], 3.0)
        self.assertEqual(report["median_ms"], 2.0)
        self.assertAlmostEqual(report["population_stdev_ms"], 2.160246899469287)
        self.assertGreater(report["two_matrix_construction_peak_bytes"], 0)

    def test_rejects_non_positive_parameters(self) -> None:
        for arguments in ((0, 10, 3), (3, 9, 3), (3, 10, 1)):
            with self.subTest(arguments=arguments):
                with self.assertRaises(ValueError):
                    collect_benchmark(*arguments)


if __name__ == "__main__":
    unittest.main()
