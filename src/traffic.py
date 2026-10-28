"""Synthetic traffic generation for Network Bandwidth Allocation Simulator."""

import random
from typing import Dict, List, Tuple

from src.models import Packet, PacketStatus, Priority, SimulationConfig, TrafficClass, User


SCENARIO_OFFERED_RATIOS = {
    "Light Load": 0.35,        # 35% of link capacity
    "Moderate Load": 0.85,     # 85% of link capacity
    "Heavy Congestion": 1.75,  # 175% of link capacity
    "Mixed Traffic": 1.15,     # 115% of link capacity
}


def build_users_for_scenario(config: SimulationConfig) -> List[User]:
    """Create the synthetic users and their configurations deterministically."""
    rng = random.Random(config.seed)
    users: List[User] = []

    # Map classes and weights
    classes = [
        TrafficClass.VOICE,
        TrafficClass.VIDEO_STREAM,
        TrafficClass.WEB,
        TrafficClass.DOWNLOAD,
    ]
    weights = [
        config.traffic_mix.get(c.value, 0.25) for c in classes
    ]
    total_weight = sum(weights)
    if total_weight > 0:
        norm_weights = [w / total_weight for w in weights]
    else:
        norm_weights = [0.25, 0.25, 0.25, 0.25]

    # Calculate total offered bandwidth target
    multiplier = SCENARIO_OFFERED_RATIOS.get(config.scenario_name, 1.0)
    total_offered_mbps = config.bandwidth_mbps * multiplier

    # Allocate user rates
    # Some traffic types naturally demand more bandwidth than others (e.g., Download > Video > Web > Voice)
    class_rate_factors = {
        TrafficClass.VOICE: 0.15,
        TrafficClass.WEB: 0.45,
        TrafficClass.VIDEO_STREAM: 1.0,
        TrafficClass.DOWNLOAD: 2.0,
    }

    # Assign class to each user cyclically or weighted
    class_assignments: List[TrafficClass] = []
    # Ensure at least 1 of each class if num_users >= 4
    if config.num_users >= 4:
        class_assignments.extend(classes)
        remaining = config.num_users - 4
        if remaining > 0:
            extra = rng.choices(classes, weights=norm_weights, k=remaining)
            class_assignments.extend(extra)
    else:
        class_assignments = rng.choices(classes, weights=norm_weights, k=config.num_users)

    # Calculate baseline rates
    raw_rates = [class_rate_factors[c] for c in class_assignments]
    sum_factors = sum(raw_rates) if raw_rates else 1.0
    scale = total_offered_mbps / sum_factors

    for i, t_class in enumerate(class_assignments):
        user_id = i + 1
        name = f"User_{user_id:02d} ({t_class.name.capitalize()})"
        priority = t_class.default_priority.value
        rate_mbps = raw_rates[i] * scale
        avg_packet_size = t_class.typical_packet_size

        user = User(
            user_id=user_id,
            name=name,
            traffic_class=t_class,
            priority=priority,
            target_rate_mbps=rate_mbps,
            avg_packet_size_bytes=avg_packet_size,
        )
        users.append(user)

    return users


