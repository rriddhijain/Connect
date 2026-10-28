"""Tests for scheduling policy behaviors (Equal Share, Priority, Round Robin)."""

from src.models import Packet, PacketStatus, Priority, SimulationConfig, TrafficClass
from src.policies.equal_share import EqualSharePolicy
from src.policies.priority import PrioritySchedulingPolicy
from src.policies.round_robin import RoundRobinPolicy
from src.queues import QueueManager
from src.simulator import NetworkSimulator
from src.traffic import build_users_for_scenario, generate_packet_trace


def test_priority_scheduling_favors_high_priority():
    """In heavy congestion, high-priority packets must experience lower loss and priority service."""
    config = SimulationConfig(
        bandwidth_mbps=5.0,
        num_users=6,
        duration_seconds=10.0,
        time_step_seconds=0.01,
        max_queue_packets=15,
        seed=42,
        scenario_name="Heavy Congestion",
    )
    users = build_users_for_scenario(config)
    _, packets_by_step = generate_packet_trace(config, users)

    sim = NetworkSimulator(config)
    result = sim.run_policy(PrioritySchedulingPolicy(), users, packets_by_step)

    # Separate delivered packets by priority
    high_pkts = [p for p in result.all_packets if p.priority == Priority.HIGH.value]
    low_pkts = [p for p in result.all_packets if p.priority == Priority.LOW.value]

    high_del = [p for p in high_pkts if p.status == PacketStatus.DELIVERED]
    low_del = [p for p in low_pkts if p.status == PacketStatus.DELIVERED]

    high_pdr = len(high_del) / len(high_pkts) if high_pkts else 0
    low_pdr = len(low_del) / len(low_pkts) if low_pkts else 0

    # High priority delivery ratio should exceed low priority delivery ratio
    assert high_pdr > low_pdr


def test_round_robin_turn_taking():
    """Verify that Round-Robin alternates between users with queued data."""
    qm = QueueManager(user_ids=[1, 2], max_queue_packets=10)

    # Enqueue 3 packets for user 1 and 3 packets for user 2
    for i in range(3):
        qm.enqueue(Packet(
            packet_id=i + 1,
            user_id=1,
            traffic_class=TrafficClass.WEB,
            priority=2,
            size_bytes=500,
            arrival_time=0.0,
            queue_entry_time=0.0,
        ))
        qm.enqueue(Packet(
            packet_id=i + 10,
            user_id=2,
            traffic_class=TrafficClass.WEB,
            priority=2,
            size_bytes=500,
            arrival_time=0.0,
            queue_entry_time=0.0,
        ))

    rr = RoundRobinPolicy(quantum_bytes=600)
    # Available budget allows transmitting 4 packets (2000 bytes)
    tx, tx_bytes = rr.schedule(qm, available_budget_bytes=2000, current_time=0.0)

    # Round robin should alternate users: User 1, User 2, User 1, User 2
    assert len(tx) == 4
    uids = [p.user_id for p in tx]
    assert uids == [1, 2, 1, 2]


def test_empty_queues_handled_gracefully():
    """Schedulers must return empty lists without crashing when queues are empty."""
    qm = QueueManager(user_ids=[1, 2], max_queue_packets=10)

    for pol in [EqualSharePolicy(), PrioritySchedulingPolicy(), RoundRobinPolicy()]:
        tx, tx_bytes = pol.schedule(qm, available_budget_bytes=5000, current_time=0.0)
        assert tx == []
        assert tx_bytes == 0
