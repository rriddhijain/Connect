"""Data models for Network Bandwidth Allocation Simulator."""

from dataclasses import dataclass, field
from enum import Enum
from typing import Dict, Optional


class Priority(int, Enum):
    """Traffic priority levels (lower integer value = higher priority)."""
    HIGH = 1
    MEDIUM = 2
    LOW = 3


class TrafficClass(str, Enum):
    """Traffic classes representing different synthetic network applications."""
    VOICE = "Voice / Video Call"
    VIDEO_STREAM = "Online Lecture / Video"
    WEB = "Web Browsing"
    DOWNLOAD = "File Download"

    @property
    def default_priority(self) -> Priority:
        if self == TrafficClass.VOICE or self == TrafficClass.VIDEO_STREAM:
            return Priority.HIGH
        elif self == TrafficClass.WEB:
            return Priority.MEDIUM
        else:
            return Priority.LOW

    @property
    def typical_packet_size(self) -> int:
        """Typical packet size in bytes."""
        if self == TrafficClass.VOICE:
            return 200
        elif self == TrafficClass.VIDEO_STREAM:
            return 1000
        elif self == TrafficClass.WEB:
            return 1200
        else:  # DOWNLOAD
            return 1400


class PacketStatus(str, Enum):
    """Status of a packet in the network."""
    QUEUED = "queued"
    DELIVERED = "delivered"
    DROPPED_BUFFER_OVERFLOW = "dropped_buffer_overflow"


@dataclass
class Packet:
    """Represents an individual synthetic network packet."""
    packet_id: int
    user_id: int
    traffic_class: TrafficClass
    priority: int  # 1: High, 2: Medium, 3: Low
    size_bytes: int
    arrival_time: float  # Simulation timestamp in seconds
    queue_entry_time: float
    delivery_time: Optional[float] = None
    status: PacketStatus = PacketStatus.QUEUED
    drop_reason: Optional[str] = None

    @property
    def size_bits(self) -> int:
        return self.size_bytes * 8

    @property
    def latency_seconds(self) -> Optional[float]:
        if self.delivery_time is not None:
            return max(0.0, self.delivery_time - self.arrival_time)
        return None

    @property
    def latency_ms(self) -> Optional[float]:
        lat = self.latency_seconds
        return lat * 1000.0 if lat is not None else None


@dataclass
class User:
    """Represents a synthetic user generating traffic."""
    user_id: int
    name: str
    traffic_class: TrafficClass
    priority: int
    target_rate_mbps: float
    avg_packet_size_bytes: int

    # Live counters during simulation
    packets_generated: int = 0
    packets_delivered: int = 0
    packets_dropped: int = 0
    bytes_generated: int = 0
    bytes_delivered: int = 0
    bytes_dropped: int = 0


@dataclass
class SimulationConfig:
    """Simulation run configuration."""
    bandwidth_mbps: float = 20.0
    num_users: int = 10
    duration_seconds: float = 60.0
    time_step_seconds: float = 0.01  # 10 milliseconds
    max_queue_packets: int = 50
    seed: int = 42
    scenario_name: str = "Moderate Load"
    traffic_mix: Dict[str, float] = field(default_factory=lambda: {
        TrafficClass.VOICE.value: 0.25,
        TrafficClass.VIDEO_STREAM.value: 0.25,
        TrafficClass.WEB.value: 0.25,
        TrafficClass.DOWNLOAD.value: 0.25,
    })
    # Deficit / Byte quantum for Round Robin
    rr_quantum_bytes: int = 1500
