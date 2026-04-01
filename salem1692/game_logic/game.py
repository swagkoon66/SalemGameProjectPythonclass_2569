"""
Main game logic for Salem 1692 - Multiplayer version
"""

import random
from .player import Player
from .deck import Deck, CardType
from .roles import RoleManager, Role

class Game:
    """Main game controller for multiplayer"""
    
    def __init__(self):
        self.players = []
        self.current_player_index = 0
        self.deck = Deck()
        self.game_log = []
        self.winner = None
        self.accusation_phase = False
        self.accused_player = None
        self.accused_by = None
        self.votes_cast = set()
        
    def setup_game(self, player_names, player_ids=None):
        """Initialize the game with players"""
        self.game_log.clear()
        self.add_to_log("=== Game Setup ===")
        
        # Create players
        num_players = len(player_names)
        roles = RoleManager.assign_roles(num_players)
        random.shuffle(roles)
        
        for i, name in enumerate(player_names):
            player_id = player_ids[i] if player_ids else i
            player = Player(name, player_id, roles[i])
            self.players.append(player)
            self.add_to_log(f"{name} joins the game as {roles[i]}")
        
        # Give each player starting cards
        for player in self.players:
            for _ in range(3):
                card = self.deck.draw_card()
                if card:
                    player.add_card(card)
        
        self.add_to_log(f"\nGame begins! {num_players} players.")
        self.add_to_log(f"Witches: {sum(1 for p in self.players if p.is_witch())}")
        self.add_to_log(f"Townsfolk: {sum(1 for p in self.players if not p.is_witch())}")
        
        # Randomize turn order
        random.shuffle(self.players)
        self.current_player_index = 0
        
        # Return role assignments for server to send to clients
        return {player.id: player.role.value for player in self.players}
        
    def get_current_player(self):
        """Get the player whose turn it is"""
        if self.players and self.current_player_index < len(self.players):
            return self.players[self.current_player_index]
        return None
    
    def next_turn(self):
        """Move to next player's turn"""
        start_index = self.current_player_index
        while True:
            self.current_player_index = (self.current_player_index + 1) % len(self.players)
            if self.players[self.current_player_index].alive:
                break
            if self.current_player_index == start_index:
                break
        
        self.accusation_phase = False
        self.accused_player = None
        self.accused_by = None
        self.votes_cast.clear()
        
        return self.get_current_player()
    
    def draw_card(self, player_id):
        """Player draws a card"""
        player = self._get_player_by_id(player_id)
        if not player or not player.alive:
            return None, "Invalid player"
        
        current = self.get_current_player()
        if player.id != current.id:
            return None, "Not your turn!"
        
        card = self.deck.draw_card()
        if card:
            player.add_card(card)
            message = f"{player.name} draws a card: {card}"
            self.add_to_log(message)
            
            # Apply card effect
            effect_message = card.effect(player, self)
            if effect_message:
                self.add_to_log(effect_message)
            
            return card, message
        else:
            return None, "No cards left in deck!"
    
    def start_accusation(self, player_id, accused_name):
        """Start an accusation against a player"""
        current = self.get_current_player()
        if current.id != player_id:
            return False, "Not your turn!"
        
        if not current or not current.alive:
            return False, "Invalid player turn"
        
        # Find accused player
        accused = None
        for player in self.players:
            if player.name == accused_name and player.alive:
                accused = player
                break
        
        if not accused:
            return False, "Player not found or already eliminated"
        
        if accused == current:
            return False, "Cannot accuse yourself!"
        
        self.accusation_phase = True
        self.accused_player = accused
        self.accused_by = current
        self.votes_cast.clear()
        
        # Reset votes
        for player in self.players:
            player.reset_votes()
        
        message = f"{current.name} accuses {accused.name} of witchcraft!"
        self.add_to_log(message)
        
        return True, message
    
    def cast_vote(self, voter_id, vote_guilty):
        """Cast a vote in an accusation"""
        if not self.accusation_phase:
            return False, "No accusation in progress"
        
        voter = self._get_player_by_id(voter_id)
        if not voter or not voter.alive:
            return False, "Invalid voter"
        
        if voter_id in self.votes_cast:
            return False, "You have already voted!"
        
        self.votes_cast.add(voter_id)
        
        if vote_guilty and self.accused_player:
            self.accused_player.add_vote()
            self.add_to_log(f"{voter.name} votes guilty against {self.accused_player.name}")
            return True, f"{voter.name} votes GUILTY"
        else:
            self.add_to_log(f"{voter.name} votes not guilty")
            return True, f"{voter.name} votes NOT GUILTY"
    
    def resolve_accusation(self):
        """Resolve the current accusation"""
        if not self.accusation_phase or not self.accused_player:
            return False, "No accusation to resolve"
        
        accused = self.accused_player
        alive_players = [p for p in self.players if p.alive]
        votes_needed = len(alive_players) // 2 + 1
        
        if accused.votes >= votes_needed:
            # Accused is eliminated
            accused.eliminate()
            message = f"{accused.name} is found guilty and is eliminated!"
            self.add_to_log(message)
            
            if accused.is_witch():
                self.add_to_log(f"{accused.name} was a Witch!")
            else:
                self.add_to_log(f"{accused.name} was an innocent Townsperson...")
        else:
            message = f"{accused.name} is found not guilty!"
            self.add_to_log(message)
        
        self.accusation_phase = False
        self.accused_player = None
        self.accused_by = None
        
        # Check win condition
        winner = self.check_win_condition()
        
        return True, message, winner
    
    def check_win_condition(self):
        """Check if the game has ended"""
        alive_players = [p for p in self.players if p.alive]
        alive_witches = sum(1 for p in alive_players if p.is_witch())
        alive_townsfolk = len(alive_players) - alive_witches
        
        if alive_witches == 0:
            self.winner = "Town"
            self.add_to_log("\n=== The Town has won! All witches are eliminated! ===")
            return "Town"
        elif alive_witches >= alive_townsfolk:
            self.winner = "Witches"
            self.add_to_log("\n=== The Witches have won! They outnumber the Town! ===")
            return "Witches"
        
        return None
    
    def get_game_state(self, for_player_id=None):
        """Get current game state for display"""
        alive_players = [p for p in self.players if p.alive]
        current = self.get_current_player()
        
        # For a specific player, hide role information of others
        players_data = []
        for player in self.players:
            player_info = {
                'id': player.id,
                'name': player.name,
                'alive': player.alive,
                'is_current': player.id == current.id if current else False
            }
            # Only reveal role to the player themselves or if game is over
            if for_player_id == player.id or self.winner:
                player_info['role'] = player.role.value
            players_data.append(player_info)
        
        state = {
            'players': players_data,
            'alive_players': [p.id for p in alive_players],
            'current_player': current.id if current else None,
            'current_player_name': current.name if current else None,
            'accusation_phase': self.accusation_phase,
            'accused_player': self.accused_player.id if self.accused_player else None,
            'accused_player_name': self.accused_player.name if self.accused_player else None,
            'winner': self.winner,
            'log': self.game_log[-20:],  # Last 20 log entries
            'votes_needed': len(alive_players) // 2 + 1 if self.accusation_phase else 0,
            'votes_cast': len(self.votes_cast),
            'guilty_votes': self.accused_player.votes if self.accused_player else 0
        }
        
        return state
    
    def get_player_hand(self, player_id):
        """Get a player's hand"""
        for player in self.players:
            if player.id == player_id:
                return player.hand
        return []
    
    def get_player_role(self, player_id):
        """Get player's role"""
        for player in self.players:
            if player.id == player_id:
                return player.role.value if player.role else None
        return None
    
    def add_to_log(self, message):
        """Add message to game log"""
        self.game_log.append(message)
        print(message)
    
    def _get_player_by_id(self, player_id):
        """Get player by ID"""
        for player in self.players:
            if player.id == player_id:
                return player
        return None