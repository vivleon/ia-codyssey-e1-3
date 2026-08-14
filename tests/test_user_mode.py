"""user_mode.py와 main.py의 입력 흐름을 확인합니다."""


import unittest

from main import choose_menu, run
from user_mode import read_matrix, run_user_mode


def make_fake_input(answers):
    """테스트에서 키보드 입력 대신 준비한 답을 하나씩 돌려줍니다."""

    answer_iterator = iter(answers)

    def fake_input(prompt=""):
        return next(answer_iterator)

    return fake_input


class UserModeTest(unittest.TestCase):

    def test_wrong_column_count_is_asked_again(self):
        answers = [
            "1 0",
            "1 0 1",
            "0 1 0",
            "1 0 1",
        ]
        messages = []

        matrix = read_matrix(
            "테스트",
            3,
            make_fake_input(answers),
            messages.append,
        )

        self.assertEqual(len(matrix), 3)
        self.assertTrue(any("입력 형식 오류" in text for text in messages))

    def test_non_number_is_asked_again(self):
        answers = [
            "a 0 1",
            "1 0 1",
            "0 1 0",
            "1 0 1",
        ]
        messages = []

        read_matrix("테스트", 3, make_fake_input(answers), messages.append)

        self.assertTrue(any("숫자만" in text for text in messages))

    def test_menu_wrong_value_is_asked_again(self):
        messages = []
        choice = choose_menu(make_fake_input(["9", "2"]), messages.append)

        self.assertEqual(choice, "2")
        self.assertTrue(any("입력 오류" in text for text in messages))

    def test_user_mode_prints_scores_and_winner(self):
        cross_rows = ["0 1 0", "1 1 1", "0 1 0"]
        x_rows = ["1 0 1", "0 1 0", "1 0 1"]
        answers = cross_rows + x_rows + x_rows
        messages = []

        run_user_mode(make_fake_input(answers), messages.append, 10)
        all_text = "\n".join(messages)

        self.assertIn("A 점수: 1", all_text)
        self.assertIn("B 점수: 5", all_text)
        self.assertIn("판정: B", all_text)
        self.assertIn("ms", all_text)

    def test_keyboard_interrupt_is_safe(self):
        def stop_input(prompt=""):
            raise KeyboardInterrupt

        messages = []
        result = run(stop_input, messages.append)

        self.assertFalse(result)
        self.assertTrue(any("안전하게 종료" in text for text in messages))


if __name__ == "__main__":
    unittest.main()
