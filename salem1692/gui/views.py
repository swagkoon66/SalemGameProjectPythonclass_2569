"""
GUI Views for Salem 1692
Fixed version - handles dictionaries correctly
"""

import tkinter as tk
from tkinter import ttk, messagebox, scrolledtext
import time
from datetime import datetime

class SetupView(ttk.Frame):
    """Game setup view"""
    
    def __init__(self, parent, app):
        super().__init__(parent)
        self.app = app
        self.player_entries = []
        self.setup_ui()
        
    def setup_ui(self):
        """Setup the UI elements"""
        # Title
        title_frame = ttk.Frame(self)
        title_frame.pack(pady=20)
        
        title_label = ttk.Label(title_frame, text="Salem 1692", 
                                font=('Arial', 24, 'bold'))
        title_label.pack()
        
        subtitle = ttk.Label(title_frame, 
                            text="Accusation & Deception - The Witch Hunt Game",
                            font=('Arial', 12))
        subtitle.pack()
        
        # Player input section
        input_frame = ttk.LabelFrame(self, text="Player Setup", padding=10)
        input_frame.pack(pady=20, padx=50, fill='both')
        
        # Player count selector
        count_frame = ttk.Frame(input_frame)
        count_frame.pack(pady=10)
        
        ttk.Label(count_frame, text="Number of Players:").pack(side='left', padx=5)
        
        self.player_count = tk.IntVar(value=4)
        count_spinbox = ttk.Spinbox(count_frame, from_=4, to=12, 
                                    textvariable=self.player_count,
                                    width=5, command=self.update_player_fields)
        count_spinbox.pack(side='left', padx=5)
        
        ttk.Button(count_frame, text="Update", 
                   command=self.update_player_fields).pack(side='left', padx=5)
        
        # Player name entries
        self.names_frame = ttk.Frame(input_frame)
        self.names_frame.pack(pady=10)
        
        self.update_player_fields()
        
        # Buttons
        button_frame = ttk.Frame(self)
        button_frame.pack(pady=20)
        
        ttk.Button(button_frame, text="Start Game", 
                   command=self.start_game).pack(side='left', padx=10)
        
        ttk.Button(button_frame, text="View History", 
                   command=lambda: self.app.show_history_view()).pack(side='left', padx=10)
        
        # Info label
        info_label = ttk.Label(self, 
                              text="Need 4-12 players. Witches will be assigned automatically.",
                              font=('Arial', 10))
        info_label.pack(pady=10)
        
    def update_player_fields(self):
        """Update player name fields based on count"""
        # Clear existing
        for widget in self.names_frame.winfo_children():
            widget.destroy()
        
        self.player_entries = []
        count = self.player_count.get()
        
        # Create entry fields
        for i in range(count):
            frame = ttk.Frame(self.names_frame)
            frame.pack(pady=5)
            
            ttk.Label(frame, text=f"Player {i+1}:").pack(side='left', padx=5)
            
            entry = ttk.Entry(frame, width=20)
            entry.pack(side='left', padx=5)
            entry.insert(0, f"Player {i+1}")
            
            self.player_entries.append(entry)
            
    def start_game(self):
        """Start the game with entered player names"""
        player_names = []
        for entry in self.player_entries:
            name = entry.get().strip()
            if name:
                player_names.append(name)
            else:
                messagebox.showerror("Error", "Please enter all player names")
                return
        
        # Validate
        from utils.helpers import validate_player_names
        valid, msg = validate_player_names(player_names)
        
        if not valid:
            messagebox.showerror("Error", msg)
            return
        
        self.app.show_game_view(player_names)


