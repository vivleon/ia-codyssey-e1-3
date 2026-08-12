"""data.json 스키마 검증, 케이스 분석, 성능 측정."""

import json
import re
from dataclasses import dataclass
from json import JSONDecodeError
from pathlib import Path
from typing import Dict, List, Mapping, Optional, Sequence

from npu import (
    EPSILON,
    STANDARD_LABELS,
    LabelError,
    Matrix,
    MatrixError,
    benchmark_mac,
    classify,
    generate_pattern,
    normalize_label,
)


PATTERN_KEY = re.compile(r"^size_(\d+)_(\d+)$")


class DataAnalysisError(ValueError):
    """파일 전체를 분석할 수 없는 JSON 또는 최상위 스키마 오류."""


class CaseSchemaError(ValueError):
    """특정 패턴 케이스만 분석할 수 없는 스키마 오류."""


@dataclass(frozen=True)
class CaseResult:
    """패턴 한 건의 점수, 판정, 기대값 비교 결과."""

    identifier: str
    expected: Optional[str]
    predicted: str
    scores: Dict[str, float]
    passed: bool
    reason: Optional[str] = None


@dataclass(frozen=True)
class AnalysisReport:
    """모든 케이스 결과와 집계 정보를 제공한다."""

    results: List[CaseResult]

    @property
    def total_count(self) -> int:
        return len(self.results)

    @property
    def passed_count(self) -> int:
        return sum(1 for result in self.results if result.passed)

    @property
    def failed_count(self) -> int:
        return self.total_count - self.passed_count

    @property
    def failures(self) -> List[CaseResult]:
        return [result for result in self.results if not result.passed]


@dataclass(frozen=True)
class PerformanceResult:
    """특정 크기의 평균 MAC 실행 시간과 연산 횟수."""

    size: int
    average_ms: float
    operations: int
    repeats: int


def load_json_file(path: Path) -> Mapping[str, object]:
    """UTF-8 JSON 파일을 읽고 사용자가 이해할 수 있는 오류로 변환한다."""
    try:
        with Path(path).open("r", encoding="utf-8") as data_handle:
            data = json.load(data_handle)
    except FileNotFoundError as error:
        raise DataAnalysisError(f"데이터 파일을 찾을 수 없습니다: {path}") from error
    except JSONDecodeError as error:
        raise DataAnalysisError(
            f"JSON 형식 오류: {error.lineno}행 {error.colno}열"
        ) from error
    except OSError as error:
        raise DataAnalysisError(f"데이터 파일을 읽을 수 없습니다: {error}") from error

    if not isinstance(data, dict):
        raise DataAnalysisError("JSON 최상위 값은 객체여야 합니다.")
    return data


def analyze_dataset(
    data: Mapping[str, object],
    epsilon: float = EPSILON,
) -> AnalysisReport:
    """필터와 패턴을 검증하고 모든 케이스를 중단 없이 분석한다."""
    if not isinstance(data, Mapping):
        raise DataAnalysisError("분석 데이터는 객체여야 합니다.")
    raw_filters = data.get("filters")
    raw_patterns = data.get("patterns")
    if not isinstance(raw_filters, dict):
        raise DataAnalysisError("filters는 객체여야 합니다.")
    if not isinstance(raw_patterns, dict):
        raise DataAnalysisError("patterns는 객체여야 합니다.")

    results = []
    for identifier, raw_case in raw_patterns.items():
        expected: Optional[str] = None
        try:
            if not isinstance(identifier, str):
                raise CaseSchemaError("패턴 식별자는 문자열이어야 합니다.")
            size = _extract_size(identifier)
            if not isinstance(raw_case, dict):
                raise CaseSchemaError("패턴 항목은 객체여야 합니다.")

            expected = normalize_label(raw_case.get("expected"))
            pattern = Matrix(raw_case.get("input"))
            if pattern.size != size:
                raise CaseSchemaError(
                    f"키가 선언한 크기는 {size}×{size}이지만 "
                    f"패턴은 {pattern.size}×{pattern.size}입니다."
                )

            filters = _load_filter_group(raw_filters, size)
            classification = classify(pattern, filters, epsilon)
            # expected는 Cross 또는 X로 정규화된다. 동점인 UNDECIDED는 어느
            # 기대 라벨과도 같지 않으므로 분석 리포트에서 FAIL로 집계한다.
            passed = classification.predicted == expected
            reason = _comparison_reason(
                classification.predicted,
                expected,
                classification.scores,
                epsilon,
            )
            results.append(
                CaseResult(
                    identifier=identifier,
                    expected=expected,
                    predicted=classification.predicted,
                    scores=classification.scores,
                    passed=passed,
                    reason=reason,
                )
            )
        except (CaseSchemaError, LabelError, MatrixError, TypeError) as error:
            results.append(
                CaseResult(
                    identifier=str(identifier),
                    expected=expected,
                    predicted="ERROR",
                    scores={},
                    passed=False,
                    reason=f"스키마/데이터 오류: {error}",
                )
            )

    return AnalysisReport(results=results)


