"""Mini NPU Simulator 실행 파일.

사용자와 직접 만나는 입력·출력은 이 파일이 담당한다. 실제 MAC 공식은
``npu.py``, JSON 데이터 검증은 ``analysis.py``에 맡긴다.

실행 흐름:
모드 선택 → 사용자 입력 모드 또는 JSON 분석 모드 → 결과 출력
"""

import argparse
from pathlib import Path

from analysis import analyze_dataset, load_json_file, measure_sizes, summarize
from npu import EPSILON, compare_scores, mac_score, measure_mac_time


# __file__은 현재 main.py의 경로다. 같은 폴더의 data.json을 기본 파일로 쓴다.
# 이렇게 하면 다른 폴더에서 main.py를 실행해도 data.json을 찾을 수 있다.
DATA_FILE = Path(__file__).with_name("data.json")


def read_matrix(title, size=3, input_func=input, output_func=print):
    """사용자에게 숫자 행렬을 한 줄씩 입력받아 2차원 목록으로 반환한다.

    ``input_func``와 ``output_func``의 기본값은 input과 print다. 테스트에서는
    가짜 입력 함수를 전달해 키보드 입력 없이 같은 동작을 확인한다.
    """
    output_func(f"\n{title}: {size}줄을 입력하세요.")
    output_func("한 줄에 숫자를 공백으로 구분합니다. 취소: Ctrl+C")

    # 완성된 각 행을 차례대로 담으면 최종적으로 2차원 목록이 된다.
    matrix = []
    for row_number in range(1, size + 1):
        # 한 행이 잘못되면 while 반복으로 같은 행만 다시 입력받는다.
        while True:
            # split()은 "1 0 1"을 ["1", "0", "1"]로 나눈다.
            words = input_func(f"{row_number}행: ").split()

            # 3×3 모드에서는 한 행에 정확히 숫자 후보 3개가 필요하다.
            if len(words) != size:
                output_func(f"입력 오류: 숫자 {size}개를 입력하세요.")
                continue

            try:
                # 문자열을 float로 바꾸면 정수와 실수 입력을 모두 처리할 수 있다.
                row = [float(word) for word in words]
            except ValueError:
                output_func("입력 오류: 숫자만 입력하세요.")
                continue

            # 검사를 통과한 행만 저장하고 while 반복을 끝낸다.
            matrix.append(row)
            break

    return matrix


def choose_mode(input_func=input, output_func=print):
    """1 또는 2를 입력받아 내부 모드 이름 user 또는 json을 반환한다."""
    output_func("\n1. 사용자 입력 모드")
    output_func("2. data.json 분석 모드")

    # 다른 문자를 입력하면 올바른 번호를 받을 때까지 다시 묻는다.
    while True:
        choice = input_func("선택: ").strip()
        if choice == "1":
            return "user"
        if choice == "2":
            return "json"
        output_func("입력 오류: 1 또는 2를 입력하세요.")


def print_performance(performance, output_func=print):
    """크기별 평균 시간과 N² 연산 횟수 딕셔너리를 표로 출력한다."""
    # 모든 행은 같은 반복 횟수로 측정한다. 첫 행에서 그 값을 가져온다.
    repeats = performance[0]["repeats"] if performance else 0
    output_func(f"\n[성능 분석: 크기별 {repeats}회 평균]")
    output_func("크기       평균 시간(ms)       연산 횟수(N²)")
    output_func("-" * 48)

    # item 예: {"size": 5, "average_ms": 0.01, "operations": 25, ...}
    for item in performance:
        size_text = f"{item['size']}×{item['size']}"
        output_func(
            f"{size_text:<10} {item['average_ms']:>12.6f} "
            f"{item['operations']:>18}"
        )


def run_user_mode(input_func=input, output_func=print, repeats=10):
    """3×3 필터 두 개와 패턴 하나를 입력받아 점수·판정·시간을 출력한다."""
    # 1단계: 비교 기준이 되는 필터 A와 B를 입력받는다.
    filter_a = read_matrix("필터 A", input_func=input_func, output_func=output_func)
    filter_b = read_matrix("필터 B", input_func=input_func, output_func=output_func)

    # 2단계: 어느 필터와 더 비슷한지 알아볼 입력 패턴을 받는다.
    pattern = read_matrix("입력 패턴", input_func=input_func, output_func=output_func)

    # 3단계: 같은 패턴을 두 필터와 각각 MAC 계산한다.
    score_a = mac_score(pattern, filter_a)
    score_b = mac_score(pattern, filter_b)

    # 4단계: epsilon 정책으로 A/B/UNDECIDED 중 하나를 결정한다.
    predicted = compare_scores(score_a, score_b)

    # 5단계: 파일과 화면 I/O를 제외한 MAC 함수의 1회 평균 시간을 구한다.
    average_ms = measure_mac_time(pattern, filter_a, repeats)

    output_func("\n[MAC 결과]")
    output_func(f"A 점수: {score_a:.16g}")
    output_func(f"B 점수: {score_b:.16g}")
    output_func(f"평균 연산 시간({repeats}회): {average_ms:.6f} ms")

    if predicted == "UNDECIDED":
        # 내부 표준값보다 쉬운 한국어 문구를 사용자 모드에서 보여준다.
        output_func(f"판정: 판정 불가 (점수 차이 < {EPSILON:g})")
        output_func(f"점수 차이: {abs(score_a - score_b):.16g}")
    else:
        output_func(f"판정: {predicted}")

    # 사용자 모드에서는 방금 측정한 3×3 한 행만 성능 표에 넣는다.
    print_performance(
        [
            {
                "size": 3,
                "average_ms": average_ms,
                "operations": 9,
                "repeats": repeats,
            }
        ],
        output_func,
    )


