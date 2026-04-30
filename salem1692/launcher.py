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
from utils.helpers import save_game_result

APP_BG = "#0f1722"
SURFACE_BG = "#16202d"
SURFACE_ALT = "#1b2635"
PANEL_BG = "#223144"
TEXT_MAIN = "#ecf3ff"
TEXT_MUTED = "#9eb1c8"
ACCENT_GOLD = "#f4b942"
ACCENT_RED = "#ef6a5b"
ACCENT_BLUE = "#5aa9e6"
ACCENT_GREEN = "#55d187"
LINE_COLOR = "#31465f"


def style_text_widget(widget, *, height=None):
    widget.configure(
        bg="#101924",
        fg=TEXT_MAIN,
        insertbackground=TEXT_MAIN,
        selectbackground="#35506f",
        selectforeground="white",
        relief="flat",
        bd=0,
        padx=10,
        pady=10,
    )
    if height is not None:
        widget.configure(height=height)


def style_listbox_widget(widget, *, height=None):
    widget.configure(
        bg="#101924",
        fg=TEXT_MAIN,
        selectbackground="#35506f",
        selectforeground="white",
        highlightthickness=1,
        highlightbackground=LINE_COLOR,
        highlightcolor=ACCENT_GOLD,
        relief="flat",
        bd=0,
        activestyle="none",
    )
    if height is not None:
        widget.configure(height=height)


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
    when the host starts the game.
    """

    def __init__(self, root, launcher, role, player_id, player_name, all_players):
        self.root = root
        self.launcher = launcher
        self.role = role
        self.is_witch = (role == "Witch")
        self.is_constable = (role == "Constable")
        self.player_id = player_id
        self.player_name = player_name
        self.all_players = all_players
        self.game_state = {}
        self.waiting_for_vote = False
        self.voting_dialog = None
        self.night_dialog = None
        self.confess_phase_dialog = None     # the confess phase popup
        self._vote_after_id = None
        self._night_after_id = None
        self._constable_after_id = None
        self._has_voted = False
        self._dawn_voted = False

        self.win = tk.Toplevel(root)
        self.win.title(f"Salem 1692 – {player_name}")
        self.win.geometry("1220x820")
        self.win.minsize(1080, 760)
        self.win.configure(bg=APP_BG)
        self.win.protocol("WM_DELETE_WINDOW", self._on_close)

        self._build_ui()
        self._show_role_reveal()
        # Only the modified function is shown below. Replace your existing _show_role_reveal with this.

    def _show_role_reveal(self):
        r = tk.Toplevel(self.win)
        r.title("Your Role")
        r.configure(bg="#2c3e50")

        is_witch = self.is_witch
        is_constable = self.is_constable

        if is_witch:
            label_text = "🔮 WITCH 🔮"
            label_color = "#e74c3c"
            desc = "You are a WITCH!\nWork with your coven to eliminate townsfolk.\nUse deception to survive!"
        elif is_constable:
            label_text = "⚖️ CONSTABLE ⚖️"
            label_color = "#3498db"
            desc = "You are the CONSTABLE!\nEach Night you may choose one player to protect with your Gavel.\nThey cannot be killed by the witches that night."
        else:
            label_text = "🏠 TOWNSPERSON 🏠"
            label_color = "#27ae60"
            desc = "You are a TOWNSPERSON!\nFind and eliminate all witches.\nTrust your instincts!"

        # Build UI FIRST
        tk.Label(r, text=label_text, bg="#2c3e50", fg=label_color,
                 font=("Arial", 34, "bold")).pack(pady=38)

        tk.Label(r, text=desc, bg="#2c3e50", fg="white",
                 wraplength=540, justify="center", font=("Arial", 15)).pack(pady=14)

        ttk.Button(r, text="I Understand", command=r.destroy).pack(pady=26)

        # Force proper size AFTER widgets exist
        r.update_idletasks()
        r.geometry("620x480")
        r.minsize(620, 480)
        r.resizable(False, False)

        # Bring to front and make modal
        r.transient(self.win)
        r.grab_set()
        r.lift()
        r.attributes('-topmost', True)
        r.after(10, lambda: r.attributes('-topmost', False))

        self._center(r)


    # ── UI ──────────────────────────────────────

    @staticmethod
    def _center(win):
        """Center a Toplevel window on the screen using its declared geometry size."""
        win.update_idletasks()
        # Parse the declared WxH from the geometry string (set before _center is called)
        geo = win.geometry()   # e.g. "620x480+0+0"
        try:
            w, h = [int(v) for v in geo.split('+')[0].split('x')]
        except (ValueError, IndexError):
            w = win.winfo_reqwidth()
            h = win.winfo_reqheight()
        sw = win.winfo_screenwidth()
        sh = win.winfo_screenheight()
        x = (sw - w) // 2
        y = (sh - h) // 2
        win.geometry(f"{w}x{h}+{x}+{y}")

    def _build_ui(self):
        top = tk.Frame(self.win, bg=PANEL_BG, padx=16, pady=12)
        top.pack(fill="x")

        is_witch = self.is_witch
        is_constable = self.is_constable
        if is_witch and is_constable:
            role_color, role_icon = "#e74c3c", "🔮⚖️"
        elif is_witch:
            role_color, role_icon = "#e74c3c", "🔮"
        elif is_constable:
            role_color, role_icon = "#3498db", "⚖️"
        else:
            role_color, role_icon = "#27ae60", "🏠"
        self.role_lbl = tk.Label(top, text=f"Salem 1692   {role_icon} {self.role}",
                 bg=PANEL_BG, fg=role_color,
                 font=("Segoe UI", 20, "bold"))
        self.role_lbl.pack(side="left", padx=12)

        self.status_lbl = tk.Label(top, text="Waiting for game...",
                                   bg=PANEL_BG, fg=TEXT_MAIN,
                                   font=("Segoe UI Semibold", 12))
        self.status_lbl.pack(side="left", padx=20)

        # FIX: Black Cat label always visible in header
        self.black_cat_lbl = tk.Label(top, text="🐈 Black Cat: ?",
                                      bg="#1b2431", fg=ACCENT_GOLD,
                                      padx=16, pady=10,
                                      font=("Segoe UI Semibold", 12))
        self.black_cat_lbl.pack(side="right", padx=12)

        pane = ttk.PanedWindow(self.win, orient="horizontal", style="Game.TPanedwindow")
        pane.pack(fill="both", expand=True, padx=6, pady=4)

        left = ttk.Frame(pane, style="Surface.TFrame")
        pane.add(left, weight=1)

        pf = ttk.LabelFrame(left, text="Players", padding=10, style="App.TLabelframe")
        pf.pack(fill="both", expand=True, pady=4)
        self.players_canvas = tk.Canvas(pf, bg=SURFACE_BG, highlightthickness=0, bd=0)
        self.players_canvas.pack(fill="both", expand=True)
        # keep players_lb as a hidden dummy so old code references don't crash
        self.players_lb = tk.Listbox(pf)  # not packed

        hf = ttk.LabelFrame(left, text="Your Hand  (double-click to play)", padding=10, style="App.TLabelframe")
        hf.pack(fill="x", pady=4)
        self.hand_lb = tk.Listbox(hf, height=6, font=("Consolas", 12))
        self.hand_lb.pack(fill="x")
        # FIX: double-click to play a card from hand
        self.hand_lb.bind("<Double-Button-1>", self._play_selected_card)

        af = ttk.LabelFrame(left, text="Actions", padding=10, style="App.TLabelframe")
        af.pack(fill="x", pady=4)
        btn_row = ttk.Frame(af)
        btn_row.pack()
        self.draw_btn    = ttk.Button(btn_row, text="🎴 Draw Card",  command=self._draw_card,
                                      state="disabled", width=14, style="Accent.TButton")
        self.accuse_btn  = ttk.Button(btn_row, text="🙏 Confess",    command=self._confess,
                                      state="disabled", width=14, style="Secondary.TButton")
        self.end_btn     = ttk.Button(btn_row, text="⏭ End Turn",   command=self._end_turn,
                                      state="disabled", width=14, style="Danger.TButton")
        self.draw_btn.pack(side="left", padx=3, pady=4)
        self.accuse_btn.pack(side="left", padx=3, pady=4)
        self.end_btn.pack(side="left", padx=3, pady=4)

        right = ttk.Frame(pane, style="Surface.TFrame")
        pane.add(right, weight=1)

        lf = ttk.LabelFrame(right, text="Game Log", padding=10, style="App.TLabelframe")
        lf.pack(fill="both", expand=True, pady=4)

        # FIX: remove state="disabled" so mouse-wheel scrolling works;
        #      instead we use a tag trick to keep text read-only but scrollable.
        self.log_text = scrolledtext.ScrolledText(lf, height=18, font=("Consolas", 10))
        self.log_text.pack(fill="both", expand=True)
        # Make it visually read-only without blocking scroll events
        self.log_text.bind("<Key>", lambda e: "break")

        cf = ttk.LabelFrame(right, text="Chat", padding=10, style="App.TLabelframe")
        cf.pack(fill="x", pady=4)
        chat_input_row = ttk.Frame(cf)
        chat_input_row.pack(side="bottom", fill="x", pady=3)
        self.chat_entry = ttk.Entry(chat_input_row)
        self.chat_entry.pack(side="left", fill="x", expand=True, padx=4)
        self.chat_entry.bind("<Return>", lambda e: self._send_chat())
        ttk.Button(chat_input_row, text="Send", command=self._send_chat, style="Accent.TButton").pack(side="right", padx=4)
        self.chat_text = scrolledtext.ScrolledText(cf, height=8, font=("Consolas", 10))
        self.chat_text.pack(fill="both", expand=True)
        self.chat_text.bind("<Key>", lambda e: "break")

        # Redraw player bars when canvas is resized
        self.players_canvas.bind("<Configure>", lambda e: self._refresh_players())
        style_listbox_widget(self.hand_lb, height=6)
        style_text_widget(self.log_text)
        style_text_widget(self.chat_text)

    # ── State updates ────────────────────────────

    def update_state(self, state):
        self.game_state = state
        self._refresh_players()
        self._refresh_hand()
        self._refresh_log()
        self._refresh_turn()

        # FIX: show black cat owner to everyone
        bc = state.get("black_cat_owner", "?")
        self.black_cat_lbl.config(text=f"🐈 Black Cat: {bc}")

        # Accusation voting popup
        if state.get("accusation_phase"):
            accused = state.get("accused_player_name")
            is_accused = (accused == self.player_name)
            if accused and not self.waiting_for_vote and not self.voting_dialog and not self._has_voted and not is_accused:
                self.waiting_for_vote = True
                if self._vote_after_id is not None:
                    self.win.after_cancel(self._vote_after_id)
                    self._vote_after_id = None
                self._vote_after_id = self.win.after(100, self._show_voting_dialog, accused)
        else:
            # Accusation phase ended — reset for next round
            self._has_voted = False

        # Conspiracy transfer popup
        transfers = state.get("conspiracy_transfers", [])
        if transfers:
            self.win.after(200, self._show_conspiracy_popup, transfers)

        # Dawn phase — show Black Cat placement dialog to witches
        if state.get("dawn_pending") and not self._dawn_voted:
            if self.is_witch:
                self.win.after(150, self._show_dawn_dialog)
            else:
                self.status_lbl.config(text="🌅 Dawn – witches are placing the Black Cat…", fg="#e67e22")
        elif not state.get("dawn_pending"):
            self._dawn_voted = False  # reset for potential future games

        if state.get("night_pending") and not self.night_dialog:
            if self.is_witch:
                if self._night_after_id is None:
                    self._night_after_id = self.win.after(150, self._show_night_dialog)
            else:
                self.status_lbl.config(text="🌙 Night phase – witches are choosing…", fg="#9b59b6")
            if state.get("is_constable") and not state.get("constable_save_submitted"):
                if self._constable_after_id is None:
                    self._constable_after_id = self.win.after(150, self._show_constable_dialog)
        elif not state.get("night_pending"):
            self.accuse_btn.config(state="disabled")
            if self._night_after_id is not None:
                self.win.after_cancel(self._night_after_id)
                self._night_after_id = None
            if self._constable_after_id is not None:
                self.win.after_cancel(self._constable_after_id)
                self._constable_after_id = None

    def _refresh_players(self):
        c = self.players_canvas
        c.delete("all")
        c.update_idletasks()
        W = c.winfo_width() or 240

        current_id = self.game_state.get("current_player")
        players = self.game_state.get("players", [])
        ROW_H = 54
        PAD_X = 8

        for i, p in enumerate(players):
            pid    = p.get("id")
            name   = p.get("name", "?")
            alive  = p.get("alive", True)
            total  = p.get("tryal_total", 5)
            hidden = p.get("tryal_hidden", total)
            acc    = p.get("accusation_total", 0)
            is_me  = (pid == self.player_id)
            is_cur = (pid == current_id)

            y = i * ROW_H + 6

            # Row background
            if not alive:
                bg = "#2a1a1a"
            elif is_cur:
                bg = "#1a3a2a"
            else:
                bg = "#1e2a38"
            c.create_rectangle(PAD_X, y, W - PAD_X, y + ROW_H - 4,
                                fill=bg, outline="#334455", width=1)

            # Turn arrow / dead skull
            if not alive:
                icon = "💀"
            elif is_cur:
                icon = "👉"
            else:
                icon = "  "
            c.create_text(PAD_X + 14, y + 14, text=icon, font=("Arial", 14), anchor="center")

            # Player name
            name_display = f"{name} (You)" if is_me else name
            name_color = "#f1c40f" if is_cur else ("#888" if not alive else "white")
            c.create_text(PAD_X + 28, y + 14, text=name_display,
                          font=("Arial", 10, "bold"), fill=name_color, anchor="w")

            # Accusation tokens (red dots)
            if alive and acc > 0:
                acc_text = f"🔴 {acc} acc"
                c.create_text(W - PAD_X - 4, y + 14, text=acc_text,
                              font=("Arial", 8), fill="#e74c3c", anchor="e")

            # Tryal HP bar
            bar_x = PAD_X + 4
            bar_y = y + ROW_H - 18
            bar_w = W - PAD_X * 2 - 8
            bar_h = 10

            # Background track
            c.create_rectangle(bar_x, bar_y, bar_x + bar_w, bar_y + bar_h,
                                fill="#2c3e50", outline="#445566", width=1)

            if total > 0 and alive:
                ratio = hidden / total
                # Colour: green→yellow→red as cards are revealed
                if ratio > 0.6:
                    fill_color = "#2ecc71"
                elif ratio > 0.3:
                    fill_color = "#f39c12"
                else:
                    fill_color = "#e74c3c"
                fill_w = max(1, int(bar_w * ratio))
                c.create_rectangle(bar_x, bar_y, bar_x + fill_w, bar_y + bar_h,
                                   fill=fill_color, outline="")

            # Label inside / beside bar
            label = f"{hidden}/{total} tryal" if alive else "eliminated"
            label_color = "#aaa" if not alive else "white"
            c.create_text(bar_x + bar_w // 2, bar_y + bar_h // 2,
                          text=label, font=("Arial", 7), fill=label_color, anchor="center")

        # Resize canvas height to fit all players
        total_h = len(players) * ROW_H + 10
        c.config(height=total_h)

    def _refresh_hand(self):
        self.hand_lb.delete(0, tk.END)
        hand = self.game_state.get("hand", [])
        for card in hand:
            self.hand_lb.insert(tk.END, f"  {card}")
        if not hand:
            self.hand_lb.insert(tk.END, "  (no cards)")

    def _refresh_log(self):
        # FIX: keep scroll position — only auto-scroll when already near bottom
        try:
            yview = self.log_text.yview()
            at_bottom = yview[1] >= 0.99
        except Exception:
            at_bottom = True

        self.log_text.delete(1.0, tk.END)
        for entry in self.game_state.get("log", []):
            self.log_text.insert(tk.END, f"{entry}\n")

        if at_bottom:
            self.log_text.see(tk.END)

    def _refresh_turn(self):
        current_id = self.game_state.get("current_player")
        night = self.game_state.get("night_pending", False)
        dawn = self.game_state.get("dawn_pending", False)
        if night or dawn:
            return
        # Confess button is never available during normal turns
        self.accuse_btn.config(state="disabled")
        if current_id == self.player_id:
            self.status_lbl.config(text="🎯 IT'S YOUR TURN!", fg="#f1c40f")
            self.draw_btn.config(state="normal")
            self.end_btn.config(state="normal")
        else:
            cur_name = self.game_state.get("current_player_name", "…")
            self.status_lbl.config(text=f"Waiting for {cur_name}…", fg="white")
            self.draw_btn.config(state="disabled")
            self.end_btn.config(state="disabled")

    # ── Actions ──────────────────────────────────

    def _draw_card(self):
        self.launcher.connection.send(Message(MessageType.DRAW_CARD))
        self.draw_btn.config(state="disabled")

    # FIX: Play a card from hand by double-clicking it
    def _play_selected_card(self, event=None):
        sel = self.hand_lb.curselection()
        if not sel:
            return
        hand = self.game_state.get("hand", [])
        if not hand:
            return
        idx = sel[0]
        card_str = hand[idx] if idx < len(hand) else None
        if card_str is None:
            return

        # Determine if card needs a target
        no_target_cards = []   # cards that need no target (none in this ruleset)
        one_target_cards = ["Accusation", "Evidence", "Testimony", "Asylum", "Piety", "Alibi", "Curse", "Stock", "Arson"]
        two_target_cards = ["Scapegoat", "Robbery"]

        card_name = card_str.split(" [")[0].strip()

        alive_others = [p["name"] for p in self.game_state.get("players", [])
                        if p.get("alive") and p.get("id") != self.player_id]

        if card_name in two_target_cards:
            self._play_card_dialog_two_targets(idx, card_name, alive_others)
        elif card_name in one_target_cards:
            self._play_card_dialog_one_target(idx, card_name, alive_others)
        else:
            # Unknown / no-target card — just send with no target
            self.launcher.connection.send(Message(MessageType.PLAY_CARD, {
                "hand_index": idx,
                "target": None,
                "secondary": None,
            }))

    def _play_card_dialog_one_target(self, idx, card_name, players):
        if not players:
            messagebox.showinfo("No Targets", "No other alive players to target!", parent=self.win)
            return
        dlg = tk.Toplevel(self.win)
        dlg.title(f"Play {card_name}")
        dlg.geometry("520x300")
        dlg.transient(self.win)
        dlg.grab_set()
        self._center(dlg)
        ttk.Label(dlg, text=f"Choose target for {card_name}:", font=("Arial", 14)).pack(pady=26)
        target_var = tk.StringVar()
        ttk.Combobox(dlg, textvariable=target_var, values=players, width=30).pack(pady=8)
        def confirm():
            if target_var.get():
                self.launcher.connection.send(Message(MessageType.PLAY_CARD, {
                    "hand_index": idx,
                    "target": target_var.get(),
                    "secondary": None,
                }))
                dlg.destroy()
        ttk.Button(dlg, text="▶ Play Card", command=confirm).pack(pady=16)

    def _play_card_dialog_two_targets(self, idx, card_name, players):
        if len(players) < 2:
            messagebox.showinfo("Not Enough Targets", "Need at least 2 other alive players!", parent=self.win)
            return
        dlg = tk.Toplevel(self.win)
        dlg.title(f"Play {card_name}")
        dlg.geometry("560x380")
        dlg.transient(self.win)
        dlg.grab_set()
        self._center(dlg)
        ttk.Label(dlg, text=f"Play {card_name} — choose two targets:", font=("Arial", 14)).pack(pady=16)
        ttk.Label(dlg, text="From (source):", font=("Arial", 13)).pack(anchor="w", padx=20)
        t1_var = tk.StringVar()
        ttk.Combobox(dlg, textvariable=t1_var, values=players, width=30).pack(pady=4)
        ttk.Label(dlg, text="To (destination):", font=("Arial", 13)).pack(anchor="w", padx=20)
        t2_var = tk.StringVar()
        ttk.Combobox(dlg, textvariable=t2_var, values=players, width=30).pack(pady=4)
        def confirm():
            if t1_var.get() and t2_var.get() and t1_var.get() != t2_var.get():
                self.launcher.connection.send(Message(MessageType.PLAY_CARD, {
                    "hand_index": idx,
                    "target": t1_var.get(),
                    "secondary": t2_var.get(),
                }))
                dlg.destroy()
            else:
                messagebox.showwarning("Invalid", "Please choose two different players.", parent=dlg)
        ttk.Button(dlg, text="▶ Play Card", command=confirm).pack(pady=16)

    def _confess(self):
        own_tryals = self.game_state.get("own_tryals", [])
        hidden = [t for t in own_tryals if not t.get("revealed")]
        if not hidden:
            messagebox.showinfo("No Cards", "You have no hidden Tryal cards left to sacrifice.", parent=self.win)
            return

        dlg = tk.Toplevel(self.win)
        dlg.title("🙏 Confess")
        dlg.geometry("600x340")
        dlg.configure(bg="#2c3e50")
        dlg.transient(self.win)
        dlg.grab_set()
        self._center(dlg)

        tk.Label(dlg, text="🙏  CONFESS  🙏",
                 bg="#2c3e50", fg="#f39c12", font=("Arial", 14, "bold")).pack(pady=14)
        tk.Label(dlg,
                 text="Sacrifice one hidden Tryal card.\nIf witches target you tonight, you will survive.\nWarning: the card will be revealed to everyone!",
                 bg="#2c3e50", fg="white", font=("Arial", 13), justify="center").pack(pady=6)

        def confirm():
            self.launcher.connection.send(Message(MessageType.CONFESS, {}))
            self.accuse_btn.config(state="disabled")
            dlg.destroy()
            self.status_lbl.config(text="🙏 Confessed — protected tonight.", fg="#f39c12")

        def cancel():
            dlg.destroy()

        btn_row = ttk.Frame(dlg)
        btn_row.pack(pady=14)
        ttk.Button(btn_row, text="🙏 Yes, Confess", command=confirm, width=16).pack(side="left", padx=8)
        ttk.Button(btn_row, text="Cancel",           command=cancel,  width=10).pack(side="left", padx=8)

    def _end_turn(self):
        self.launcher.connection.send(Message(MessageType.NEXT_TURN))
        self.draw_btn.config(state="disabled")
        self.accuse_btn.config(state="disabled")
        self.end_btn.config(state="disabled")
        self.status_lbl.config(text="Turn ended…", fg="white")

    # Dawn dialog — only shown to witches, once per game start
    def _show_dawn_dialog(self):
        if self._dawn_voted:
            return
        all_players = [p["name"] for p in self.game_state.get("players", [])
                       if p.get("alive") and p.get("name") != self.player_name]
        if not all_players:
            return

        dlg = tk.Toplevel(self.win)
        dlg.title("🌅 Dawn – Place the Black Cat")
        dlg.geometry("640x400")
        dlg.configure(bg="#1a1535")
        dlg.transient(self.win)
        dlg.grab_set()
        self._center(dlg)

        tk.Label(dlg, text="🌅  DAWN PHASE  🌅",
                 bg="#1a1535", fg="#e67e22", font=("Arial", 16, "bold")).pack(pady=16)
        tk.Label(dlg, text="As a Witch, secretly choose who receives\nthe Black Cat 🐈 (your Conspiracy target).",
                 bg="#1a1535", fg="white", font=("Arial", 14), justify="center").pack(pady=4)

        target_var = tk.StringVar()
        ttk.Combobox(dlg, textvariable=target_var,
                     values=all_players, width=30).pack(pady=16)

        def confirm():
            target = target_var.get()
            if not target:
                messagebox.showwarning("No target", "Please choose a player for the Black Cat.", parent=dlg)
                return
            self._dawn_voted = True
            self.launcher.connection.send(Message(MessageType.DAWN_VOTE, {"target": target}))
            dlg.destroy()
            self.status_lbl.config(text="🌅 Dawn vote submitted…", fg="#e67e22")

        ttk.Button(dlg, text="🐈 Place Black Cat", command=confirm, width=26).pack(pady=16)

    # FIX: Night kill dialog — only shown to witches
    def _show_night_dialog(self):
        self._night_after_id = None
        if self.night_dialog:
            return
        alive_others = [p["name"] for p in self.game_state.get("players", [])
                        if p.get("alive") and p.get("id") != self.player_id]
        if not alive_others:
            return

        self.night_dialog = tk.Toplevel(self.win)
        self.night_dialog.title("🌙 Night Phase")
        self.night_dialog.geometry("640x380")
        self.night_dialog.configure(bg="#1a1a2e")
        self.night_dialog.transient(self.win)
        self.night_dialog.grab_set()
        self._center(self.night_dialog)

        tk.Label(self.night_dialog, text="🌙  NIGHT PHASE  🌙",
                 bg="#1a1a2e", fg="#9b59b6", font=("Arial", 16, "bold")).pack(pady=16)
        tk.Label(self.night_dialog, text="As a Witch, choose who to eliminate tonight:",
                 bg="#1a1a2e", fg="white", font=("Arial", 14)).pack(pady=4)

        target_var = tk.StringVar()
        ttk.Combobox(self.night_dialog, textvariable=target_var,
                     values=alive_others, width=30).pack(pady=14)

        def confirm_kill():
            victim = target_var.get()
            if not victim:
                messagebox.showwarning("No target", "Please select a player to eliminate.", parent=self.night_dialog)
                return
            self.launcher.connection.send(Message(MessageType.NIGHT_KILL, {"victim": victim}))
            self.night_dialog.destroy()
            self.night_dialog = None
            self.status_lbl.config(text="🌙 Night kill submitted…", fg="#9b59b6")

        ttk.Button(self.night_dialog, text="🔪 Submit Kill Vote",
                   command=confirm_kill, width=26).pack(pady=16)

    def _show_conspiracy_popup(self, transfers):
        dlg = tk.Toplevel(self.win)
        dlg.title("🕯️ Conspiracy!")
        dlg.geometry("560x420")
        dlg.configure(bg="#1a1a2e")
        dlg.transient(self.win)
        dlg.grab_set()

        tk.Label(dlg, text="🕯️  CONSPIRACY  🕯️",
                 bg="#1a1a2e", fg="#e67e22", font=("Arial", 18, "bold")).pack(pady=12, padx=20)
        tk.Label(dlg, text="Tryal cards have secretly changed hands!",
                 bg="#1a1a2e", fg="#bdc3c7", font=("Arial", 13)).pack(pady=2)

        tk.Frame(dlg, bg="#334", height=1).pack(fill="x", padx=16, pady=8)

        # Transfer rows
        frame = tk.Frame(dlg, bg="#1a1a2e")
        frame.pack(padx=16, pady=4, fill="x")

        KIND_ICON = {"Witch": "🔮", "Constable": "⚖️", "Not A Witch": "🏠"}
        KIND_COLOR = {"Witch": "#e74c3c", "Constable": "#3498db", "Not A Witch": "#2ecc71"}

        for t in transfers:
            giver        = t.get("giver", "?")
            receiver     = t.get("receiver", "?")
            card_kind    = t.get("card_kind")   # None unless this player is the receiver
            is_me_giver  = (giver == self.player_name)
            is_me_recv   = (receiver == self.player_name)

            row = tk.Frame(frame, bg="#232d3f", pady=5)
            row.pack(fill="x", pady=3, padx=2)

            giver_color   = "#e67e22" if is_me_giver else "#ecf0f1"
            recv_color    = "#f1c40f" if is_me_recv  else "#ecf0f1"
            giver_font    = ("Arial", 10, "bold") if is_me_giver else ("Arial", 10)
            recv_font     = ("Arial", 10, "bold") if is_me_recv  else ("Arial", 10)

            tk.Label(row, text=giver, bg="#232d3f", fg=giver_color,
                     font=giver_font, width=12, anchor="e").pack(side="left", padx=(8, 2))
            tk.Label(row, text=" ──▶ ", bg="#232d3f",
                     fg="#e67e22", font=("Arial", 13)).pack(side="left")
            tk.Label(row, text=receiver, bg="#232d3f", fg=recv_color,
                     font=recv_font, width=12, anchor="w").pack(side="left", padx=(2, 6))

            # Card badge — shown only to the receiver
            if card_kind:
                icon  = KIND_ICON.get(card_kind, "?")
                color = KIND_COLOR.get(card_kind, "white")
                tk.Label(row, text=f"{icon} {card_kind}", bg="#232d3f",
                         fg=color, font=("Arial", 12, "bold")).pack(side="left", padx=(4, 8))
            elif is_me_giver:
                tk.Label(row, text="(you gave a hidden card)", bg="#232d3f",
                         fg="#7f8c8d", font=("Arial", 12, "italic")).pack(side="left", padx=(4, 8))
            else:
                tk.Label(row, text="[hidden]", bg="#232d3f",
                         fg="#555", font=("Arial", 9)).pack(side="left", padx=(4, 8))

        # Own tryal card list after the transfer
        own_tryals = self.game_state.get("own_tryals", [])
        if own_tryals:
            tk.Frame(dlg, bg="#445", height=1).pack(fill="x", padx=16, pady=8)
            tk.Label(dlg, text="Your Tryal cards after Conspiracy:",
                     bg="#1a1a2e", fg="#bdc3c7", font=("Arial", 10, "bold")).pack(anchor="w", padx=18)

            cards_frame = tk.Frame(dlg, bg="#1a1a2e")
            cards_frame.pack(fill="x", padx=18, pady=6)

            for i, tc in enumerate(own_tryals):
                kind     = tc.get("kind", "?")
                revealed = tc.get("revealed", False)
                icon     = KIND_ICON.get(kind, "?")
                color    = KIND_COLOR.get(kind, "white")
                # Find if this is a newly received card
                just_received = any(
                    t.get("receiver") == self.player_name and t.get("card_kind") == kind
                    for t in transfers
                )
                if revealed:
                    label = f"{icon} {kind}  (revealed)"
                    fg = color
                else:
                    label = f"[?] face-down"
                    fg = "#7f8c8d"
                    # Highlight the card the player just received (last unrevealed one added)
                    if just_received and i == len(own_tryals) - 1:
                        label = f"[?] face-down  ← just received"
                        fg = "#f1c40f"

                tk.Label(cards_frame, text=f"  #{i+1}  {label}",
                         bg="#1a1a2e", fg=fg, font=("Arial", 13),
                         anchor="w").pack(fill="x")

        tk.Frame(dlg, bg="#334", height=1).pack(fill="x", padx=16, pady=8)

        # If this player just received a Witch tryal, update their role so the
        # Night kill dialog will appear for them going forward.
        for t in transfers:
            if t.get("receiver") == self.player_name and t.get("card_kind") == "Witch":
                if not self.is_witch:
                    self.is_witch = True
                    if self.is_constable:
                        self.role = "Witch+Constable"
                        self.role_lbl.config(text="🔮⚖️ Witch+Constable", fg="#e74c3c")
                    else:
                        self.role = "Witch"
                        self.role_lbl.config(text="🔮 Witch", fg="#e74c3c")
                break
        for t in transfers:
            if t.get("receiver") == self.player_name and t.get("card_kind") == "Constable":
                if not self.is_constable:
                    self.is_constable = True
                    if self.is_witch:
                        self.role = "Witch+Constable"
                        self.role_lbl.config(text="🔮⚖️ Witch+Constable", fg="#e74c3c")
                    else:
                        self.role = "Constable"
                        self.role_lbl.config(text="⚖️ Constable", fg="#3498db")
                break

        ttk.Button(dlg, text="Understood", command=dlg.destroy).pack(pady=14)

        self._center(dlg)

    def close_night_dialog(self):
        if self._night_after_id is not None:
            self.win.after_cancel(self._night_after_id)
            self._night_after_id = None
        if self._constable_after_id is not None:
            self.win.after_cancel(self._constable_after_id)
            self._constable_after_id = None
        if self.night_dialog:
            try:
                self.night_dialog.destroy()
            except Exception:
                pass
            self.night_dialog = None

    def show_confess_phase(self, seconds):
        """Show the confess phase dialog to all alive players after night submissions."""
        if self.confess_phase_dialog:
            return  # already showing
        # Witches don't confess — just show them a waiting status
        if self.is_witch:
            self.status_lbl.config(text="🕯️ Confess phase – townspeople deciding…", fg="#e67e22")
            return

        already_confessed = self.game_state.get("already_confessed", False)
        own_tryals = self.game_state.get("own_tryals", [])
        has_hidden = any(not t.get("revealed") for t in own_tryals)

        dlg = tk.Toplevel(self.win)
        dlg.title("🕯️ Confess Phase")
        dlg.geometry("660x460")
        dlg.configure(bg="#1a1a2e")
        dlg.transient(self.win)
        dlg.grab_set()
        self._center(dlg)
        dlg.protocol("WM_DELETE_WINDOW", lambda: None)  # prevent closing manually
        self.confess_phase_dialog = dlg

        tk.Label(dlg, text="🕯️  CONFESS PHASE  🕯️",
                 bg="#1a1a2e", fg="#e67e22", font=("Arial", 18, "bold")).pack(pady=16)
        tk.Label(dlg,
                 text="Witches and Constable have made their choices.\nYou may sacrifice one hidden Tryal card\nto protect yourself from being killed tonight.",
                 bg="#1a1a2e", fg="#bdc3c7", font=("Arial", 13), justify="center").pack(pady=6)

        # Countdown label
        self._confess_countdown = seconds
        countdown_lbl = tk.Label(dlg, text=f"Time remaining: {seconds}s",
                                 bg="#1a1a2e", fg="#f39c12", font=("Arial", 11, "bold"))
        countdown_lbl.pack(pady=4)

        def tick():
            if not dlg.winfo_exists():
                return
            self._confess_countdown -= 1
            if self._confess_countdown <= 0:
                countdown_lbl.config(text="Time's up!")
            else:
                countdown_lbl.config(text=f"Time remaining: {self._confess_countdown}s")
                dlg.after(1000, tick)

        dlg.after(1000, tick)

        btn_frame = ttk.Frame(dlg)
        btn_frame.pack(pady=14)

        def do_confess():
            self.launcher.connection.send(Message(MessageType.CONFESS, {}))
            self.accuse_btn.config(state="disabled")
            self.status_lbl.config(text="🙏 Confessed — protected tonight.", fg="#f39c12")
            self.close_confess_phase_dialog()

        def do_skip():
            self.launcher.connection.send(Message(MessageType.CONFESS_DONE, {}))
            self.status_lbl.config(text="🌙 Skipped confession.", fg="#9b59b6")
            self.close_confess_phase_dialog()

        if already_confessed or not has_hidden:
            # Nothing to decide — auto-skip silently and notify server
            self.confess_phase_dialog = None  # don't track the dialog
            dlg.destroy()
            self.launcher.connection.send(Message(MessageType.CONFESS_DONE, {}))
            self.status_lbl.config(text="🌙 Night phase – waiting for resolution…", fg="#9b59b6")
        else:
            ttk.Button(btn_frame, text="🙏 Confess (reveal a Tryal card)",
                       command=do_confess, width=30).pack(pady=4)
            ttk.Button(btn_frame, text="Stay Silent (take the risk)",
                       command=do_skip, width=30).pack(pady=4)

    def close_confess_phase_dialog(self):
        if self.confess_phase_dialog:
            try:
                self.confess_phase_dialog.destroy()
            except Exception:
                pass
            self.confess_phase_dialog = None

    def _show_constable_dialog(self):
        self._constable_after_id = None
        if self.night_dialog:
            return
        alive_others = [p["name"] for p in self.game_state.get("players", [])
                        if p.get("alive") and p.get("name") != self.player_name]
        if not alive_others:
            return

        self.night_dialog = tk.Toplevel(self.win)
        self.night_dialog.title("⚖️ Constable – Night Phase")
        self.night_dialog.geometry("640x420")
        self.night_dialog.configure(bg="#1a2a3a")
        self.night_dialog.transient(self.win)
        self.night_dialog.grab_set()
        self._center(self.night_dialog)

        tk.Label(self.night_dialog, text="⚖️  CONSTABLE – NIGHT PHASE  ⚖️",
                 bg="#1a2a3a", fg="#3498db", font=("Arial", 18, "bold")).pack(pady=16)
        tk.Label(self.night_dialog,
                 text="Choose one player to protect with your Gavel.\nThey cannot be killed by witches tonight.",
                 bg="#1a2a3a", fg="white", font=("Arial", 14), justify="center").pack(pady=4)

        target_var = tk.StringVar()
        ttk.Combobox(self.night_dialog, textvariable=target_var,
                     values=alive_others, width=30).pack(pady=14)

        def confirm_save():
            target = target_var.get()
            if not target:
                messagebox.showwarning("No target", "Please select a player to protect.", parent=self.night_dialog)
                return
            self.launcher.connection.send(Message(MessageType.NIGHT_SAVE, {"save": target}))
            self.night_dialog.destroy()
            self.night_dialog = None
            self.status_lbl.config(text="⚖️ Constable save submitted…", fg="#3498db")

        def skip_save():
            self.launcher.connection.send(Message(MessageType.NIGHT_SAVE, {"save": None}))
            self.night_dialog.destroy()
            self.night_dialog = None
            self.status_lbl.config(text="🌙 Night phase – watching…", fg="#9b59b6")

        btn_row = ttk.Frame(self.night_dialog)
        btn_row.pack(pady=16)
        ttk.Button(btn_row, text="🛡️ Protect Player", command=confirm_save, width=18).pack(side="left", padx=8)
        ttk.Button(btn_row, text="Skip (no save)", command=skip_save, width=14).pack(side="left", padx=8)

    def _show_voting_dialog(self, accused_name):
        self._vote_after_id = None
        if self.voting_dialog:
            return  # Dialog already open, do not open another
        self.voting_dialog = tk.Toplevel(self.win)
        self.voting_dialog.title("Vote!")
        self.voting_dialog.geometry("600x320")
        self.voting_dialog.transient(self.win)
        self.voting_dialog.grab_set()
        self._center(self.voting_dialog)
        ttk.Label(self.voting_dialog, text=f"⚖️  {accused_name} is on trial!  ⚖️",
                  font=("Arial", 16, "bold")).pack(pady=22)
        ttk.Label(self.voting_dialog, text="Do you believe they are a witch?",
                  font=("Arial", 14)).pack(pady=6)
        bf = ttk.Frame(self.voting_dialog)
        bf.pack(pady=22)
        def vote(guilty):
            self._has_voted = True          # prevent dialog from re-appearing after vote
            self.launcher.connection.send(Message(MessageType.VOTE, {"guilty": guilty}))
            if self.voting_dialog:
                self.voting_dialog.destroy()
                self.voting_dialog = None
            self.waiting_for_vote = False
        ttk.Button(bf, text="🔴 GUILTY",     command=lambda: vote(True),  width=20).pack(side="left", padx=14)
        ttk.Button(bf, text="🟢 NOT GUILTY", command=lambda: vote(False), width=20).pack(side="left", padx=14)

    def close_voting(self):
        self.waiting_for_vote = False
        self._has_voted = False   # reset for next accusation round
        if self._vote_after_id is not None:
            self.win.after_cancel(self._vote_after_id)
            self._vote_after_id = None
        if self.voting_dialog:
            try:
                self.voting_dialog.destroy()
            except Exception:
                pass
            self.voting_dialog = None

    # ── Chat ─────────────────────────────────────

    def add_chat(self, sender, msg):
        self.chat_text.insert(tk.END, f"{sender}: {msg}\n" if sender else f"{msg}\n")
        self.chat_text.see(tk.END)

    def _send_chat(self):
        text = self.chat_entry.get().strip()
        if text and self.launcher.connection:
            self.launcher.connection.send(Message(MessageType.CHAT_MESSAGE, {"text": text}))
            self.chat_entry.delete(0, tk.END)

    # ── Game over / close ────────────────────────

    def show_game_over(self, winner):
        msg = f"Game Over!\n{winner} wins!\n\n"
        if winner == "Witches" and self.is_witch:
            msg += "Congratulations! Your coven triumphed! 🔮"
        elif winner == "Town" and not self.is_witch:
            msg += "Well done! Salem is cleansed! 🏠"
        else:
            msg += "Better luck next time!"
        messagebox.showinfo("Game Over", msg, parent=self.win)
        self.draw_btn.config(state="disabled")
        self.accuse_btn.config(state="disabled")
        self.end_btn.config(state="disabled")
        self.status_lbl.config(text=f"🏆 {winner} wins!", fg="#f39c12")
        # Save game using function from 'utils' module
        save_game_result(msg)

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
    def __init__(self):
        self.root = tk.Tk()
        self.root.title("Salem 1692 – Launcher")
        self.root.geometry("1040x820")
        self.root.minsize(920, 760)
        self.root.configure(bg=APP_BG)
        self.style = ttk.Style(self.root)
        self._configure_theme()

        self.local_ip = get_local_ip()

        # ── server state ──
        self.server = None
        self.game = None
        self.players_ready = {}
        self.game_started = False
        self.voting_in_progress = False
        self.night_kill_votes = {}
        self.constable_save_vote = None
        self.dawn_votes = {}
        self.confess_phase_active = False   # True during confess window
        self.confess_phase_timer = None     # root.after id for auto-resolve
        self.confess_responses = set()      # client ids who responded (confess or skip)

        # ── client state ──
        self.connection = None
        self.player_id = None
        self.player_name = None
        self.role = None
        self.is_witch = False
        self.is_constable = False
        self.game_state = None
        self.waiting_for_vote = False
        self.voting_dialog = None
        self.is_ready = False
        self.game_window = None

        self._build_ui()

    # ══════════════════════════════════════════
    #  UI construction
    # ══════════════════════════════════════════

    def _configure_theme(self):
        self.style.theme_use("clam")
        self.style.configure(".", background=APP_BG, foreground=TEXT_MAIN, fieldbackground="#101924")
        self.style.configure("TFrame", background=APP_BG)
        self.style.configure("Surface.TFrame", background=SURFACE_BG)
        self.style.configure("TLabel", background=APP_BG, foreground=TEXT_MAIN, font=("Segoe UI", 10))
        self.style.configure("Status.TLabel", background=PANEL_BG, foreground=TEXT_MUTED, padding=(12, 8))
        self.style.configure("TEntry", fieldbackground="#101924", foreground=TEXT_MAIN, padding=7)
        self.style.configure("TCombobox", fieldbackground="#101924", foreground=TEXT_MAIN, padding=6)
        self.style.configure("TNotebook", background=APP_BG, borderwidth=0)
        self.style.configure("TNotebook.Tab", background=SURFACE_BG, foreground=TEXT_MUTED,
                             padding=(18, 10), font=("Segoe UI Semibold", 10))
        self.style.map("TNotebook.Tab", background=[("selected", PANEL_BG)],
                       foreground=[("selected", TEXT_MAIN)])
        self.style.configure("App.TLabelframe", background=SURFACE_BG, borderwidth=1, relief="solid")
        self.style.configure("App.TLabelframe.Label", background=SURFACE_BG,
                             foreground=ACCENT_GOLD, font=("Segoe UI Semibold", 11))
        self.style.configure("Game.TPanedwindow", background=APP_BG, sashwidth=10)
        self.style.configure("Accent.TButton", background=ACCENT_GOLD, foreground="#11161d",
                             borderwidth=0, padding=(14, 9), font=("Segoe UI Semibold", 10))
        self.style.configure("Secondary.TButton", background="#2e4863", foreground=TEXT_MAIN,
                             borderwidth=0, padding=(14, 9), font=("Segoe UI Semibold", 10))
        self.style.configure("Danger.TButton", background="#6a2d35", foreground=TEXT_MAIN,
                             borderwidth=0, padding=(14, 9), font=("Segoe UI Semibold", 10))
        self.style.map("Accent.TButton", background=[("active", "#ffd36a"), ("disabled", "#5f5640")],
                       foreground=[("disabled", "#d4c7a0")])
        self.style.map("Secondary.TButton", background=[("active", "#3b5d80"), ("disabled", "#34404d")],
                       foreground=[("disabled", "#8391a0")])
        self.style.map("Danger.TButton", background=[("active", "#88414b"), ("disabled", "#433238")],
                       foreground=[("disabled", "#99878b")])

    def _build_ui(self):
        notebook = ttk.Notebook(self.root)
        notebook.pack(fill="both", expand=True, padx=12, pady=12)

        host_frame = ttk.Frame(notebook)
        notebook.add(host_frame, text="🏠  Host (Server)")
        self._build_host_tab(host_frame)

        player_frame = ttk.Frame(notebook)
        notebook.add(player_frame, text="🎮  Player (Client)")
        self._build_player_tab(player_frame)

        self.status_var = tk.StringVar(value="Ready")
        ttk.Label(self.root, textvariable=self.status_var, style="Status.TLabel").pack(
            side="bottom", fill="x"
        )

    # ─── HOST TAB ───────────────────────────────

    def _build_host_tab(self, parent):
        main = ttk.Frame(parent, style="Surface.TFrame")
        main.pack(fill="both", expand=True, padx=10, pady=10)

        ctrl = ttk.LabelFrame(main, text="Server Control", padding=12, style="App.TLabelframe")
        ctrl.pack(fill="x", pady=4)

        pf = ttk.Frame(ctrl)
        pf.pack(fill="x", pady=4)
        ttk.Label(pf, text="Port:").pack(side="left", padx=4)
        self.srv_port_var = tk.StringVar(value="5555")
        ttk.Entry(pf, textvariable=self.srv_port_var, width=8).pack(side="left", padx=4)

        btn_row = ttk.Frame(ctrl)
        btn_row.pack(pady=4)
        self.srv_start_btn = ttk.Button(btn_row, text="▶ Start Server", command=self.start_server,
                                        style="Accent.TButton")
        self.srv_start_btn.pack(side="left", padx=4)
        self.srv_stop_btn = ttk.Button(btn_row, text="■ Stop Server", command=self.stop_server,
                                       state="disabled", style="Danger.TButton")
        self.srv_stop_btn.pack(side="left", padx=4)
        self.srv_game_btn = ttk.Button(btn_row, text="🎮 Start Game", command=self.start_game,
                                       state="disabled", style="Secondary.TButton")
        self.srv_game_btn.pack(side="left", padx=4)

        self.host_join_btn = ttk.Button(
            ctrl, text="⚡ Also Join as Player (same machine)",
            command=self._host_join_self, state="disabled", style="Secondary.TButton"
        )
        self.host_join_btn.pack(pady=4)

        info = ttk.LabelFrame(main, text="Connection Info", padding=12, style="App.TLabelframe")
        info.pack(fill="x", pady=4)
        ttk.Label(info, text=f"Your Local IP: {self.local_ip}",
                  font=("Arial", 10, "bold"), foreground="blue").pack(anchor="w")
        ttk.Label(info, text=(
            "• Same machine → localhost / 127.0.0.1\n"
            "• Same Wi-Fi   → use IP above\n"
            "• Internet     → public IP + port forwarding"
        ), justify="left", foreground="gray").pack(anchor="w", pady=4)

        pl = ttk.LabelFrame(main, text="Connected Players", padding=12, style="App.TLabelframe")
        pl.pack(fill="x", pady=4)
        self.srv_players_lb = tk.Listbox(pl, height=7)
        style_listbox_widget(self.srv_players_lb, height=7)
        self.srv_players_lb.pack(fill="x")
        self.srv_count_var = tk.StringVar(value="Players: 0")
        ttk.Label(pl, textvariable=self.srv_count_var).pack()

        log = ttk.LabelFrame(main, text="Server Log", padding=12, style="App.TLabelframe")
        log.pack(fill="both", expand=True, pady=4)
        self.srv_log = scrolledtext.ScrolledText(log, height=12, width=80, font=("Consolas", 10))
        style_text_widget(self.srv_log)
        self.srv_log.pack(fill="both", expand=True)

    # ─── PLAYER TAB ─────────────────────────────

    def _build_player_tab(self, parent):
        main = ttk.Frame(parent, style="Surface.TFrame")
        main.pack(fill="both", expand=True, padx=10, pady=10)

        conn = ttk.LabelFrame(main, text="Connect to Server", padding=12, style="App.TLabelframe")
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
        ttk.Entry(row2, textvariable=self.cli_name_var, width=30).pack(side="left", padx=4)

        btn_row = ttk.Frame(conn)
        btn_row.pack(pady=4)
        self.cli_connect_btn = ttk.Button(btn_row, text="🔌 Connect", command=self.connect_to_server,
                                          style="Accent.TButton")
        self.cli_connect_btn.pack(side="left", padx=4)
        self.cli_disconnect_btn = ttk.Button(btn_row, text="⛔ Disconnect",
                                             command=self.disconnect_from_server, state="disabled",
                                             style="Danger.TButton")
        self.cli_disconnect_btn.pack(side="left", padx=4)
        self.cli_ready_btn = ttk.Button(btn_row, text="✅ Ready", command=self.toggle_ready,
                                        state="disabled", width=14, style="Secondary.TButton")
        self.cli_ready_btn.pack(side="left", padx=4)

        # Hidden buttons kept for legacy game-logic references
        self.cli_draw_btn = ttk.Button(self.root, text="🎴 Draw Card", command=self.draw_card,
                                       state="disabled", width=14)
        self.cli_accuse_btn = ttk.Button(self.root, text="⚖️ Accuse", command=self.accuse_player,
                                         state="disabled", width=14)
        self.cli_end_btn = ttk.Button(self.root, text="⏭ End Turn", command=self.end_turn,
                                      state="disabled", width=14)

        pl = ttk.LabelFrame(main, text="Players", padding=12, style="App.TLabelframe")
        pl.pack(fill="x", pady=4)
        self.cli_players_lb = tk.Listbox(pl, height=6)
        style_listbox_widget(self.cli_players_lb, height=6)
        self.cli_players_lb.pack(fill="x")

        nb = ttk.Notebook(main)
        nb.pack(fill="both", expand=True, pady=4)

        chat_fr = ttk.Frame(nb)
        nb.add(chat_fr, text="💬 Chat")
        ci = ttk.Frame(chat_fr)
        ci.pack(side="bottom", fill="x", pady=3)
        self.cli_chat_entry = ttk.Entry(ci)
        self.cli_chat_entry.pack(side="left", fill="x", expand=True, padx=4)
        self.cli_chat_entry.bind("<Return>", lambda e: self.send_chat())
        ttk.Button(ci, text="Send", command=self.send_chat, style="Accent.TButton").pack(side="right", padx=4)
        self.cli_chat_text = scrolledtext.ScrolledText(chat_fr, height=10, state="disabled", font=("Consolas", 10))
        style_text_widget(self.cli_chat_text, height=10)
        self.cli_chat_text.pack(fill="both", expand=True)

        log_fr = ttk.Frame(nb)
        nb.add(log_fr, text="📜 Log")
        self.cli_log_text = scrolledtext.ScrolledText(log_fr, height=10, font=("Consolas", 10))
        style_text_widget(self.cli_log_text, height=10)
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
            try:
                self._broadcast(Message(MessageType.CHAT_MESSAGE, {
                    "text": "🔴 SERVER CLOSED – The host has stopped the server.",
                    "server_closing": True,
                }))
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
        self.night_kill_votes.clear()
        self.constable_save_vote = None
        self.dawn_votes = {}
        self.confess_phase_active = False
        if self.confess_phase_timer:
            self.root.after_cancel(self.confess_phase_timer)
            self.confess_phase_timer = None
        self.confess_responses = set()
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

            if client_id not in self.players_ready:
                self.players_ready[client_id] = {"name": pname, "ready": False}
                self._srv_update_players()
                self._srv_log(f"✓ {pname} joined")
                players = self._player_list()
                for cid in list(self.server.clients):
                    self.server.send_to_client(cid, Message(MessageType.PLAYER_LIST, {"players": players}))
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

        # FIX: Handle PLAY_CARD from client
        elif message.type == MessageType.PLAY_CARD:
            if self.game_started and self.game and not self.voting_in_progress:
                hand_index = message.data.get("hand_index", 0)
                target = message.data.get("target")
                secondary = message.data.get("secondary")
                # Validate it's this player's turn
                current = self.game.get_current_player()
                if not current or current.id != client_id:
                    self.server.send_to_client(client_id, Message(MessageType.ERROR, {
                        "text": "It's not your turn."
                    }))
                    return
                success, result = self.game.play_card(hand_index, target, secondary)
                self.server.send_to_client(client_id, Message(MessageType.PLAY_CARD, {
                    "success": success,
                    "message": result,
                }))
                self._srv_log(f"PLAY_CARD: {result}")
                self._broadcast_game_state()
                if self.game.winner:
                    self._broadcast(Message(MessageType.GAME_OVER, {"winner": self.game.winner}))
                    self.game_started = False

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

        # FIX: Handle NIGHT_KILL votes from witches
        elif message.type == MessageType.NIGHT_KILL:
            if self.game_started and self.game and self.game.night_pending:
                victim_name = message.data.get("victim")
                sender_name = self.server.get_client_name(client_id)
                # Only accept votes from alive witches
                witch_player = self.game._get_player_by_id(client_id)
                if witch_player and witch_player.alive and witch_player.is_witch():
                    self.night_kill_votes[client_id] = victim_name
                    self._srv_log(f"🌙 Night vote from {sender_name}: → {victim_name}")
                    # Check if all witches have voted
                    alive_witches = [p for p in self.game.players if p.alive and p.is_witch()]
                    if len(self.night_kill_votes) >= len(alive_witches):
                        self._try_resolve_night()

        # Constable submits their save choice
        elif message.type == MessageType.NIGHT_SAVE:
            if self.game_started and self.game and self.game.night_pending:
                constable_player = self.game._get_player_by_id(client_id)
                if constable_player and constable_player.alive and constable_player.currently_has_constable():
                    save_target = message.data.get("save")  # may be None (skip)
                    self.constable_save_vote = save_target if save_target else ""  # "" = constable submitted, chose no save
                    sender_name = self.server.get_client_name(client_id)
                    self._srv_log(f"⚖️ Constable {sender_name} protects: {save_target or '(no one)'}")
                    # Store on game object so get_game_state can report it
                    self.game.constable_save_vote = save_target
                    self._broadcast_game_state()
                    self._try_resolve_night()

        # Witches vote on Black Cat placement during Dawn
        elif message.type == MessageType.DAWN_VOTE:
            if self.game_started and self.game and self.game.dawn_pending:
                witch_player = self.game._get_player_by_id(client_id)
                if witch_player and witch_player.alive and witch_player.is_witch():
                    target_name = message.data.get("target")
                    if target_name:
                        self.dawn_votes[client_id] = target_name
                        sender_name = self.server.get_client_name(client_id)
                        self._srv_log(f"🐈 Dawn vote from {sender_name}: Black Cat → {target_name}")
                        alive_witches = [p for p in self.game.players if p.alive and p.is_witch()]
                        if len(self.dawn_votes) >= len(alive_witches):
                            self._resolve_dawn()

        # Player confesses (or we receive skip via CONFESS_DONE) during confess phase
        elif message.type == MessageType.CONFESS:
            if self.game_started and self.game and self.confess_phase_active:
                success, result = self.game.confess(client_id)
                self.confess_responses.add(client_id)
                self._srv_log(f"🙏 {result}")
                self._broadcast(Message(MessageType.CHAT_MESSAGE, {"text": f"🙏 {result}"}))
                self._broadcast_game_state()
                self._check_confess_phase_complete()

        elif message.type == MessageType.CONFESS_DONE:
            # Player chose to skip confessing
            if self.game_started and self.game and self.confess_phase_active:
                self.confess_responses.add(client_id)
                self._check_confess_phase_complete()

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
        try:
            if self.server and client_id in self.server.clients:
                self.server.remove_client(client_id)
        except Exception as e:
            self._srv_log(f"Kick error for {client_id}: {e}")

    def _start_voting_phase(self):
        self.voting_in_progress = True
        accused_name = self.game.accused_player.name if self.game.accused_player else "?"
        accused_by = self.game.accused_by.name if self.game.accused_by else "Someone"
        self._broadcast(Message(MessageType.CHAT_MESSAGE, {
            "text": f"🔔 VOTING – {accused_name} accused by {accused_by}! All must vote! 🔔"
        }))
        self._srv_log(f"VOTING: {accused_name} is on trial")
        self._broadcast_game_state()

    def _resolve_dawn(self):
        """Tally witch dawn votes and place the Black Cat on the majority target."""
        from collections import Counter
        counts = Counter(self.dawn_votes.values())
        target_name = counts.most_common(1)[0][0]
        self.dawn_votes.clear()
        success, msg = self.game.place_black_cat(target_name)
        self._srv_log(f"🐈 {msg}")
        self._broadcast(Message(MessageType.CHAT_MESSAGE, {"text": f"🐈 {msg}"}))
        self._broadcast_game_state()

    def _resolve_accusation(self):
        success, msg, winner = self.game.resolve_accusation()
        self._broadcast(Message(MessageType.RESOLVE_ACCUSATION, {
            "message": msg,
            "eliminated_player": None,
        }))
        self._srv_log(msg)
        if winner:
            self._broadcast(Message(MessageType.GAME_OVER, {"winner": winner}))
            self._srv_log(f"🏆 GAME OVER! {winner} wins!")
            self.game_started = False
        self.voting_in_progress = False
        self._broadcast_game_state()

    # Resolve night once both witches AND the constable (if alive) have submitted
    def _try_resolve_night(self):
        if not self.game or not self.game.night_pending:
            return
        alive_witches = [p for p in self.game.players if p.alive and p.is_witch()]
        alive_constables = [p for p in self.game.players if p.alive and p.currently_has_constable()]
        witches_ready = len(self.night_kill_votes) >= len(alive_witches)
        constable_ready = (not alive_constables) or (self.constable_save_vote is not None)
        if witches_ready and constable_ready and not self.confess_phase_active:
            self._start_confess_phase()

    def _start_confess_phase(self):
        """Open a timed window for all players to confess before night resolves."""
        self.confess_phase_active = True
        self.confess_responses = set()
        CONFESS_SECONDS = 20
        self._srv_log(f"🕯️ Confess phase — players have {CONFESS_SECONDS}s to confess!")
        self._broadcast(Message(MessageType.CONFESS_PHASE, {"seconds": CONFESS_SECONDS}))
        # Auto-resolve after timer
        self.confess_phase_timer = self.root.after(
            CONFESS_SECONDS * 1000, self._end_confess_phase
        )

    def _end_confess_phase(self):
        """Timer expired or all players responded — proceed to night resolution."""
        if self.confess_phase_timer:
            self.root.after_cancel(self.confess_phase_timer)
            self.confess_phase_timer = None
        self.confess_phase_active = False
        self.confess_responses = set()
        self._resolve_night()

    def _check_confess_phase_complete(self):
        """End confess phase early if every alive non-witch player has responded."""
        if not self.game or not self.confess_phase_active:
            return
        eligible = [p for p in self.game.players if p.alive and not p.is_witch()]
        if len(self.confess_responses) >= len(eligible):
            self._srv_log("🕯️ All players responded — resolving night early.")
            self._end_confess_phase()

    def _resolve_night(self):
        if not self.night_kill_votes:
            return
        from collections import Counter
        counts = Counter(self.night_kill_votes.values())
        victim_name = counts.most_common(1)[0][0]
        self.night_kill_votes.clear()

        # constable_save_vote: None = not submitted yet / no constable, "" = skip, else a name
        save_name = self.constable_save_vote if self.constable_save_vote else None
        self.constable_save_vote = None
        self.game.constable_save_vote = None

        success, result = self.game.resolve_night(kill_name=victim_name, save_name=save_name)
        self._srv_log(f"🌙 Night resolved: {result}")
        self._broadcast(Message(MessageType.CHAT_MESSAGE, {"text": f"🌙 {result}"}))

        # Close night dialog on all clients
        self._broadcast(Message(MessageType.NIGHT_RESOLVED, {"result": result}))

        if self.game.winner:
            self._broadcast(Message(MessageType.GAME_OVER, {"winner": self.game.winner}))
            self._srv_log(f"🏆 GAME OVER! {self.game.winner} wins!")
            self.game_started = False

        self._broadcast_game_state()

    def _broadcast_game_state(self):
        for cid in self.server.clients:
            state = self.game.get_game_state(for_player_id=cid)
            state["hand"] = [str(c) for c in self.game.get_player_hand(cid)]
            if self.voting_in_progress and self.game.accused_player:
                state["voting_info"] = {
                    "accused": self.game.accused_player.name,
                    "votes_cast": len(self.game.votes_cast),
                    "guilty_votes": sum(1 for v in self.game.votes_cast.values() if v),
                }
            self.server.send_to_client(cid, Message(MessageType.GAME_STATE, {"state": state}))
        # Clear transfers after broadcast — popup should show only once per conspiracy
        self.game.last_conspiracy_transfers = []

    def _broadcast(self, message):
        if self.server:
            self.server.broadcast(message)

    def _update_start_btn(self):
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

    def _host_join_self(self):
        port = self.srv_port_var.get()
        self.cli_host_var.set("127.0.0.1")
        self.cli_port_var.set(port)
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
            self.root.after(0, self._on_server_closed)
        else:
            self.root.after(0, self._handle_server_message, message)

    def _on_name_taken(self, taken_name, server_message):
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
        if not self.connection:
            return
        try:
            self.connection.disconnect()
        except Exception:
            pass
        self.connection = None

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

        self.cli_connect_btn.config(state="normal")
        self.cli_disconnect_btn.config(state="disabled")
        self.cli_ready_btn.config(text="✅ Ready", state="disabled")
        self.cli_draw_btn.config(state="disabled")
        self.cli_accuse_btn.config(state="disabled")
        self.cli_end_btn.config(state="disabled")
        self.cli_players_lb.delete(0, tk.END)
        self.status_var.set("⛔ Disconnected – Host stopped the server")
        self._cli_log("⛔ The host has stopped the server.")
        self._add_chat("System", "⛔ The server has been closed by the host. You have been disconnected.")
        messagebox.showwarning("Server Closed", "The host has stopped the server.\n\nYou have been disconnected.")

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

        # FIX: show play-card result
        elif message.type == MessageType.PLAY_CARD:
            parent = self.game_window.win if self.game_window else self.root
            if message.data.get("success"):
                self._cli_log(f"▶ {message.data.get('message')}")
            else:
                messagebox.showerror("Cannot Play Card", message.data.get("message", ""), parent=parent)

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

        # FIX: close night dialog on all clients after night resolves
        elif message.type == MessageType.NIGHT_RESOLVED:
            result = message.data.get("result", "")
            self._cli_log(f"🌙 {result}")
            if self.game_window:
                self.game_window.close_night_dialog()
                self.game_window.close_confess_phase_dialog()

        elif message.type == MessageType.CONFESS_PHASE:
            seconds = message.data.get("seconds", 20)
            if self.game_window:
                self.game_window.show_confess_phase(seconds)

        elif message.type == MessageType.GAME_OVER:
            winner = message.data.get("winner")
            self._cli_log(f"🏆 GAME OVER! {winner} wins!")
            if self.game_window:
                self.game_window.show_game_over(winner)
            else:
                msg = f"Game Over!\n{winner} wins!\n\n"
                if winner == "Witches" and self.is_witch:
                    msg += "Congratulations! Your coven triumphed!"
                elif winner == "Town" and not self.is_witch:
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

    def _update_display(self):
        if not self.game_state:
            return
        if "log" in self.game_state:
            self.cli_log_text.delete(1.0, tk.END)
            for entry in self.game_state["log"]:
                self.cli_log_text.insert(tk.END, f"{entry}\n")
            self.cli_log_text.see(tk.END)
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
        dlg.geometry("520x300")
        dlg.transient(self.root)
        dlg.update_idletasks()
        geo = dlg.geometry()
        try:
            w, h = [int(v) for v in geo.split('+')[0].split('x')]
        except (ValueError, IndexError):
            w, h = dlg.winfo_reqwidth(), dlg.winfo_reqheight()
        sw, sh = dlg.winfo_screenwidth(), dlg.winfo_screenheight()
        dlg.geometry(f"{w}x{h}+{(sw-w)//2}+{(sh-h)//2}")
        ttk.Label(dlg, text="Select player to accuse:", font=("Arial", 14)).pack(pady=26)
        accused_var = tk.StringVar()
        ttk.Combobox(dlg, textvariable=accused_var, values=players, width=20).pack(pady=14)
        def confirm():
            if accused_var.get():
                self.connection.send(Message(MessageType.ACCUSE, {"accused": accused_var.get()}))
                self.status_var.set(f"Accusing {accused_var.get()}…")
                dlg.destroy()
        ttk.Button(dlg, text="⚖️ Accuse", command=confirm).pack(pady=26)

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