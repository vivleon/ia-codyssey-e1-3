"""MAC 계산에 필요한 가장 기본적인 함수들.

이 파일에는 화면 출력이나 JSON 처리가 없다. 순수한 계산만 모아 두면
입력 방식이 바뀌어도 MAC 원리는 그대로 재사용할 수 있다.

처음 읽을 때는 다음 순서가 쉽다.
1. ``mac_score``: 같은 위치를 곱하고 더한다.
2. ``compare_scores``: 두 점수를 epsilon으로 비교한다.
3. ``classify``: Cross와 X 계산을 한 번에 묶는다.
"""

from time import perf_counter


# 두 점수의 차이가 이 값보다 작으면 의미 있는 차이가 아니라고 본다.
# 1e-9는 0.000000001을 뜻한다.
EPSILON = 1e-9


def validate_matrix(matrix):
    """행렬이 숫자로 된 정사각형 목록인지 확인하고 한 변의 길이를 반환한다.

    예를 들어 ``[[1, 0], [0, 1]]``은 2×2 행렬이므로 2를 반환한다.
    빈 목록, 행마다 길이가 다른 목록, 문자열이 섞인 목록은 거부한다.
    """
    # JSON 배열과 사용자 입력은 Python에서 list가 된다.
    # 먼저 가장 바깥쪽 값이 비어 있지 않은 목록인지 확인한다.
    if not isinstance(matrix, list) or not matrix:
        raise ValueError("행렬은 비어 있지 않은 행의 목록이어야 합니다.")

    # 정사각형 행렬에서는 행의 개수와 각 행의 열 개수가 모두 size와 같다.
    size = len(matrix)
    for row_number, row in enumerate(matrix, start=1):
        if not isinstance(row, list) or len(row) != size:
            raise ValueError(f"{size}×{size} 정사각형 행렬이어야 합니다.")

        # bool도 Python에서는 int의 한 종류이므로 별도로 제외한다.
        for value in row:
            if isinstance(value, bool) or not isinstance(value, (int, float)):
                raise ValueError(f"{row_number}행에는 숫자만 사용할 수 있습니다.")

    return size


def normalize_label(label):
    """여러 라벨 표현을 프로그램이 사용하는 Cross 또는 X로 바꾼다.

    JSON의 expected에는 ``+``가, 필터 키에는 ``cross``가 사용될 수 있다.
    두 표현을 모두 ``Cross``로 바꿔야 문자열 차이 때문에 판정이 틀리지 않는다.
    """
    if not isinstance(label, str):
        raise ValueError("라벨은 문자열이어야 합니다.")

    # 딕셔너리의 왼쪽은 외부 입력, 오른쪽은 내부 표준 라벨이다.
    label_map = {
        "+": "Cross",
        "cross": "Cross",
        "x": "X",
    }
    # 앞뒤 공백과 대소문자 차이를 먼저 없앤다.
    key = label.strip().lower()

    # 모르는 라벨을 임의로 Cross나 X로 추측하지 않는다.
    if key not in label_map:
        raise ValueError(f"지원하지 않는 라벨입니다: {label!r}")
    return label_map[key]


def mac_score(pattern, filter_matrix):
    """같은 위치의 값을 곱하고 모두 더해 MAC 점수를 반환한다.

    MAC은 Multiply-Accumulate의 약자다.
    Multiply는 위치별 곱셈, Accumulate는 곱한 값을 계속 더하는 과정이다.
    """
    # 계산 전에 두 입력이 각각 올바른 정사각형 행렬인지 확인한다.
    pattern_size = validate_matrix(pattern)
    filter_size = validate_matrix(filter_matrix)

    # 같은 위치끼리 곱하려면 두 행렬의 크기가 반드시 같아야 한다.
    if pattern_size != filter_size:
        raise ValueError("패턴과 필터의 크기가 다릅니다.")

    # total은 지금까지 계산한 곱셈 결과의 누적 합이다.
    total = 0.0

    # 바깥 반복문은 행, 안쪽 반복문은 열을 움직인다.
    # N×N 행렬의 모든 N²개 위치를 정확히 한 번 방문한다.
    for row in range(pattern_size):
        for column in range(pattern_size):
            # 예: pattern[0][1]과 filter_matrix[0][1]을 곱해 더한다.
            total += pattern[row][column] * filter_matrix[row][column]
    return total


