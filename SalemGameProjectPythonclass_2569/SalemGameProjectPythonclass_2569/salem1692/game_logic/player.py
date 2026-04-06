"""
Player class for Salem 1692
"""

from .roles import Role

class Player:
    """Represents a player in the game"""
    
    def __init__(self, name, player_id, role=None):
        self.name = name
        self.id = player_id
        self.role = role
        self.alive = True
        self.hand = []  # Cards in hand
        self.accused = False
        self.defense_cards = []
        self.votes = 0  # Votes received in current accusation
        
    def is_witch(self):
        """Check if player is a witch"""
        return self.role == Role.WITCH
    
    def eliminate(self):
        """Remove player from game"""
        self.alive = False
        
    def add_card(self, card):
        """Add a card to player's hand"""
        self.hand.append(card)
        
    def remove_card(self, card):
        """Remove a card from player's hand"""
        if card in self.hand:
            self.hand.remove(card)
            return card
        return None
    
    def get_hand_size(self):
        """Get number of cards in hand"""
        return len(self.hand)
    
    def reset_votes(self):
        """Reset votes for new accusation"""
        self.votes = 0
        
    def add_vote(self):
        """Add a vote to this player"""
        self.votes += 1
        
    def __str__(self):
        status = "Alive" if self.alive else "Eliminated"
        role_str = str(self.role) if self.role else "Unknown"
        return f"{self.name} ({role_str}) - {status}"