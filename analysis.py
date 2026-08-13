"""data.json을 읽고 패턴을 분석하는 함수들.

이 파일은 JSON이라는 외부 데이터와 ``npu.py``의 계산 함수를 연결한다.
계산 공식은 여기에서 다시 만들지 않고 ``classify``를 호출한다.

전체 흐름:
JSON 읽기 → 패턴 키에서 N 추출 → size_N 필터 선택 → MAC 판정 → 결과 저장
"""

import json
import re

from npu import EPSILON, classify, make_pattern, measure_mac_time, normalize_label
from npu import validate_matrix


# 허용하는 패턴 키는 size_5_1, size_13_2 같은 형태다.
# 첫 번째 괄호 (\d+)는 행렬 크기 N, 두 번째 괄호는 패턴 순번을 뜻한다.
# ^와 $는 문자열의 처음부터 끝까지 규칙에 맞아야 한다는 의미다.
PATTERN_KEY = re.compile(r"^size_(\d+)_(\d+)$")


def load_json_file(path):
    """UTF-8 JSON 파일을 읽어 Python 딕셔너리로 반환한다.

    파일 전체를 읽지 못하는 문제는 분석을 시작할 수 없으므로 ValueError로
    알린다. 개별 패턴 문제를 격리하는 처리는 ``analyze_dataset``이 담당한다.
    """
    try:
        # with 블록이 끝나면 파일이 자동으로 닫힌다.
        with open(path, "r", encoding="utf-8") as file:
            data = json.load(file)
    except FileNotFoundError as error:
        # 원래 예외를 사용자에게 이해하기 쉬운 한국어 메시지로 바꾼다.
        raise ValueError(f"데이터 파일을 찾을 수 없습니다: {path}") from error
    except json.JSONDecodeError as error:
        # JSON의 쉼표나 괄호가 잘못되었을 때 행과 열을 알려준다.
        raise ValueError(
            f"JSON 형식 오류: {error.lineno}행 {error.colno}열"
        ) from error
    except OSError as error:
        raise ValueError(f"데이터 파일을 읽을 수 없습니다: {error}") from error

    # 이 과제의 최상위 구조에는 filters와 patterns라는 키가 있어야 하므로
    # JSON 배열(list)이 아니라 JSON 객체(dict)여야 한다.
    if not isinstance(data, dict):
        raise ValueError("JSON의 가장 바깥쪽 값은 객체여야 합니다.")
    return data


def extract_size(pattern_key):
    """``size_13_2`` 같은 패턴 키에서 행렬 크기 13을 꺼낸다."""
    if not isinstance(pattern_key, str):
        raise ValueError("패턴 키는 문자열이어야 합니다.")

    # fullmatch는 문자열 전체가 PATTERN_KEY 규칙에 맞는지 검사한다.
    match = PATTERN_KEY.fullmatch(pattern_key)
    if match is None:
        raise ValueError(
            "패턴 키는 size_{N}_{idx} 형식이어야 합니다(예: size_5_1)."
        )

    # group(1)은 정규식의 첫 번째 괄호, 즉 N이다. 문자열이므로 int로 바꾼다.
    return int(match.group(1))


def load_filter_group(all_filters, size):
    """filters에서 size_N 그룹을 찾아 라벨과 행렬을 검사한다.

    예를 들어 size가 13이면 ``filters["size_13"]``을 선택한다.
    반환값은 라벨이 정규화된 ``{"Cross": 행렬, "X": 행렬}``이다.
    """
    # f-string으로 숫자 size를 JSON 키 형식인 size_N으로 바꾼다.
    group_name = f"size_{size}"
    group = all_filters.get(group_name)
    if not isinstance(group, dict):
        raise ValueError(
            f"{group_name} 필터 객체가 없습니다. "
            f"filters에 {group_name}과 cross/x 필터를 추가하세요."
        )

    # 외부 키 cross/x를 내부 표준 라벨 Cross/X로 바꿔 저장할 딕셔너리다.
    filters = {}
    for raw_label, matrix in group.items():
        label = normalize_label(raw_label)

        # cross와 +가 함께 있으면 둘 다 Cross가 되므로 어떤 필터를 써야 할지
        # 모호하다. 그래서 조용히 덮어쓰지 않고 중복 오류로 처리한다.
        if label in filters:
            raise ValueError(f"{label} 필터가 중복되었습니다.")

        # 키가 size_13이면 실제 필터도 반드시 13×13이어야 한다.
        if validate_matrix(matrix) != size:
            raise ValueError(f"{label} 필터는 {size}×{size}이어야 합니다.")
        filters[label] = matrix

    # MAC 비교에는 두 후보가 모두 필요하다.
    missing = [label for label in ("Cross", "X") if label not in filters]
    if missing:
        raise ValueError(f"필수 필터가 없습니다: {', '.join(missing)}")
    return filters