def compare_scores(score_a, score_b, label_a="A", label_b="B", epsilon=EPSILON):
    """두 점수를 비교해 우세 라벨 또는 UNDECIDED를 반환한다.

    실수는 컴퓨터 내부에서 정확히 표현되지 않을 수 있다. 따라서 ``==``로
    완전한 같음을 검사하지 않고, 두 점수의 차이가 epsilon보다 작은지 본다.
    """
    if epsilon <= 0:
        raise ValueError("epsilon은 0보다 커야 합니다.")

    # abs는 차이의 부호를 없애고 거리만 구한다.
    if abs(score_a - score_b) < epsilon:
        return "UNDECIDED"

    # 동점이 아닐 때만 실제 대소를 비교한다.
    if score_a > score_b:
        return label_a
    return label_b


def classify(pattern, filters, epsilon=EPSILON):
    """Cross와 X 필터의 점수를 계산하고 ``(점수들, 판정)``을 반환한다.

    ``filters``는 ``{"Cross": 행렬, "X": 행렬}`` 형태의 딕셔너리다.
    반환 예: ``({"Cross": 1.0, "X": 5.0}, "X")``
    """
    # 두 후보 중 하나라도 없으면 비교 자체가 불가능하다.
    if "Cross" not in filters or "X" not in filters:
        raise ValueError("Cross와 X 필터가 모두 필요합니다.")

    # 같은 패턴을 두 필터에 각각 MAC 연산한다.
    scores = {
        "Cross": mac_score(pattern, filters["Cross"]),
        "X": mac_score(pattern, filters["X"]),
    }

    # 점수 계산과 동점 정책을 분리하면 각각 독립적으로 이해하고 테스트할 수 있다.
    predicted = compare_scores(
        scores["Cross"],
        scores["X"],
        "Cross",
        "X",
        epsilon,
    )
    return scores, predicted


def measure_mac_time(pattern, filter_matrix, repeats=10):
    """MAC 계산만 여러 번 실행해 1회 평균 시간을 밀리초(ms)로 반환한다.

    파일 읽기, 사용자 입력, 화면 출력은 이 함수 밖에서 수행한다. 따라서
    타이머 사이에는 평가 기준이 요구하는 ``mac_score`` 호출만 들어간다.
    """
    if not isinstance(repeats, int) or isinstance(repeats, bool) or repeats < 1:
        raise ValueError("반복 횟수는 1 이상의 정수여야 합니다.")

    # 첫 실행은 캐시와 인터프리터 준비 비용의 영향을 더 받을 수 있다.
    # 그래서 3번 미리 실행하지만, 이 준비 실행은 측정 시간에 포함하지 않는다.
    for _ in range(3):
        mac_score(pattern, filter_matrix)

    # perf_counter는 짧은 실행 시간을 재는 데 적합한 고해상도 타이머다.
    start = perf_counter()
    for _ in range(repeats):
        mac_score(pattern, filter_matrix)
    elapsed_seconds = perf_counter() - start

    # 초 × 1000 = 밀리초, 전체 시간 ÷ 반복 횟수 = 1회 평균이다.
    return elapsed_seconds * 1000 / repeats


def make_pattern(size, label):
    """성능 측정용 N×N Cross 또는 X 패턴을 2차원 목록으로 만든다."""
    if not isinstance(size, int) or isinstance(size, bool) or size < 1:
        raise ValueError("크기는 1 이상의 정수여야 합니다.")

    label = normalize_label(label)

    # 먼저 모든 위치가 0인 N×N 목록을 만든다.
    matrix = [[0.0 for _ in range(size)] for _ in range(size)]

    if label == "Cross":
        # 가운데 행과 가운데 열을 1로 만들면 십자가가 된다.
        center = size // 2
        for index in range(size):
            matrix[center][index] = 1.0
            matrix[index][center] = 1.0
    else:
        # 왼쪽 위→오른쪽 아래, 오른쪽 위→왼쪽 아래 대각선을 1로 만든다.
        for index in range(size):
            matrix[index][index] = 1.0
            matrix[index][size - index - 1] = 1.0

    return matrix
