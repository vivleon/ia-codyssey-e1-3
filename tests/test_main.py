"""main.py의 입력과 출력 테스트.

실제 키보드와 화면 대신 iterator 입력과 messages.append 출력을 전달한다.
그래서 사람이 직접 입력하지 않아도 사용자 모드의 흐름을 반복 검증할 수 있다.
"""

import unittest
from pathlib import Path

from main import read_matrix, run


# tests 폴더에서 프로젝트 루트의 data.json 경로를 만든다.
DATA_FILE = Path(__file__).parents[1] / "data.json"


class MainTest(unittest.TestCase):
    def test_input_error_asks_again(self):
        # 앞의 두 입력은 의도적인 오류, 뒤의 세 입력은 올바른 3×3 행렬이다.
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
        # Cross 필터 A, X 필터 B, X 패턴을 차례대로 입력한다.
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
        # 실제 data.json의 사람용 요약 문구를 확인한다.
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
        # 가짜 입력 함수가 Ctrl+C 상황을 발생시키도록 만든다.
        messages = []

        def interrupted_input(_prompt):
            raise KeyboardInterrupt

        self.assertFalse(
            run("user", input_func=interrupted_input, output_func=messages.append)
        )
        self.assertTrue(any("안전하게 종료" in message for message in messages))


if __name__ == "__main__":
    unittest.main()
