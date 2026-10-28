"""Performance metrics calculation and Jain's fairness index."""

from dataclasses import dataclass
from typing import Dict, List, Optional
import numpy as np

from src.models import Packet, User
from src.simulator import SimulationResult


@dataclass
class PolicyMetrics:
    """Calculated performance metrics for a policy simulation run."""
    policy_name: str
    total_generated: int
    total_delivered: int
    total_dropped: int
    total_remaining: int
    delivered_bits: int
    throughput_mbps: float
    delivery_ratio_pct: float
    loss_ratio_pct: float
    remaining_ratio_pct: float
    mean_latency_ms: Optional[float]
    p95_latency_ms: Optional[float]
    utilization_pct: float
    jains_fairness_index: float
    user_metrics: List[Dict]
    class_metrics: Dict[str, Dict]


def calculate_jains_fairness(user_throughputs: List[float]) -> float:
    """
    Compute Jain's Fairness Index across all users:
    J = (sum(x_i) ** 2) / (n * sum(x_i ** 2))
    Returns a value between 1/n (worst) and 1.0 (perfect fairness).
    If all values are 0, returns 0.0.
    """
    n = len(user_throughputs)
    if n <= 0:
        return 1.0

    sum_x = sum(user_throughputs)
    sum_x_sq = sum(x * x for x in user_throughputs)

    if sum_x_sq == 0.0 or sum_x == 0.0:
        return 0.0

    fairness = (sum_x ** 2) / (n * sum_x_sq)
    return float(np.clip(fairness, 0.0, 1.0))


def compute_metrics(result: SimulationResult) -> PolicyMetrics:
    """Compute all standard network metrics from a completed SimulationResult."""
    duration = result.duration_seconds
    capacity_mbps = result.config.bandwidth_mbps
    gen_count = len(result.all_packets)
    del_count = len(result.delivered_packets)
    drop_count = len(result.dropped_packets)
    rem_count = len(result.remaining_packets)
    del_bits = result.total_delivered_bits

    # 1. Throughput & Ratios
    throughput_mbps = (del_bits / duration / 1_000_000.0) if duration > 0 else 0.0
    pdr = (del_count / gen_count * 100.0) if gen_count > 0 else 0.0
    plr = (drop_count / gen_count * 100.0) if gen_count > 0 else 0.0
    rem_pct = (rem_count / gen_count * 100.0) if gen_count > 0 else 0.0

    # 2. Latency metrics (for delivered packets)
    latencies_ms = [
        pkt.latency_ms for pkt in result.delivered_packets
        if pkt.latency_ms is not None
    ]
    if latencies_ms:
        mean_lat = float(np.mean(latencies_ms))
        p95_lat = float(np.percentile(latencies_ms, 95))
    else:
        mean_lat = None
        p95_lat = None

    # 3. Bandwidth Utilization
    total_capacity_bits = capacity_mbps * 1_000_000.0 * duration
    utilization_pct = (del_bits / total_capacity_bits * 100.0) if total_capacity_bits > 0 else 0.0
    utilization_pct = min(100.0, utilization_pct)  # Cap at theoretical maximum

    # 4. Per-user statistics
    user_metrics = []
    user_throughputs = []
    user_del_map: Dict[int, List[Packet]] = {u.user_id: [] for u in result.users}
    for pkt in result.delivered_packets:
        if pkt.user_id in user_del_map:
            user_del_map[pkt.user_id].append(pkt)

    user_rem_map: Dict[int, int] = {u.user_id: 0 for u in result.users}
    for pkt in result.remaining_packets:
        if pkt.user_id in user_rem_map:
            user_rem_map[pkt.user_id] += 1

    for u in result.users:
        u_del_pkts = user_del_map[u.user_id]
        u_del_bits = u.bytes_delivered * 8
        u_thru = (u_del_bits / duration / 1_000_000.0) if duration > 0 else 0.0
        user_throughputs.append(u_thru)

        u_gen = u.packets_generated
        u_del = u.packets_delivered
        u_drop = u.packets_dropped
        u_rem = user_rem_map.get(u.user_id, 0)

        u_latencies = [
            pkt.latency_ms for pkt in u_del_pkts if pkt.latency_ms is not None
        ]
        u_mean_lat = float(np.mean(u_latencies)) if u_latencies else None
        u_p95_lat = float(np.percentile(u_latencies, 95)) if u_latencies else None

        user_metrics.append({
            "User ID": u.user_id,
            "Name": u.name,
            "Traffic Class": u.traffic_class.value,
            "Priority": u.priority,
            "Generated Packets": u_gen,
            "Delivered Packets": u_del,
            "Dropped Packets": u_drop,
            "Remaining Packets": u_rem,
            "Delivered (MB)": round(u.bytes_delivered / (1024 * 1024), 3),
            "Throughput (Mbps)": round(u_thru, 4),
            "Delivery Ratio (%)": round((u_del / u_gen * 100.0) if u_gen > 0 else 0.0, 2),
            "Loss Ratio (%)": round((u_drop / u_gen * 100.0) if u_gen > 0 else 0.0, 2),
            "Mean Latency (ms)": round(u_mean_lat, 2) if u_mean_lat is not None else None,
            "P95 Latency (ms)": round(u_p95_lat, 2) if u_p95_lat is not None else None,
        })

    # 5. Jain's fairness index
    fairness = calculate_jains_fairness(user_throughputs)

    # 6. Aggregate by Traffic Class
    class_metrics = {}
    classes = set(u.traffic_class.value for u in result.users)
    for c_val in classes:
        matching_u = [m for m in user_metrics if m["Traffic Class"] == c_val]
        c_gen = sum(m["Generated Packets"] for m in matching_u)
        c_del = sum(m["Delivered Packets"] for m in matching_u)
        c_drop = sum(m["Dropped Packets"] for m in matching_u)
        c_thru = sum(m["Throughput (Mbps)"] for m in matching_u)
        c_lats = [
            m["Mean Latency (ms)"] for m in matching_u if m["Mean Latency (ms)"] is not None
        ]
        class_metrics[c_val] = {
            "Generated": c_gen,
            "Delivered": c_del,
            "Dropped": c_drop,
            "Throughput (Mbps)": round(c_thru, 3),
            "Delivery Ratio (%)": round((c_del / c_gen * 100.0) if c_gen > 0 else 0.0, 2),
            "Loss Ratio (%)": round((c_drop / c_gen * 100.0) if c_gen > 0 else 0.0, 2),
            "Mean Latency (ms)": round(float(np.mean(c_lats)), 2) if c_lats else None,
        }

    return PolicyMetrics(
        policy_name=result.policy_name,
        total_generated=gen_count,
        total_delivered=del_count,
        total_dropped=drop_count,
        total_remaining=rem_count,
        delivered_bits=del_bits,
        throughput_mbps=round(throughput_mbps, 3),
        delivery_ratio_pct=round(pdr, 2),
        loss_ratio_pct=round(plr, 2),
        remaining_ratio_pct=round(rem_pct, 2),
        mean_latency_ms=round(mean_lat, 2) if mean_lat is not None else None,
        p95_latency_ms=round(p95_lat, 2) if p95_lat is not None else None,
        utilization_pct=round(utilization_pct, 2),
        jains_fairness_index=round(fairness, 4),
        user_metrics=user_metrics,
        class_metrics=class_metrics,
    )
