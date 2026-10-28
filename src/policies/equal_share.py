"""Equal Bandwidth Allocation Policy (Fair-Share Service)."""

from typing import List, Tuple

from src.models import Packet
from src.policies.base import SchedulingPolicy
from src.queues import QueueManager


class EqualSharePolicy(SchedulingPolicy):
    """
    Equal bandwidth allocation — divides available link transmission service
    equally among active users in each time step.
    """

    def __init__(self):
        super().__init__(
            name="Equal Allocation",
            description=(
                "Divides available link capacity equally among active users with queued data. "
                "Ensures baseline fairness across active flows."
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

        while remaining_budget > 0:
            active_uids = queue_manager.get_active_user_ids()
            if not active_uids:
                break

            fair_share = max(1, remaining_budget // len(active_uids))
            any_transmitted = False

            for uid in active_uids:
                queue = queue_manager.get_queue(uid)
                if not queue or queue.is_empty():
                    continue

                user_spent = 0
                while not queue.is_empty():
                    next_pkt = queue.peek()
                    if next_pkt is None:
                        break

                    # Check if packet fits in remaining total budget
                    if next_pkt.size_bytes > remaining_budget:
                        break

                    # Allow packet if user hasn't consumed fair share or first packet fits budget
                    if (user_spent + next_pkt.size_bytes <= fair_share) or (user_spent == 0 and next_pkt.size_bytes <= remaining_budget):
                        pkt = queue.pop()
                        if pkt is not None:
                            transmitted.append(pkt)
                            remaining_budget -= pkt.size_bytes
                            user_spent += pkt.size_bytes
                            total_bytes += pkt.size_bytes
                            any_transmitted = True
                            if user_spent >= fair_share:
                                break
                    else:
                        break

            if not any_transmitted:
                # If no user could transmit within fair_share but budget remains,
                # allow the first user whose packet fits in remaining budget to transmit
                progress = False
                for uid in queue_manager.get_active_user_ids():
                    queue = queue_manager.get_queue(uid)
                    if queue and not queue.is_empty():
                        pkt = queue.peek()
                        if pkt and pkt.size_bytes <= remaining_budget:
                            pkt = queue.pop()
                            if pkt is not None:
                                transmitted.append(pkt)
                                remaining_budget -= pkt.size_bytes
                                total_bytes += pkt.size_bytes
                                progress = True
                                break
                if not progress:
                    break

        return transmitted, total_bytes
