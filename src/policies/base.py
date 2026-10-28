"""Base policy interface for packet schedulers."""

from abc import ABC, abstractmethod
from typing import List, Tuple

from src.models import Packet
from src.queues import QueueManager


class SchedulingPolicy(ABC):
    """Abstract base class for network packet scheduling and bandwidth allocation policies."""

    def __init__(self, name: str, description: str):
        self.name = name
        self.description = description

    @abstractmethod
    def schedule(
        self,
        queue_manager: QueueManager,
        available_budget_bytes: int,
        current_time: float,
    ) -> Tuple[List[Packet], int]:
        """
        Select and dequeue packets to transmit within the available byte budget.

        Args:
            queue_manager: The QueueManager holding all user queues.
            available_budget_bytes: Maximum number of bytes permitted to transmit.
            current_time: Current simulation timestamp in seconds.

        Returns:
            transmitted_packets: List of packets that were dequeued and transmitted.
            bytes_transmitted: Total bytes transmitted.
        """
        pass

    def reset(self) -> None:
        """Reset internal scheduler state (e.g., turn pointers or deficits) between simulation runs."""
        pass
