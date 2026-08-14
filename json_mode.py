"""data.json 파일을 읽고 여러 패턴을 분석하는 모드입니다."""


import json

from mac import calculate_mac, check_matrix, choose_winner, normalize_label
from performance import measure_sizes, print_performance_table


def load_json(file_path):
    """JSON 파일을 읽어 딕셔너리로 돌려줍니다."""

    try:
        with open(file_path, "r", encoding="utf-8") as file:
            data = json.load(file)

    except FileNotFoundError as error:
        raise ValueError(f"파일을 찾을 수 없습니다: {file_path}") from error

    except json.JSONDecodeError as error:
        raise ValueError(f"JSON 문법 오류: {error.lineno}행") from error

    if not isinstance(data, dict):
        raise ValueError("JSON의 가장 바깥쪽은 객체여야 합니다.")

    return data


def get_size_from_key(pattern_key):
    """size_13_2 같은 키에서 크기 13을 꺼냅니다."""

    if not isinstance(pattern_key, str):
        raise ValueError("패턴 키는 글자여야 합니다.")

    parts = pattern_key.split("_")

    # 올바른 키는 ["size", "13", "2"]처럼 세 부분입니다.
    if len(parts) != 3 or parts[0] != "size":
        raise ValueError("패턴 키는 size_{N}_{idx} 형식이어야 합니다.")

    if not parts[1].isdigit() or not parts[2].isdigit():
        raise ValueError("패턴 키의 N과 idx는 숫자여야 합니다.")

    return int(parts[1])


def get_filters(all_filters, size):
    """size_N 필터를 찾아 Cross와 X라는 표준 이름으로 정리합니다."""

    group_name = f"size_{size}"
    filter_group = all_filters.get(group_name)

    if not isinstance(filter_group, dict):
        raise ValueError(f"filters에 {group_name}이 없습니다.")

    standard_filters = {}

    for original_label, matrix in filter_group.items():
        standard_label = normalize_label(original_label)

        if standard_label in standard_filters:
            raise ValueError(f"{standard_label} 필터가 중복되었습니다.")

        check_matrix(matrix, size)
        standard_filters[standard_label] = matrix

    if "Cross" not in standard_filters or "X" not in standard_filters:
        raise ValueError("Cross와 X 필터가 모두 필요합니다.")

    return standard_filters


def analyze_one_case(pattern_key, case, all_filters):
    """패턴 한 개의 점수, 판정, PASS/FAIL을 구합니다."""

    size = get_size_from_key(pattern_key)

    if not isinstance(case, dict):
        raise ValueError("패턴 항목은 객체여야 합니다.")

    pattern = case.get("input")
    expected = normalize_label(case.get("expected"))

    check_matrix(pattern, size)
    filters = get_filters(all_filters, size)

    cross_score = calculate_mac(pattern, filters["Cross"])
    x_score = calculate_mac(pattern, filters["X"])

    predicted = choose_winner(
        cross_score,
        x_score,
        "Cross",
        "X",
    )

    passed = predicted == expected
    reason = ""

    if predicted == "UNDECIDED":
        difference = abs(cross_score - x_score)
        reason = f"점수 차이 {difference:.16g}가 epsilon보다 작음"

    elif not passed:
        reason = f"판정 {predicted}이 expected {expected}와 다름"

    return {
        "id": pattern_key,
        "expected": expected,
        "predicted": predicted,
        "cross_score": cross_score,
        "x_score": x_score,
        "passed": passed,
        "reason": reason,
    }


def analyze_all(data):
    """모든 패턴을 분석하되, 한 케이스가 틀려도 계속 진행합니다."""

    all_filters = data.get("filters")
    all_patterns = data.get("patterns")

    if not isinstance(all_filters, dict):
        raise ValueError("filters는 객체여야 합니다.")

    if not isinstance(all_patterns, dict):
        raise ValueError("patterns는 객체여야 합니다.")

    results = []

    for pattern_key, case in all_patterns.items():
        try:
            result = analyze_one_case(pattern_key, case, all_filters)

        except (TypeError, ValueError) as error:
            # 오류를 결과로 저장하면 다음 패턴 분석을 계속할 수 있습니다.
            result = {
                "id": str(pattern_key),
                "expected": "UNKNOWN",
                "predicted": "ERROR",
                "cross_score": None,
                "x_score": None,
                "passed": False,
                "reason": f"데이터/스키마 오류: {error}",
            }

        results.append(result)

    return results


def count_results(results):
    """전체, 통과, 실패 개수를 셉니다."""

    passed_count = 0
    failed_results = []

    for result in results:
        if result["passed"]:
            passed_count = passed_count + 1
        else:
            failed_results.append(result)

    return {
        "total": len(results),
        "passed": passed_count,
        "failed": len(failed_results),
        "failures": failed_results,
    }


def print_case(result, print_function=print):
    """패턴 한 개의 분석 결과를 출력합니다."""

    print_function(f"\n--- {result['id']} ---")

    if result["cross_score"] is not None:
        print_function(f"Cross 점수: {result['cross_score']:.16g}")
        print_function(f"X 점수: {result['x_score']:.16g}")

    status = "PASS" if result["passed"] else "FAIL"

    print_function(
        f"판정: {result['predicted']} | "
        f"expected: {result['expected']} | {status}"
    )

    if result["reason"]:
        print_function(f"사유: {result['reason']}")


def print_summary(results, print_function=print):
    """전체 결과와 실패 케이스를 출력합니다."""

    summary = count_results(results)

    print_function("\n[결과 요약]")
    print_function(f"총 테스트: {summary['total']}개")
    print_function(f"통과: {summary['passed']}개")
    print_function(f"실패: {summary['failed']}개")

    if summary["failed"] == 0:
        print_function("실패 케이스가 없습니다.")
    else:
        print_function("\n실패 케이스:")

        for result in summary["failures"]:
            print_function(f"- {result['id']}: {result['reason']}")


def run_json_mode(file_path, print_function=print, repeats=10):
    """JSON 로드, 판정, 성능 분석, 결과 요약을 순서대로 실행합니다."""

    print_function("\n=== data.json 분석 모드 ===")

    try:
        data = load_json(file_path)
        results = analyze_all(data)

    except ValueError as error:
        print_function(f"분석 중단: {error}")
        return False

    for result in results:
        print_case(result, print_function)

    performance_results = measure_sizes(repeats)
    print_performance_table(performance_results, repeats, print_function)
    print_summary(results, print_function)

    return True
