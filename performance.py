"""MAC 연산 시간을 재는 기능을 모아 둔 파일입니다."""


from time import perf_counter

from mac import calculate_mac, calculate_mac_1d, flatten_matrix, make_pattern


def average_mac_time(pattern, filter_matrix, repeats=10):
    """2차원 MAC을 여러 번 실행하고 한 번의 평균 시간을 ms로 구합니다."""

    if not isinstance(repeats, int) or isinstance(repeats, bool) or repeats < 1:
        raise ValueError("반복 횟수는 1 이상의 정수여야 합니다.")

    # 준비 운동은 측정에 포함하지 않습니다.
    calculate_mac(pattern, filter_matrix)

    # 타이머 사이에는 입력, 출력, 파일 읽기를 넣지 않습니다.
    start_time = perf_counter()

    for count in range(repeats):
        calculate_mac(pattern, filter_matrix)

    end_time = perf_counter()

    total_seconds = end_time - start_time
    average_milliseconds = total_seconds * 1000 / repeats

    return average_milliseconds


def average_mac_1d_time(pattern, filter_values, repeats=10):
    """1차원 MAC을 여러 번 실행하고 한 번의 평균 시간을 ms로 구합니다."""

    if not isinstance(repeats, int) or isinstance(repeats, bool) or repeats < 1:
        raise ValueError("반복 횟수는 1 이상의 정수여야 합니다.")

    calculate_mac_1d(pattern, filter_values)
    start_time = perf_counter()

    for count in range(repeats):
        calculate_mac_1d(pattern, filter_values)

    end_time = perf_counter()

    return (end_time - start_time) * 1000 / repeats


def measure_sizes(repeats=10):
    """3, 5, 13, 25 크기의 MAC 시간과 N² 연산 횟수를 구합니다."""

    sizes = [3, 5, 13, 25]
    results = []

    for size in sizes:
        pattern = make_pattern(size, "Cross")
        average_ms = average_mac_time(pattern, pattern, repeats)

        result = {
            "size": size,
            "average_ms": average_ms,
            "operations": size * size,
        }

        results.append(result)

    return results


def print_performance_table(results, repeats=10, print_function=print):
    """크기별 성능 결과를 보기 쉬운 표로 출력합니다."""

    print_function(f"\n[성능 분석: {repeats}회 평균]")
    print_function("크기       평균 시간(ms)       연산 횟수(N²)")
    print_function("-" * 48)

    for result in results:
        size = result["size"]
        average_ms = result["average_ms"]
        operations = result["operations"]

        print_function(f"{size}×{size:<7} {average_ms:>12.6f} {operations:>18}")


def compare_2d_and_1d(size=25, repeats=10):
    """보너스: 같은 입력으로 2차원 MAC과 1차원 MAC을 비교합니다."""

    pattern_2d = make_pattern(size, "Cross")
    filter_2d = make_pattern(size, "Cross")

    pattern_1d = flatten_matrix(pattern_2d)
    filter_1d = flatten_matrix(filter_2d)

    score_2d = calculate_mac(pattern_2d, filter_2d)
    score_1d = calculate_mac_1d(pattern_1d, filter_1d)

    time_2d = average_mac_time(pattern_2d, filter_2d, repeats)
    time_1d = average_mac_1d_time(pattern_1d, filter_1d, repeats)

    return {
        "size": size,
        "repeats": repeats,
        "score_2d": score_2d,
        "score_1d": score_1d,
        "time_2d": time_2d,
        "time_1d": time_1d,
    }


def print_bonus_result(result, print_function=print):
    """보너스 비교 결과를 출력합니다."""

    print_function("\n[보너스: 2차원과 1차원 MAC 비교]")
    print_function(f"크기: {result['size']}×{result['size']}")
    print_function(f"반복: {result['repeats']}회")
    print_function(f"2차원 점수: {result['score_2d']:.16g}")
    print_function(f"1차원 점수: {result['score_1d']:.16g}")
    print_function(f"2차원 평균 시간: {result['time_2d']:.6f} ms")
    print_function(f"1차원 평균 시간: {result['time_1d']:.6f} ms")

    if result["score_2d"] == result["score_1d"]:
        print_function("점수 확인: 두 방법의 계산 결과가 같습니다.")
    else:
        print_function("점수 확인: 두 방법의 계산 결과가 다릅니다.")
