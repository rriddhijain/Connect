"""Tests for packet accounting and capacity enforcement."""

import pytest
from src.models import SimulationConfig
from src.policies.equal_share import EqualSharePolicy
from src.policies.priority import PrioritySchedulingPolicy
from src.policies.round_robin import RoundRobinPolicy
from src.simulator import NetworkSimulator
from src.traffic import build_users_for_scenario, generate_packet_trace


@pytest.mark.parametrize("policy_cls", [
    EqualSharePolicy,
    PrioritySchedulingPolicy,
    RoundRobinPolicy,
])
def test_packet_conservation_invariant(policy_cls):
    """
    Every generated packet must be accounted for:
    generated == delivered + dropped + remaining_in_queue
    """
    config = SimulationConfig(
        bandwidth_mbps=10.0,
        num_users=6,
        duration_seconds=5.0,
        time_step_seconds=0.01,
        max_queue_packets=20,
        seed=123,
        scenario_name="Heavy Congestion",
    )
    users = build_users_for_scenario(config)
    _, packets_by_step = generate_packet_trace(config, users)

    simulator = NetworkSimulator(config)
    policy = policy_cls()
    result = simulator.run_policy(policy, users, packets_by_step)

    total_gen = len(result.all_packets)
    total_del = len(result.delivered_packets)
    total_drop = len(result.dropped_packets)
    total_rem = len(result.remaining_packets)

    assert total_gen == total_del + total_drop + total_rem
    assert total_gen > 0


@pytest.mark.parametrize("policy_cls", [
    EqualSharePolicy,
    PrioritySchedulingPolicy,
    RoundRobinPolicy,
])
def test_bandwidth_capacity_limit_enforced(policy_cls):
    """
    Delivered data must never exceed configured link capacity.
    delivered_bits <= capacity_mbps * 1_000_000 * duration_seconds
    """
    config = SimulationConfig(
        bandwidth_mbps=5.0,
        num_users=8,
        duration_seconds=10.0,
        time_step_seconds=0.01,
        max_queue_packets=30,
        seed=77,
        scenario_name="Heavy Congestion",
    )
    users = build_users_for_scenario(config)
    _, packets_by_step = generate_packet_trace(config, users)

    simulator = NetworkSimulator(config)
    policy = policy_cls()
    result = simulator.run_policy(policy, users, packets_by_step)

    max_allowed_bits = config.bandwidth_mbps * 1_000_000.0 * config.duration_seconds
    assert result.total_delivered_bits <= max_allowed_bits + 1500 * 8  # within MTU boundary


def test_replay_same_arrival_trace_across_policies():
    """All three policies must receive the exact same packet trace."""
    config = SimulationConfig(
        bandwidth_mbps=15.0,
        num_users=6,
        duration_seconds=5.0,
        seed=42,
        scenario_name="Mixed Traffic",
    )
    users = build_users_for_scenario(config)
    all_pkts, packets_by_step = generate_packet_trace(config, users)

    sim = NetworkSimulator(config)

    res_eq = sim.run_policy(EqualSharePolicy(), users, packets_by_step)
    res_prio = sim.run_policy(PrioritySchedulingPolicy(), users, packets_by_step)
    res_rr = sim.run_policy(RoundRobinPolicy(), users, packets_by_step)

    # Identical generated packet set
    assert len(res_eq.all_packets) == len(res_prio.all_packets) == len(res_rr.all_packets) == len(all_pkts)

    for p_eq, p_prio, p_rr in zip(res_eq.all_packets, res_prio.all_packets, res_rr.all_packets):
        assert p_eq.packet_id == p_prio.packet_id == p_rr.packet_id
        assert p_eq.size_bytes == p_prio.size_bytes == p_rr.size_bytes
        assert p_eq.arrival_time == p_prio.arrival_time == p_rr.arrival_time
