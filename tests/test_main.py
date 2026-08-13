"""main.py의 입력과 출력 테스트."""

import unittest
from pathlib import Path

from main import read_matrix, run


DATA_FILE = Path(__file__).parents[1] / "data.json"


class MainTest(unittest.TestCase):
    def test_input_error_asks_again(self):
        answers = iter(["1 2", "a b c", "1 0 0", "0 1 0", "0 0 1"])
        messages = []

        matrix = read_matrix(
            "테스트",
            input_func=lambda _prompt: next(answers),
            output_func=messages.append,
        )

        self.assertEqual(matrix, [[1, 0, 0], [0, 1, 0], [0, 0, 1]])
        self.assertTrue(any("숫자 3개" in message for message in messages))
        self.assertTrue(any("숫자만" in message for message in messages))

    def test_user_mode_prints_b_result(self):
        answers = iter(
            [
                "0 1 0", "1 1 1", "0 1 0",  # 필터 A
                "1 0 1", "0 1 0", "1 0 1",  # 필터 B
                "1 0 1", "0 1 0", "1 0 1",  # 패턴
            ]
        )
        messages = []

        self.assertTrue(
            run(
                "user",
                repeats=10,
                input_func=lambda _prompt: next(answers),
                output_func=messages.append,
            )
        )
        self.assertIn("A 점수: 1", messages)
        self.assertIn("B 점수: 5", messages)
        self.assertIn("판정: B", messages)

    def test_user_mode_prints_undecided(self):
        answers = iter(["1 0 0", "0 1 0", "0 0 1"] * 3)
        messages = []

        run(
            "user",
            repeats=10,
            input_func=lambda _prompt: next(answers),
            output_func=messages.append,
        )
        self.assertTrue(any("판정 불가" in message for message in messages))

    def test_json_mode_prints_summary(self):
        messages = []
        self.assertTrue(run("json", DATA_FILE, 10, output_func=messages.append))
        self.assertIn("총 테스트: 6개", messages)
        self.assertIn("통과: 3개", messages)
        self.assertIn("실패: 3개", messages)
        self.assertTrue(any("UNDECIDED" in message for message in messages))

    def test_missing_file_ends_cleanly(self):
        messages = []
        self.assertFalse(run("json", Path("missing.json"), 10, output_func=messages.append))
        self.assertTrue(any("분석 중단" in message for message in messages))

    def test_keyboard_interrupt_ends_cleanly(self):
        messages = []

        def interrupted_input(_prompt):
            raise KeyboardInterrupt

        self.assertFalse(
            run("user", input_func=interrupted_input, output_func=messages.append)
        )
        self.assertTrue(any("안전하게 종료" in message for message in messages))


if __name__ == "__main__":
    unittest.main()
