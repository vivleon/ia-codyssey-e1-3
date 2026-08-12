"""콘솔 입력 검증과 실행 흐름 테스트."""

import json
import unittest
from pathlib import Path
from unittest.mock import patch

from main import SimulatorApp


PROJECT_ROOT = Path(__file__).resolve().parents[1]


class SimulatorAppTest(unittest.TestCase):
    def make_app(self, answers, data_path=None, **app_options):
        messages = []
        answer_iterator = iter(answers)
        app = SimulatorApp(
            data_path=data_path or PROJECT_ROOT / "data.json",
            repeats=10,
            input_func=lambda _: next(answer_iterator),
            output_func=messages.append,
            **app_options,
        )
        return app, messages

    def test_matrix_input_retries_column_count_and_parse_error(self) -> None:
        app, messages = self.make_app(
            [
                "1 2",
                "1 two 3",
                "1 2 3",
                "4 5 6",
                "7 8 9",
            ]
        )

        matrix = app.read_matrix("테스트 행렬")

        self.assertEqual(matrix.get(2, 2), 9.0)
        error_messages = [
            message for message in messages if "입력 형식 오류" in message
        ]
        self.assertEqual(len(error_messages), 2)

    def test_user_mode_calculates_b_filter_result(self) -> None:
        answers = [
            "0 1 0",
            "1 1 1",
            "0 1 0",
            "1 0 1",
            "0 1 0",
            "1 0 1",
            "1 0 1",
            "0 1 0",
            "1 0 1",
        ]
        app, messages = self.make_app(answers)

        with patch("main.benchmark_mac", return_value=0.012):
            app.run_user_mode()

        self.assertIn("A 점수: 1", messages)
        self.assertIn("B 점수: 5", messages)
        self.assertIn("판정: B", messages)
        result_indexes = {
            prefix: next(
                index
                for index, message in enumerate(messages)
                if message.startswith(prefix)
            )
            for prefix in ("A 점수:", "B 점수:", "연산 시간", "판정:")
        }
        self.assertLess(result_indexes["A 점수:"], result_indexes["B 점수:"])
        self.assertLess(result_indexes["B 점수:"], result_indexes["연산 시간"])
        self.assertLess(result_indexes["연산 시간"], result_indexes["판정:"])
        self.assertEqual(
            messages[result_indexes["연산 시간"]],
            "연산 시간(MAC 1회 평균/10회): 0.012000 ms",
        )

    def test_user_mode_displays_undecided_with_score_difference(self) -> None:
        matrix_rows = ["1 0 0", "0 1 0", "0 0 1"]
        app, messages = self.make_app(matrix_rows * 3)

        with patch("main.benchmark_mac", return_value=0.001):
            app.run_user_mode()

        undecided = next(
            message for message in messages if message.startswith("판정: 판정 불가")
        )
        self.assertEqual(undecided, "판정: 판정 불가 (|A-B| < 1e-09)")
        self.assertIn("점수 차이: 0", messages)
        self.assertNotIn("판정: UNDECIDED", messages)

    def test_custom_epsilon_changes_user_mode_tie_threshold(self) -> None:
        answers = [
            "0 1 0",
            "1 1 1",
            "0 1 0",
            "1 0 1",
            "0 1 0",
            "1 0 1",
            "1 0 1",
            "0 1 0",
            "1 0 1",
        ]
        app, messages = self.make_app(answers, epsilon=5.0)

        with patch("main.benchmark_mac", return_value=0.001):
            app.run_user_mode()

        self.assertTrue(
            any("판정: 판정 불가 (|A-B| < 5" in message for message in messages)
        )

    def test_keyboard_interrupt_during_matrix_input_exits_safely(self) -> None:
        def raise_interrupt(_: str) -> str:
            raise KeyboardInterrupt

        messages = []
        app = SimulatorApp(
            input_func=raise_interrupt,
            output_func=messages.append,
        )

        completed = app.run("user")

        self.assertFalse(completed)
        self.assertTrue(any("Ctrl+C" in message for message in messages))
        self.assertTrue(any("안전하게 종료" in message for message in messages))

    def test_rejects_invalid_epsilon_configuration(self) -> None:
        for epsilon in (0.0, -1.0, float("inf"), float("nan"), True):
            with self.subTest(epsilon=epsilon):
                with self.assertRaises(ValueError):
                    SimulatorApp(epsilon=epsilon)

    def test_json_mode_prints_dynamic_summary(self) -> None:
        app, messages = self.make_app([])

        completed = app.run_json_mode()

        self.assertTrue(completed)
        self.assertIn("총 테스트: 6개", messages)
        self.assertIn("통과: 3개", messages)
        self.assertIn("실패: 3개", messages)
        self.assertFalse(
            any(message.startswith("SUMMARY_JSON:") for message in messages)
        )

    def test_json_mode_can_print_machine_readable_summary(self) -> None:
        app, messages = self.make_app([], summary_json=True)

        completed = app.run_json_mode()

        self.assertTrue(completed)
        summary_line = next(
            message for message in messages if message.startswith("SUMMARY_JSON:")
        )
        summary = json.loads(summary_line.split("SUMMARY_JSON: ", 1)[1])
        self.assertEqual(summary["total"], 6)
        self.assertEqual(summary["passed"], 3)
        self.assertEqual(summary["failed"], 3)
        self.assertEqual(summary["total"], summary["passed"] + summary["failed"])
        self.assertEqual(len(summary["failures"]), 3)

    def test_custom_epsilon_is_used_in_json_analysis_and_summary(self) -> None:
        app, messages = self.make_app([], epsilon=1e-18, summary_json=True)

        completed = app.run_json_mode()

        self.assertTrue(completed)
        summary_line = next(
            message for message in messages if message.startswith("SUMMARY_JSON:")
        )
        summary = json.loads(summary_line.split("SUMMARY_JSON: ", 1)[1])
        self.assertEqual(summary["epsilon"], 1e-18)
        self.assertEqual(summary["total"], 6)
        self.assertEqual(summary["passed"], 3)
        self.assertEqual(summary["failed"], 3)
        self.assertTrue(
            all(
                failure["predicted"] != "UNDECIDED"
                for failure in summary["failures"]
            )
        )

    def test_missing_json_file_does_not_crash(self) -> None:
        missing_path = PROJECT_ROOT / "missing-data.json"
        app, messages = self.make_app(
            [],
            data_path=missing_path,
        )

        completed = app.run_json_mode()

        self.assertFalse(completed)
        self.assertTrue(any("분석 중단" in message for message in messages))
        self.assertTrue(
            any(str(missing_path.resolve()) in message for message in messages)
        )

    def test_eof_exits_safely(self) -> None:
        def raise_eof(_: str) -> str:
            raise EOFError

        messages = []
        app = SimulatorApp(
            input_func=raise_eof,
            output_func=messages.append,
        )

        completed = app.run()

        self.assertFalse(completed)
        self.assertTrue(any("안전하게 종료" in message for message in messages))


if __name__ == "__main__":
    unittest.main()
