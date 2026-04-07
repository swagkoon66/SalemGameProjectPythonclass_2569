"""
Salem 1692 - Combined Launcher
One device can host a server AND join as a player simultaneously.
"""

import tkinter as tk
from tkinter import ttk, messagebox, scrolledtext
import threading
import time
import socket
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from network.connection import ServerConnection, ClientConnection
from network.protocol import Message, MessageType
from game_logic.game import Game


# ─────────────────────────────────────────────
#  Helpers
# ─────────────────────────────────────────────

def get_local_ip():
    try:
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        s.connect(("8.8.8.8", 80))
        ip = s.getsockname()[0]
        s.close()
        return ip
    except Exception:
        try:
            hostname = socket.gethostname()
            ip = socket.gethostbyname(hostname)
            return ip if not ip.startswith("127.") else "Unable to detect"
        except Exception:
            return "127.0.0.1"


# ─────────────────────────────────────────────
#  Game Window (pops up on each client when game starts)
# ─────────────────────────────────────────────

class GameWindow:
    """
    Full-screen game popup that opens on every player's device
    when the host starts the game.  All in-game interaction
    (draw, accuse, vote, end turn, chat) happens here.
    """

    def __init__(self, root, launcher, role, player_id, player_name, all_players):
        self.root = root
        self.launcher = launcher
        self.role = role
        self.player_id = player_id
        self.player_name = player_name
        self.all_players = all_players
        self.game_state = {}
        self.waiting_for_vote = False
        self.voting_dialog = None

        self.win = tk.Toplevel(root)
        self.win.title(f"Salem 1692 – {player_name}")
        self.win.geometry("1000x750")
        self.win.protocol("WM_DELETE_WINDOW", self._on_close)

        self._build_ui()
        self._show_role_reveal()

    # ── UI ──────────────────────────────────────

    def _build_ui(self):
        top = tk.Frame(self.win, bg="#2c3e50", pady=6)
        top.pack(fill="x")

        is_witch = self.role == "Witch"
        role_color = "#e74c3c" if is_witch else "#27ae60"
        role_icon  = "🔮" if is_witch else "🏠"
        tk.Label(top, text=f"Salem 1692   {role_icon} {self.role}",
                 bg="#2c3e50", fg=role_color,
                 font=("Arial", 14, "bold")).pack(side="left", padx=12)

        self.status_lbl = tk.Label(top, text="Waiting for game…",
                                   bg="#2c3e50", fg="white",
                                   font=("Arial", 11))
        self.status_lbl.pack(side="left", padx=20)

        pane = ttk.PanedWindow(self.win, orient="horizontal")
        pane.pack(fill="both", expand=True, padx=6, pady=4)

        left = ttk.Frame(pane)
        pane.add(left, weight=1)

        pf = ttk.LabelFrame(left, text="Players", padding=6)
        pf.pack(fill="both", expand=True, pady=4)
        self.players_lb = tk.Listbox(pf, font=("Courier", 10))
        self.players_lb.pack(fill="both", expand=True)

        hf = ttk.LabelFrame(left, text="Your Hand", padding=6)
        hf.pack(fill="x", pady=4)
        self.hand_lb = tk.Listbox(hf, height=5, font=("Courier", 10))
        self.hand_lb.pack(fill="x")

        af = ttk.LabelFrame(left, text="Actions", padding=6)
        af.pack(fill="x", pady=4)
        btn_row = ttk.Frame(af)
        btn_row.pack()
        self.draw_btn   = ttk.Button(btn_row, text="🎴 Draw Card", command=self._draw_card,  state="disabled", width=14)
        self.accuse_btn = ttk.Button(btn_row, text="⚖️ Accuse",    command=self._accuse,      state="disabled", width=14)
        self.end_btn    = ttk.Button(btn_row, text="⏭ End Turn",  command=self._end_turn,    state="disabled", width=14)
        self.draw_btn.pack(side="left", padx=3, pady=4)
        self.accuse_btn.pack(side="left", padx=3, pady=4)
        self.end_btn.pack(side="left", padx=3, pady=4)

        right = ttk.Frame(pane)
        pane.add(right, weight=1)

        lf = ttk.LabelFrame(right, text="Game Log", padding=6)
        lf.pack(fill="both", expand=True, pady=4)
        self.log_text = scrolledtext.ScrolledText(lf, height=18, state="disabled",
                                                  font=("Courier", 9))
        self.log_text.pack(fill="both", expand=True)

        cf = ttk.LabelFrame(right, text="Chat", padding=6)
        cf.pack(fill="x", pady=4)
        chat_input_row = ttk.Frame(cf)
        chat_input_row.pack(side="bottom", fill="x", pady=3)
        self.chat_entry = ttk.Entry(chat_input_row)
        self.chat_entry.pack(side="left", fill="x", expand=True, padx=4)
        self.chat_entry.bind("<Return>", lambda e: self._send_chat())
        ttk.Button(chat_input_row, text="Send", command=self._send_chat).pack(side="right", padx=4)
        self.chat_text = scrolledtext.ScrolledText(cf, height=8, state="disabled",
                                                   font=("Courier", 9))
        self.chat_text.pack(fill="both", expand=True)

    def _show_role_reveal(self):
        r = tk.Toplevel(self.win)
        r.title("Your Role")
        r.geometry("420x320")
        r.configure(bg="#2c3e50")
        r.transient(self.win)
        r.grab_set()
        is_witch = self.role == "Witch"
        tk.Label(r, text="🔮 WITCH 🔮" if is_witch else "🏠 TOWNSPERSON 🏠",
                 bg="#2c3e50",
                 fg="#e74c3c" if is_witch else "#27ae60",
                 font=("Arial", 26, "bold")).pack(pady=30)
        desc = ("You are a WITCH!\nWork with your coven to eliminate townsfolk.\nUse deception to survive!"
                if is_witch else
                "You are a TOWNSPERSON!\nFind and eliminate all witches.\nTrust your instincts!")
        tk.Label(r, text=desc, bg="#2c3e50", fg="white",
                 wraplength=370, justify="center", font=("Arial", 12)).pack(pady=10)
        ttk.Button(r, text="I Understand", command=r.destroy).pack(pady=20)

    # ── State updates ────────────────────────────

    def update_state(self, state):
        self.game_state = state
        self._refresh_players()
        self._refresh_hand()
        self._refresh_log()
        self._refresh_turn()
        if state.get("accusation_phase"):
            accused = state.get("accused_player_name")
            if accused and not self.waiting_for_vote:
                self.win.after(100, self._show_voting_dialog, accused)

    def _refresh_players(self):
        self.players_lb.delete(0, tk.END)
        current_id = self.game_state.get("current_player")
        for p in self.game_state.get("players", []):
            pid   = p.get("id")
            name  = p.get("name", "?")
            alive = p.get("alive", True)
            marker = "👉" if pid == current_id else ("💀" if not alive else "  ")
            tag = " (You)" if pid == self.player_id else ""
            self.players_lb.insert(tk.END, f"{marker} {'✓' if alive else '✗'} {name}{tag}")

    def _refresh_hand(self):
        self.hand_lb.delete(0, tk.END)
        hand = self.game_state.get("hand", [])
        for card in hand:
            self.hand_lb.insert(tk.END, f"  {card}")
        if not hand:
            self.hand_lb.insert(tk.END, "  (no cards)")

    def _refresh_log(self):
        self.log_text.config(state="normal")
        self.log_text.delete(1.0, tk.END)
        for entry in self.game_state.get("log", []):
            self.log_text.insert(tk.END, f"{entry}\n")
        self.log_text.see(tk.END)
        self.log_text.config(state="disabled")

    def _refresh_turn(self):
        current_id = self.game_state.get("current_player")
        if current_id == self.player_id:
            self.status_lbl.config(text="🎯 IT'S YOUR TURN!", fg="#f1c40f")
            self.draw_btn.config(state="normal")
            self.accuse_btn.config(state="normal")
            self.end_btn.config(state="normal")
        else:
            cur_name = self.game_state.get("current_player_name", "…")
            self.status_lbl.config(text=f"Waiting for {cur_name}…", fg="white")
            self.draw_btn.config(state="disabled")
            self.accuse_btn.config(state="disabled")
            self.end_btn.config(state="disabled")

    # ── Actions ──────────────────────────────────

    def _draw_card(self):
        self.launcher.connection.send(Message(MessageType.DRAW_CARD))
        self.draw_btn.config(state="disabled")

    def _accuse(self):
        players = [p["name"] for p in self.game_state.get("players", [])
                   if p.get("alive") and p.get("id") != self.player_id]
        if not players:
            messagebox.showinfo("No Targets", "No other players to accuse!", parent=self.win)
            return
        dlg = tk.Toplevel(self.win)
        dlg.title("Accuse Player")
        dlg.geometry("350x200")
        dlg.transient(self.win)
        ttk.Label(dlg, text="Select player to accuse:", font=("Arial", 11)).pack(pady=15)
        accused_var = tk.StringVar()
        ttk.Combobox(dlg, textvariable=accused_var, values=players, width=20).pack(pady=10)
        def confirm():
            if accused_var.get():
                self.launcher.connection.send(Message(MessageType.ACCUSE, {"accused": accused_var.get()}))
                dlg.destroy()
        ttk.Button(dlg, text="⚖️ Accuse", command=confirm).pack(pady=15)

    def _end_turn(self):
        self.launcher.connection.send(Message(MessageType.NEXT_TURN))
        self.draw_btn.config(state="disabled")
        self.accuse_btn.config(state="disabled")
        self.end_btn.config(state="disabled")
        self.status_lbl.config(text="Turn ended…", fg="white")

    def _show_voting_dialog(self, accused_name):
        if self.waiting_for_vote:
            return
        self.waiting_for_vote = True
        self.voting_dialog = tk.Toplevel(self.win)
        self.voting_dialog.title("Vote!")
        self.voting_dialog.geometry("420x220")
        self.voting_dialog.transient(self.win)
        self.voting_dialog.grab_set()
        ttk.Label(self.voting_dialog, text=f"⚖️  {accused_name} is on trial!  ⚖️",
                  font=("Arial", 13, "bold")).pack(pady=18)
        ttk.Label(self.voting_dialog, text="Do you believe they are a witch?",
                  font=("Arial", 11)).pack(pady=6)
        bf = ttk.Frame(self.voting_dialog)
        bf.pack(pady=18)
        def vote(guilty):
            self.launcher.connection.send(Message(MessageType.VOTE, {"guilty": guilty}))
            if self.voting_dialog:
                self.voting_dialog.destroy()
                self.voting_dialog = None
            self.waiting_for_vote = False
        ttk.Button(bf, text="🔴 GUILTY",     command=lambda: vote(True),  width=16).pack(side="left", padx=10)
        ttk.Button(bf, text="🟢 NOT GUILTY", command=lambda: vote(False), width=16).pack(side="left", padx=10)

    def close_voting(self):
        self.waiting_for_vote = False
        if self.voting_dialog:
            try:
                self.voting_dialog.destroy()
            except Exception:
                pass
            self.voting_dialog = None

    # ── Chat ─────────────────────────────────────

    def add_chat(self, sender, msg):
        self.chat_text.config(state="normal")
        self.chat_text.insert(tk.END, f"{sender}: {msg}\n" if sender else f"{msg}\n")
        self.chat_text.see(tk.END)
        self.chat_text.config(state="disabled")

    def _send_chat(self):
        text = self.chat_entry.get().strip()
        if text and self.launcher.connection:
            self.launcher.connection.send(Message(MessageType.CHAT_MESSAGE, {"text": text}))
            self.chat_entry.delete(0, tk.END)

    # ── Game over / close ────────────────────────

    def show_game_over(self, winner):
        msg = f"Game Over!\n{winner} wins!\n\n"
        if winner == "Witches" and self.role == "Witch":
            msg += "Congratulations! Your coven triumphed! 🔮"
        elif winner == "Town" and self.role == "Townsperson":
            msg += "Well done! Salem is cleansed! 🏠"
        else:
            msg += "Better luck next time!"
        messagebox.showinfo("Game Over", msg, parent=self.win)
        self.draw_btn.config(state="disabled")
        self.accuse_btn.config(state="disabled")
        self.end_btn.config(state="disabled")
        self.status_lbl.config(text=f"🏆 {winner} wins!", fg="#f39c12")

    def _on_close(self):
        self.win.withdraw()

    def destroy(self):
        try:
            self.win.destroy()
        except Exception:
            pass


