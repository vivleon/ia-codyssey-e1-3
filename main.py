"""Mini NPU Simulator를 시작하는 메인 파일입니다."""


from pathlib import Path

from json_mode import run_json_mode
from performance import compare_2d_and_1d, print_bonus_result
from user_mode import run_user_mode


# main.py와 같은 폴더에 있는 data.json을 사용합니다.
DATA_FILE = Path(__file__).with_name("data.json")


def choose_menu(input_function=input, print_function=print):
    """올바른 메뉴 번호가 들어올 때까지 다시 묻습니다."""

    print_function("\n1. 사용자 입력 (3×3)")
    print_function("2. data.json 분석")
    print_function("3. 보너스: 2차원/1차원 성능 비교")
    print_function("0. 종료")

    while True:
        choice = input_function("선택: ").strip()

        if choice in ["0", "1", "2", "3"]:
            return choice

        print_function("입력 오류: 0, 1, 2, 3 중 하나를 입력하세요.")


def run(input_function=input, print_function=print):
    """메뉴에서 고른 기능을 실행합니다."""

    print_function("=== Mini NPU Simulator ===")

    try:
        choice = choose_menu(input_function, print_function)

        if choice == "1":
            run_user_mode(input_function, print_function, 10)

        elif choice == "2":
            run_json_mode(DATA_FILE, print_function, 10)

        elif choice == "3":
            result = compare_2d_and_1d(25, 10)
            print_bonus_result(result, print_function)

        else:
            print_function("프로그램을 종료합니다.")

        return True

    except (KeyboardInterrupt, EOFError):
        print_function("\n입력이 취소되어 안전하게 종료합니다.")
        return False


# 이 파일을 직접 실행할 때만 프로그램을 시작합니다.
if __name__ == "__main__":
    run()