def analyze_file(path: Path, epsilon: float = EPSILON) -> AnalysisReport:
    """JSON 파일을 읽고 모든 패턴을 분석한다."""
    return analyze_dataset(load_json_file(path), epsilon)


def measure_sizes(
    sizes: Sequence[int] = (3, 5, 13, 25),
    repeats: int = 10,
) -> List[PerformanceResult]:
    """생성한 Cross 패턴으로 크기별 MAC 평균 시간을 측정한다."""
    results = []
    for size in sizes:
        pattern = generate_pattern(size, "Cross")
        filter_matrix = generate_pattern(size, "Cross")
        average_ms = benchmark_mac(pattern, filter_matrix, repeats)
        results.append(
            PerformanceResult(
                size=size,
                average_ms=average_ms,
                operations=size * size,
                repeats=repeats,
            )
        )
    return results


def _extract_size(identifier: str) -> int:
    match = PATTERN_KEY.fullmatch(identifier)
    if match is None:
        raise CaseSchemaError(
            "패턴 키는 size_{N}_{idx} 형식이어야 합니다."
        )
    return int(match.group(1))


def _load_filter_group(
    raw_filters: Mapping[str, object],
    size: int,
) -> Dict[str, Matrix]:
    group_key = f"size_{size}"
    raw_group = raw_filters.get(group_key)
    if not isinstance(raw_group, dict):
        raise CaseSchemaError(f"{group_key} 필터 객체가 없습니다.")

    normalized_filters: Dict[str, Matrix] = {}
    for raw_label, raw_matrix in raw_group.items():
        standard_label = normalize_label(raw_label)
        if standard_label in normalized_filters:
            raise CaseSchemaError(f"{standard_label} 필터가 중복되었습니다.")
        matrix = Matrix(raw_matrix)
        if matrix.size != size:
            raise CaseSchemaError(
                f"{standard_label} 필터 크기는 {size}×{size}이어야 하지만 "
                f"{matrix.size}×{matrix.size}입니다."
            )
        normalized_filters[standard_label] = matrix

    missing = [
        label for label in STANDARD_LABELS if label not in normalized_filters
    ]
    if missing:
        raise CaseSchemaError(f"필수 필터가 없습니다: {', '.join(missing)}")
    return normalized_filters


def _comparison_reason(
    predicted: str,
    expected: str,
    scores: Mapping[str, float],
    epsilon: float,
) -> Optional[str]:
    if predicted == expected:
        return None
    if predicted == "UNDECIDED":
        difference = abs(scores["Cross"] - scores["X"])
        return (
            f"점수 차이 {difference:.16g}가 epsilon({epsilon:g})보다 작아 "
            "UNDECIDED로 판정됨"
        )
    return f"판정 {predicted}이 기대값 {expected}과 다름"
