"""
Card deck management for Salem 1692
"""

import random
from enum import Enum

class CardType(Enum):
    """Types of cards in Salem 1692"""
    INFLUENCE = "Influence"
    EVIDENCE = "Evidence"
    WITCHCRAFT = "Witchcraft"
    DEFENSE = "Defense"
    ACCUSATION = "Accusation"

class Card:
    """Represents a card in the game"""
    
    def __init__(self, card_type, description, effect):
        self.type = card_type
        self.description = description
        self.effect = effect
        
    def __str__(self):
        return f"{self.type.value}: {self.description}"

class Deck:
    """Manages the card deck"""
    
    def __init__(self):
        self.cards = []
        self.discard_pile = []
        self._initialize_deck()
        
    def _initialize_deck(self):
        """Create the initial deck of cards"""
        
        # Influence cards - can sway votes
        for i in range(8):
            self.cards.append(Card(
                CardType.INFLUENCE,
                "Gain influence over others",
                lambda player, game: self._influence_effect(player, game)
            ))
        
        # Evidence cards - can be used to accuse
        for i in range(6):
            self.cards.append(Card(
                CardType.EVIDENCE,
                "Find evidence against another player",
                lambda player, game: self._evidence_effect(player, game)
            ))
        
        # Witchcraft cards - witches can use these
        for i in range(5):
            self.cards.append(Card(
                CardType.WITCHCRAFT,
                "Perform witchcraft",
                lambda player, game: self._witchcraft_effect(player, game)
            ))
        
        # Defense cards - protect against accusations
        for i in range(6):
            self.cards.append(Card(
                CardType.DEFENSE,
                "Defend against accusations",
                lambda player, game: self._defense_effect(player, game)
            ))
        
        # Accusation cards - force an accusation
        for i in range(5):
            self.cards.append(Card(
                CardType.ACCUSATION,
                "Force an accusation",
                lambda player, game: self._accusation_effect(player, game)
            ))
        
        random.shuffle(self.cards)
    
    def draw_card(self):
        """Draw a card from the deck"""
        if not self.cards:
            self._reshuffle_discard()
        
        if self.cards:
            return self.cards.pop()
        return None
    
    def discard_card(self, card):
        """Add a card to the discard pile"""
        self.discard_pile.append(card)
    
    def _reshuffle_discard(self):
        """Reshuffle discard pile into deck"""
        self.cards = self.discard_pile.copy()
        self.discard_pile = []
        random.shuffle(self.cards)
    
    def _influence_effect(self, player, game):
        """Effect of influence card"""
        return f"{player.name} gains influence! +1 vote power."
    
    def _evidence_effect(self, player, game):
        """Effect of evidence card"""
        return f"{player.name} finds evidence! Can accuse one extra player."
    
    def _witchcraft_effect(self, player, game):
        """Effect of witchcraft card"""
        if player.is_witch():
            return f"{player.name} performs witchcraft! Gains special power."
        else:
            return f"{player.name} is corrupted by witchcraft! Loses next turn."
    
    def _defense_effect(self, player, game):
        """Effect of defense card"""
        player.defense_cards.append(self)
        return f"{player.name} gains a defense token!"
    
    def _accusation_effect(self, player, game):
        """Effect of accusation card"""
        return f"{player.name} can make an immediate accusation!"