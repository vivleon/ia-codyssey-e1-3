"""MAC 계산에 필요한 가장 기본적인 함수들."""

from time import perf_counter


EPSILON = 1e-9


def validate_matrix(matrix):
    """행렬이 숫자로 된 정사각형 목록인지 확인한다."""
    if not isinstance(matrix, list) or not matrix:
        raise ValueError("행렬은 비어 있지 않은 행의 목록이어야 합니다.")

    size = len(matrix)
    for row_number, row in enumerate(matrix, start=1):
        if not isinstance(row, list) or len(row) != size:
            raise ValueError(f"{size}×{size} 정사각형 행렬이어야 합니다.")

        for value in row:
            if isinstance(value, bool) or not isinstance(value, (int, float)):
                raise ValueError(f"{row_number}행에는 숫자만 사용할 수 있습니다.")

    return size


def normalize_label(label):
    """여러 라벨 표현을 프로그램이 사용하는 Cross 또는 X로 바꾼다."""
    if not isinstance(label, str):
        raise ValueError("라벨은 문자열이어야 합니다.")

    label_map = {
        "+": "Cross",
        "cross": "Cross",
        "x": "X",
    }
    key = label.strip().lower()

    if key not in label_map:
        raise ValueError(f"지원하지 않는 라벨입니다: {label!r}")
    return label_map[key]


def mac_score(pattern, filter_matrix):
    """같은 위치의 값을 곱하고 모두 더해 MAC 점수를 반환한다."""
    pattern_size = validate_matrix(pattern)
    filter_size = validate_matrix(filter_matrix)

    if pattern_size != filter_size:
        raise ValueError("패턴과 필터의 크기가 다릅니다.")

    total = 0.0
    for row in range(pattern_size):
        for column in range(pattern_size):
            total += pattern[row][column] * filter_matrix[row][column]
    return total


def compare_scores(score_a, score_b, label_a="A", label_b="B", epsilon=EPSILON):
    """두 점수를 비교해 우세 라벨 또는 UNDECIDED를 반환한다."""
    if epsilon <= 0:
        raise ValueError("epsilon은 0보다 커야 합니다.")

    if abs(score_a - score_b) < epsilon:
        return "UNDECIDED"
    if score_a > score_b:
        return label_a
    return label_b


def classify(pattern, filters, epsilon=EPSILON):
    """Cross와 X 필터의 점수를 계산하고 최종 라벨을 판정한다."""
    if "Cross" not in filters or "X" not in filters:
        raise ValueError("Cross와 X 필터가 모두 필요합니다.")

    scores = {
        "Cross": mac_score(pattern, filters["Cross"]),
        "X": mac_score(pattern, filters["X"]),
    }
    predicted = compare_scores(
        scores["Cross"],
        scores["X"],
        "Cross",
        "X",
        epsilon,
    )
    return scores, predicted


def measure_mac_time(pattern, filter_matrix, repeats=10):
    """MAC 계산만 여러 번 실행해 1회 평균 시간을 밀리초로 반환한다."""
    if not isinstance(repeats, int) or isinstance(repeats, bool) or repeats < 1:
        raise ValueError("반복 횟수는 1 이상의 정수여야 합니다.")

    # 첫 실행의 영향을 줄이기 위한 준비 실행이다. 측정 시간에는 포함하지 않는다.
    for _ in range(3):
        mac_score(pattern, filter_matrix)

    start = perf_counter()
    for _ in range(repeats):
        mac_score(pattern, filter_matrix)
    elapsed_seconds = perf_counter() - start

    return elapsed_seconds * 1000 / repeats


def make_pattern(size, label):
    """성능 측정용 Cross 또는 X 패턴을 만든다."""
    if not isinstance(size, int) or isinstance(size, bool) or size < 1:
        raise ValueError("크기는 1 이상의 정수여야 합니다.")

    label = normalize_label(label)
    matrix = [[0.0 for _ in range(size)] for _ in range(size)]

    if label == "Cross":
        center = size // 2
        for index in range(size):
            matrix[center][index] = 1.0
            matrix[index][center] = 1.0
    else:
        for index in range(size):
            matrix[index][index] = 1.0
            matrix[index][size - index - 1] = 1.0

    return matrix
