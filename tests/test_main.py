"""콘솔 입력 검증과 실행 흐름 테스트."""

import unittest
from pathlib import Path

from main import SimulatorApp


PROJECT_ROOT = Path(__file__).resolve().parents[1]


class SimulatorAppTest(unittest.TestCase):
    def make_app(self, answers, data_path=None):
        messages = []
        answer_iterator = iter(answers)
        app = SimulatorApp(
            data_path=data_path or PROJECT_ROOT / "data.json",
            repeats=10,
            input_func=lambda _: next(answer_iterator),
            output_func=messages.append,
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

        app.run_user_mode()

        self.assertIn("A 점수: 1", messages)
        self.assertIn("B 점수: 5", messages)
        self.assertIn("판정: B", messages)
        self.assertTrue(any("평균/10회" in message for message in messages))

    def test_json_mode_prints_dynamic_summary(self) -> None:
        app, messages = self.make_app([])

        completed = app.run_json_mode()

        self.assertTrue(completed)
        self.assertIn("총 테스트: 6개", messages)
        self.assertIn("통과: 3개", messages)
        self.assertIn("실패: 3개", messages)

    def test_missing_json_file_does_not_crash(self) -> None:
        app, messages = self.make_app(
            [],
            data_path=PROJECT_ROOT / "missing-data.json",
        )

        completed = app.run_json_mode()

        self.assertFalse(completed)
        self.assertTrue(any("분석 중단" in message for message in messages))

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
