"""data.json을 읽고 패턴을 분석하는 함수들."""

import json
import re

from npu import EPSILON, classify, make_pattern, measure_mac_time, normalize_label
from npu import validate_matrix


PATTERN_KEY = re.compile(r"^size_(\d+)_(\d+)$")


def load_json_file(path):
    """UTF-8 JSON 파일을 읽는다."""
    try:
        with open(path, "r", encoding="utf-8") as file:
            data = json.load(file)
    except FileNotFoundError as error:
        raise ValueError(f"데이터 파일을 찾을 수 없습니다: {path}") from error
    except json.JSONDecodeError as error:
        raise ValueError(
            f"JSON 형식 오류: {error.lineno}행 {error.colno}열"
        ) from error
    except OSError as error:
        raise ValueError(f"데이터 파일을 읽을 수 없습니다: {error}") from error

    if not isinstance(data, dict):
        raise ValueError("JSON의 가장 바깥쪽 값은 객체여야 합니다.")
    return data


def extract_size(pattern_key):
    """size_13_2 같은 패턴 키에서 크기 13을 꺼낸다."""
    if not isinstance(pattern_key, str):
        raise ValueError("패턴 키는 문자열이어야 합니다.")

    match = PATTERN_KEY.fullmatch(pattern_key)
    if match is None:
        raise ValueError(
            "패턴 키는 size_{N}_{idx} 형식이어야 합니다(예: size_5_1)."
        )
    return int(match.group(1))


def load_filter_group(all_filters, size):
    """filters에서 size_N 그룹을 찾아 라벨과 행렬을 검사한다."""
    group_name = f"size_{size}"
    group = all_filters.get(group_name)
    if not isinstance(group, dict):
        raise ValueError(
            f"{group_name} 필터 객체가 없습니다. "
            f"filters에 {group_name}과 cross/x 필터를 추가하세요."
        )

    filters = {}
    for raw_label, matrix in group.items():
        label = normalize_label(raw_label)
        if label in filters:
            raise ValueError(f"{label} 필터가 중복되었습니다.")
        if validate_matrix(matrix) != size:
            raise ValueError(f"{label} 필터는 {size}×{size}이어야 합니다.")
        filters[label] = matrix

    missing = [label for label in ("Cross", "X") if label not in filters]
    if missing:
        raise ValueError(f"필수 필터가 없습니다: {', '.join(missing)}")
    return filters


def analyze_dataset(data, epsilon=EPSILON):
    """모든 패턴을 분석하고 결과 목록을 반환한다."""
    if not isinstance(data, dict):
        raise ValueError("분석 데이터는 객체여야 합니다.")

    all_filters = data.get("filters")
    all_patterns = data.get("patterns")
    if not isinstance(all_filters, dict):
        raise ValueError("filters는 객체여야 합니다.")
    if not isinstance(all_patterns, dict):
        raise ValueError("patterns는 객체여야 합니다.")

    results = []
    for pattern_key, case in all_patterns.items():
        expected = None

        try:
            size = extract_size(pattern_key)
            if not isinstance(case, dict):
                raise ValueError("패턴 항목은 객체여야 합니다.")

            expected = normalize_label(case.get("expected"))
            pattern = case.get("input")
            if validate_matrix(pattern) != size:
                raise ValueError(f"패턴은 키에 맞게 {size}×{size}이어야 합니다.")

            filters = load_filter_group(all_filters, size)
            scores, predicted = classify(pattern, filters, epsilon)
            passed = predicted == expected

            reason = ""
            if predicted == "UNDECIDED":
                difference = abs(scores["Cross"] - scores["X"])
                reason = (
                    f"점수 차이 {difference:.16g}가 epsilon({epsilon:g})보다 "
                    "작아 UNDECIDED로 판정됨"
                )
            elif not passed:
                reason = f"판정 {predicted}이 기대값 {expected}과 다름"

            results.append(
                {
                    "id": pattern_key,
                    "expected": expected,
                    "predicted": predicted,
                    "scores": scores,
                    "passed": passed,
                    "reason": reason,
                }
            )
        except (TypeError, ValueError) as error:
            results.append(
                {
                    "id": str(pattern_key),
                    "expected": expected,
                    "predicted": "ERROR",
                    "scores": {},
                    "passed": False,
                    "reason": f"스키마/데이터 오류: {error}",
                }
            )

    return results


def summarize(results):
    """전체·통과·실패 개수와 실패 목록을 계산한다."""
    failures = [result for result in results if not result["passed"]]
    return {
        "total": len(results),
        "passed": len(results) - len(failures),
        "failed": len(failures),
        "failures": failures,
    }


def measure_sizes(sizes=(3, 5, 13, 25), repeats=10):
    """크기별 MAC 평균 시간과 N² 연산 횟수를 구한다."""
    performance = []
    for size in sizes:
        pattern = make_pattern(size, "Cross")
        average_ms = measure_mac_time(pattern, pattern, repeats)
        performance.append(
            {
                "size": size,
                "average_ms": average_ms,
                "operations": size * size,
                "repeats": repeats,
            }
        )
    return performance
