"""
Main GUI application for Salem 1692
"""

import tkinter as tk
from tkinter import ttk, messagebox
import sys
import os

# Add parent directory to path for imports
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from game_logic import Game
from utils.helpers import save_game_result, get_game_history
from gui.views import SetupView, GameView, HistoryView

class SalemGameApp:
    """Main application class"""
    
    def __init__(self):
        self.root = tk.Tk()
        self.root.title("Salem 1692 - Accusation & Deception")
        self.root.geometry("1000x700")
        self.root.configure(bg='#2c3e50')
        
        self.game = None
        self.current_view = None
        
        self.setup_ui()
        
    def setup_ui(self):
        """Setup the initial UI"""
        # Create main container
        self.main_container = ttk.Frame(self.root)
        self.main_container.pack(fill='both', expand=True, padx=10, pady=10)
        
        # Show setup view
        self.show_setup_view()
        
    def show_setup_view(self):
        """Show the game setup view"""
        self.clear_container()
        self.current_view = SetupView(self.main_container, self)
        self.current_view.pack(fill='both', expand=True)
        
    def show_game_view(self, player_names):
        """Show the main game view"""
        # Create new game
        self.game = Game()
        self.game.setup_game(player_names)
        
        self.clear_container()
        self.current_view = GameView(self.main_container, self, self.game)
        self.current_view.pack(fill='both', expand=True)
        
    def show_history_view(self):
        """Show game history view"""
        history_data = get_game_history()
        
        self.clear_container()
        self.current_view = HistoryView(self.main_container, self, history_data)
        self.current_view.pack(fill='both', expand=True)
        
    def clear_container(self):
        """Clear all widgets from main container"""
        for widget in self.main_container.winfo_children():
            widget.destroy()
            
    def end_game(self, winner, players, duration):
        """Handle game end"""
        # Save game result
        save_game_result(winner, players, duration)
        
        # Show result dialog
        result_msg = f"Game Over!\n{winner} have won the game!"
        messagebox.showinfo("Game Over", result_msg)
        
        # Return to setup
        self.show_setup_view()
        
    def run(self):
        """Start the application"""
        self.root.mainloop()