class GameView(ttk.Frame):
    """Main game play view"""
    
    def __init__(self, parent, app, game):
        super().__init__(parent)
        self.app = app
        self.game = game
        self.start_time = time.time()
        self.setup_ui()
        self.update_display()
        
    def setup_ui(self):
        """Setup the game UI"""
        # Create paned window for split view
        self.paned = ttk.PanedWindow(self, orient='horizontal')
        self.paned.pack(fill='both', expand=True)
        
        # Left panel - Game info and players
        left_frame = ttk.Frame(self.paned)
        self.paned.add(left_frame, weight=1)
        
        # Game status
        status_frame = ttk.LabelFrame(left_frame, text="Game Status", padding=10)
        status_frame.pack(fill='x', pady=5)
        
        self.current_player_label = ttk.Label(status_frame, text="Current Player: ", 
                                              font=('Arial', 12, 'bold'))
        self.current_player_label.pack()
        
        self.turn_info = ttk.Label(status_frame, text="")
        self.turn_info.pack()
        
        # Players list
        players_frame = ttk.LabelFrame(left_frame, text="Players", padding=10)
        players_frame.pack(fill='both', expand=True, pady=5)
        
        self.players_listbox = tk.Listbox(players_frame, height=10)
        self.players_listbox.pack(fill='both', expand=True)
        
        # Action buttons
        action_frame = ttk.LabelFrame(left_frame, text="Actions", padding=10)
        action_frame.pack(fill='x', pady=5)
        
        self.draw_btn = ttk.Button(action_frame, text="Draw Card", 
                                   command=self.draw_card)
        self.draw_btn.pack(fill='x', pady=2)
        
        self.accuse_btn = ttk.Button(action_frame, text="Accuse Player", 
                                     command=self.show_accuse_dialog)
        self.accuse_btn.pack(fill='x', pady=2)
        
        self.next_btn = ttk.Button(action_frame, text="End Turn", 
                                   command=self.end_turn)
        self.next_btn.pack(fill='x', pady=2)
        
        # Right panel - Game log
        right_frame = ttk.Frame(self.paned)
        self.paned.add(right_frame, weight=1)
        
        log_frame = ttk.LabelFrame(right_frame, text="Game Log", padding=10)
        log_frame.pack(fill='both', expand=True)
        
        self.log_text = scrolledtext.ScrolledText(log_frame, height=20, width=40)
        self.log_text.pack(fill='both', expand=True)
        
        # Hand display (bottom)
        hand_frame = ttk.LabelFrame(self, text="Your Hand", padding=10)
        hand_frame.pack(fill='x', pady=5)
        
        self.hand_text = tk.Text(hand_frame, height=4, width=80)
        self.hand_text.pack(fill='x')
        
    def update_display(self):
        """Update all display elements"""
        try:
            state = self.game.get_game_state()
            
            # Update current player
            current = state.get('current_player')
            current_name = current.name if hasattr(current, 'name') else str(current)
            self.current_player_label.config(text=f"Current Player: {current_name}")
            
            # Update players list - FIXED: Check if player is dict or object
            self.players_listbox.delete(0, tk.END)
            for player in state.get('players', []):
                # Handle both Player objects and dictionaries
                if hasattr(player, 'alive'):  # It's a Player object
                    status = "✓" if player.alive else "✗"
                    name = player.name
                    role_hint = " (W)" if hasattr(player, 'is_witch') and player.is_witch() and player.alive else ""
                else:  # It's a dictionary
                    status = "✓" if player.get('alive', True) else "✗"
                    name = player.get('name', 'Unknown')
                    role_hint = " (W)" if player.get('is_witch', False) and player.get('alive', True) else ""
                
                self.players_listbox.insert(tk.END, f"{status} {name}{role_hint}")
            
            # Update log
            self.log_text.delete(1.0, tk.END)
            for entry in state.get('log', []):
                self.log_text.insert(tk.END, f"{entry}\n")
            self.log_text.see(tk.END)
            
            # Update hand for current player
            if current:
                current_name = current.name if hasattr(current, 'name') else str(current)
                hand = self.game.get_player_hand(current_name)
                self.hand_text.delete(1.0, tk.END)
                if hand:
                    hand_str = "\n".join([f"• {card}" for card in hand])
                    self.hand_text.insert(tk.END, hand_str)
                else:
                    self.hand_text.insert(tk.END, "No cards in hand")
            
            # Check if game ended
            if state.get('winner'):
                duration = int(time.time() - self.start_time)
                self.app.end_game(state['winner'], state.get('players', []), duration)
                return
            
            # Check if in accusation phase
            if state.get('accusation_phase'):
                self.accuse_btn.config(state='disabled')
                self.draw_btn.config(state='disabled')
                
                # Show voting dialog if not already showing
                if not hasattr(self, 'voting_dialog') or self.voting_dialog is None:
                    accused = state.get('accused_player')
                    accused_name = accused.name if hasattr(accused, 'name') else str(accused)
                    self.show_voting_dialog(accused_name)
            else:
                self.accuse_btn.config(state='normal')
                self.draw_btn.config(state='normal')
            
            # Schedule next update
            self.after(1000, self.update_display)
            
        except Exception as e:
            print(f"Error in update_display: {e}")
            import traceback
            traceback.print_exc()
        
    def draw_card(self):
        """Draw a card action"""
        card, message = self.game.draw_card()
        if card:
            messagebox.showinfo("Card Drawn", message)
        else:
            messagebox.showerror("Error", message)
            
    def show_accuse_dialog(self):
        """Show dialog to select player to accuse"""
        state = self.game.get_game_state()
        current = state.get('current_player')
        
        # Get alive players except current
        accusable = []
        for player in state.get('players', []):
            if hasattr(player, 'alive'):
                alive = player.alive
                name = player.name
            else:
                alive = player.get('alive', True)
                name = player.get('name', 'Unknown')
            
            if alive and name != (current.name if hasattr(current, 'name') else str(current)):
                accusable.append(name)
        
        if not accusable:
            messagebox.showinfo("No Targets", "No other players to accuse!")
            return
        
        # Create dialog
        dialog = tk.Toplevel(self)
        dialog.title("Accuse Player")
        dialog.geometry("300x200")
        
        ttk.Label(dialog, text="Select player to accuse:").pack(pady=10)
        
        accused_var = tk.StringVar()
        accused_combo = ttk.Combobox(dialog, textvariable=accused_var, 
                                     values=accusable)
        accused_combo.pack(pady=10)
        
        def confirm():
            if accused_var.get():
                success, message = self.game.start_accusation(accused_var.get())
                if success:
                    messagebox.showinfo("Accusation", message)
                    dialog.destroy()
                else:
                    messagebox.showerror("Error", message)
        
        ttk.Button(dialog, text="Accuse", command=confirm).pack(pady=10)
        
    def show_voting_dialog(self, accused_name):
        """Show voting dialog during accusation phase"""
        self.voting_dialog = tk.Toplevel(self)
        self.voting_dialog.title("Vote!")
        self.voting_dialog.geometry("400x300")
        
        ttk.Label(self.voting_dialog, 
                 text=f"Accusation against {accused_name}!", 
                 font=('Arial', 12, 'bold')).pack(pady=10)
        
        ttk.Label(self.voting_dialog, 
                 text="Cast your vote:").pack(pady=5)
        
        state = self.game.get_game_state()
        self.votes_cast = set()
        
        # Get alive players excluding accused
        voters = []
        for player in state.get('players', []):
            if hasattr(player, 'alive'):
                alive = player.alive
                name = player.name
            else:
                alive = player.get('alive', True)
                name = player.get('name', 'Unknown')
            
            if alive and name != accused_name:
                voters.append(name)
        
        # Create voting buttons for each player
        for voter_name in voters:
            frame = ttk.Frame(self.voting_dialog)
            frame.pack(pady=2)
            
            ttk.Label(frame, text=f"{voter_name}:").pack(side='left', padx=5)
            
            def make_vote_func(v_name):
                def vote_func():
                    if v_name in self.votes_cast:
                        messagebox.showwarning("Already Voted", 
                                              "You have already voted!")
                        return
                    
                    success, msg = self.game.cast_vote(v_name, accused_name)
                    if success:
                        self.votes_cast.add(v_name)
                        messagebox.showinfo("Vote Cast", 
                                          f"{v_name} votes GUILTY!")
                        
                        # Check if all votes are in
                        if len(self.votes_cast) == len(voters):
                            self.resolve_accusation()
                    else:
                        messagebox.showerror("Error", msg)
                
                return vote_func
            
            ttk.Button(frame, text="Vote Guilty", 
                      command=make_vote_func(voter_name)).pack(side='left', padx=5)
        
        # Button to resolve (for testing)
        ttk.Button(self.voting_dialog, text="Resolve Accusation", 
                  command=self.resolve_accusation).pack(pady=20)
        
    def resolve_accusation(self):
        """Resolve the current accusation"""
        success, message = self.game.resolve_accusation()
        if success:
            if hasattr(self, 'voting_dialog') and self.voting_dialog:
                self.voting_dialog.destroy()
                self.voting_dialog = None
            messagebox.showinfo("Accusation Result", message)
        
    def end_turn(self):
        """End current player's turn"""
        if not self.game.accusation_phase:
            self.game.next_turn()
            messagebox.showinfo("Turn End", "Next player's turn!")


class HistoryView(ttk.Frame):
    """Game history view"""
    
    def __init__(self, parent, app, history_data):
        super().__init__(parent)
        self.app = app
        self.history_data = history_data
        self.setup_ui()
        
    def setup_ui(self):
        """Setup the history UI"""
        # Title
        title_label = ttk.Label(self, text="Game History", 
                               font=('Arial', 18, 'bold'))
        title_label.pack(pady=20)
        
        # Treeview for history
        columns = ('Date', 'Winner', 'Players', 'Num Players', 'Witches')
        tree = ttk.Treeview(self, columns=columns, show='headings', height=15)
        
        # Define headings
        for col in columns:
            tree.heading(col, text=col)
            tree.column(col, width=150)
        
        # Add data
        for record in self.history_data:
            tree.insert('', 'end', values=record)
        
        tree.pack(pady=10, padx=20, fill='both', expand=True)
        
        # Back button
        ttk.Button(self, text="Back to Setup", 
                  command=lambda: self.app.show_setup_view()).pack(pady=20)