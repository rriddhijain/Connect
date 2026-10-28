"""Export helpers for simulator metrics and configuration."""

import json
from typing import Dict, List
import pandas as pd

from src.metrics import PolicyMetrics
from src.models import SimulationConfig


def export_comparison_dataframe(metrics_list: List[PolicyMetrics]) -> pd.DataFrame:
    """Format high-level policy comparison metrics into a DataFrame."""
    rows = []
    for m in metrics_list:
        rows.append({
            "Policy": m.policy_name,
            "Throughput (Mbps)": m.throughput_mbps,
            "Delivery Ratio (%)": m.delivery_ratio_pct,
            "Packet Loss (%)": m.loss_ratio_pct,
            "Mean Latency (ms)": m.mean_latency_ms if m.mean_latency_ms is not None else "N/A",
            "P95 Latency (ms)": m.p95_latency_ms if m.p95_latency_ms is not None else "N/A",
            "Utilization (%)": m.utilization_pct,
            "Jain's Fairness": m.jains_fairness_index,
            "Packets Generated": m.total_generated,
            "Packets Delivered": m.total_delivered,
            "Packets Dropped": m.total_dropped,
            "Packets Remaining": m.total_remaining,
        })
    return pd.DataFrame(rows)


def export_user_dataframe(metrics_list: List[PolicyMetrics]) -> pd.DataFrame:
    """Format detailed per-user metrics across all policies into a single DataFrame."""
    rows = []
    for m in metrics_list:
        for u in m.user_metrics:
            row = {"Policy": m.policy_name}
            row.update(u)
            rows.append(row)
    return pd.DataFrame(rows)


def export_config_json(config: SimulationConfig) -> str:
    """Export simulation parameters as formatted JSON string."""
    cfg_dict = {
        "scenario_name": config.scenario_name,
        "bandwidth_mbps": config.bandwidth_mbps,
        "num_users": config.num_users,
        "duration_seconds": config.duration_seconds,
        "time_step_seconds": config.time_step_seconds,
        "max_queue_packets": config.max_queue_packets,
        "seed": config.seed,
        "traffic_mix": config.traffic_mix,
        "rr_quantum_bytes": config.rr_quantum_bytes,
    }
    return json.dumps(cfg_dict, indent=2)
