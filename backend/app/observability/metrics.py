from __future__ import annotations

import threading
from dataclasses import dataclass


@dataclass
class TimingAgg:
    count: int = 0
    sum_ms: float = 0.0
    min_ms: float | None = None
    max_ms: float | None = None

    def observe(self, duration_ms: float) -> None:
        self.count += 1
        self.sum_ms += float(duration_ms)
        if self.min_ms is None or duration_ms < self.min_ms:
            self.min_ms = float(duration_ms)
        if self.max_ms is None or duration_ms > self.max_ms:
            self.max_ms = float(duration_ms)


class RequestMetrics:
    """
    Minimal in-process metrics. Stable, low-cardinality aggregates only.
    """

    def __init__(self) -> None:
        self._lock = threading.Lock()
        self._total = 0
        self._by_method: dict[str, int] = {}
        self._by_status: dict[str, int] = {}
        self._timing = TimingAgg()

    def observe(self, *, method: str, status_code: int, duration_ms: float) -> None:
        m = (method or "").upper() or "UNKNOWN"
        s = str(int(status_code))
        d = float(duration_ms)
        with self._lock:
            self._total += 1
            self._by_method[m] = self._by_method.get(m, 0) + 1
            self._by_status[s] = self._by_status.get(s, 0) + 1
            self._timing.observe(d)

    def render_text(self) -> str:
        """
        Simple, stable, line-oriented format (text/plain).
        """
        with self._lock:
            total = self._total
            by_method = dict(self._by_method)
            by_status = dict(self._by_status)
            t = TimingAgg(
                count=self._timing.count,
                sum_ms=self._timing.sum_ms,
                min_ms=self._timing.min_ms,
                max_ms=self._timing.max_ms,
            )

        lines: list[str] = []
        lines.append(f"requests_total {total}")
        for k in sorted(by_method.keys()):
            lines.append(f'requests_by_method{{method="{k}"}} {by_method[k]}')
        for k in sorted(by_status.keys(), key=lambda x: int(x) if x.isdigit() else 10**9):
            lines.append(f'requests_by_status{{status="{k}"}} {by_status[k]}')

        lines.append(f"request_duration_ms_count {t.count}")
        lines.append(f"request_duration_ms_sum {t.sum_ms:.3f}")
        lines.append(f"request_duration_ms_min {0.0 if t.min_ms is None else t.min_ms:.3f}")
        lines.append(f"request_duration_ms_max {0.0 if t.max_ms is None else t.max_ms:.3f}")

        avg = (t.sum_ms / t.count) if t.count else 0.0
        lines.append(f"request_duration_ms_avg {avg:.3f}")
        return "\n".join(lines) + "\n"


metrics = RequestMetrics()

