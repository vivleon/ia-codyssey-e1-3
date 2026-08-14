"""사용자가 3×3 숫자를 직접 입력하는 모드입니다."""


from mac import EPSILON, calculate_mac, choose_winner
from performance import average_mac_time, print_performance_table


def read_matrix(title, size=3, input_function=input, print_function=print):
    """한 줄씩 숫자를 입력받아 N×N 리스트를 만듭니다."""

    print_function(f"\n{title}: {size}줄을 입력하세요.")
    print_function(f"한 줄에 숫자 {size}개를 공백으로 구분해 입력하세요.")

    matrix = []

    # 행을 하나씩 입력받습니다.
    for row_number in range(1, size + 1):

        # 올바른 한 행이 들어올 때까지 같은 행을 다시 묻습니다.
        while True:
            text = input_function(f"{row_number}행: ")
            words = text.split()

            if len(words) != size:
                print_function(
                    f"입력 형식 오류: 각 줄에 {size}개의 숫자를 "
                    "공백으로 구분해 입력하세요."
                )
                continue

            try:
                row = []

                for word in words:
                    row.append(float(word))

            except ValueError:
                print_function("입력 형식 오류: 숫자만 입력하세요.")
                continue

            matrix.append(row)
            break

    return matrix


def run_user_mode(input_function=input, print_function=print, repeats=10):
    """필터 A, 필터 B, 패턴을 입력받아 점수와 판정을 출력합니다."""

    print_function("\n=== 사용자 입력 모드 ===")

    filter_a = read_matrix("필터 A", 3, input_function, print_function)
    filter_b = read_matrix("필터 B", 3, input_function, print_function)

    print_function("\n필터 A와 필터 B를 저장했습니다.")

    pattern = read_matrix("입력 패턴", 3, input_function, print_function)

    score_a = calculate_mac(pattern, filter_a)
    score_b = calculate_mac(pattern, filter_b)
    winner = choose_winner(score_a, score_b)

    time_a = average_mac_time(pattern, filter_a, repeats)
    time_b = average_mac_time(pattern, filter_b, repeats)
    average_time = (time_a + time_b) / 2

    print_function("\n[MAC 결과]")
    print_function(f"A 점수: {score_a:.16g}")
    print_function(f"B 점수: {score_b:.16g}")
    print_function(f"평균 연산 시간({repeats}회): {average_time:.6f} ms")

    if winner == "UNDECIDED":
        difference = abs(score_a - score_b)
        print_function(f"판정: 판정 불가 (점수 차이 < {EPSILON:g})")
        print_function(f"실제 점수 차이: {difference:.16g}")
    else:
        print_function(f"판정: {winner}")

    performance_result = [
        {
            "size": 3,
            "average_ms": average_time,
            "operations": 9,
        }
    ]

    print_performance_table(performance_result, repeats, print_function)
