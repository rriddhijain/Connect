"""Strict Priority-Based Packet Scheduling Policy."""

from typing import List, Tuple

from src.models import Packet
from src.policies.base import SchedulingPolicy
from src.queues import QueueManager


class PrioritySchedulingPolicy(SchedulingPolicy):
    """
    Strict priority packet scheduling — serves higher-priority traffic before
    lower-priority traffic while respecting total link capacity.
    """

    def __init__(self):
        super().__init__(
            name="Priority Scheduling",
            description=(
                "Strict priority scheduler: High-priority packets (Voice/Video) are served first, "
                "followed by Medium (Web), then Low (Download). Under congestion, low-priority "
                "traffic may experience starvation and high packet drops."
            ),
        )

    def schedule(
        self,
        queue_manager: QueueManager,
        available_budget_bytes: int,
        current_time: float,
    ) -> Tuple[List[Packet], int]:
        transmitted: List[Packet] = []
        total_bytes = 0
        remaining_budget = available_budget_bytes

        # Group queues by priority: 1 (High) -> 2 (Medium) -> 3 (Low)
        # We iterate in strict priority order
        while remaining_budget > 0:
            active_uids = queue_manager.get_active_user_ids()
            if not active_uids:
                break

            # Find the best priority level among active queues
            # We check the front packet of each active queue to determine its priority
            candidate_queues = []
            for uid in active_uids:
                q = queue_manager.get_queue(uid)
                if q and not q.is_empty():
                    front_pkt = q.peek()
                    if front_pkt:
                        candidate_queues.append((front_pkt.priority, uid, q))

            if not candidate_queues:
                break

            # Sort by priority rank (1 = High, 2 = Medium, 3 = Low)
            candidate_queues.sort(key=lambda item: item[0])

            # Try to transmit from the highest available priority tier
            transmitted_in_tier = False
            for priority_level in sorted(list(set(item[0] for item in candidate_queues))):
                tier_queues = [q for p, uid, q in candidate_queues if p == priority_level]

                for q in tier_queues:
                    while not q.is_empty():
                        pkt = q.peek()
                        if pkt is None or pkt.size_bytes > remaining_budget:
                            break

                        # Transmit this packet
                        pkt = q.pop()
                        if pkt is not None:
                            transmitted.append(pkt)
                            remaining_budget -= pkt.size_bytes
                            total_bytes += pkt.size_bytes
                            transmitted_in_tier = True

                if transmitted_in_tier:
                    # After serving higher priority tier in this cycle, re-evaluate from the top
                    break

            if not transmitted_in_tier:
                # No packet in any tier could fit into the remaining budget
                break

        return transmitted, total_bytes
