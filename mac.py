"""MAC 계산의 가장 기본적인 기능을 모아 둔 파일입니다."""


# 두 점수의 차이가 이 값보다 작으면 동점으로 봅니다.
# 1e-9는 0.000000001입니다.
EPSILON = 1e-9


def check_matrix(matrix, expected_size=None):
    """숫자로 된 정사각형 행렬인지 확인하고 크기 N을 돌려줍니다."""

    # 행렬은 비어 있지 않은 리스트여야 합니다.
    if not isinstance(matrix, list) or len(matrix) == 0:
        raise ValueError("행렬은 비어 있지 않은 리스트여야 합니다.")

    size = len(matrix)

    # expected_size가 있으면 약속한 크기와 같은지 확인합니다.
    if expected_size is not None and size != expected_size:
        raise ValueError(f"행렬은 {expected_size}×{expected_size}이어야 합니다.")

    # 각 행의 길이와 각 값의 종류를 차례대로 확인합니다.
    for row in matrix:
        if not isinstance(row, list) or len(row) != size:
            raise ValueError(f"행렬은 {size}×{size} 정사각형이어야 합니다.")

        for value in row:
            if isinstance(value, bool) or not isinstance(value, (int, float)):
                raise ValueError("행렬에는 숫자만 넣을 수 있습니다.")

    return size


def normalize_label(label):
    """여러 라벨 표현을 프로그램의 표준 라벨 Cross 또는 X로 바꿉니다."""

    if not isinstance(label, str):
        raise ValueError("라벨은 글자여야 합니다.")

    # 앞뒤 공백을 없애고 소문자로 바꾸면 비교가 쉬워집니다.
    simple_label = label.strip().lower()

    if simple_label == "+" or simple_label == "cross":
        return "Cross"

    if simple_label == "x":
        return "X"

    raise ValueError(f"지원하지 않는 라벨입니다: {label}")


def calculate_mac(pattern, filter_matrix):
    """같은 위치의 숫자를 곱하고 모두 더한 MAC 점수를 구합니다."""

    pattern_size = check_matrix(pattern)
    filter_size = check_matrix(filter_matrix)

    if pattern_size != filter_size:
        raise ValueError("패턴과 필터의 크기가 다릅니다.")

    total = 0.0

    # 바깥쪽 반복문은 행을 움직입니다.
    for row in range(pattern_size):

        # 안쪽 반복문은 열을 움직입니다.
        for column in range(pattern_size):
            pattern_value = pattern[row][column]
            filter_value = filter_matrix[row][column]

            # Multiply: 같은 위치의 두 값을 곱합니다.
            multiplied_value = pattern_value * filter_value

            # Accumulate: 곱한 값을 total에 계속 더합니다.
            total = total + multiplied_value

    return total


def choose_winner(score_a, score_b, name_a="A", name_b="B"):
    """두 점수를 비교해 승자 이름 또는 UNDECIDED를 돌려줍니다."""

    difference = abs(score_a - score_b)

    # 실수의 아주 작은 오차는 실제 승패로 보지 않습니다.
    if difference < EPSILON:
        return "UNDECIDED"

    if score_a > score_b:
        return name_a

    return name_b


def make_pattern(size, label):
    """보너스: 원하는 크기의 Cross 또는 X 패턴을 자동으로 만듭니다."""

    if not isinstance(size, int) or isinstance(size, bool) or size < 1:
        raise ValueError("크기는 1 이상의 정수여야 합니다.")

    standard_label = normalize_label(label)

    # 먼저 모든 칸이 0인 N×N 리스트를 만듭니다.
    pattern = []

    for row in range(size):
        new_row = []

        for column in range(size):
            new_row.append(0)

        pattern.append(new_row)

    if standard_label == "Cross":
        center = size // 2

        for index in range(size):
            pattern[center][index] = 1
            pattern[index][center] = 1

    else:
        for index in range(size):
            pattern[index][index] = 1
            pattern[index][size - index - 1] = 1

    return pattern


def flatten_matrix(matrix):
    """보너스: 2차원 행렬을 한 줄짜리 1차원 리스트로 바꿉니다."""

    check_matrix(matrix)
    flat_list = []

    for row in matrix:
        for value in row:
            flat_list.append(value)

    return flat_list


def calculate_mac_1d(pattern, filter_values):
    """보너스: 1차원 리스트 두 개로 MAC 점수를 구합니다."""

    if not isinstance(pattern, list) or not isinstance(filter_values, list):
        raise ValueError("1차원 MAC에는 리스트 두 개가 필요합니다.")

    if len(pattern) == 0 or len(pattern) != len(filter_values):
        raise ValueError("두 리스트는 길이가 같고 비어 있지 않아야 합니다.")

    total = 0.0

    for index in range(len(pattern)):
        total = total + pattern[index] * filter_values[index]

    return total
