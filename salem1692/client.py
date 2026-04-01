"""
Salem 1692 - Game Client (Player)
Updated with better connection handling and UI
"""

import tkinter as tk
from tkinter import ttk, messagebox, scrolledtext
import threading
import time
import socket

from network.connection import ClientConnection
from network.protocol import Message, MessageType

class GameClient:
    """Main client class for players"""
    
    def __init__(self):
        self.root = tk.Tk()
        self.root.title("Salem 1692 - Game Client")
        self.root.geometry("900x700")
        self.root.configure(bg='#2c3e50')
        
        self.connection = None
        self.player_id = None
        self.player_name = None
        self.role = None
        self.game_state = None
        self.waiting_for_vote = False
        self.voting_dialog = None
        self.chat_messages = []
        
        self.setup_ui()
        
    def setup_ui(self):
        """Setup the client UI"""
        # Main container
        main_frame = ttk.Frame(self.root)
        main_frame.pack(fill='both', expand=True, padx=10, pady=10)
        
        # Connection section
        conn_frame = ttk.LabelFrame(main_frame, text="Connect to Server", padding=10)
        conn_frame.pack(fill='x', pady=5)
        
        # Server address
        addr_frame = ttk.Frame(conn_frame)
        addr_frame.pack(fill='x', pady=5)
        
        ttk.Label(addr_frame, text="Server IP:").pack(side='left', padx=5)
        self.host_var = tk.StringVar(value="localhost")
        host_entry = ttk.Entry(addr_frame, textvariable=self.host_var, width=15)
        host_entry.pack(side='left', padx=5)
        
        ttk.Label(addr_frame, text="Port:").pack(side='left', padx=5)
        self.port_var = tk.StringVar(value="5555")
        port_entry = ttk.Entry(addr_frame, textvariable=self.port_var, width=8)
        port_entry.pack(side='left', padx=5)
        
        # Player name
        name_frame = ttk.Frame(conn_frame)
        name_frame.pack(fill='x', pady=5)
        
        ttk.Label(name_frame, text="Your Name:").pack(side='left', padx=5)
        self.name_var = tk.StringVar()
        name_entry = ttk.Entry(name_frame, textvariable=self.name_var, width=20)
        name_entry.pack(side='left', padx=5)
        
        self.connect_btn = ttk.Button(conn_frame, text="Connect", command=self.connect_to_server)
        self.connect_btn.pack(pady=5)
        
        # Connection tips
        tips_frame = ttk.LabelFrame(main_frame, text="Connection Tips", padding=5)
        tips_frame.pack(fill='x', pady=5)
        
        tips_text = """
        • Same computer: Use "localhost" or "127.0.0.1"
        • Same Wi-Fi: Use the host's local IP (e.g., 192.168.x.x)
        • Internet: Use host's public IP (requires port forwarding)
        """
        tips_label = ttk.Label(tips_frame, text=tips_text, justify='left', foreground='gray')
        tips_label.pack()
        
        # Game info section
        info_frame = ttk.LabelFrame(main_frame, text="Game Info", padding=10)
        info_frame.pack(fill='x', pady=5)
        
        self.role_label = ttk.Label(info_frame, text="Role: Not connected", font=('Arial', 12, 'bold'))
        self.role_label.pack()
        
        self.turn_label = ttk.Label(info_frame, text="", font=('Arial', 11))
        self.turn_label.pack()
        
        # Players section
        players_frame = ttk.LabelFrame(main_frame, text="Players", padding=10)
        players_frame.pack(fill='x', pady=5)
        
        self.players_listbox = tk.Listbox(players_frame, height=6)
        self.players_listbox.pack(fill='x')
        
        # Action buttons
        action_frame = ttk.LabelFrame(main_frame, text="Actions", padding=10)
        action_frame.pack(fill='x', pady=5)
        
        button_frame = ttk.Frame(action_frame)
        button_frame.pack()
        
        self.draw_btn = ttk.Button(button_frame, text="🎴 Draw Card", command=self.draw_card, state='disabled', width=15)
        self.draw_btn.pack(side='left', padx=5)
        
        self.accuse_btn = ttk.Button(button_frame, text="⚖️ Accuse Player", command=self.accuse_player, state='disabled', width=15)
        self.accuse_btn.pack(side='left', padx=5)
        
        self.end_turn_btn = ttk.Button(button_frame, text="⏭️ End Turn", command=self.end_turn, state='disabled', width=15)
        self.end_turn_btn.pack(side='left', padx=5)
        
        # Hand section
        hand_frame = ttk.LabelFrame(main_frame, text="Your Hand", padding=10)
        hand_frame.pack(fill='x', pady=5)
        
        self.hand_text = tk.Text(hand_frame, height=4, width=80)
        self.hand_text.pack(fill='x')
        
        # Create notebook for chat and log
        notebook = ttk.Notebook(main_frame)
        notebook.pack(fill='both', expand=True, pady=5)
        
        # Chat tab
        chat_frame = ttk.Frame(notebook)
        notebook.add(chat_frame, text="💬 Chat")
        
        self.chat_text = scrolledtext.ScrolledText(chat_frame, height=12)
        self.chat_text.pack(fill='both', expand=True)
        
        chat_input_frame = ttk.Frame(chat_frame)
        chat_input_frame.pack(fill='x', pady=5)
        
        self.chat_entry = ttk.Entry(chat_input_frame)
        self.chat_entry.pack(side='left', fill='x', expand=True, padx=5)
        self.chat_entry.bind('<Return>', lambda e: self.send_chat())
        
        ttk.Button(chat_input_frame, text="Send", command=self.send_chat).pack(side='right', padx=5)
        
        # Game log tab
        log_frame = ttk.Frame(notebook)
        notebook.add(log_frame, text="📜 Game Log")
        
        self.log_text = scrolledtext.ScrolledText(log_frame, height=12)
        self.log_text.pack(fill='both', expand=True)
        
        # Status bar
        self.status_var = tk.StringVar(value="Not connected")
        status_bar = ttk.Label(self.root, textvariable=self.status_var, relief='sunken')
        status_bar.pack(side='bottom', fill='x')
        
    def connect_to_server(self):
        """Connect to the game server"""
        try:
            host = self.host_var.get()
            port = int(self.port_var.get())
            player_name = self.name_var.get().strip()
            
            if not player_name:
                messagebox.showerror("Error", "Please enter your name")
                return
            
            if len(player_name) > 20:
                messagebox.showerror("Error", "Name too long (max 20 characters)")
                return
            
            self.player_name = player_name
            self.connection = ClientConnection(host, port)
            
            if self.connection.connect():
                self.connection.register_handler(self.handle_message)
                self.connection.send(Message(MessageType.CONNECT, {'name': player_name}))
                self.status_var.set(f"Connected to {host}:{port}")
                self.connect_btn.config(state='disabled')
                self.log(f"Connected to server at {host}:{port}")
                self.log("Waiting for game to start...")
                self.add_chat_message("System", "Connected to server. Waiting for host to start the game...")
            else:
                messagebox.showerror("Error", f"Failed to connect to {host}:{port}\nMake sure the server is running and the IP/port is correct.")
        except Exception as e:
            messagebox.showerror("Error", f"Connection error: {e}")
    
    def handle_message(self, message):
        """Handle messages from server"""
        if message.type == MessageType.CONNECT_ACK:
            self.player_id = message.data.get('player_id')
            self.log(f"Connected as {self.player_name} (ID: {self.player_id})")
            # Send join request
            self.connection.send(Message(MessageType.JOIN_GAME, {'name': self.player_name}))
        
        elif message.type == MessageType.GAME_START:
            self.role = message.data.get('role')
            self.player_id = message.data.get('player_id')
            self.role_label.config(text=f"Your Role: {self.role}")
            
            # Show role in popup with dramatic effect
            role_window = tk.Toplevel(self.root)
            role_window.title("Your Role")
            role_window.geometry("400x300")
            role_window.configure(bg='#2c3e50')
            
            # Center the window
            role_window.transient(self.root)
            role_window.grab_set()
            
            role_text = "🔮 WITCH 🔮" if self.role == "Witch" else "🏠 TOWNSPERSON 🏠"
            role_color = "#8e44ad" if self.role == "Witch" else "#27ae60"
            
            ttk.Label(role_window, text=role_text, 
                     font=('Arial', 24, 'bold'), foreground=role_color).pack(pady=30)
            
            ttk.Label(role_window, text="Your secret role in this game:", 
                     font=('Arial', 12)).pack()
            
            if self.role == "Witch":
                ttk.Label(role_window, text="You are a WITCH!\nWork with other witches to eliminate the townsfolk.\nUse deception and strategy to survive!", 
                         wraplength=350, justify='center').pack(pady=20)
            else:
                ttk.Label(role_window, text="You are a TOWNSPERSON!\nFind and eliminate all witches.\nTrust your instincts!", 
                         wraplength=350, justify='center').pack(pady=20)
            
            ttk.Button(role_window, text="I Understand", 
                      command=role_window.destroy).pack(pady=20)
            
            self.log(f"Game started! You are a {self.role}")
            self.enable_controls(True)
            
            # Schedule UI update
            self.root.after(100, self.update_display)
        
        elif message.type == MessageType.GAME_STATE:
            state_data = message.data.get('state', {})
            self.game_state = state_data
            self.update_display()
            
            # Check if it's our turn
            if self.game_state.get('current_player') == self.player_id:
                self.status_var.set("🎯 It's YOUR turn! 🎯")
                self.turn_label.config(text="✨ IT'S YOUR TURN! ✨", foreground='green')
                self.draw_btn.config(state='normal')
                self.accuse_btn.config(state='normal')
                self.end_turn_btn.config(state='normal')
            else:
                current_name = self.game_state.get('current_player_name', 'Someone')
                self.status_var.set(f"Waiting for {current_name}'s turn")
                self.turn_label.config(text=f"Waiting for {current_name}'s turn...", foreground='orange')
                self.draw_btn.config(state='disabled')
                self.accuse_btn.config(state='disabled')
                self.end_turn_btn.config(state='disabled')
            
            # Check if in accusation phase
            if self.game_state.get('accusation_phase'):
                accused = self.game_state.get('accused_player_name')
                if accused and not self.waiting_for_vote:
                    self.show_voting_dialog(accused)
        
        elif message.type == MessageType.DRAW_CARD:
            if message.data.get('success'):
                messagebox.showinfo("Card Drawn", message.data.get('message'))
                self.log(message.data.get('message'))
            else:
                messagebox.showerror("Error", message.data.get('message'))
        
        elif message.type == MessageType.ACCUSE:
            if message.data.get('success'):
                self.log(message.data.get('message'))
            else:
                messagebox.showerror("Error", message.data.get('message'))
        
        elif message.type == MessageType.VOTE:
            self.log(message.data.get('message'))
        
        elif message.type == MessageType.RESOLVE_ACCUSATION:
            self.log(message.data.get('message'))
            self.waiting_for_vote = False
            if self.voting_dialog:
                self.voting_dialog.destroy()
                self.voting_dialog = None
        
        elif message.type == MessageType.GAME_OVER:
            winner = message.data.get('winner')
            self.log(f"🏆 GAME OVER! {winner} wins! 🏆")
            
            result_msg = f"Game Over!\n{winner} wins!\n\n"
            if winner == "Witches" and self.role == "Witch":
                result_msg += "Congratulations! Your coven has triumphed!"
            elif winner == "Town" and self.role == "Townsperson":
                result_msg += "Well done! You've cleansed Salem of witches!"
            else:
                result_msg += "Better luck next time!"
            
            messagebox.showinfo("Game Over", result_msg)
            self.enable_controls(False)
            self.role_label.config(text=f"Game Over - {winner} wins!")
        
        elif message.type == MessageType.CHAT_MESSAGE:
            text = message.data.get('text', '')
            self.add_chat_message(None, text)
        
        elif message.type == MessageType.PLAYER_LIST:
            players = message.data.get('players', [])
            self.update_players_list(players)
    
    def update_display(self):
        """Update UI with current game state"""
        if not self.game_state:
            return
        
        # Update game log
        if 'log' in self.game_state:
            self.log_text.delete(1.0, tk.END)
            for entry in self.game_state['log']:
                self.log_text.insert(tk.END, f"{entry}\n")
            self.log_text.see(tk.END)
        
        # Update hand
        if 'hand' in self.game_state:
            self.hand_text.delete(1.0, tk.END)
            if self.game_state['hand']:
                hand_str = "\n".join([f"• {card}" for card in self.game_state['hand']])
                self.hand_text.insert(tk.END, hand_str)
            else:
                self.hand_text.insert(tk.END, "No cards in hand")
        
        # Update voting info
        if 'voting_info' in self.game_state:
            info = self.game_state['voting_info']
            votes_needed = self.game_state.get('votes_needed', 0)
            if votes_needed > 0:
                self.status_var.set(f"Voting: {info['guilty_votes']}/{votes_needed} guilty votes needed")
    
    def update_players_list(self, players):
        """Update players list display"""
        self.players_listbox.delete(0, tk.END)
        for player in players:
            # Check if player is alive
            alive = True
            if self.game_state:
                for p in self.game_state.get('players', []):
                    if p.get('id') == player['id']:
                        alive = p.get('alive', True)
                        break
            
            # Determine marker
            if self.game_state and self.game_state.get('current_player') == player['id']:
                marker = "👉"
            elif not alive:
                marker = "💀"
            else:
                marker = "  "
            
            status = "✓" if alive else "✗"
            name = player['name']
            
            # Add role hint for self
            if player['id'] == self.player_id and self.role:
                role_hint = f" ({self.role[0]})"
            else:
                role_hint = ""
            
            self.players_listbox.insert(tk.END, f"{marker} {status} {name}{role_hint}")
    
    def draw_card(self):
        """Draw a card"""
        self.connection.send(Message(MessageType.DRAW_CARD))
        self.draw_btn.config(state='disabled')
        self.status_var.set("Drawing card...")
    
    def accuse_player(self):
        """Show dialog to accuse a player"""
        if not self.game_state:
            return
        
        # Get alive players except self
        players = []
        for player in self.game_state.get('players', []):
            if player.get('alive', False) and player.get('id') != self.player_id:
                players.append(player.get('name'))
        
        if not players:
            messagebox.showinfo("No Targets", "No other players to accuse!")
            return
        
        dialog = tk.Toplevel(self.root)
        dialog.title("Accuse Player")
        dialog.geometry("350x200")
        dialog.transient(self.root)
        
        ttk.Label(dialog, text="Select player to accuse:", 
                 font=('Arial', 11)).pack(pady=15)
        
        accused_var = tk.StringVar()
        accused_combo = ttk.Combobox(dialog, textvariable=accused_var, 
                                     values=players, width=20)
        accused_combo.pack(pady=10)
        
        def confirm():
            if accused_var.get():
                self.connection.send(Message(MessageType.ACCUSE, 
                                            {'accused': accused_var.get()}))
                self.status_var.set(f"Accusing {accused_var.get()}...")
                dialog.destroy()
        
        ttk.Button(dialog, text="⚖️ Accuse", command=confirm).pack(pady=15)
    
    def show_voting_dialog(self, accused_name):
        """Show voting dialog"""
        self.waiting_for_vote = True
        
        self.voting_dialog = tk.Toplevel(self.root)
        self.voting_dialog.title("Vote!")
        self.voting_dialog.geometry("400x200")
        self.voting_dialog.transient(self.root)
        
        # Make it stay on top
        self.voting_dialog.grab_set()
        
        ttk.Label(self.voting_dialog, text=f"⚖️ {accused_name} is on trial! ⚖️", 
                 font=('Arial', 12, 'bold')).pack(pady=15)
        
        ttk.Label(self.voting_dialog, text="Do you believe they are a witch?", 
                 font=('Arial', 11)).pack(pady=10)
        
        button_frame = ttk.Frame(self.voting_dialog)
        button_frame.pack(pady=20)
        
        def vote(guilty):
            self.connection.send(Message(MessageType.VOTE, {'guilty': guilty}))
            self.status_var.set(f"Voted {'GUILTY' if guilty else 'NOT GUILTY'}")
            self.voting_dialog.destroy()
            self.voting_dialog = None
            self.waiting_for_vote = False
        
        ttk.Button(button_frame, text="🔴 GUILTY", 
                  command=lambda: vote(True),
                  width=15).pack(side='left', padx=10)
        
        ttk.Button(button_frame, text="🟢 NOT GUILTY", 
                  command=lambda: vote(False),
                  width=15).pack(side='left', padx=10)
    
    def end_turn(self):
        """End current player's turn"""
        self.connection.send(Message(MessageType.NEXT_TURN))
        self.draw_btn.config(state='disabled')
        self.accuse_btn.config(state='disabled')
        self.end_turn_btn.config(state='disabled')
        self.status_var.set("Turn ended")
        self.log("You ended your turn")
    
    def send_chat(self):
        """Send chat message"""
        text = self.chat_entry.get().strip()
        if text:
            self.connection.send(Message(MessageType.CHAT_MESSAGE, {'text': text}))
            self.add_chat_message("You", text)
            self.chat_entry.delete(0, tk.END)
    
    def add_chat_message(self, sender, message):
        """Add message to chat"""
        if sender:
            self.chat_text.insert(tk.END, f"{sender}: {message}\n")
        else:
            self.chat_text.insert(tk.END, f"{message}\n")
        self.chat_text.see(tk.END)
    
    def enable_controls(self, enabled):
        """Enable/disable game controls"""
        # Buttons are enabled/disabled based on turn, so we don't set them here
        pass
    
    def log(self, message):
        """Add message to log"""
        timestamp = time.strftime('%H:%M:%S')
        self.log_text.insert(tk.END, f"[{timestamp}] {message}\n")
        self.log_text.see(tk.END)
    
    def run(self):
        """Run the client application"""
        self.root.mainloop()

if __name__ == "__main__":
    client = GameClient()
    client.run()