"""
Role definitions for Salem 1692
"""

from enum import Enum

class Role(Enum):
    """Player roles in the game"""
    TOWNSPERSON = "Townsperson"
    WITCH = "Witch"
    
    def __str__(self):
        return self.value

class RoleManager:
    """Manages role distribution"""
    
    @staticmethod
    def assign_roles(num_players):
        """
        Assign roles to players based on game rules
        
        For Salem 1692:
        - 4-5 players: 2 witches
        - 6-7 players: 3 witches
        - 8-10 players: 4 witches
        - 11-12 players: 5 witches
        """
        roles = []
        
        # Determine number of witches
        if num_players <= 5:
            num_witches = 2
        elif num_players <= 7:
            num_witches = 3
        elif num_players <= 10:
            num_witches = 4
        else:
            num_witches = 5
        
        # Create roles list
        roles.extend([Role.WITCH] * num_witches)
        roles.extend([Role.TOWNSPERSON] * (num_players - num_witches))
        
        return roles