"""
Playing deck for Salem 1692
"""

import random
from dataclasses import dataclass
from enum import Enum


class CardColor(Enum):
    GREEN = "Green"
    BLUE = "Blue"
    RED = "Red"
    BLACK = "Black"


@dataclass
class Card:
    name: str
    color: CardColor
    description: str
    accusation_value: int = 0

    def __str__(self):
        if self.color == CardColor.RED:
            return f"{self.name} [{self.color.value} +{self.accusation_value}]"
        return f"{self.name} [{self.color.value}]"


class Deck:
    """
    Salem-style deck.
    This keeps the rule-important cards and their colors/behaviors.
    """

    def __init__(self):
        self.cards = []
        self.discard_pile = []
        self.black_cat_card = Card(
            "Black Cat",
            CardColor.BLUE,
            "Blue card placed during Dawn. Also matters for Conspiracy.",
        )
        self.night_card = Card(
            "Night",
            CardColor.BLACK,
            "Black card. Witches attempt a kill; Constable attempts a save.",
        )
        self.conspiracy_card = Card(
            "Conspiracy",
            CardColor.BLACK,
            "All players take one hidden Tryal card from the player to the left.",
        )
        self._initialize_deck()

    def _initialize_deck(self):
        self.cards = []

        # Red cards  (+1 / +3 / +7)
        for _ in range(18):
            self.cards.append(Card("Accusation", CardColor.RED, "Place 1 accusation token.", accusation_value=1))
        for _ in range(8):
            self.cards.append(Card("Evidence", CardColor.RED, "Place 3 accusation tokens.", accusation_value=3))
        for _ in range(4):
            self.cards.append(Card("Testimony", CardColor.RED, "Place 7 accusation tokens — instant reveal!", accusation_value=7))

        # Blue cards
        for _ in range(4):
            self.cards.append(Card("Asylum", CardColor.BLUE, "Protects from Night kill."))
        for _ in range(4):
            self.cards.append(Card("Piety", CardColor.BLUE, "A persistent effect card."))
        for _ in range(4):
            self.cards.append(Card("Alibi", CardColor.BLUE, "A persistent effect card."))

        # Green cards
        for _ in range(4):
            self.cards.append(Card("Curse", CardColor.GREEN, "Discard one blue card from a player."))
        for _ in range(4):
            self.cards.append(Card("Scapegoat", CardColor.GREEN, "Move all red and blue cards from one player to another."))
        for _ in range(4):
            self.cards.append(Card("Robbery", CardColor.GREEN, "Take a random hand card from one player and give it to another."))

        random.shuffle(self.cards)

    def setup_draw_pile(self):
        """
        Per rulebook:
        - remove Black Cat, Night, Conspiracy
        - deal 3 cards to players
        - shuffle Conspiracy back in
        - put Night at the bottom
        - Black Cat aside for Dawn
        """
        random.shuffle(self.cards)
        self.cards.append(self.conspiracy_card)
        random.shuffle(self.cards)
        self.cards.insert(0, self.night_card)  # bottom of deck if drawing with pop()

    def draw_card(self):
        if not self.cards:
            return None
        return self.cards.pop()

    def discard_card(self, card):
        if card is not None:
            self.discard_pile.append(card)

    def discard_many(self, cards):
        for card in cards:
            self.discard_card(card)

    def reshuffle_after_night(self):
        """
        After Night, discard pile reforms the deck, Night returns to bottom.
        """
        temp = [card for card in self.discard_pile if card.name != "Night"]
        self.discard_pile = []

        random.shuffle(temp)
        self.cards = temp
        self.cards.insert(0, self.night_card)