def generate_packet_trace(
    config: SimulationConfig, users: List[User]
) -> Tuple[List[Packet], Dict[int, List[Packet]]]:
    """
    Generate synthetic packets deterministically from the random seed.
    Returns:
        all_packets: List of all generated Packet objects.
        packets_by_step: Dictionary mapping time_step index -> list of arriving packets in that step.
    """
    rng = random.Random(config.seed + 100)
    all_packets: List[Packet] = []
    packet_id_counter = 1
    duration = config.duration_seconds
    dt = config.time_step_seconds
    total_steps = int(duration / dt)

    packets_by_step: Dict[int, List[Packet]] = {step: [] for step in range(total_steps + 1)}

    for user in users:
        t_class = user.traffic_class
        target_bps = user.target_rate_mbps * 1_000_000

        curr_time = rng.uniform(0.0, 0.05)  # slight initial stagger

        if t_class == TrafficClass.VOICE:
            # Frequent, small packets with minor jitter
            # e.g., 200 bytes per packet
            base_size = 200
            interval = (base_size * 8.0) / target_bps if target_bps > 0 else 0.02
            interval = max(0.005, min(0.050, interval))

            while curr_time < duration:
                size = int(rng.gauss(base_size, 15))
                size = max(100, min(300, size))
                step_idx = min(total_steps, int(curr_time / dt))

                pkt = Packet(
                    packet_id=packet_id_counter,
                    user_id=user.user_id,
                    traffic_class=t_class,
                    priority=user.priority,
                    size_bytes=size,
                    arrival_time=round(curr_time, 5),
                    queue_entry_time=round(curr_time, 5),
                    status=PacketStatus.QUEUED,
                )
                packet_id_counter += 1
                all_packets.append(pkt)
                packets_by_step[step_idx].append(pkt)

                jitter = rng.uniform(-0.002, 0.002)
                curr_time += max(0.002, interval + jitter)

        elif t_class == TrafficClass.VIDEO_STREAM:
            # Medium-large packets periodic (e.g. streaming chunks / frames)
            base_size = 1000
            interval = (base_size * 8.0) / target_bps if target_bps > 0 else 0.033
            interval = max(0.004, min(0.066, interval))

            while curr_time < duration:
                size = int(rng.gauss(base_size, 80))
                size = max(500, min(1400, size))
                step_idx = min(total_steps, int(curr_time / dt))

                pkt = Packet(
                    packet_id=packet_id_counter,
                    user_id=user.user_id,
                    traffic_class=t_class,
                    priority=user.priority,
                    size_bytes=size,
                    arrival_time=round(curr_time, 5),
                    queue_entry_time=round(curr_time, 5),
                    status=PacketStatus.QUEUED,
                )
                packet_id_counter += 1
                all_packets.append(pkt)
                packets_by_step[step_idx].append(pkt)

                curr_time += interval

        elif t_class == TrafficClass.WEB:
            # Bursty traffic: ON/OFF model
            # ON periods: group of 5-15 packets of ~1200 bytes
            # OFF periods: idle 0.5s - 2.5s
            while curr_time < duration:
                # Burst (ON period)
                burst_packets = rng.randint(4, 14)
                burst_spacing = rng.uniform(0.005, 0.015)
                for _ in range(burst_packets):
                    if curr_time >= duration:
                        break
                    size = int(rng.gauss(1200, 100))
                    size = max(400, min(1450, size))
                    step_idx = min(total_steps, int(curr_time / dt))

                    pkt = Packet(
                        packet_id=packet_id_counter,
                        user_id=user.user_id,
                        traffic_class=t_class,
                        priority=user.priority,
                        size_bytes=size,
                        arrival_time=round(curr_time, 5),
                        queue_entry_time=round(curr_time, 5),
                        status=PacketStatus.QUEUED,
                    )
                    packet_id_counter += 1
                    all_packets.append(pkt)
                    packets_by_step[step_idx].append(pkt)
                    curr_time += burst_spacing

                # Idle (OFF period)
                idle_duration = rng.expovariate(1.0)
                idle_duration = max(0.2, min(3.0, idle_duration))
                curr_time += idle_duration

        else:  # TrafficClass.DOWNLOAD
            # Bulk download: large packets sent continuously
            base_size = 1400
            interval = (base_size * 8.0) / target_bps if target_bps > 0 else 0.008
            interval = max(0.001, interval)

            while curr_time < duration:
                size = int(rng.gauss(base_size, 40))
                size = max(1000, min(1500, size))
                step_idx = min(total_steps, int(curr_time / dt))

                pkt = Packet(
                    packet_id=packet_id_counter,
                    user_id=user.user_id,
                    traffic_class=t_class,
                    priority=user.priority,
                    size_bytes=size,
                    arrival_time=round(curr_time, 5),
                    queue_entry_time=round(curr_time, 5),
                    status=PacketStatus.QUEUED,
                )
                packet_id_counter += 1
                all_packets.append(pkt)
                packets_by_step[step_idx].append(pkt)

                curr_time += interval

    all_packets.sort(key=lambda p: (p.arrival_time, p.packet_id))
    return all_packets, packets_by_step
