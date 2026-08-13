"""Mini NPU Simulator 실행 파일."""

import argparse
from pathlib import Path

from analysis import analyze_dataset, load_json_file, measure_sizes, summarize
from npu import EPSILON, compare_scores, mac_score, measure_mac_time


DATA_FILE = Path(__file__).with_name("data.json")


def read_matrix(title, size=3, input_func=input, output_func=print):
    """사용자에게 숫자 행렬을 한 줄씩 입력받는다."""
    output_func(f"\n{title}: {size}줄을 입력하세요.")
    output_func("한 줄에 숫자를 공백으로 구분합니다. 취소: Ctrl+C")

    matrix = []
    for row_number in range(1, size + 1):
        while True:
            words = input_func(f"{row_number}행: ").split()

            if len(words) != size:
                output_func(f"입력 오류: 숫자 {size}개를 입력하세요.")
                continue

            try:
                row = [float(word) for word in words]
            except ValueError:
                output_func("입력 오류: 숫자만 입력하세요.")
                continue

            matrix.append(row)
            break

    return matrix


def choose_mode(input_func=input, output_func=print):
    """1 또는 2를 입력받아 실행 모드를 반환한다."""
    output_func("\n1. 사용자 입력 모드")
    output_func("2. data.json 분석 모드")

    while True:
        choice = input_func("선택: ").strip()
        if choice == "1":
            return "user"
        if choice == "2":
            return "json"
        output_func("입력 오류: 1 또는 2를 입력하세요.")


def print_performance(performance, output_func=print):
    """크기별 평균 시간과 N² 연산 횟수를 표로 출력한다."""
    repeats = performance[0]["repeats"] if performance else 0
    output_func(f"\n[성능 분석: 크기별 {repeats}회 평균]")
    output_func("크기       평균 시간(ms)       연산 횟수(N²)")
    output_func("-" * 48)

    for item in performance:
        size_text = f"{item['size']}×{item['size']}"
        output_func(
            f"{size_text:<10} {item['average_ms']:>12.6f} "
            f"{item['operations']:>18}"
        )


def run_user_mode(input_func=input, output_func=print, repeats=10):
    """3×3 필터 두 개와 패턴 하나를 입력받아 판정한다."""
    filter_a = read_matrix("필터 A", input_func=input_func, output_func=output_func)
    filter_b = read_matrix("필터 B", input_func=input_func, output_func=output_func)
    pattern = read_matrix("입력 패턴", input_func=input_func, output_func=output_func)

    score_a = mac_score(pattern, filter_a)
    score_b = mac_score(pattern, filter_b)
    predicted = compare_scores(score_a, score_b)
    average_ms = measure_mac_time(pattern, filter_a, repeats)

    output_func("\n[MAC 결과]")
    output_func(f"A 점수: {score_a:.16g}")
    output_func(f"B 점수: {score_b:.16g}")
    output_func(f"평균 연산 시간({repeats}회): {average_ms:.6f} ms")

    if predicted == "UNDECIDED":
        output_func(f"판정: 판정 불가 (점수 차이 < {EPSILON:g})")
        output_func(f"점수 차이: {abs(score_a - score_b):.16g}")
    else:
        output_func(f"판정: {predicted}")

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
    """JSON 패턴별 점수와 PASS/FAIL을 출력한다."""
    for result in results:
        output_func(f"\n--- {result['id']} ---")

        if result["scores"]:
            output_func(f"Cross 점수: {result['scores']['Cross']:.16g}")
            output_func(f"X 점수: {result['scores']['X']:.16g}")

        status = "PASS" if result["passed"] else "FAIL"
        expected = result["expected"] or "UNKNOWN"
        output_func(
            f"판정: {result['predicted']} | expected: {expected} | {status}"
        )
        if result["reason"]:
            output_func(f"사유: {result['reason']}")


def print_summary(results, output_func=print):
    """총 테스트 수와 실패 케이스를 출력한다."""
    summary = summarize(results)

    output_func("\n[결과 요약]")
    output_func(f"총 테스트: {summary['total']}개")
    output_func(f"통과: {summary['passed']}개")
    output_func(f"실패: {summary['failed']}개")

    if summary["failures"]:
        output_func("\n실패 케이스:")
        for result in summary["failures"]:
            output_func(f"- {result['id']}: {result['reason']}")
    else:
        output_func("실패 케이스가 없습니다.")


def run_json_mode(data_path=DATA_FILE, output_func=print, repeats=10):
    """data.json의 모든 패턴을 분석한다."""
    output_func(f"\nJSON 파일 읽기: {Path(data_path).resolve()}")

    try:
        data = load_json_file(data_path)
        results = analyze_dataset(data)
    except ValueError as error:
        output_func(f"분석 중단: {error}")
        return False

    print_case_results(results, output_func)
    print_performance(measure_sizes(repeats=repeats), output_func)
    print_summary(results, output_func)
    return True


def run(mode=None, data_path=DATA_FILE, repeats=10, input_func=input, output_func=print):
    """프로그램을 실행하고 정상 종료 여부를 반환한다."""
    output_func("=== Mini NPU Simulator ===")

    try:
        selected_mode = mode or choose_mode(input_func, output_func)
        if selected_mode == "user":
            run_user_mode(input_func, output_func, repeats)
            return True
        if selected_mode == "json":
            return run_json_mode(data_path, output_func, repeats)
        output_func(f"지원하지 않는 모드입니다: {selected_mode}")
        return False
    except (KeyboardInterrupt, EOFError):
        output_func("\n입력이 중단되어 안전하게 종료합니다.")
        return False


def main():
    parser = argparse.ArgumentParser(description="Mini NPU Simulator")
    parser.add_argument("--mode", choices=("user", "json"))
    parser.add_argument("--data", type=Path, default=DATA_FILE)
    parser.add_argument("--repeats", type=int, default=10)
    args = parser.parse_args()

    if args.repeats < 10:
        print("설정 오류: 반복 횟수는 최소 10회여야 합니다.")
        return 2
    return 0 if run(args.mode, args.data, args.repeats) else 1


if __name__ == "__main__":
    raise SystemExit(main())
