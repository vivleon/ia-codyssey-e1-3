"""Mini NPU Simulator 콘솔 애플리케이션."""

import argparse
import json
import math
from pathlib import Path
from typing import Callable, List, Optional, Sequence

from analysis import (
    AnalysisReport,
    DataAnalysisError,
    PerformanceResult,
    analyze_dataset,
    load_json_file,
    measure_sizes,
)
from npu import (
    EPSILON,
    Matrix,
    benchmark_mac,
    compare_scores,
    mac_score,
)


DEFAULT_DATA_PATH = Path(__file__).resolve().with_name("data.json")


class SimulatorApp:
    """사용자 입력 모드와 JSON 분석 모드의 콘솔 흐름을 관리한다."""

    def __init__(
        self,
        data_path: Path = DEFAULT_DATA_PATH,
        repeats: int = 10,
        input_func: Callable[[str], str] = input,
        output_func: Callable[[str], None] = print,
        epsilon: float = EPSILON,
        summary_json: bool = False,
    ) -> None:
        if repeats < 10:
            raise ValueError("성능 측정 반복 횟수는 최소 10회여야 합니다.")
        if (
            isinstance(epsilon, bool)
            or not isinstance(epsilon, (int, float))
            or not math.isfinite(epsilon)
            or epsilon <= 0
        ):
            raise ValueError("epsilon은 0보다 큰 유한한 숫자여야 합니다.")
        self.data_path = Path(data_path)
        self.repeats = repeats
        self.epsilon = float(epsilon)
        self.summary_json = summary_json
        self.input = input_func
        self.output = output_func

    def run(self, mode: Optional[str] = None) -> bool:
        """선택한 모드를 실행하고 정상 완료 여부를 반환한다."""
        self.output("=== Mini NPU Simulator ===")
        try:
            selected_mode = mode or self._read_mode()
            if selected_mode == "user":
                self.run_user_mode()
                return True
            if selected_mode == "json":
                return self.run_json_mode()
            raise ValueError(f"지원하지 않는 모드입니다: {selected_mode}")
        except (KeyboardInterrupt, EOFError):
            self.output("\n입력이 중단되어 안전하게 종료합니다.")
            return False

    def _read_mode(self) -> str:
        self.output("\n[모드 선택]")
        self.output("1. 사용자 입력 (3×3)")
        self.output("2. data.json 분석")
        while True:
            selected = self.input("선택: ").strip()
            if selected == "1":
                return "user"
            if selected == "2":
                return "json"
            self.output("입력 오류: 1 또는 2를 입력하세요.")

    def read_matrix(self, title: str, size: int = 3) -> Matrix:
        """행 단위 숫자 입력을 검증하고 n×n Matrix로 만든다."""
        self.output(f"\n{title} ({size}줄 입력, 공백 구분)")
        self.output("입력을 취소하려면 Ctrl+C를 누르세요.")
        rows: List[List[float]] = []
        for row_index in range(size):
            while True:
                raw_row = self.input(f"{row_index + 1}행: ").strip()
                parts = raw_row.split()
                if len(parts) != size:
                    self.output(
                        f"입력 형식 오류: 각 줄에 {size}개의 숫자를 "
                        "공백으로 구분해 입력하세요."
                    )
                    continue
                try:
                    row = [float(part) for part in parts]
                except ValueError:
                    self.output(
                        f"입력 형식 오류: 각 줄에 {size}개의 숫자를 "
                        "공백으로 구분해 입력하세요."
                    )
                    continue
                rows.append(row)
                break
        return Matrix(rows)

    def run_user_mode(self) -> None:
        """필터 A/B와 패턴을 입력받아 3×3 MAC 판정을 수행한다."""
        self.output("\n" + "-" * 48)
        self.output("[1] 필터 입력")
        self.output("-" * 48)
        filter_a = self.read_matrix("필터 A")
        filter_b = self.read_matrix("필터 B")
        self.output("✓ 필터 A, B 저장 완료")

        self.output("\n" + "-" * 48)
        self.output("[2] 패턴 입력")
        self.output("-" * 48)
        pattern = self.read_matrix("패턴")
        self.output("✓ 패턴 저장 완료")

        score_a = mac_score(pattern, filter_a)
        score_b = mac_score(pattern, filter_b)
        predicted = compare_scores(
            score_a,
            score_b,
            "A",
            "B",
            self.epsilon,
        )
        average_ms = benchmark_mac(pattern, filter_a, self.repeats)

        self.output("\n" + "-" * 48)
        self.output("[3] MAC 결과")
        self.output("-" * 48)
        self.output(f"A 점수: {score_a:.16g}")
        self.output(f"B 점수: {score_b:.16g}")
        self.output(
            f"연산 시간(MAC 1회 평균/{self.repeats}회): "
            f"{average_ms:.6f} ms"
        )
        if predicted == "UNDECIDED":
            # 내부 판정값은 유지하고 사용자 모드에서만
            # 쉬운 한국어로 표시한다.
            difference = abs(score_a - score_b)
            self.output(f"판정: 판정 불가 (|A-B| < {self.epsilon:g})")
            self.output(f"점수 차이: {difference:.16g}")
        else:
            self.output(f"판정: {predicted}")

        self._print_performance(
            [
                PerformanceResult(
                    size=3,
                    average_ms=average_ms,
                    operations=9,
                    repeats=self.repeats,
                )
            ],
            section_number=4,
        )

    def run_json_mode(self) -> bool:
        """data.json을 케이스별로 분석하고 성능 및 실패 요약을 출력한다."""
        data_path = self.data_path.resolve()
        self.output("\n" + "-" * 48)
        self.output("[1] JSON 데이터 로드")
        self.output("-" * 48)
        try:
            data = load_json_file(data_path)
            self.output(f"✓ 로드 완료: {data_path}")
            report = analyze_dataset(data, self.epsilon)
        except DataAnalysisError as error:
            self.output(f"분석 중단 ({data_path}): {error}")
            return False

        self.output("\n" + "-" * 48)
        self.output("[2] 패턴 분석 (라벨 정규화 적용)")
        self.output("-" * 48)
        self._print_case_results(report)

        performance = measure_sizes(
            sizes=(3, 5, 13, 25),
            repeats=self.repeats,
        )
        self._print_performance(performance)
        self._print_summary(report)
        return True

    def _print_case_results(self, report: AnalysisReport) -> None:
        for result in report.results:
            self.output(f"\n--- {result.identifier} ---")
            if result.scores:
                self.output(f"Cross 점수: {result.scores['Cross']:.16g}")
                self.output(f"X 점수: {result.scores['X']:.16g}")
            expected = result.expected or "UNKNOWN"
            status = "PASS" if result.passed else "FAIL"
            self.output(
                f"판정: {result.predicted} | expected: {expected} | {status}"
            )
            if result.reason:
                self.output(f"사유: {result.reason}")

    def _print_performance(
        self,
        performance: Sequence[PerformanceResult],
        section_number: int = 3,
    ) -> None:
        repeats = performance[0].repeats if performance else self.repeats
        self.output("\n" + "-" * 48)
        self.output(f"[{section_number}] 성능 분석 (평균/{repeats}회)")
        self.output("-" * 48)
        self.output("크기       평균 시간(ms)       연산 횟수(N²)")
        self.output("-" * 48)
        for result in performance:
            size_label = f"{result.size}×{result.size}"
            self.output(
                f"{size_label:<10} {result.average_ms:>12.6f} "
                f"{result.operations:>18}"
            )

    def _print_summary(self, report: AnalysisReport) -> None:
        self.output("\n" + "-" * 48)
        self.output("[4] 결과 요약")
        self.output("-" * 48)
        self.output(f"총 테스트: {report.total_count}개")
        self.output(f"통과: {report.passed_count}개")
        self.output(f"실패: {report.failed_count}개")

        if report.failures:
            self.output("\n실패 케이스:")
            for result in report.failures:
                self.output(f"- {result.identifier}: {result.reason}")
        else:
            self.output("\n실패 케이스가 없습니다.")

        if self.summary_json:
            summary = {
                "total": report.total_count,
                "passed": report.passed_count,
                "failed": report.failed_count,
                "epsilon": self.epsilon,
                "failures": [
                    {
                        "identifier": result.identifier,
                        "predicted": result.predicted,
                        "expected": result.expected,
                        "reason": result.reason,
                    }
                    for result in report.failures
                ],
            }
            self.output(
                "SUMMARY_JSON: "
                + json.dumps(summary, ensure_ascii=False, separators=(",", ":"))
            )


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Mini NPU Simulator")
    parser.add_argument(
        "--mode",
        choices=("user", "json"),
        help="메뉴를 생략하고 지정한 모드 실행",
    )
    parser.add_argument(
        "--data",
        type=Path,
        default=DEFAULT_DATA_PATH,
        help="분석할 data.json 경로",
    )
    parser.add_argument(
        "--repeats",
        type=int,
        default=10,
        help="크기별 MAC 반복 측정 횟수(최소 10)",
    )
    parser.add_argument(
        "--epsilon",
        type=float,
        default=EPSILON,
        help="동점으로 간주할 절대 허용오차(기본값: 1e-9)",
    )
    parser.add_argument(
        "--summary-json",
        action="store_true",
        help="사람용 결과 뒤에 SUMMARY_JSON 한 줄 출력",
    )
    return parser


def main() -> int:
    args = build_parser().parse_args()
    try:
        app = SimulatorApp(
            data_path=args.data,
            repeats=args.repeats,
            epsilon=args.epsilon,
            summary_json=args.summary_json,
        )
    except ValueError as error:
        print(f"설정 오류: {error}")
        return 2
    return 0 if app.run(args.mode) else 1


if __name__ == "__main__":
    raise SystemExit(main())
