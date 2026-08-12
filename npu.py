"""외부 라이브러리 없이 구현한 Mini NPU 핵심 연산."""

from dataclasses import dataclass
from time import perf_counter_ns
from typing import Dict, List, Mapping, Sequence


EPSILON = 1e-9
STANDARD_LABELS = ("Cross", "X")
WARMUP_REPEATS = 3


class MatrixError(ValueError):
    """행렬의 값이나 크기가 올바르지 않을 때 발생한다."""


class LabelError(ValueError):
    """지원하지 않는 라벨을 발견했을 때 발생한다."""


class Matrix:
    """n×n 실수 행렬을 저장하고 위치별 읽기/쓰기를 제공한다."""

    def __init__(self, rows: Sequence[Sequence[float]]) -> None:
        if isinstance(rows, (str, bytes)) or not isinstance(rows, Sequence):
            raise MatrixError("행렬은 행의 목록이어야 합니다.")
        if not rows:
            raise MatrixError("행렬은 비어 있을 수 없습니다.")

        size = len(rows)
        normalized: List[List[float]] = []
        for row_index, row in enumerate(rows):
            if isinstance(row, (str, bytes)) or not isinstance(row, Sequence):
                raise MatrixError(f"{row_index + 1}행은 숫자 목록이어야 합니다.")
            if len(row) != size:
                raise MatrixError(
                    f"{size}×{size} 행렬이어야 하지만 "
                    f"{row_index + 1}행의 열 수는 {len(row)}개입니다."
                )

            normalized_row: List[float] = []
            for column_index, value in enumerate(row):
                if isinstance(value, bool) or not isinstance(value, (int, float)):
                    raise MatrixError(
                        f"({row_index + 1}, {column_index + 1}) 값은 "
                        "숫자여야 합니다."
                    )
                normalized_row.append(float(value))
            normalized.append(normalized_row)

        self._size = size
        self._values = normalized

    @property
    def size(self) -> int:
        """행렬 한 변의 길이를 반환한다."""
        return self._size

    def get(self, row: int, column: int) -> float:
        """0부터 시작하는 위치의 값을 읽는다."""
        self._validate_position(row, column)
        return self._values[row][column]

    def set(self, row: int, column: int, value: float) -> None:
        """0부터 시작하는 위치에 숫자 값을 저장한다."""
        self._validate_position(row, column)
        if isinstance(value, bool) or not isinstance(value, (int, float)):
            raise MatrixError("저장할 값은 숫자여야 합니다.")
        self._values[row][column] = float(value)

    def to_rows(self) -> List[List[float]]:
        """호출자가 수정해도 원본이 바뀌지 않는 2차원 목록을 반환한다."""
        return [list(row) for row in self._values]

    def flatten(self) -> List[float]:
        """행 우선 순서의 1차원 목록으로 변환한다."""
        return [value for row in self._values for value in row]

    def _validate_position(self, row: int, column: int) -> None:
        if not 0 <= row < self._size or not 0 <= column < self._size:
            raise IndexError(
                f"행과 열은 0부터 {self._size - 1} 사이여야 합니다."
            )


@dataclass(frozen=True)
class Classification:
    """두 필터의 점수와 최종 판정 결과."""

    scores: Dict[str, float]
    predicted: str


def normalize_label(raw_label: object) -> str:
    """JSON 라벨과 필터 키를 Cross 또는 X로 정규화한다."""
    if not isinstance(raw_label, str):
        raise LabelError("라벨은 문자열이어야 합니다.")

    normalized = raw_label.strip().lower()
    mapping = {
        "+": "Cross",
        "cross": "Cross",
        "x": "X",
    }
    if normalized not in mapping:
        raise LabelError(f"지원하지 않는 라벨입니다: {raw_label!r}")
    return mapping[normalized]


def mac_score(pattern: Matrix, filter_matrix: Matrix) -> float:
    """같은 위치의 값을 곱하고 누적하는 MAC 점수를 계산한다."""
    if pattern.size != filter_matrix.size:
        raise MatrixError(
            f"패턴({pattern.size}×{pattern.size})과 필터"
            f"({filter_matrix.size}×{filter_matrix.size})의 크기가 다릅니다."
        )

    total = 0.0
    for row in range(pattern.size):
        for column in range(pattern.size):
            total += pattern.get(row, column) * filter_matrix.get(row, column)
    return total


def classify(
    pattern: Matrix,
    filters: Mapping[str, Matrix],
    epsilon: float = EPSILON,
) -> Classification:
    """Cross와 X 점수를 계산하고 epsilon 정책으로 판정한다."""
    if epsilon < 0:
        raise ValueError("epsilon은 0 이상이어야 합니다.")
    missing = [label for label in STANDARD_LABELS if label not in filters]
    if missing:
        raise MatrixError(f"필수 필터가 없습니다: {', '.join(missing)}")

    scores = {
        label: mac_score(pattern, filters[label])
        for label in STANDARD_LABELS
    }
    predicted = compare_scores(
        scores["Cross"],
        scores["X"],
        "Cross",
        "X",
        epsilon,
    )
    return Classification(scores=scores, predicted=predicted)


def compare_scores(
    score_a: float,
    score_b: float,
    label_a: str = "A",
    label_b: str = "B",
    epsilon: float = EPSILON,
) -> str:
    """두 점수를 비교해 우세 라벨 또는 UNDECIDED를 반환한다."""
    if epsilon < 0:
        raise ValueError("epsilon은 0 이상이어야 합니다.")
    difference = score_a - score_b
    if abs(difference) < epsilon:
        return "UNDECIDED"
    if difference > 0:
        return label_a
    return label_b


def benchmark_mac(
    pattern: Matrix,
    filter_matrix: Matrix,
    repeats: int = 10,
) -> float:
    """I/O를 제외하고 MAC 함수 호출 시간의 평균을 밀리초로 반환한다."""
    if isinstance(repeats, bool) or not isinstance(repeats, int) or repeats <= 0:
        raise ValueError("반복 횟수는 1 이상의 정수여야 합니다.")

    # 짧은 연산은 첫 호출 비용과 실행 환경의 순간적인 영향을 크게 받는다.
    # 측정에 포함하지 않는 소규모 워밍업으로 캐시와 인터프리터 경로를 준비한다.
    for _ in range(WARMUP_REPEATS):
        mac_score(pattern, filter_matrix)
    started_at = perf_counter_ns()
    for _ in range(repeats):
        mac_score(pattern, filter_matrix)
    elapsed_ns = perf_counter_ns() - started_at
    return elapsed_ns / repeats / 1_000_000


def generate_pattern(size: int, label: str) -> Matrix:
    """성능 측정에 사용할 Cross 또는 X 패턴을 생성한다."""
    if isinstance(size, bool) or not isinstance(size, int) or size <= 0:
        raise MatrixError("크기는 1 이상의 정수여야 합니다.")
    standard_label = normalize_label(label)
    rows = [[0.0 for _ in range(size)] for _ in range(size)]

    if standard_label == "Cross":
        center = size // 2
        for index in range(size):
            rows[center][index] = 1.0
            rows[index][center] = 1.0
    else:
        for index in range(size):
            rows[index][index] = 1.0
            rows[index][size - index - 1] = 1.0
    return Matrix(rows)