def analyze_dataset(data, epsilon=EPSILON):
    """모든 패턴을 분석하고 패턴별 결과 딕셔너리 목록을 반환한다.

    한 패턴이 잘못되어도 전체 반복문을 멈추지 않는다. 잘못된 패턴만
    ERROR/FAIL 결과로 추가하고 다음 패턴을 계속 분석하는 것이 핵심이다.
    """
    if not isinstance(data, dict):
        raise ValueError("분석 데이터는 객체여야 합니다.")

    # dict.get은 키가 없을 때 프로그램을 즉시 중단시키지 않고 None을 준다.
    # 이어지는 isinstance 검사에서 더 구체적인 메시지를 만들 수 있다.
    all_filters = data.get("filters")
    all_patterns = data.get("patterns")
    if not isinstance(all_filters, dict):
        raise ValueError("filters는 객체여야 합니다.")
    if not isinstance(all_patterns, dict):
        raise ValueError("patterns는 객체여야 합니다.")

    # 각 패턴의 점수·판정·PASS/FAIL을 차례대로 담을 목록이다.
    results = []
    for pattern_key, case in all_patterns.items():
        # 오류가 expected 정규화 이전에 발생할 수 있으므로 기본값은 None이다.
        expected = None

        try:
            # 1단계: 키에서 N을 꺼내고 케이스 구조를 확인한다.
            size = extract_size(pattern_key)
            if not isinstance(case, dict):
                raise ValueError("패턴 항목은 객체여야 합니다.")

            # 2단계: expected를 Cross/X로 정규화하고 입력 행렬을 검사한다.
            expected = normalize_label(case.get("expected"))
            pattern = case.get("input")
            if validate_matrix(pattern) != size:
                raise ValueError(f"패턴은 키에 맞게 {size}×{size}이어야 합니다.")

            # 3단계: 같은 N의 필터를 가져와 두 MAC 점수와 판정을 구한다.
            filters = load_filter_group(all_filters, size)
            scores, predicted = classify(pattern, filters, epsilon)

            # 내부 판정 문자열과 정규화된 expected가 완전히 같아야 PASS다.
            # UNDECIDED는 Cross도 X도 아니므로 자연스럽게 FAIL이 된다.
            passed = predicted == expected

            # PASS에는 이유가 필요 없으므로 빈 문자열을 사용한다.
            reason = ""
            if predicted == "UNDECIDED":
                # 수치 비교 문제를 설명할 수 있도록 실제 점수 차이도 기록한다.
                difference = abs(scores["Cross"] - scores["X"])
                reason = (
                    f"점수 차이 {difference:.16g}가 epsilon({epsilon:g})보다 "
                    "작아 UNDECIDED로 판정됨"
                )
            elif not passed:
                reason = f"판정 {predicted}이 기대값 {expected}과 다름"

            # 딕셔너리 한 개가 패턴 한 건의 분석 결과다.
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
            # 케이스 단위 오류 격리: 오류를 결과로 바꾸고 다음 반복을 계속한다.
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
    """전체·통과·실패 개수와 실패 목록을 하나의 딕셔너리로 반환한다."""
    # passed가 False인 결과만 새 목록에 모은다.
    failures = [result for result in results if not result["passed"]]
    return {
        "total": len(results),
        "passed": len(results) - len(failures),
        "failed": len(failures),
        "failures": failures,
    }


def measure_sizes(sizes=(3, 5, 13, 25), repeats=10):
    """크기별 MAC 평균 시간과 N² 연산 횟수를 구한다.

    실제 JSON 파일 읽기나 화면 출력은 여기에서 하지 않는다. 같은 방식으로
    만든 Cross 패턴끼리 MAC 함수만 측정하므로 크기 변화에 집중할 수 있다.
    """
    performance = []
    for size in sizes:
        # 입력 크기만 다르고 계산 내용은 같도록 Cross 패턴을 자동 생성한다.
        pattern = make_pattern(size, "Cross")
        average_ms = measure_mac_time(pattern, pattern, repeats)

        # N×N 행렬의 위치 수는 N²이므로 size * size로 계산한다.
        performance.append(
            {
                "size": size,
                "average_ms": average_ms,
                "operations": size * size,
                "repeats": repeats,
            }
        )
    return performance
