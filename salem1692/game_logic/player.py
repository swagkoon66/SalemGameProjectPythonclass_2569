"""
Player model for Salem 1692
"""

from typing import List, Optional
from .roles import TryalType, TryalCard


class Player:
    """Represents a player in the game."""

    def __init__(self, name, player_id):
        self.name = name
        self.id = player_id
        self.alive = True

        self.hand = []  # playing cards in hand
        self.tryal_cards: List[TryalCard] = []

        self.blue_cards = []   # cards staying in front of player
        self.red_cards = []    # accusation cards in front of player

        self.ever_witch = False
        self.confessed_this_night = False
        self.gavel_protected = False

    def assign_tryal_cards(self, cards: List[TryalCard]):
        self.tryal_cards = cards
        for card in cards:
            if card.kind == TryalType.WITCH:
                self.ever_witch = True

    def is_witch(self) -> bool:
        return self.ever_witch

    def currently_has_constable(self) -> bool:
        """Constable power is active only while the Tryal card is still face-down."""
        return any(
            card.kind == TryalType.CONSTABLE and not card.revealed
            for card in self.tryal_cards
        )

    def add_card(self, card):
        self.hand.append(card)

    def remove_card_by_index(self, index: int):
        if index < 0 or index >= len(self.hand):
            return None
        return self.hand.pop(index)

    def add_blue_card(self, card):
        self.blue_cards.append(card)

    def remove_blue_card_by_name(self, card_name: str):
        for i, card in enumerate(self.blue_cards):
            if card.name == card_name:
                return self.blue_cards.pop(i)
        return None

    def has_blue_card(self, card_name: str) -> bool:
        return any(card.name == card_name for card in self.blue_cards)

    def add_red_card(self, card):
        self.red_cards.append(card)

    def clear_red_cards(self):
        self.red_cards.clear()

    def accusation_total(self) -> int:
        return sum(getattr(card, "accusation_value", 0) for card in self.red_cards)

    def unrevealed_tryal_indices(self):
        return [i for i, card in enumerate(self.tryal_cards) if not card.revealed]

    def revealed_tryals(self):
        return [card for card in self.tryal_cards if card.revealed]

    def reveal_tryal(self, index: Optional[int] = None):
        unrevealed = self.unrevealed_tryal_indices()
        if not unrevealed:
            return None

        if index is None or index not in unrevealed:
            index = unrevealed[0]

        self.tryal_cards[index].revealed = True
        return self.tryal_cards[index]

    def all_tryals_revealed(self) -> bool:
        return all(card.revealed for card in self.tryal_cards)

    def has_revealed_witch(self) -> bool:
        return any(card.kind == TryalType.WITCH and card.revealed for card in self.tryal_cards)

    def reset_night_flags(self):
        self.confessed_this_night = False
        self.gavel_protected = False

    def die(self):
        self.alive = False
        for card in self.tryal_cards:
            card.revealed = True

    def public_status(self):
        hidden = sum(1 for c in self.tryal_cards if not c.revealed)
        revealed = len(self.tryal_cards) - hidden
        return f"{self.name} | {'Alive' if self.alive else 'Dead'} | Tryals: {revealed} revealed / {hidden} hidden"

    def __str__(self):
        return self.public_status()