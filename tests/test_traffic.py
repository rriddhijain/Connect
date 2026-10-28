"""Tests for synthetic traffic generation and determinism."""

from src.models import SimulationConfig, TrafficClass
from src.traffic import build_users_for_scenario, generate_packet_trace


def test_traffic_generation_reproducibility():
    """Verify that identical random seeds produce the exact same packet trace."""
    config1 = SimulationConfig(seed=42, duration_seconds=5.0, num_users=4)
    users1 = build_users_for_scenario(config1)
    pkts1, _ = generate_packet_trace(config1, users1)

    config2 = SimulationConfig(seed=42, duration_seconds=5.0, num_users=4)
    users2 = build_users_for_scenario(config2)
    pkts2, _ = generate_packet_trace(config2, users2)

    assert len(pkts1) == len(pkts2)
    for p1, p2 in zip(pkts1, pkts2):
        assert p1.packet_id == p2.packet_id
        assert p1.user_id == p2.user_id
        assert p1.traffic_class == p2.traffic_class
        assert p1.size_bytes == p2.size_bytes
        assert p1.arrival_time == p2.arrival_time


def test_traffic_generation_different_seeds():
    """Verify that different random seeds produce different traces."""
    config1 = SimulationConfig(seed=42, duration_seconds=5.0, num_users=4)
    users1 = build_users_for_scenario(config1)
    pkts1, _ = generate_packet_trace(config1, users1)

    config2 = SimulationConfig(seed=999, duration_seconds=5.0, num_users=4)
    users2 = build_users_for_scenario(config2)
    pkts2, _ = generate_packet_trace(config2, users2)

    # Different seeds should not have identical arrival sequences
    sizes1 = [p.size_bytes for p in pkts1]
    sizes2 = [p.size_bytes for p in pkts2]
    assert sizes1 != sizes2


def test_all_traffic_classes_present():
    """Verify that synthetic traffic covers voice, video, web, and download."""
    config = SimulationConfig(seed=42, duration_seconds=5.0, num_users=8)
    users = build_users_for_scenario(config)
    pkts, _ = generate_packet_trace(config, users)

    classes_present = set(p.traffic_class for p in pkts)
    assert TrafficClass.VOICE in classes_present
    assert TrafficClass.VIDEO_STREAM in classes_present
    assert TrafficClass.WEB in classes_present
    assert TrafficClass.DOWNLOAD in classes_present
