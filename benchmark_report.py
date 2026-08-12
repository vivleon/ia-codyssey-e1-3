"""MAC 실행 시간 분포와 행렬 생성 메모리를 JSON으로 출력한다."""

import argparse
import json
import platform
import statistics
import tracemalloc
from typing import Dict, List, Union

from npu import benchmark_mac, generate_pattern


MetricValue = Union[int, float, str, List[float]]


def collect_benchmark(
    size: int = 25,
    repeats: int = 10,
    groups: int = 5,
) -> Dict[str, MetricValue]:
    """동일 MAC 측정을 여러 묶음 실행해 분포와 메모리 지표를 반환한다."""
    if isinstance(size, bool) or not isinstance(size, int) or size <= 0:
        raise ValueError("size는 1 이상의 정수여야 합니다.")
    if isinstance(repeats, bool) or not isinstance(repeats, int) or repeats < 10:
        raise ValueError("repeats는 10 이상의 정수여야 합니다.")
    if isinstance(groups, bool) or not isinstance(groups, int) or groups < 2:
        raise ValueError("groups는 2 이상의 정수여야 합니다.")

    tracemalloc.start()
    try:
        pattern = generate_pattern(size, "Cross")
        filter_matrix = generate_pattern(size, "Cross")
        _, construction_peak_bytes = tracemalloc.get_traced_memory()
    finally:
        tracemalloc.stop()

    samples_ms = [
        benchmark_mac(pattern, filter_matrix, repeats)
        for _ in range(groups)
    ]
    return {
        "python": platform.python_version(),
        "platform": platform.platform(),
        "size": size,
        "operations_per_mac": size * size,
        "repeats_per_group": repeats,
        "groups": groups,
        "samples_ms": samples_ms,
        "mean_ms": statistics.mean(samples_ms),
        "median_ms": statistics.median(samples_ms),
        "population_stdev_ms": statistics.pstdev(samples_ms),
        "two_matrix_construction_peak_bytes": construction_peak_bytes,
        "memory_scope": "tracemalloc peak while constructing pattern and filter",
    }


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Mini NPU 반복 벤치마크 JSON 리포트"
    )
    parser.add_argument("--size", type=int, default=25, help="행렬 한 변의 크기")
    parser.add_argument(
        "--repeats",
        type=int,
        default=10,
        help="묶음당 MAC 반복 횟수",
    )
    parser.add_argument(
        "--groups",
        type=int,
        default=5,
        help="평균·중앙값·표준편차 계산용 측정 묶음 수",
    )
    return parser


def main() -> int:
    args = build_parser().parse_args()
    try:
        report = collect_benchmark(args.size, args.repeats, args.groups)
    except ValueError as error:
        print(f"설정 오류: {error}")
        return 2
    print(json.dumps(report, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
