"""
Salem 1692 - Game Server (Host)
Updated with IP detection and better connection handling
"""

import tkinter as tk
from tkinter import ttk, messagebox, scrolledtext
import threading
import time
import socket

from network.connection import ServerConnection
from network.protocol import Message, MessageType
from game_logic.game import Game

def get_local_ip():
    """Get the local IP address of this computer"""
    try:
        # Create a socket to find the local IP
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        s.connect(("8.8.8.8", 80))
        ip = s.getsockname()[0]
        s.close()
        return ip
    except:
        # Fallback methods
        try:
            hostname = socket.gethostname()
            ip = socket.gethostbyname(hostname)
            if ip.startswith('127.'):
                return "Unable to detect - check network"
            return ip
        except:
            return "127.0.0.1"

class GameServer:
    """Main server class for hosting the game"""
    
    def __init__(self):
        self.root = tk.Tk()
        self.root.title("Salem 1692 - Game Server (Host)")
        self.root.geometry("850x700")
        self.root.configure(bg='#2c3e50')
        
        self.server = None
        self.game = None
        self.players_ready = {}
        self.game_started = False
        self.voting_in_progress = False
        
        self.setup_ui()
        
    def setup_ui(self):
        """Setup the server UI"""
        # Main container
        main_frame = ttk.Frame(self.root)
        main_frame.pack(fill='both', expand=True, padx=10, pady=10)
        
        # Server control section
        control_frame = ttk.LabelFrame(main_frame, text="Server Control", padding=10)
        control_frame.pack(fill='x', pady=5)
        
        # Port selection
        port_frame = ttk.Frame(control_frame)
        port_frame.pack(fill='x', pady=5)
        
        ttk.Label(port_frame, text="Port:").pack(side='left', padx=5)
        self.port_var = tk.StringVar(value="5555")
        port_entry = ttk.Entry(port_frame, textvariable=self.port_var, width=10)
        port_entry.pack(side='left', padx=5)
        
        self.start_btn = ttk.Button(control_frame, text="Start Server", command=self.start_server)
        self.start_btn.pack(pady=5)
        
        self.stop_btn = ttk.Button(control_frame, text="Stop Server", command=self.stop_server, state='disabled')
        self.stop_btn.pack(pady=5)
        
        self.start_game_btn = ttk.Button(control_frame, text="Start Game", command=self.start_game, state='disabled')
        self.start_game_btn.pack(pady=5)
        
        # Connection Info Section
        info_frame = ttk.LabelFrame(main_frame, text="Connection Information", padding=10)
        info_frame.pack(fill='x', pady=5)
        
        self.local_ip = get_local_ip()
        
        ip_label = ttk.Label(info_frame, text=f"Your Local IP Address: {self.local_ip}", 
                            font=('Arial', 10, 'bold'), foreground='blue')
        ip_label.pack(pady=2)
        
        ttk.Label(info_frame, text=f"Port: {self.port_var.get()}", font=('Arial', 10)).pack(pady=2)
        
        tips_text = """
        Connection Tips:
        • Players on SAME computer: Use "localhost" or "127.0.0.1"
        • Players on SAME Wi-Fi: Use the IP address shown above
        • Players over INTERNET: Need port forwarding, then use your public IP
        """
        tips_label = ttk.Label(info_frame, text=tips_text, justify='left', foreground='gray')
        tips_label.pack(pady=5)
        
        # Players section
        players_frame = ttk.LabelFrame(main_frame, text="Connected Players", padding=10)
        players_frame.pack(fill='x', pady=5)
        
        self.players_listbox = tk.Listbox(players_frame, height=8)
        self.players_listbox.pack(fill='x')
        
        # Player count label
        self.player_count_var = tk.StringVar(value="Players: 0")
        ttk.Label(players_frame, textvariable=self.player_count_var).pack(pady=2)
        
        # Game log section
        log_frame = ttk.LabelFrame(main_frame, text="Game Log", padding=10)
        log_frame.pack(fill='both', expand=True, pady=5)
        
        self.log_text = scrolledtext.ScrolledText(log_frame, height=15, width=80)
        self.log_text.pack(fill='both', expand=True)
        
        # Status bar
        self.status_var = tk.StringVar(value="Server not started")
        status_bar = ttk.Label(self.root, textvariable=self.status_var, relief='sunken')
        status_bar.pack(side='bottom', fill='x')
        
    def start_server(self):
        """Start the game server"""
        try:
            port = int(self.port_var.get())
            self.server = ServerConnection(port=port)
            
            if self.server.start():
                self.server.message_handler = self.handle_client_message
                self.status_var.set(f"Server running on port {port} - IP: {self.local_ip}")
                self.start_btn.config(state='disabled')
                self.stop_btn.config(state='normal')
                self.log("=" * 50)
                self.log("Server started successfully!")
                self.log(f"Local IP: {self.local_ip}")
                self.log(f"Port: {port}")
                self.log("Waiting for players to connect...")
                self.log("=" * 50)
            else:
                messagebox.showerror("Error", "Failed to start server")
        except Exception as e:
            messagebox.showerror("Error", f"Failed to start server: {e}")
    
    def stop_server(self):
        """Stop the game server"""
        if self.server:
            self.server.stop()
            self.server = None
        self.status_var.set("Server stopped")
        self.start_btn.config(state='normal')
        self.stop_btn.config(state='disabled')
        self.start_game_btn.config(state='disabled')
        self.players_listbox.delete(0, tk.END)
        self.player_count_var.set("Players: 0")
        self.players_ready.clear()
        self.game_started = False
        self.voting_in_progress = False
        self.log("Server stopped")
    
    def start_game(self):
        """Start the game with connected players"""
        if len(self.server.clients) < 4:
            messagebox.showwarning("Not Enough Players", 
                                  f"Need at least 4 players to start. Currently: {len(self.server.clients)} players")
            return
        
        if len(self.server.clients) > 12:
            messagebox.showwarning("Too Many Players", 
                                  f"Maximum 12 players allowed. Currently: {len(self.server.clients)} players")
            return
        
        # Create game with connected players
        player_names = []
        player_ids = []
        for client_id, client in self.server.clients.items():
            player_names.append(client['name'])
            player_ids.append(client_id)
        
        self.game = Game()
        role_assignments = self.game.setup_game(player_names, player_ids)
        
        # Send role assignments to each player
        for client_id in self.server.clients:
            role = role_assignments.get(client_id)
            self.server.send_to_client(client_id, Message(MessageType.GAME_START, {
                'role': role,
                'player_id': client_id,
                'player_name': self.server.get_client_name(client_id),
                'all_players': [{'id': pid, 'name': name} for pid, name in 
                               zip(player_ids, player_names)]
            }))
        
        self.game_started = True
        self.start_game_btn.config(state='disabled')
        
        # Send initial game state
        self.broadcast_game_state()
        self.log("=" * 50)
        self.log("Game started!")
        self.log(f"Players: {', '.join(player_names)}")
        witches = sum(1 for p in self.game.players if p.is_witch())
        self.log(f"Witches: {witches}, Townsfolk: {len(player_names) - witches}")
        self.log("=" * 50)
        
        # Announce first player
        current = self.game.get_current_player()
        if current:
            self.log(f"First turn: {current.name}")
    
    def handle_client_message(self, client_id, message):
        """Handle messages from clients"""
        if message.type == MessageType.JOIN_GAME:
            # Player wants to join
            player_name = message.data.get('name', f'Player{client_id}')
            self.players_ready[client_id] = {'name': player_name, 'ready': False}
            self.update_players_list()
            self.log(f"✓ {player_name} joined the game")
            
            # Send player list to all
            self.broadcast_player_list()
            
            # Enable start game button if enough players
            if len(self.server.clients) >= 4:
                self.start_game_btn.config(state='normal')
                self.log(f"Ready to start! {len(self.server.clients)} players connected")
        
        elif message.type == MessageType.DRAW_CARD:
            if self.game_started and self.game and not self.voting_in_progress:
                card, result = self.game.draw_card(client_id)
                self.server.send_to_client(client_id, Message(MessageType.DRAW_CARD, {
                    'success': card is not None,
                    'message': result,
                    'card': str(card) if card else None
                }))
                self.broadcast_game_state()
                self.log(f"Player drew a card")
        
        elif message.type == MessageType.ACCUSE:
            if self.game_started and self.game and not self.voting_in_progress:
                accused_name = message.data.get('accused')
                success, result = self.game.start_accusation(client_id, accused_name)
                self.server.send_to_client(client_id, Message(MessageType.ACCUSE, {
                    'success': success,
                    'message': result
                }))
                if success:
                    self.log(f"Accusation started: {self.server.get_client_name(client_id)} accuses {accused_name}")
                    self.broadcast_game_state()
                    # Start voting phase
                    self.start_voting_phase()
        
        elif message.type == MessageType.VOTE:
            if self.game_started and self.game and self.voting_in_progress:
                vote_guilty = message.data.get('guilty', False)
                success, result = self.game.cast_vote(client_id, vote_guilty)
                self.server.send_to_client(client_id, Message(MessageType.VOTE, {
                    'success': success,
                    'message': result
                }))
                if success:
                    self.broadcast_game_state()
                    self.log(f"Vote cast by {self.server.get_client_name(client_id)}")
                    
                    # Check if all votes are in
                    alive_players = [p for p in self.game.players if p.alive]
                    voters_needed = len(alive_players) - 1  # Exclude the accused
                    
                    if len(self.game.votes_cast) >= voters_needed:
                        self.resolve_accusation()
        
        elif message.type == MessageType.NEXT_TURN:
            if self.game_started and self.game and not self.voting_in_progress:
                next_player = self.game.next_turn()
                if next_player:
                    self.log(f"Turn ended. Now it's {next_player.name}'s turn")
                self.broadcast_game_state()
        
        elif message.type == MessageType.CHAT_MESSAGE:
            text = message.data.get('text', '')
            player_name = self.server.get_client_name(client_id)
            self.broadcast(Message(MessageType.CHAT_MESSAGE, {
                'text': f"{player_name}: {text}"
            }))
            self.log(f"{player_name}: {text}")
    
    def start_voting_phase(self):
        """Start the voting phase for an accusation"""
        self.voting_in_progress = True
        state = self.game.get_game_state()
        accused_name = state.get('accused_player_name')
        accused_by = state.get('accused_by_name') if 'accused_by_name' in state else "Someone"
        
        self.broadcast(Message(MessageType.CHAT_MESSAGE, {
            'text': f"🔔 VOTING PHASE - {accused_name} has been accused by {accused_by}! All players must vote! 🔔"
        }))
        
        self.log(f"VOTING PHASE: {accused_name} is on trial")
        
        # Send voting prompt to all alive players except the accused
        for client_id in self.server.clients:
            player = self.game._get_player_by_id(client_id)
            if player and player.alive and client_id != self.game.accused_player.id:
                self.server.send_to_client(client_id, Message(MessageType.GAME_STATE, {
                    'state': 'voting',
                    'accused': accused_name,
                    'accused_by': self.game.accused_by.name if self.game.accused_by else "Someone"
                }))
    
    def resolve_accusation(self):
        """Resolve the current accusation"""
        success, message, winner = self.game.resolve_accusation()
        
        self.broadcast(Message(MessageType.RESOLVE_ACCUSATION, {
            'message': message,
            'eliminated_player': self.game.accused_player.name if self.game.accused_player else None
        }))
        
        self.log(message)
        
        if winner:
            # Game over
            self.broadcast(Message(MessageType.GAME_OVER, {
                'winner': winner
            }))
            self.log(f"🏆 GAME OVER! {winner} wins! 🏆")
            self.game_started = False
            self.voting_in_progress = False
        else:
            self.voting_in_progress = False
        
        self.broadcast_game_state()
    
    def broadcast_game_state(self):
        """Send current game state to all players"""
        for client_id in self.server.clients:
            state = self.game.get_game_state(for_player_id=client_id)
            # Add player's hand for this client
            state['hand'] = [str(card) for card in self.game.get_player_hand(client_id)]
            # Add voting info
            if self.voting_in_progress and self.game.accused_player:
                state['voting_info'] = {
                    'accused': self.game.accused_player.name,
                    'votes_cast': len(self.game.votes_cast),
                    'guilty_votes': self.game.accused_player.votes if self.game.accused_player else 0
                }
            self.server.send_to_client(client_id, Message(MessageType.GAME_STATE, {
                'state': state
            }))
    
    def broadcast_player_list(self):
        """Send player list to all clients"""
        players = []
        for client_id, client in self.server.clients.items():
            players.append({
                'id': client_id,
                'name': client['name']
            })
        
        self.broadcast(Message(MessageType.PLAYER_LIST, {'players': players}))
    
    def broadcast(self, message):
        """Broadcast message to all clients"""
        if self.server:
            self.server.broadcast(message)
    
    def update_players_list(self):
        """Update the players list in UI"""
        self.players_listbox.delete(0, tk.END)
        for client_id, client in self.server.clients.items():
            ready_status = "✓" if self.players_ready.get(client_id, {}).get('ready', False) else "○"
            self.players_listbox.insert(tk.END, f"{ready_status} {client['name']}")
        self.player_count_var.set(f"Players: {len(self.server.clients)}")
    
    def log(self, message):
        """Add message to log"""
        timestamp = time.strftime('%H:%M:%S')
        self.log_text.insert(tk.END, f"[{timestamp}] {message}\n")
        self.log_text.see(tk.END)
        self.root.update_idletasks()
    
    def run(self):
        """Run the server application"""
        self.root.mainloop()

if __name__ == "__main__":
    server = GameServer()
    server.run()