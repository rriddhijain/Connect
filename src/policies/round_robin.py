"""Round-Robin Packet Scheduling Policy."""

from typing import List, Tuple

from src.models import Packet
from src.policies.base import SchedulingPolicy
from src.queues import QueueManager


class RoundRobinPolicy(SchedulingPolicy):
    """
    Round-robin packet scheduling — serves active user queues in rotating turns
    so that no single user can monopolize the transmission link.
    """

    def __init__(self, quantum_bytes: int = 1500):
        super().__init__(
            name="Round-Robin",
            description=(
                "Cycles through active user queues in turn, giving each user equal transmission opportunities. "
                "Prevents any single user from monopolizing link transmission opportunities."
            ),
        )
        self.quantum_bytes = quantum_bytes
        self.last_served_user_idx: int = 0

    def reset(self) -> None:
        self.last_served_user_idx = 0

    def schedule(
        self,
        queue_manager: QueueManager,
        available_budget_bytes: int,
        current_time: float,
    ) -> Tuple[List[Packet], int]:
        transmitted: List[Packet] = []
        total_bytes = 0
        remaining_budget = available_budget_bytes

        active_uids = queue_manager.get_active_user_ids()
        if not active_uids:
            return transmitted, total_bytes

        # Normalize last_served_user_idx within active_uids length
        start_idx = self.last_served_user_idx % len(active_uids)

        # Loop until remaining budget is too small for any packet or queues empty
        max_cycles = 1000  # safety guard
        cycle_count = 0

        while remaining_budget > 0 and cycle_count < max_cycles:
            cycle_count += 1
            active_uids = queue_manager.get_active_user_ids()
            if not active_uids:
                break

            progress_in_cycle = False
            num_active = len(active_uids)

            for step_offset in range(num_active):
                curr_idx = (start_idx + step_offset) % num_active
                uid = active_uids[curr_idx]
                q = queue_manager.get_queue(uid)
                if not q or q.is_empty():
                    continue

                # Serve 1 packet (or up to quantum_bytes) for this user's turn
                bytes_served_this_turn = 0
                while not q.is_empty():
                    pkt = q.peek()
                    if pkt is None:
                        break

                    if pkt.size_bytes > remaining_budget:
                        # Cannot fit in remaining link budget
                        break

                    # Transmit packet
                    pkt = q.pop()
                    if pkt is not None:
                        transmitted.append(pkt)
                        remaining_budget -= pkt.size_bytes
                        total_bytes += pkt.size_bytes
                        bytes_served_this_turn += pkt.size_bytes
                        progress_in_cycle = True

                    # After 1 packet (or quantum limit reached), yield turn to next user
                    if bytes_served_this_turn >= min(self.quantum_bytes, pkt.size_bytes if pkt else 1500):
                        break

                self.last_served_user_idx = (curr_idx + 1) % max(1, num_active)

            if not progress_in_cycle:
                # No active queue has a packet that can fit within remaining_budget
                break

            # Update start_idx for subsequent passes in this time step
            start_idx = self.last_served_user_idx

        return transmitted, total_bytes
