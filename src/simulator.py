"""Discrete-time network bottleneck link simulation engine."""

import copy
from dataclasses import dataclass, field
from typing import Dict, List

from src.models import Packet, PacketStatus, SimulationConfig, User
from src.policies.base import SchedulingPolicy
from src.queues import QueueManager


@dataclass
class TimeStepSnapshot:
    """Snapshot of network state at a discrete time step."""
    step: int
    time_seconds: float
    transmitted_bytes: int
    transmitted_packets: int
    dropped_packets: int
    total_queued_packets: int
    total_queued_bytes: int
    instant_throughput_mbps: float


@dataclass
class SimulationResult:
    """Complete simulation results for a policy run."""
    policy_name: str
    config: SimulationConfig
    users: List[User]
    all_packets: List[Packet]
    delivered_packets: List[Packet]
    dropped_packets: List[Packet]
    remaining_packets: List[Packet]
    snapshots: List[TimeStepSnapshot]
    total_transmitted_bytes: int
    total_delivered_bits: int
    duration_seconds: float


class NetworkSimulator:
    """
    Discrete-time network bottleneck link simulator.
    Simulates packet arrival, queueing, and transmission under a chosen scheduling policy.
    """

    def __init__(self, config: SimulationConfig):
        self.config = config

    def run_policy(
        self,
        policy: SchedulingPolicy,
        users: List[User],
        packets_by_step: Dict[int, List[Packet]],
    ) -> SimulationResult:
        """
        Execute simulation for a specific policy using the provided packet trace.
        Deep-copies users and packets so that multiple policies run on identical inputs.
        """
        # Deep-copy users and policy reset
        sim_users = [copy.deepcopy(u) for u in users]
        user_map = {u.user_id: u for u in sim_users}
        policy.reset()

        queue_manager = QueueManager(
            user_ids=[u.user_id for u in sim_users],
            max_queue_packets=self.config.max_queue_packets,
        )

        dt = self.config.time_step_seconds
        duration = self.config.duration_seconds
        total_steps = int(duration / dt)

        # Budget per step in bytes: (C * 1_000_000 * dt) / 8
        step_budget_bytes = int((self.config.bandwidth_mbps * 1_000_000.0 * dt) / 8.0)

        delivered_packets: List[Packet] = []
        dropped_packets: List[Packet] = []
        all_sim_packets: List[Packet] = []
        snapshots: List[TimeStepSnapshot] = []

        total_transmitted_bytes = 0
        token_accumulator = 0  # Unused transmission capacity accumulator, capped at 1 step budget
        max_accumulated_budget = step_budget_bytes

        for step in range(total_steps):
            current_time = round(step * dt, 5)
            step_dropped_count = 0

            # 1. Ingest arriving packets for this time step
            arriving = packets_by_step.get(step, [])
            for orig_pkt in arriving:
                pkt = copy.deepcopy(orig_pkt)
                all_sim_packets.append(pkt)
                u = user_map.get(pkt.user_id)
                if u:
                    u.packets_generated += 1
                    u.bytes_generated += pkt.size_bytes

                enqueued = queue_manager.enqueue(pkt)
                if not enqueued:
                    dropped_packets.append(pkt)
                    step_dropped_count += 1
                    if u:
                        u.packets_dropped += 1
                        u.bytes_dropped += pkt.size_bytes

            # 2. Add step transmission budget
            token_accumulator = min(max_accumulated_budget, token_accumulator + step_budget_bytes)

            # 3. Schedule and transmit packets
            tx_packets, tx_bytes = policy.schedule(
                queue_manager=queue_manager,
                available_budget_bytes=token_accumulator,
                current_time=current_time,
            )

            token_accumulator = max(0, token_accumulator - tx_bytes)
            total_transmitted_bytes += tx_bytes

            # Mark delivered packets
            for pkt in tx_packets:
                pkt.status = PacketStatus.DELIVERED
                pkt.delivery_time = round(current_time + dt, 5)
                delivered_packets.append(pkt)
                u = user_map.get(pkt.user_id)
                if u:
                    u.packets_delivered += 1
                    u.bytes_delivered += pkt.size_bytes

            # Record time series snapshot
            instant_mbps = (tx_bytes * 8.0) / (dt * 1_000_000.0) if dt > 0 else 0.0
            snapshots.append(
                TimeStepSnapshot(
                    step=step,
                    time_seconds=current_time,
                    transmitted_bytes=tx_bytes,
                    transmitted_packets=len(tx_packets),
                    dropped_packets=step_dropped_count,
                    total_queued_packets=queue_manager.total_queued_packets(),
                    total_queued_bytes=queue_manager.total_queued_bytes(),
                    instant_throughput_mbps=instant_mbps,
                )
            )

        # 4. End of simulation accounting: inspect remaining packets in queue
        remaining_packets = queue_manager.get_all_remaining_packets()

        # Invariant assertion check:
        # total_generated == delivered + dropped + remaining
        total_gen = len(all_sim_packets)
        total_del = len(delivered_packets)
        total_drop = len(dropped_packets)
        total_rem = len(remaining_packets)
        assert total_gen == total_del + total_drop + total_rem, (
            f"Accounting mismatch: gen={total_gen} != del({total_del}) + drop({total_drop}) + rem({total_rem})"
        )

        return SimulationResult(
            policy_name=policy.name,
            config=self.config,
            users=sim_users,
            all_packets=all_sim_packets,
            delivered_packets=delivered_packets,
            dropped_packets=dropped_packets,
            remaining_packets=remaining_packets,
            snapshots=snapshots,
            total_transmitted_bytes=total_transmitted_bytes,
            total_delivered_bits=total_transmitted_bytes * 8,
            duration_seconds=duration,
        )
