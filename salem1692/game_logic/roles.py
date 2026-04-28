"""
Role and Tryal-card definitions for Salem 1692
"""

from dataclasses import dataclass
from enum import Enum
import random


class TryalType(Enum):
    NOT_A_WITCH = "Not A Witch"
    WITCH = "Witch"
    CONSTABLE = "Constable"

    def __str__(self):
        return self.value


@dataclass
class TryalCard:
    kind: TryalType
    revealed: bool = False

    def __str__(self):
        if self.revealed:
            return self.kind.value
        return "Face-down Tryal"


class RoleManager:
    """
    Builds the Tryal-card pool using the official player-count table.
    """

    TRYAL_COUNTS = {
        4: {"not_witch": 18, "witch": 1, "constable": 1},
        5: {"not_witch": 23, "witch": 1, "constable": 1},
        6: {"not_witch": 27, "witch": 2, "constable": 1},
        7: {"not_witch": 32, "witch": 2, "constable": 1},
        8: {"not_witch": 29, "witch": 2, "constable": 1},
        9: {"not_witch": 33, "witch": 2, "constable": 1},
        10: {"not_witch": 27, "witch": 2, "constable": 1},
        11: {"not_witch": 30, "witch": 2, "constable": 1},
        12: {"not_witch": 33, "witch": 2, "constable": 1},
    }

    @staticmethod
    def build_tryal_deck(num_players: int):
        if num_players not in RoleManager.TRYAL_COUNTS:
            raise ValueError("Salem supports 4 to 12 players.")

        counts = RoleManager.TRYAL_COUNTS[num_players]
        total_cards = counts["not_witch"] + counts["witch"] + counts["constable"]
        cards_per_player = total_cards // num_players

        tryal_cards = (
            [TryalCard(TryalType.NOT_A_WITCH) for _ in range(counts["not_witch"])]
            + [TryalCard(TryalType.WITCH) for _ in range(counts["witch"])]
            + [TryalCard(TryalType.CONSTABLE) for _ in range(counts["constable"])]
        )
        random.shuffle(tryal_cards)

        return tryal_cards, cards_per_player