def print_case_results(results, output_func=print):
    """JSON 패턴별 점수, 판정, expected, PASS/FAIL을 출력한다."""
    for result in results:
        output_func(f"\n--- {result['id']} ---")

        # 스키마 오류 케이스의 scores는 빈 딕셔너리이므로 점수를 출력하지 않는다.
        if result["scores"]:
            output_func(f"Cross 점수: {result['scores']['Cross']:.16g}")
            output_func(f"X 점수: {result['scores']['X']:.16g}")

        # bool 값 passed를 사람이 읽는 문자열 PASS 또는 FAIL로 바꾼다.
        status = "PASS" if result["passed"] else "FAIL"
        expected = result["expected"] or "UNKNOWN"
        output_func(
            f"판정: {result['predicted']} | expected: {expected} | {status}"
        )
        if result["reason"]:
            output_func(f"사유: {result['reason']}")


def print_summary(results, output_func=print):
    """총 테스트·통과·실패 수와 실패 케이스의 이유를 출력한다."""
    summary = summarize(results)

    output_func("\n[결과 요약]")
    output_func(f"총 테스트: {summary['total']}개")
    output_func(f"통과: {summary['passed']}개")
    output_func(f"실패: {summary['failed']}개")

    if summary["failures"]:
        # 실패 목록을 생략하지 않아 어느 JSON 데이터를 고칠지 알 수 있게 한다.
        output_func("\n실패 케이스:")
        for result in summary["failures"]:
            output_func(f"- {result['id']}: {result['reason']}")
    else:
        output_func("실패 케이스가 없습니다.")


def run_json_mode(data_path=DATA_FILE, output_func=print, repeats=10):
    """data.json의 모든 패턴을 분석하고 성능 표와 요약을 출력한다."""
    output_func(f"\nJSON 파일 읽기: {Path(data_path).resolve()}")

    try:
        # 파일 읽기와 전체 패턴 분석은 실패 가능성이 있으므로 예외를 처리한다.
        data = load_json_file(data_path)
        results = analyze_dataset(data)
    except ValueError as error:
        # 파일 전체를 읽을 수 없는 경우에도 Python 오류 추적 대신 안내문을 준다.
        output_func(f"분석 중단: {error}")
        return False

    # 평가 기준의 순서: 케이스 결과 → 크기별 성능 → 전체 요약.
    print_case_results(results, output_func)
    print_performance(measure_sizes(repeats=repeats), output_func)
    print_summary(results, output_func)
    return True


def run(mode=None, data_path=DATA_FILE, repeats=10, input_func=input, output_func=print):
    """선택한 모드를 실행하고 정상 종료이면 True, 아니면 False를 반환한다."""
    output_func("=== Mini NPU Simulator ===")

    try:
        # --mode가 없으면 메뉴에서 선택하고, 있으면 메뉴를 건너뛴다.
        selected_mode = mode or choose_mode(input_func, output_func)
        if selected_mode == "user":
            run_user_mode(input_func, output_func, repeats)
            return True
        if selected_mode == "json":
            return run_json_mode(data_path, output_func, repeats)
        output_func(f"지원하지 않는 모드입니다: {selected_mode}")
        return False
    except (KeyboardInterrupt, EOFError):
        # Ctrl+C(KeyboardInterrupt)와 입력 종료(EOF)를 안전한 종료로 바꾼다.
        output_func("\n입력이 중단되어 안전하게 종료합니다.")
        return False


def main():
    """명령행 옵션을 읽고 프로그램의 종료 코드를 반환한다."""
    # argparse를 사용하면 --mode, --data, --repeats 도움말과 검증을 제공한다.
    parser = argparse.ArgumentParser(description="Mini NPU Simulator")
    parser.add_argument("--mode", choices=("user", "json"))
    parser.add_argument("--data", type=Path, default=DATA_FILE)
    parser.add_argument("--repeats", type=int, default=10)
    args = parser.parse_args()

    # 과제 기준은 각 크기별 최소 10회 반복이다.
    if args.repeats < 10:
        print("설정 오류: 반복 횟수는 최소 10회여야 합니다.")
        return 2

    # 정상 완료는 종료 코드 0, 실행 실패는 1이다.
    return 0 if run(args.mode, args.data, args.repeats) else 1


# 이 파일을 직접 실행했을 때만 main()을 호출한다.
# 테스트에서 import할 때는 자동 실행되지 않는다.
if __name__ == "__main__":
    raise SystemExit(main())
