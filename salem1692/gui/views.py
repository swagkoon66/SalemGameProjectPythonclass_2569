"""
GUI Views for Salem 1692
Updated for Salem-style rules
"""

import tkinter as tk
from tkinter import ttk, messagebox, scrolledtext
import time


class SetupView(ttk.Frame):
    """Game setup view"""

    def __init__(self, parent, app):
        super().__init__(parent)
        self.app = app
        self.player_entries = []
        self.setup_ui()

    def setup_ui(self):
        title_frame = ttk.Frame(self)
        title_frame.pack(pady=20)

        ttk.Label(title_frame, text="Salem 1692", font=("Arial", 24, "bold")).pack()
        ttk.Label(
            title_frame,
            text="Salem-rule version",
            font=("Arial", 12),
        ).pack()

        input_frame = ttk.LabelFrame(self, text="Player Setup", padding=10)
        input_frame.pack(pady=20, padx=50, fill="both")

        count_frame = ttk.Frame(input_frame)
        count_frame.pack(pady=10)

        ttk.Label(count_frame, text="Number of Players:").pack(side="left", padx=5)

        self.player_count = tk.IntVar(value=4)
        count_spinbox = ttk.Spinbox(
            count_frame,
            from_=4,
            to=12,
            textvariable=self.player_count,
            width=5,
            command=self.update_player_fields,
        )
        count_spinbox.pack(side="left", padx=5)

        ttk.Button(count_frame, text="Update", command=self.update_player_fields).pack(
            side="left", padx=5
        )

        self.names_frame = ttk.Frame(input_frame)
        self.names_frame.pack(pady=10)

        self.update_player_fields()

        button_frame = ttk.Frame(self)
        button_frame.pack(pady=20)

        ttk.Button(button_frame, text="Start Game", command=self.start_game).pack(
            side="left", padx=10
        )

        # KOON REMOVED
        # ttk.Button(
        #     button_frame,
        #     text="View History",
        #     command=lambda: self.app.show_history_view(),
        # ).pack(side="left", padx=10)

    def update_player_fields(self):
        for widget in self.names_frame.winfo_children():
            widget.destroy()

        self.player_entries = []
        count = self.player_count.get()

        for i in range(count):
            frame = ttk.Frame(self.names_frame)
            frame.pack(pady=5)

            ttk.Label(frame, text=f"Player {i + 1}:").pack(side="left", padx=5)
            entry = ttk.Entry(frame, width=20)
            entry.pack(side="left", padx=5)
            entry.insert(0, f"Player {i + 1}")
            self.player_entries.append(entry)

    def start_game(self):
        player_names = []
        for entry in self.player_entries:
            name = entry.get().strip()
            if not name:
                messagebox.showerror("Error", "Please enter all player names")
                return
            player_names.append(name)

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
        self.paned = ttk.PanedWindow(self, orient="horizontal")
        self.paned.pack(fill="both", expand=True)

        left_frame = ttk.Frame(self.paned)
        self.paned.add(left_frame, weight=1)

        status_frame = ttk.LabelFrame(left_frame, text="Game Status", padding=10)
        status_frame.pack(fill="x", pady=5)

        self.current_player_label = ttk.Label(
            status_frame, text="Current Player:", font=("Arial", 12, "bold")
        )
        self.current_player_label.pack()

        self.turn_info = ttk.Label(status_frame, text="")
        self.turn_info.pack()

        self.progress_label = ttk.Label(status_frame, text="")
        self.progress_label.pack()

        players_frame = ttk.LabelFrame(left_frame, text="Players", padding=10)
        players_frame.pack(fill="both", expand=True, pady=5)

        self.players_listbox = tk.Listbox(players_frame, height=10)
        self.players_listbox.pack(fill="both", expand=True)

        action_frame = ttk.LabelFrame(left_frame, text="Actions", padding=10)
        action_frame.pack(fill="x", pady=5)

        self.draw_btn = ttk.Button(action_frame, text="Draw 2 Cards", command=self.draw_cards)
        self.draw_btn.pack(fill="x", pady=2)

        self.play_btn = ttk.Button(action_frame, text="Play Card", command=self.show_play_card_dialog)
        self.play_btn.pack(fill="x", pady=2)

        self.night_btn = ttk.Button(action_frame, text="Resolve Night", command=self.show_night_dialog)
        self.night_btn.pack(fill="x", pady=2)

        self.next_btn = ttk.Button(action_frame, text="End Turn", command=self.end_turn)
        self.next_btn.pack(fill="x", pady=2)

        right_frame = ttk.Frame(self.paned)
        self.paned.add(right_frame, weight=1)

        log_frame = ttk.LabelFrame(right_frame, text="Game Log", padding=10)
        log_frame.pack(fill="both", expand=True)

        self.log_text = scrolledtext.ScrolledText(log_frame, height=20, width=40)
        self.log_text.pack(fill="both", expand=True)

        hand_frame = ttk.LabelFrame(self, text="Current Player Hand", padding=10)
        hand_frame.pack(fill="x", pady=5)

        self.hand_text = tk.Text(hand_frame, height=8, width=80)
        self.hand_text.pack(fill="x")

    def update_display(self):
        try:
            state = self.game.get_game_state()
            current = state.get("current_player")

            if current:
                self.current_player_label.config(text=f"Current Player: {current.name}")
            else:
                self.current_player_label.config(text="Current Player: -")

            self.turn_info.config(
                text=f"Draw used: {state.get('turn_has_drawn')} | Cards played: {state.get('turn_cards_played')}"
            )
            self.progress_label.config(
                text=f"Revealed Witch Tryals: {state.get('revealed_witch_tryals')}/{state.get('total_witch_tryals')}"
            )

            self.players_listbox.delete(0, tk.END)
            for player in state.get("players", []):
                hidden = sum(1 for c in player.tryal_cards if not c.revealed)
                revealed = len(player.tryal_cards) - hidden
                black_cat = " | Black Cat" if self.game.black_cat_owner == player else ""
                blue = f" | Blue: {[c.name for c in player.blue_cards]}" if player.blue_cards else ""
                red = f" | Accusations: {player.accusation_total()}" if player.red_cards else ""
                line = f"{'✓' if player.alive else '✗'} {player.name} | Tryals {revealed}/{hidden} revealed-hidden{black_cat}{blue}{red}"
                self.players_listbox.insert(tk.END, line)

            self.log_text.delete(1.0, tk.END)
            for entry in state.get("log", []):
                self.log_text.insert(tk.END, f"{entry}\n")
            self.log_text.see(tk.END)

            if current:
                hand = self.game.get_player_hand(current.name)
                self.hand_text.delete(1.0, tk.END)
                if hand:
                    for idx, card in enumerate(hand):
                        self.hand_text.insert(tk.END, f"{idx}: {card}\n")
                else:
                    self.hand_text.insert(tk.END, "No cards in hand.")

            if state.get("winner"):
                duration = int(time.time() - self.start_time)
                self.app.end_game(state["winner"], state.get("players", []), duration)
                return

            if state.get("night_pending"):
                self.night_btn.config(state="normal")
                self.draw_btn.config(state="disabled")
                self.play_btn.config(state="disabled")
            else:
                self.night_btn.config(state="disabled")
                self.draw_btn.config(state="normal")
                self.play_btn.config(state="normal")

            self.after(1000, self.update_display)

        except Exception as e:
            print(f"Error in update_display: {e}")
            import traceback
            traceback.print_exc()

    def draw_cards(self):
        success, message = self.game.draw_cards_for_current_player()
        if success:
            messagebox.showinfo("Draw", message)
        else:
            messagebox.showerror("Error", message)

    def show_play_card_dialog(self):
        current = self.game.get_current_player()
        if not current:
            return

        if not current.hand:
            messagebox.showinfo("No Cards", "Current player has no cards to play.")
            return

        dialog = tk.Toplevel(self)
        dialog.title("Play Card")
        dialog.geometry("420x350")

        ttk.Label(dialog, text=f"Current player: {current.name}", font=("Arial", 12, "bold")).pack(pady=10)

        ttk.Label(dialog, text="Choose card index:").pack()
        card_var = tk.StringVar()
        card_combo = ttk.Combobox(dialog, textvariable=card_var, state="readonly")
        card_combo["values"] = [f"{i}: {card}" for i, card in enumerate(current.hand)]
        card_combo.pack(pady=5)

        players = [p.name for p in self.game.players if p.alive and p.name != current.name]

        ttk.Label(dialog, text="Target player (if needed):").pack()
        target_var = tk.StringVar()
        target_combo = ttk.Combobox(dialog, textvariable=target_var, values=players, state="readonly")
        target_combo.pack(pady=5)

        ttk.Label(dialog, text="Second target (Scapegoat / Robbery):").pack()
        second_var = tk.StringVar()
        second_combo = ttk.Combobox(dialog, textvariable=second_var, values=players, state="readonly")
        second_combo.pack(pady=5)

        def confirm():
            if not card_var.get():
                messagebox.showerror("Error", "Choose a card.")
                return

            hand_index = int(card_var.get().split(":")[0])
            target = target_var.get() or None
            second = second_var.get() or None

            success, message = self.game.play_card(hand_index, target, second)
            if success:
                messagebox.showinfo("Played", message)
                dialog.destroy()
            else:
                messagebox.showerror("Error", message)

        ttk.Button(dialog, text="Play Card", command=confirm).pack(pady=15)

    def show_night_dialog(self):
        if not self.game.night_pending:
            messagebox.showinfo("Night", "Night is not pending.")
            return

        dialog = tk.Toplevel(self)
        dialog.title("Resolve Night")
        dialog.geometry("420x350")

        alive_names = [p.name for p in self.game.players if p.alive]
        alive_names_no_self = alive_names[:]

        ttk.Label(dialog, text="Resolve the Night phase", font=("Arial", 12, "bold")).pack(pady=10)

        ttk.Label(dialog, text="Witches kill:").pack()
        kill_var = tk.StringVar()
        ttk.Combobox(dialog, textvariable=kill_var, values=alive_names, state="readonly").pack(pady=5)

        ttk.Label(dialog, text="Constable saves (optional):").pack()
        save_var = tk.StringVar()
        ttk.Combobox(dialog, textvariable=save_var, values=alive_names_no_self, state="readonly").pack(pady=5)

        ttk.Label(dialog, text="Player who confesses (optional):").pack()
        confess_var = tk.StringVar()
        ttk.Combobox(dialog, textvariable=confess_var, values=alive_names, state="readonly").pack(pady=5)

        ttk.Label(dialog, text="Tryal index to reveal on confession (optional number):").pack()
        confess_index_entry = ttk.Entry(dialog)
        confess_index_entry.pack(pady=5)

        def confirm():
            if not kill_var.get():
                messagebox.showerror("Error", "Pick who the witches try to kill.")
                return

            confess_index = confess_index_entry.get().strip()
            confess_index = int(confess_index) if confess_index.isdigit() else None

            success, message = self.game.resolve_night(
                kill_name=kill_var.get(),
                save_name=save_var.get() or None,
                confess_name=confess_var.get() or None,
                confess_tryal_index=confess_index,
            )
            if success:
                messagebox.showinfo("Night Resolved", message)
                dialog.destroy()
            else:
                messagebox.showerror("Error", message)

        ttk.Button(dialog, text="Resolve Night", command=confirm).pack(pady=15)

    def end_turn(self):
        current, message = self.game.next_turn()
        if current:
            messagebox.showinfo("Turn End", message)
        else:
            messagebox.showerror("Error", message)


class HistoryView(ttk.Frame):
    """Game history view"""

    def __init__(self, parent, app, history_data):
        super().__init__(parent)
        self.app = app
        self.history_data = history_data
        self.setup_ui()

    def setup_ui(self):
        ttk.Label(self, text="Game History", font=("Arial", 18, "bold")).pack(pady=20)

        columns = ("Date", "Winner", "Players", "Num Players", "Witches")
        tree = ttk.Treeview(self, columns=columns, show="headings", height=15)

        for col in columns:
            tree.heading(col, text=col)
            tree.column(col, width=150)

        for record in self.history_data:
            tree.insert("", "end", values=record)

        tree.pack(pady=10, padx=20, fill="both", expand=True)

        ttk.Button(self, text="Back to Setup", command=lambda: self.app.show_setup_view()).pack(pady=20)