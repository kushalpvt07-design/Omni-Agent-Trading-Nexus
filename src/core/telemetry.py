"""
src.core.telemetry — Low-overhead in-memory telemetry for latency and execution success.

Tracks:
  - Per-agent latency (ms) and rolling averages
  - Per-request total pipeline response time (T_total and T_avg, Paper Eq. 6 & 7)
  - Trade execution attempts (N_t), successes (N_s), and success rate E_s (Paper Eq. 5)
  - Categorized error counts
"""

import time
import threading
import logging
from collections import defaultdict
from typing import Dict, Any, List

logger = logging.getLogger("omni-nexus.telemetry")


class TelemetryRegistry:
    """Thread-safe singleton registry for swarm performance and execution telemetry."""

    def __init__(self) -> None:
        self._lock = threading.Lock()
        self._pipeline_runs: int = 0
        self._pipeline_latencies_ms: List[float] = []
        self._agent_latencies_ms: Dict[str, List[float]] = defaultdict(list)
        self._execution_attempts: int = 0
        self._execution_successes: int = 0
        self._execution_failures: int = 0
        self._error_counts: Dict[str, int] = defaultdict(int)

    def record_agent_latency(self, agent_name: str, duration_ms: float) -> None:
        with self._lock:
            bucket = self._agent_latencies_ms[agent_name]
            bucket.append(round(duration_ms, 2))
            if len(bucket) > 500:
                del bucket[:-500]

    def record_pipeline_run(self, total_duration_ms: float) -> None:
        with self._lock:
            self._pipeline_runs += 1
            self._pipeline_latencies_ms.append(round(total_duration_ms, 2))
            if len(self._pipeline_latencies_ms) > 500:
                del self._pipeline_latencies_ms[:-500]

    def record_execution_outcome(self, success: bool, error_type: str | None = None) -> None:
        with self._lock:
            self._execution_attempts += 1
            if success:
                self._execution_successes += 1
            else:
                self._execution_failures += 1
                if error_type:
                    self._error_counts[error_type] += 1

    def record_error(self, error_type: str) -> None:
        with self._lock:
            self._error_counts[error_type] += 1

    def get_snapshot(self) -> Dict[str, Any]:
        with self._lock:
            n_t = self._execution_attempts
            n_s = self._execution_successes
            # Paper Eq. (5): E_s = (N_s / N_t) * 100
            execution_success_rate = round((n_s / n_t) * 100.0, 2) if n_t > 0 else 100.0

            # Paper Eq. (7): T_avg = (1 / N) * sum(T_i)
            n_runs = len(self._pipeline_latencies_ms)
            t_avg_ms = (
                round(sum(self._pipeline_latencies_ms) / n_runs, 2)
                if n_runs > 0
                else 0.0
            )

            agent_stats: Dict[str, Dict[str, float | int]] = {}
            for agent, samples in self._agent_latencies_ms.items():
                if samples:
                    agent_stats[agent] = {
                        "count": len(samples),
                        "avg_ms": round(sum(samples) / len(samples), 2),
                        "min_ms": round(min(samples), 2),
                        "max_ms": round(max(samples), 2),
                        "last_ms": round(samples[-1], 2),
                    }

            return {
                "pipeline_runs": self._pipeline_runs,
                "average_response_time_ms": t_avg_ms,
                "execution_attempts_Nt": n_t,
                "execution_successes_Ns": n_s,
                "execution_failures": self._execution_failures,
                "execution_success_rate_Es_pct": execution_success_rate,
                "agent_latencies": agent_stats,
                "error_counts": dict(self._error_counts),
            }

    def reset(self) -> None:
        with self._lock:
            self._pipeline_runs = 0
            self._pipeline_latencies_ms.clear()
            self._agent_latencies_ms.clear()
            self._execution_attempts = 0
            self._execution_successes = 0
            self._execution_failures = 0
            self._error_counts.clear()


telemetry = TelemetryRegistry()


class Timer:
    """Context manager for measuring elapsed time in milliseconds."""

    def __init__(self, agent_name: str | None = None) -> None:
        self.agent_name = agent_name
        self.start_ns: int = 0
        self.elapsed_ms: float = 0.0

    def __enter__(self) -> "Timer":
        self.start_ns = time.perf_counter_ns()
        return self

    def __exit__(self, exc_type, exc_val, exc_tb) -> None:
        self.elapsed_ms = round((time.perf_counter_ns() - self.start_ns) / 1_000_000.0, 2)
        if self.agent_name:
            telemetry.record_agent_latency(self.agent_name, self.elapsed_ms)
