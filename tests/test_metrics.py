"""Tests for metrics and Jain's fairness calculation."""

import numpy as np
from src.metrics import calculate_jains_fairness, compute_metrics
from src.models import Packet, PacketStatus, SimulationConfig, TrafficClass, User
from src.simulator import SimulationResult


def test_jains_fairness_equal_allocation():
    """Equal throughput among all users must produce Jain's index of 1.0."""
    throughputs = [10.0, 10.0, 10.0, 10.0]
    j = calculate_jains_fairness(throughputs)
    assert np.isclose(j, 1.0)


def test_jains_fairness_single_user_monopoly():
    """When 1 out of 4 users receives all bandwidth, fairness should equal 1/4 = 0.25."""
    throughputs = [40.0, 0.0, 0.0, 0.0]
    j = calculate_jains_fairness(throughputs)
    assert np.isclose(j, 0.25)


def test_jains_fairness_all_zero():
    """All zeros should return 0.0 without divide-by-zero error."""
    throughputs = [0.0, 0.0, 0.0]
    j = calculate_jains_fairness(throughputs)
    assert j == 0.0


def test_compute_metrics_accuracy():
    """Verify calculated metrics match explicit formulas."""
    config = SimulationConfig(bandwidth_mbps=10.0, duration_seconds=1.0)
    user = User(
        user_id=1,
        name="User 1",
        traffic_class=TrafficClass.WEB,
        priority=2,
        target_rate_mbps=5.0,
        avg_packet_size_bytes=1000,
        packets_generated=10,
        packets_delivered=8,
        packets_dropped=2,
        bytes_generated=10000,
        bytes_delivered=8000,
        bytes_dropped=2000,
    )

    del_pkts = [
        Packet(
            packet_id=i,
            user_id=1,
            traffic_class=TrafficClass.WEB,
            priority=2,
            size_bytes=1000,
            arrival_time=0.1,
            queue_entry_time=0.1,
            delivery_time=0.12,  # 20ms latency
            status=PacketStatus.DELIVERED,
        )
        for i in range(8)
    ]
    drop_pkts = [
        Packet(
            packet_id=i + 8,
            user_id=1,
            traffic_class=TrafficClass.WEB,
            priority=2,
            size_bytes=1000,
            arrival_time=0.5,
            queue_entry_time=0.5,
            status=PacketStatus.DROPPED_BUFFER_OVERFLOW,
        )
        for i in range(2)
    ]

    result = SimulationResult(
        policy_name="Test Policy",
        config=config,
        users=[user],
        all_packets=del_pkts + drop_pkts,
        delivered_packets=del_pkts,
        dropped_packets=drop_pkts,
        remaining_packets=[],
        snapshots=[],
        total_transmitted_bytes=8000,
        total_delivered_bits=64000,
        duration_seconds=1.0,
    )

    metrics = compute_metrics(result)

    assert metrics.total_generated == 10
    assert metrics.total_delivered == 8
    assert metrics.total_dropped == 2
    assert metrics.delivery_ratio_pct == 80.0
    assert metrics.loss_ratio_pct == 20.0
    # Throughput: 64,000 bits / 1.0s / 1e6 = 0.064 Mbps
    assert np.isclose(metrics.throughput_mbps, 0.064)
    # Latency: (0.12 - 0.10) * 1000 = 20.0 ms
    assert np.isclose(metrics.mean_latency_ms, 20.0)
    assert np.isclose(metrics.p95_latency_ms, 20.0)
