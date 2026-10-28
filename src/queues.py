"""FIFO Queue management with buffer overflow drop accounting."""

from collections import deque
from typing import Dict, List, Optional

from src.models import Packet, PacketStatus


class UserQueue:
    """FIFO packet queue for a single synthetic user."""

    def __init__(self, user_id: int, max_packets: int = 50):
        self.user_id = user_id
        self.max_packets = max_packets
        self._queue: deque[Packet] = deque()
        self.total_enqueued_count = 0
        self.total_dropped_count = 0
        self.total_served_count = 0

    def enqueue(self, packet: Packet) -> bool:
        """
        Attempt to enqueue a packet.
        If queue is at capacity, mark packet as dropped and return False.
        """
        if len(self._queue) >= self.max_packets:
            packet.status = PacketStatus.DROPPED_BUFFER_OVERFLOW
            packet.drop_reason = f"Queue overflow for User {self.user_id} (limit={self.max_packets})"
            self.total_dropped_count += 1
            return False

        self._queue.append(packet)
        self.total_enqueued_count += 1
        return True

    def peek(self) -> Optional[Packet]:
        """View the next packet without removing it."""
        return self._queue[0] if self._queue else None

    def pop(self) -> Optional[Packet]:
        """Pop the next packet in FIFO order."""
        if self._queue:
            self.total_served_count += 1
            return self._queue.popleft()
        return None

    def is_empty(self) -> bool:
        return len(self._queue) == 0

    @property
    def packet_count(self) -> int:
        return len(self._queue)

    @property
    def total_bytes(self) -> int:
        return sum(pkt.size_bytes for pkt in self._queue)

    def get_remaining_packets(self) -> List[Packet]:
        return list(self._queue)


class QueueManager:
    """Manages per-user queues for the shared bottleneck link."""

    def __init__(self, user_ids: List[int], max_queue_packets: int = 50):
        self.max_queue_packets = max_queue_packets
        self.queues: Dict[int, UserQueue] = {
            uid: UserQueue(user_id=uid, max_packets=max_queue_packets)
            for uid in user_ids
        }

    def enqueue(self, packet: Packet) -> bool:
        """Enqueue packet to its respective user queue."""
        if packet.user_id not in self.queues:
            self.queues[packet.user_id] = UserQueue(
                user_id=packet.user_id, max_packets=self.max_queue_packets
            )
        return self.queues[packet.user_id].enqueue(packet)

    def get_queue(self, user_id: int) -> Optional[UserQueue]:
        return self.queues.get(user_id)

    def get_active_user_ids(self) -> List[int]:
        """Returns sorted list of user IDs that currently have queued packets."""
        return [uid for uid, q in self.queues.items() if not q.is_empty()]

    def total_queued_packets(self) -> int:
        return sum(q.packet_count for q in self.queues.values())

    def total_queued_bytes(self) -> int:
        return sum(q.total_bytes for q in self.queues.values())

    def get_all_remaining_packets(self) -> List[Packet]:
        """Collect all packets still sitting in queues at end of simulation."""
        remaining: List[Packet] = []
        for q in self.queues.values():
            remaining.extend(q.get_remaining_packets())
        return remaining