# ─────────────────────────────────────────────
#  Main application window
# ─────────────────────────────────────────────

class SalemLauncher:
    """
    Single window that holds both a Host panel (server) and a
    Player panel (client) as notebook tabs.  Both can be active
    at the same time so one machine can host *and* play.
    """

    def __init__(self):
        self.root = tk.Tk()
        self.root.title("Salem 1692 – Launcher")
        self.root.geometry("960x780")
        self.root.configure(bg="#2c3e50")

        self.local_ip = get_local_ip()

        # ── server state ──
        self.server = None
        self.game = None
        self.players_ready = {}
        self.game_started = False
        self.voting_in_progress = False

        # ── client state ──
        self.connection = None
        self.player_id = None
        self.player_name = None
        self.role = None
        self.game_state = None
        self.waiting_for_vote = False
        self.voting_dialog = None
        self.is_ready = False
        self.game_window = None

        self._build_ui()

    # ══════════════════════════════════════════
    #  UI construction
    # ══════════════════════════════════════════

    def _build_ui(self):
        notebook = ttk.Notebook(self.root)
        notebook.pack(fill="both", expand=True, padx=8, pady=8)

        host_frame = ttk.Frame(notebook)
        notebook.add(host_frame, text="🏠  Host (Server)")
        self._build_host_tab(host_frame)

        player_frame = ttk.Frame(notebook)
        notebook.add(player_frame, text="🎮  Player (Client)")
        self._build_player_tab(player_frame)

        # Shared status bar
        self.status_var = tk.StringVar(value="Ready")
        ttk.Label(self.root, textvariable=self.status_var, relief="sunken").pack(
            side="bottom", fill="x"
        )

    # ─── HOST TAB ───────────────────────────────

    def _build_host_tab(self, parent):
        main = ttk.Frame(parent)
        main.pack(fill="both", expand=True, padx=8, pady=8)

        # Control
        ctrl = ttk.LabelFrame(main, text="Server Control", padding=8)
        ctrl.pack(fill="x", pady=4)

        pf = ttk.Frame(ctrl)
        pf.pack(fill="x", pady=4)
        ttk.Label(pf, text="Port:").pack(side="left", padx=4)
        self.srv_port_var = tk.StringVar(value="5555")
        ttk.Entry(pf, textvariable=self.srv_port_var, width=8).pack(side="left", padx=4)

        btn_row = ttk.Frame(ctrl)
        btn_row.pack(pady=4)
        self.srv_start_btn = ttk.Button(btn_row, text="▶ Start Server", command=self.start_server)
        self.srv_start_btn.pack(side="left", padx=4)
        self.srv_stop_btn = ttk.Button(btn_row, text="■ Stop Server", command=self.stop_server, state="disabled")
        self.srv_stop_btn.pack(side="left", padx=4)
        self.srv_game_btn = ttk.Button(btn_row, text="🎮 Start Game", command=self.start_game, state="disabled")
        self.srv_game_btn.pack(side="left", padx=4)

        # Quick-join own server button
        self.host_join_btn = ttk.Button(
            ctrl, text="⚡ Also Join as Player (same machine)",
            command=self._host_join_self, state="disabled"
        )
        self.host_join_btn.pack(pady=4)

        # Connection info
        info = ttk.LabelFrame(main, text="Connection Info", padding=8)
        info.pack(fill="x", pady=4)
        ttk.Label(info, text=f"Your Local IP: {self.local_ip}",
                  font=("Arial", 10, "bold"), foreground="blue").pack(anchor="w")
        ttk.Label(info, text=(
            "• Same machine → localhost / 127.0.0.1\n"
            "• Same Wi-Fi   → use IP above\n"
            "• Internet     → public IP + port forwarding"
        ), justify="left", foreground="gray").pack(anchor="w", pady=4)

        # Players list
        pl = ttk.LabelFrame(main, text="Connected Players", padding=8)
        pl.pack(fill="x", pady=4)
        self.srv_players_lb = tk.Listbox(pl, height=7)
        self.srv_players_lb.pack(fill="x")
        self.srv_count_var = tk.StringVar(value="Players: 0")
        ttk.Label(pl, textvariable=self.srv_count_var).pack()

        # Log
        log = ttk.LabelFrame(main, text="Server Log", padding=8)
        log.pack(fill="both", expand=True, pady=4)
        self.srv_log = scrolledtext.ScrolledText(log, height=12, width=80)
        self.srv_log.pack(fill="both", expand=True)

    # ─── PLAYER TAB ─────────────────────────────

    def _build_player_tab(self, parent):
        main = ttk.Frame(parent)
        main.pack(fill="both", expand=True, padx=8, pady=8)

        # Connection inputs
        conn = ttk.LabelFrame(main, text="Connect to Server", padding=8)
        conn.pack(fill="x", pady=4)

        row1 = ttk.Frame(conn)
        row1.pack(fill="x", pady=3)
        ttk.Label(row1, text="Server IP:").pack(side="left", padx=4)
        self.cli_host_var = tk.StringVar(value="localhost")
        ttk.Entry(row1, textvariable=self.cli_host_var, width=18).pack(side="left", padx=4)
        ttk.Label(row1, text="Port:").pack(side="left", padx=4)
        self.cli_port_var = tk.StringVar(value="5555")
        ttk.Entry(row1, textvariable=self.cli_port_var, width=8).pack(side="left", padx=4)

        row2 = ttk.Frame(conn)
        row2.pack(fill="x", pady=3)
        ttk.Label(row2, text="Your Name:").pack(side="left", padx=4)
        self.cli_name_var = tk.StringVar()
        ttk.Entry(row2, textvariable=self.cli_name_var, width=22).pack(side="left", padx=4)

        btn_row = ttk.Frame(conn)
        btn_row.pack(pady=4)
        self.cli_connect_btn = ttk.Button(btn_row, text="🔌 Connect", command=self.connect_to_server)
        self.cli_connect_btn.pack(side="left", padx=4)
        self.cli_disconnect_btn = ttk.Button(btn_row, text="⛔ Disconnect",
                                             command=self.disconnect_from_server, state="disabled")
        self.cli_disconnect_btn.pack(side="left", padx=4)
        self.cli_ready_btn = ttk.Button(btn_row, text="✅ Ready", command=self.toggle_ready,
                                        state="disabled", width=14)
        self.cli_ready_btn.pack(side="left", padx=4)

        # Hidden action buttons (not displayed, kept for game logic)
        self.cli_draw_btn = ttk.Button(self.root, text="🎴 Draw Card", command=self.draw_card,
                                       state="disabled", width=14)
        self.cli_accuse_btn = ttk.Button(self.root, text="⚖️ Accuse", command=self.accuse_player,
                                         state="disabled", width=14)
        self.cli_end_btn = ttk.Button(self.root, text="⏭ End Turn", command=self.end_turn,
                                      state="disabled", width=14)

        # Players list
        pl = ttk.LabelFrame(main, text="Players", padding=8)
        pl.pack(fill="x", pady=4)
        self.cli_players_lb = tk.Listbox(pl, height=6)
        self.cli_players_lb.pack(fill="x")

        # Chat / Log notebook
        nb = ttk.Notebook(main)
        nb.pack(fill="both", expand=True, pady=4)

        chat_fr = ttk.Frame(nb)
        nb.add(chat_fr, text="💬 Chat")
        ci = ttk.Frame(chat_fr)
        ci.pack(side="bottom", fill="x", pady=3)
        self.cli_chat_entry = ttk.Entry(ci)
        self.cli_chat_entry.pack(side="left", fill="x", expand=True, padx=4)
        self.cli_chat_entry.bind("<Return>", lambda e: self.send_chat())
        ttk.Button(ci, text="Send", command=self.send_chat).pack(side="right", padx=4)
        self.cli_chat_text = scrolledtext.ScrolledText(chat_fr, height=10, state="disabled")
        self.cli_chat_text.pack(fill="both", expand=True)

        log_fr = ttk.Frame(nb)
        nb.add(log_fr, text="📜 Log")
        self.cli_log_text = scrolledtext.ScrolledText(log_fr, height=10)
        self.cli_log_text.pack(fill="both", expand=True)

    # ══════════════════════════════════════════
    #  SERVER LOGIC
    # ══════════════════════════════════════════

    def start_server(self):
        try:
            port = int(self.srv_port_var.get())
            self.server = ServerConnection(port=port)
            if self.server.start():
                self.server.message_handler = lambda cid, msg: self.root.after(
                    0, self.handle_client_message, cid, msg
                )
                self.srv_start_btn.config(state="disabled")
                self.srv_stop_btn.config(state="normal")
                self.host_join_btn.config(state="normal")
                self.status_var.set(f"Server running – IP: {self.local_ip}  Port: {port}")
                self._srv_log("=" * 50)
                self._srv_log(f"Server started!  IP: {self.local_ip}  Port: {port}")
                self._srv_log("Waiting for players …")
                self._srv_log("=" * 50)
            else:
                messagebox.showerror("Error", "Failed to start server")
        except Exception as e:
            messagebox.showerror("Error", f"Failed to start server: {e}")

    def stop_server(self):
        if self.server:
            # Notify every connected client before closing
            try:
                self._broadcast(Message(MessageType.CHAT_MESSAGE, {
                    "text": "🔴 SERVER CLOSED – The host has stopped the server.",
                    "server_closing": True,   # custom flag clients will check
                }))
                # Give the message a moment to flush before tearing down sockets
                self.root.after(150, self._finish_stop_server)
                return
            except Exception:
                pass
        self._finish_stop_server()

    def _finish_stop_server(self):
        if self.server:
            self.server.stop()
            self.server = None
        self.srv_start_btn.config(state="normal")
        self.srv_stop_btn.config(state="disabled")
        self.srv_game_btn.config(state="disabled")
        self.host_join_btn.config(state="disabled")
        self.srv_players_lb.delete(0, tk.END)
        self.srv_count_var.set("Players: 0")
        self.players_ready.clear()
        self.game_started = False
        self.voting_in_progress = False
        self.status_var.set("Server stopped")
        self._srv_log("Server stopped")

    def start_game(self):
        n = len(self.server.clients)
        if n < 4:
            messagebox.showwarning("Not Enough Players", f"Need at least 4 players. Have: {n}")
            return
        if n > 12:
            messagebox.showwarning("Too Many Players", f"Max 12 players. Have: {n}")
            return

        player_names, player_ids = [], []
        for cid, c in self.server.clients.items():
            player_names.append(c["name"])
            player_ids.append(cid)

        self.game = Game()
        role_assignments = self.game.setup_game(player_names, player_ids)

        for cid in self.server.clients:
            role = role_assignments.get(cid)
            self.server.send_to_client(cid, Message(MessageType.GAME_START, {
                "role": role,
                "player_id": cid,
                "player_name": self.server.get_client_name(cid),
                "all_players": [{"id": pid, "name": nm}
                                for pid, nm in zip(player_ids, player_names)],
            }))

        self.game_started = True
        self.srv_game_btn.config(state="disabled")
        self._broadcast_game_state()

        self._srv_log("=" * 50)
        self._srv_log("Game started!")
        self._srv_log(f"Players: {', '.join(player_names)}")
        witches = sum(1 for p in self.game.players if p.is_witch())
        self._srv_log(f"Witches: {witches}  Townsfolk: {len(player_names) - witches}")
        self._srv_log("=" * 50)
        cur = self.game.get_current_player()
        if cur:
            self._srv_log(f"First turn: {cur.name}")

    def handle_client_message(self, client_id, message):
        if message.type in (MessageType.JOIN_GAME, MessageType.PLAYER_JOINED):
            pname = (message.data.get("name") or
                     message.data.get("player_name") or "").strip()

            if not pname:
                return

            # ── Duplicate name check ──
            # Check against all OTHER registered players
            taken = any(
                p["name"].strip().lower() == pname.lower()
                for cid, p in self.players_ready.items()
                if cid != client_id
            )
            if taken:
                self._srv_log(f"✗ Rejected '{pname}' – name already taken")
                self.server.send_to_client(client_id, Message(MessageType.ERROR, {
                    "code": "NAME_TAKEN",
                    "name": pname,
                    "text": f"The name \"{pname}\" is already taken. Please choose a different name.",
                }))
                self.players_ready.pop(client_id, None)
                self._srv_update_players()
                self.root.after(300, self._kick_client, client_id)
                return

            # ── Register (first message) or silently ignore duplicate event ──
            if client_id not in self.players_ready:
                self.players_ready[client_id] = {"name": pname, "ready": False}
                self._srv_update_players()
                self._srv_log(f"✓ {pname} joined")
                players = self._player_list()
                for cid in list(self.server.clients):
                    if cid != client_id:
                        self.server.send_to_client(cid, Message(MessageType.PLAYER_LIST, {"players": players}))
                self.server.send_to_client(client_id, Message(MessageType.PLAYER_LIST, {"players": players}))
                self._update_start_btn()

        elif message.type == MessageType.PLAYER_READY:
            if client_id in self.players_ready:
                ready = message.data.get("ready", False)
                self.players_ready[client_id]["ready"] = ready
                name = self.players_ready[client_id]["name"]
                self._srv_log(f"{name} is {'READY ✓' if ready else 'NOT READY ○'}")
                self._srv_update_players()
                self._broadcast(Message(MessageType.PLAYER_LIST, {"players": self._player_list()}))
                self._update_start_btn()

        elif message.type in (MessageType.PLAYER_LEFT, MessageType.DISCONNECT):
            if client_id in self.players_ready:
                name = self.players_ready.pop(client_id)["name"]
                self._srv_log(f"✗ {name} left")
                self._srv_update_players()
                self._broadcast(Message(MessageType.PLAYER_LIST, {"players": self._player_list()}))
                self._update_start_btn()

        elif message.type == MessageType.DRAW_CARD:
            if self.game_started and self.game and not self.voting_in_progress:
                card, result = self.game.draw_card(client_id)
                self.server.send_to_client(client_id, Message(MessageType.DRAW_CARD, {
                    "success": card is not None,
                    "message": result,
                    "card": str(card) if card else None,
                }))
                self._broadcast_game_state()

        elif message.type == MessageType.ACCUSE:
            if self.game_started and self.game and not self.voting_in_progress:
                accused_name = message.data.get("accused")
                success, result = self.game.start_accusation(client_id, accused_name)
                self.server.send_to_client(client_id, Message(MessageType.ACCUSE,
                                                              {"success": success, "message": result}))
                if success:
                    self._srv_log(f"Accusation: {self.server.get_client_name(client_id)} → {accused_name}")
                    self._broadcast_game_state()
                    self._start_voting_phase()

        elif message.type == MessageType.VOTE:
            if self.game_started and self.game and self.voting_in_progress:
                guilty = message.data.get("guilty", False)
                success, result = self.game.cast_vote(client_id, guilty)
                self.server.send_to_client(client_id, Message(MessageType.VOTE,
                                                              {"success": success, "message": result}))
                if success:
                    self._broadcast_game_state()
                    alive = [p for p in self.game.players if p.alive]
                    if len(self.game.votes_cast) >= len(alive) - 1:
                        self._resolve_accusation()

        elif message.type == MessageType.NEXT_TURN:
            if self.game_started and self.game and not self.voting_in_progress:
                nxt, msg = self.game.next_turn(player_id=client_id)
                if nxt:
                    self._srv_log(f"Turn → {nxt.name}")
                else:
                    self._srv_log(f"End turn rejected: {msg}")
                self._broadcast_game_state()

        elif message.type == MessageType.CHAT_MESSAGE:
            text = message.data.get("text", "")
            sender = self.server.get_client_name(client_id)
            self._broadcast(Message(MessageType.CHAT_MESSAGE, {"text": f"{sender}: {text}"}))
            self._srv_log(f"{sender}: {text}")

    def _kick_client(self, client_id):
        """Forcibly disconnect a rejected client (e.g. duplicate name)."""
        try:
            if self.server and client_id in self.server.clients:
                self.server.remove_client(client_id)
        except Exception as e:
            self._srv_log(f"Kick error for {client_id}: {e}")

    def _start_voting_phase(self):
        self.voting_in_progress = True
        state = self.game.get_game_state()
        accused_name = state.get("accused_player_name", "?")
        accused_by = state.get("accused_by_name", "Someone")
        self._broadcast(Message(MessageType.CHAT_MESSAGE, {
            "text": f"🔔 VOTING – {accused_name} accused by {accused_by}! All must vote! 🔔"
        }))
        self._srv_log(f"VOTING: {accused_name} is on trial")
        for cid in self.server.clients:
            player = self.game._get_player_by_id(cid)
            if player and player.alive and cid != self.game.accused_player.id:
                self.server.send_to_client(cid, Message(MessageType.GAME_STATE, {
                    "state": "voting",
                    "accused": accused_name,
                    "accused_by": self.game.accused_by.name if self.game.accused_by else "Someone",
                }))

    def _resolve_accusation(self):
        success, msg, winner = self.game.resolve_accusation()
        self._broadcast(Message(MessageType.RESOLVE_ACCUSATION, {
            "message": msg,
            "eliminated_player": self.game.accused_player.name if self.game.accused_player else None,
        }))
        self._srv_log(msg)
        if winner:
            self._broadcast(Message(MessageType.GAME_OVER, {"winner": winner}))
            self._srv_log(f"🏆 GAME OVER! {winner} wins!")
            self.game_started = False
        self.voting_in_progress = False
        self._broadcast_game_state()

    def _broadcast_game_state(self):
        for cid in self.server.clients:
            state = self.game.get_game_state(for_player_id=cid)
            state["hand"] = [str(c) for c in self.game.get_player_hand(cid)]
            if self.voting_in_progress and self.game.accused_player:
                state["voting_info"] = {
                    "accused": self.game.accused_player.name,
                    "votes_cast": len(self.game.votes_cast),
                    "guilty_votes": self.game.accused_player.votes,
                }
            self.server.send_to_client(cid, Message(MessageType.GAME_STATE, {"state": state}))

    def _broadcast(self, message):
        if self.server:
            self.server.broadcast(message)

    def _update_start_btn(self):
        """Enable Start Game only when all players are ready and there are at least 4."""
        n = len(self.players_ready)
        all_ready = n >= 4 and all(p["ready"] for p in self.players_ready.values())
        self.srv_game_btn.config(state="normal" if all_ready else "disabled")
        if all_ready:
            self._srv_log(f"All {n} players are ready — you can start the game!")

    def _player_list(self):
        return [{"id": cid, "name": p["name"], "ready": p["ready"]}
                for cid, p in self.players_ready.items()]

    def _srv_update_players(self):
        self.srv_players_lb.delete(0, tk.END)
        for cid, p in self.players_ready.items():
            mark = "✓" if p.get("ready") else "○"
            self.srv_players_lb.insert(tk.END, f"{mark} {p['name']}")
        self.srv_count_var.set(f"Players: {len(self.players_ready)}")

    def _srv_log(self, msg):
        ts = time.strftime("%H:%M:%S")
        self.srv_log.insert(tk.END, f"[{ts}] {msg}\n")
        self.srv_log.see(tk.END)
        self.root.update_idletasks()

    # ── Quick-join helper (host joins own server) ──

    def _host_join_self(self):
        """Pre-fill the Player tab with localhost details and switch to it."""
        port = self.srv_port_var.get()
        self.cli_host_var.set("127.0.0.1")
        self.cli_port_var.set(port)
        # Switch to Player tab (index 1)
        self.root.nametowidget(self.root.winfo_children()[0]).select(1)
        self._cli_log("⚡ Pre-filled with localhost. Enter your name and click Connect!")

    # ══════════════════════════════════════════
    #  CLIENT LOGIC
    # ══════════════════════════════════════════

    def connect_to_server(self):
        host = self.cli_host_var.get().strip()
        raw_port = self.cli_port_var.get().strip()
        name = self.cli_name_var.get().strip()

        if not name:
            messagebox.showerror("Error", "Please enter your name")
            return
        if len(name) > 20:
            messagebox.showerror("Error", "Name too long (max 20 chars)")
            return
        if not raw_port.isdigit() or not (1 <= int(raw_port) <= 65535):
            messagebox.showerror("Error", "Port must be 1–65535")
            return
        if not host:
            messagebox.showerror("Error", "Please enter a server IP")
            return

        port = int(raw_port)
        self.player_name = name
        self.cli_connect_btn.config(state="disabled")
        self.status_var.set(f"Connecting to {host}:{port}…")

        def do_connect():
            try:
                self.connection = ClientConnection(host, port)
                self.connection.player_name = name
                if self.connection.connect():
                    self.connection.register_handler(self._on_server_message)
                    self.root.after(0, self._on_connected, host, port)
                else:
                    self.connection = None
                    self.root.after(0, self.cli_connect_btn.config, {"state": "normal"})
                    self.root.after(0, self.status_var.set, "Connection failed")
                    self.root.after(0, messagebox.showerror, "Error",
                                    f"Could not connect to {host}:{port}")
            except Exception as e:
                self.connection = None
                self.root.after(0, self.cli_connect_btn.config, {"state": "normal"})
                self.root.after(0, self.status_var.set, "Connection error")
                self.root.after(0, messagebox.showerror, "Error", str(e))

        threading.Thread(target=do_connect, daemon=True).start()

    def _on_connected(self, host, port):
        self.cli_disconnect_btn.config(state="normal")
        self.cli_ready_btn.config(state="normal")
        self.status_var.set(f"Connected to {host}:{port}")
        self._cli_log(f"Connected to {host}:{port}")
        self._add_chat("System", "Connected. Waiting for host to start the game…")

    def _on_server_message(self, message):
        if message is None:
            # Connection dropped unexpectedly (server closed without warning)
            self.root.after(0, self._on_server_closed)
        else:
            self.root.after(0, self._handle_server_message, message)

    def _on_name_taken(self, taken_name, server_message):
        """Called when the server rejects our name as a duplicate."""
        if self.connection:
            try:
                self.connection.disconnect()
            except Exception:
                pass
            self.connection = None

        self.player_id = self.role = self.game_state = None
        self.is_ready = False

        self.cli_connect_btn.config(state="normal")
        self.cli_disconnect_btn.config(state="disabled")
        self.cli_ready_btn.config(text="✅ Ready", state="disabled")
        self.cli_draw_btn.config(state="disabled")
        self.cli_accuse_btn.config(state="disabled")
        self.cli_end_btn.config(state="disabled")
        self.cli_players_lb.delete(0, tk.END)
        self.status_var.set(f"⚠️ Name \"{taken_name}\" already taken — choose a different name")

        self._cli_log(f"⚠️ Rejected: {server_message}")
        messagebox.showerror(
            "Name Already Taken",
            f"The name \"{taken_name}\" is already in use.\n\nPlease choose a different name and reconnect."
        )

    def _on_server_closed(self):
        """Called when the host shuts down the server (gracefully or by drop)."""
        if not self.connection:
            return   # already handled

        # Clean up connection object without sending anything (server is gone)
        try:
            self.connection.disconnect()
        except Exception:
            pass
        self.connection = None

        # Reset all client state
        self.player_id = self.role = self.game_state = None
        self.is_ready = self.waiting_for_vote = False
        if self.voting_dialog:
            try:
                self.voting_dialog.destroy()
            except Exception:
                pass
            self.voting_dialog = None
        if self.game_window:
            self.game_window.destroy()
            self.game_window = None

        # Reset UI controls
        self.cli_connect_btn.config(state="normal")
        self.cli_disconnect_btn.config(state="disabled")
        self.cli_ready_btn.config(text="✅ Ready", state="disabled")
        self.cli_draw_btn.config(state="disabled")
        self.cli_accuse_btn.config(state="disabled")
        self.cli_end_btn.config(state="disabled")
        self.cli_players_lb.delete(0, tk.END)
        self.status_var.set("⛔ Disconnected – Host stopped the server")

        # Inform the player clearly
        self._cli_log("⛔ The host has stopped the server.")
        self._add_chat("System", "⛔ The server has been closed by the host. You have been disconnected.")
        messagebox.showwarning(
            "Server Closed",
            "The host has stopped the server.\n\nYou have been disconnected."
        )

    def disconnect_from_server(self):
        if self.connection:
            self.connection.disconnect()
            self.connection = None

        self.player_id = self.role = self.game_state = None
        self.is_ready = self.waiting_for_vote = False
        if self.voting_dialog:
            self.voting_dialog.destroy()
            self.voting_dialog = None

        self.cli_connect_btn.config(state="normal")
        self.cli_disconnect_btn.config(state="disabled")
        self.cli_ready_btn.config(text="✅ Ready", state="disabled")
        self.cli_draw_btn.config(state="disabled")
        self.cli_accuse_btn.config(state="disabled")
        self.cli_end_btn.config(state="disabled")
        self.cli_players_lb.delete(0, tk.END)
        self.status_var.set("Disconnected")
        self._cli_log("Disconnected")
        self._add_chat("System", "You have disconnected.")

    def toggle_ready(self):
        self.is_ready = not self.is_ready
        if self.is_ready:
            self.cli_ready_btn.config(text="❌ Unready")
            self.status_var.set("Status: Ready!")
        else:
            self.cli_ready_btn.config(text="✅ Ready")
            self.status_var.set("Status: Not Ready")
        self.connection.send(Message(MessageType.PLAYER_READY, {"ready": self.is_ready}))

    def _handle_server_message(self, message):
        if message.type == MessageType.CONNECT_ACK:
            self.player_id = message.data.get("player_id")
            self._cli_log(f"Connected as {self.player_name} (ID: {self.player_id})")
            self.connection.send(Message(MessageType.JOIN_GAME, {"name": self.player_name}))

        elif message.type == MessageType.PLAYER_LEFT:
            name = message.data.get("player_name", "A player")
            self._add_chat("System", f"⚠️ {name} left the game.")

        elif message.type == MessageType.GAME_START:
            self.role = message.data.get("role")
            self.player_id = message.data.get("player_id")
            all_players = message.data.get("all_players", [])
            self.cli_ready_btn.config(state="disabled")
            self.cli_disconnect_btn.config(state="disabled")
            self._cli_log(f"Game started! You are a {self.role}")
            # Open the game popup window
            if self.game_window:
                self.game_window.destroy()
            self.game_window = GameWindow(
                self.root, self,
                role=self.role,
                player_id=self.player_id,
                player_name=self.player_name,
                all_players=all_players,
            )

        elif message.type == MessageType.GAME_STATE:
            self.game_state = message.data.get("state", {})
            self._update_display()
            if self.game_window:
                self.game_window.update_state(self.game_state)
            elif self.game_state.get("current_player") == self.player_id:
                self.status_var.set("🎯 It's YOUR turn!")
                self.cli_draw_btn.config(state="normal")
                self.cli_accuse_btn.config(state="normal")
                self.cli_end_btn.config(state="normal")
            else:
                cur = self.game_state.get("current_player_name", "Someone")
                self.status_var.set(f"Waiting for {cur}'s turn")
                self.cli_draw_btn.config(state="disabled")
                self.cli_accuse_btn.config(state="disabled")
                self.cli_end_btn.config(state="disabled")

        elif message.type == MessageType.DRAW_CARD:
            parent = self.game_window.win if self.game_window else self.root
            if message.data.get("success"):
                messagebox.showinfo("Card Drawn", message.data.get("message"), parent=parent)
                self._cli_log(message.data.get("message"))
            else:
                messagebox.showerror("Error", message.data.get("message"), parent=parent)

        elif message.type == MessageType.ACCUSE:
            if message.data.get("success"):
                self._cli_log(message.data.get("message"))
            else:
                messagebox.showerror("Error", message.data.get("message"))

        elif message.type == MessageType.VOTE:
            self._cli_log(message.data.get("message", ""))

        elif message.type == MessageType.RESOLVE_ACCUSATION:
            self._cli_log(message.data.get("message", ""))
            if self.game_window:
                self.game_window.close_voting()
            else:
                self.waiting_for_vote = False
                if self.voting_dialog:
                    self.voting_dialog.destroy()
                    self.voting_dialog = None

        elif message.type == MessageType.GAME_OVER:
            winner = message.data.get("winner")
            self._cli_log(f"🏆 GAME OVER! {winner} wins!")
            if self.game_window:
                self.game_window.show_game_over(winner)
            else:
                msg = f"Game Over!\n{winner} wins!\n\n"
                if winner == "Witches" and self.role == "Witch":
                    msg += "Congratulations! Your coven triumphed!"
                elif winner == "Town" and self.role == "Townsperson":
                    msg += "Well done! Salem is cleansed!"
                else:
                    msg += "Better luck next time!"
                messagebox.showinfo("Game Over", msg)
            self._enable_controls(False)

        elif message.type == MessageType.ERROR:
            code = message.data.get("code", "")
            if code == "NAME_TAKEN":
                self._on_name_taken(message.data.get("name", ""), message.data.get("text", ""))
            else:
                # Generic server error — just log and show to user
                self._cli_log(f"⚠️ Server error: {message.data.get('text', code)}")
                messagebox.showerror("Server Error", message.data.get("text", "An error occurred."))

        elif message.type == MessageType.CHAT_MESSAGE:
            text = message.data.get("text", "")
            self._add_chat(None, text)
            if self.game_window:
                self.game_window.add_chat(None, text)
            if message.data.get("server_closing"):
                self._on_server_closed()

        elif message.type == MessageType.PLAYER_LIST:
            self._update_players_list(message.data.get("players", []))

    # ─── Client helpers ──────────────────────────

    def _show_role_window(self):
        w = tk.Toplevel(self.root)
        w.title("Your Role")
        w.geometry("400x300")
        w.configure(bg="#2c3e50")
        w.transient(self.root)
        w.grab_set()
        is_witch = self.role == "Witch"
        ttk.Label(w, text="🔮 WITCH 🔮" if is_witch else "🏠 TOWNSPERSON 🏠",
                  font=("Arial", 24, "bold"),
                  foreground="#8e44ad" if is_witch else "#27ae60").pack(pady=30)
        ttk.Label(w, text="Your secret role:", font=("Arial", 12)).pack()
        desc = ("You are a WITCH!\nWork with other witches to eliminate townsfolk.\nUse deception to survive!"
                if is_witch else
                "You are a TOWNSPERSON!\nFind and eliminate all witches.\nTrust your instincts!")
        ttk.Label(w, text=desc, wraplength=350, justify="center").pack(pady=20)
        ttk.Button(w, text="I Understand", command=w.destroy).pack(pady=20)

    def _update_display(self):
        if not self.game_state:
            return
        if "log" in self.game_state:
            self.cli_log_text.delete(1.0, tk.END)
            for entry in self.game_state["log"]:
                self.cli_log_text.insert(tk.END, f"{entry}\n")
            self.cli_log_text.see(tk.END)
        if "hand" in self.game_state:
            pass  # Hand display removed
        if "voting_info" in self.game_state:
            info = self.game_state["voting_info"]
            needed = self.game_state.get("votes_needed", 0)
            if needed:
                self.status_var.set(f"Voting: {info['guilty_votes']}/{needed} guilty votes")

    def _update_players_list(self, players):
        self.cli_players_lb.delete(0, tk.END)
        for player in players:
            alive = True
            if self.game_state:
                for p in self.game_state.get("players", []):
                    if p.get("id") == player["id"]:
                        alive = p.get("alive", True)
                        break
            if self.game_state and self.game_state.get("current_player") == player["id"]:
                marker = "👉"
            elif not alive:
                marker = "💀"
            else:
                marker = "  "
            name = player["name"]
            if not self.game_state:
                ready = "✅" if player.get("ready") else "○"
                self.cli_players_lb.insert(tk.END, f"{ready} {name}")
            else:
                hint = f" ({self.role[0]})" if player["id"] == self.player_id and self.role else ""
                self.cli_players_lb.insert(tk.END,
                                           f"{marker} {'✓' if alive else '✗'} {name}{hint}")

    def draw_card(self):
        self.connection.send(Message(MessageType.DRAW_CARD))
        self.cli_draw_btn.config(state="disabled")
        self.status_var.set("Drawing card…")

    def accuse_player(self):
        if not self.game_state:
            return
        players = [p["name"] for p in self.game_state.get("players", [])
                   if p.get("alive") and p.get("id") != self.player_id]
        if not players:
            messagebox.showinfo("No Targets", "No other players to accuse!")
            return
        dlg = tk.Toplevel(self.root)
        dlg.title("Accuse Player")
        dlg.geometry("350x200")
        dlg.transient(self.root)
        ttk.Label(dlg, text="Select player to accuse:", font=("Arial", 11)).pack(pady=15)
        accused_var = tk.StringVar()
        ttk.Combobox(dlg, textvariable=accused_var, values=players, width=20).pack(pady=10)
        def confirm():
            if accused_var.get():
                self.connection.send(Message(MessageType.ACCUSE, {"accused": accused_var.get()}))
                self.status_var.set(f"Accusing {accused_var.get()}…")
                dlg.destroy()
        ttk.Button(dlg, text="⚖️ Accuse", command=confirm).pack(pady=15)

    def _show_voting_dialog(self, accused_name):
        self.waiting_for_vote = True
        self.voting_dialog = tk.Toplevel(self.root)
        self.voting_dialog.title("Vote!")
        self.voting_dialog.geometry("400x200")
        self.voting_dialog.transient(self.root)
        self.voting_dialog.grab_set()
        ttk.Label(self.voting_dialog, text=f"⚖️ {accused_name} is on trial! ⚖️",
                  font=("Arial", 12, "bold")).pack(pady=15)
        ttk.Label(self.voting_dialog, text="Do you believe they are a witch?",
                  font=("Arial", 11)).pack(pady=10)
        bf = ttk.Frame(self.voting_dialog)
        bf.pack(pady=20)
        def vote(guilty):
            self.connection.send(Message(MessageType.VOTE, {"guilty": guilty}))
            self.status_var.set(f"Voted {'GUILTY' if guilty else 'NOT GUILTY'}")
            self.voting_dialog.destroy()
            self.voting_dialog = None
            self.waiting_for_vote = False
        ttk.Button(bf, text="🔴 GUILTY", command=lambda: vote(True), width=14).pack(side="left", padx=8)
        ttk.Button(bf, text="🟢 NOT GUILTY", command=lambda: vote(False), width=14).pack(side="left", padx=8)

    def end_turn(self):
        self.connection.send(Message(MessageType.NEXT_TURN))
        self.cli_draw_btn.config(state="disabled")
        self.cli_accuse_btn.config(state="disabled")
        self.cli_end_btn.config(state="disabled")
        self.status_var.set("Turn ended")
        self._cli_log("You ended your turn")

    def send_chat(self):
        text = self.cli_chat_entry.get().strip()
        if text and self.connection:
            self.connection.send(Message(MessageType.CHAT_MESSAGE, {"text": text}))
            self.cli_chat_entry.delete(0, tk.END)

    def _add_chat(self, sender, msg):
        self.cli_chat_text.config(state="normal")
        self.cli_chat_text.insert(tk.END, f"{sender}: {msg}\n" if sender else f"{msg}\n")
        self.cli_chat_text.see(tk.END)
        self.cli_chat_text.config(state="disabled")

    def _enable_controls(self, enabled):
        state = "normal" if enabled else "disabled"
        self.cli_draw_btn.config(state=state)
        self.cli_accuse_btn.config(state=state)
        self.cli_end_btn.config(state=state)

    def _cli_log(self, msg):
        ts = time.strftime("%H:%M:%S")
        self.cli_log_text.insert(tk.END, f"[{ts}] {msg}\n")
        self.cli_log_text.see(tk.END)

    # ══════════════════════════════════════════
    #  Run
    # ══════════════════════════════════════════

    def run(self):
        self.root.mainloop()


# ─────────────────────────────────────────────

if __name__ == "__main__":
    app = SalemLauncher()
    app.run()