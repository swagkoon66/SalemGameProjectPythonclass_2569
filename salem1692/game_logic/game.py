"""
Main Salem 1692 game logic
"""

import random
from .player import Player
from .deck import Deck, CardColor
from .roles import RoleManager, TryalType


class Game:
    """Main game controller for Salem-style rules."""

    def __init__(self):
        self.players = []
        self.current_player_index = 0
        self.deck = Deck()
        self.game_log = []
        self.winner = None

        self.turn_has_drawn = False
        self.turn_cards_played = 0

        self.black_cat_owner = None
        self.night_pending = False
        self.dawn_pending = False   # True until witches place the Black Cat
        self.last_night_result = None
        self.constable_save_vote = None   # name of player the constable chose to save
        self.last_conspiracy_transfers = []
        self.confessed_this_round = set() # player ids who confessed this turn cycle

        # FIX: initialize accusation state so get_game_state() never crashes
        self.accused_player = None
        self.accused_by = None
        self.votes_cast = {}

    def setup_game(self, player_names, player_ids=None):
        self.players = []
        self.game_log.clear()
        self.winner = None
        self.current_player_index = 0
        self.turn_has_drawn = False
        self.turn_cards_played = 0
        self.black_cat_owner = None
        self.night_pending = False
        self.dawn_pending = True    # witches must place Black Cat before game begins
        self.last_night_result = None
        self.constable_save_vote = None
        self.last_conspiracy_transfers = []
        self.confessed_this_round = set()
        # FIX: also reset on new game
        self.accused_player = None
        self.accused_by = None
        self.votes_cast = {}

        self.add_to_log("=== Game Setup ===")

        for i, name in enumerate(player_names):
            pid = player_ids[i] if player_ids and i < len(player_ids) else i
            self.players.append(Player(name, pid))

        num_players = len(player_names)
        tryal_deck, cards_per_player = RoleManager.build_tryal_deck(num_players)

        for player in self.players:
            assigned = [tryal_deck.pop() for _ in range(cards_per_player)]
            player.assign_tryal_cards(assigned)

        self._separate_constable_from_witch()

        self.deck = Deck()
        self.deck.setup_draw_pile()

        # 3 starting playing cards each
        for player in self.players:
            for _ in range(3):
                card = self.deck.draw_card()
                if card:
                    player.add_card(card)

        # Black Cat is NOT placed yet — witches will choose during Dawn phase
        random.shuffle(self.players)
        self.current_player_index = 0

        total_witch_tryals = self.count_total_witch_tryals()
        self.add_to_log(f"Game begins with {num_players} players.")
        self.add_to_log(f"Each player has {cards_per_player} Tryal cards.")
        self.add_to_log(f"Total Witch Tryal cards in game: {total_witch_tryals}")
        self.add_to_log("Dawn: witches are choosing where to place the Black Cat...")

        # Build role assignment dict: {player_id: "Witch", "Constable", or "Townsperson"}
        role_assignments = {}
        for player in self.players:
            if player.is_witch():
                role_assignments[player.id] = "Witch"
            elif player.currently_has_constable():
                role_assignments[player.id] = "Constable"
            else:
                role_assignments[player.id] = "Townsperson"
        return role_assignments

    def _separate_constable_from_witch(self, *, log_change=False):
        """
        Ensure the Constable tryal is never held by a player who also has a Witch tryal.
        """
        constable_holder = next(
            (player for player in self.players
             if any(card.kind == TryalType.CONSTABLE for card in player.tryal_cards)),
            None,
        )
        if not constable_holder or not constable_holder.is_witch():
            return

        eligible_targets = [
            player for player in self.players
            if player is not constable_holder
            and not player.is_witch()
            and not any(card.kind == TryalType.CONSTABLE for card in player.tryal_cards)
        ]
        if not eligible_targets:
            return

        new_holder = random.choice(eligible_targets)
        constable_index = next(
            i for i, card in enumerate(constable_holder.tryal_cards)
            if card.kind == TryalType.CONSTABLE
        )
        replacement_index = next(
            i for i, card in enumerate(new_holder.tryal_cards)
            if card.kind == TryalType.NOT_A_WITCH
        )

        constable_holder.tryal_cards[constable_index], new_holder.tryal_cards[replacement_index] = (
            new_holder.tryal_cards[replacement_index],
            constable_holder.tryal_cards[constable_index],
        )
        if log_change:
            self.add_to_log(
                f"The Constable role shifts from {constable_holder.name} to {new_holder.name}."
            )

    def place_black_cat(self, target_name):
        """Called by server once witches agree on a Black Cat target during Dawn."""
        target = self.get_player_by_name(target_name)
        if not target or not target.alive:
            return False, f"Player '{target_name}' not found."
        self.black_cat_owner = target
        target.add_blue_card(self.deck.black_cat_card)
        self.dawn_pending = False
        # Per rulebook: the player who receives the Black Cat goes first
        self.current_player_index = self.players.index(target)
        self.add_to_log(f"The Black Cat has been placed on {target.name}.")
        self.add_to_log(f"{target.name} goes first.")
        return True, f"Black Cat placed on {target.name}."

    def confess(self, player_id):
        """Player sacrifices one tryal card to be protected from Night kill this round."""
        player = self._get_player_by_id(player_id)
        if not player or not player.alive:
            return False, "You are not in the game or are eliminated."
        if player_id in self.confessed_this_round:
            return False, "You have already confessed this round."
        unrevealed = player.unrevealed_tryal_indices()
        if not unrevealed:
            return False, "You have no hidden Tryal cards left to sacrifice."
        revealed_card = player.reveal_tryal()
        self.confessed_this_round.add(player_id)
        player.confessed_this_night = True
        msg = f"{player.name} confesses and reveals a Tryal card: {revealed_card.kind.value}."
        self.add_to_log(msg)
        # Check if revealing caused death (e.g. revealed a Witch card)
        death_msg = self.handle_reveal_death(player)
        if death_msg:
            return True, f"{msg} {death_msg}"
        return True, msg

    def count_total_witch_tryals(self):
        return sum(
            1
            for player in self.players
            for card in player.tryal_cards
            if card.kind == TryalType.WITCH
        )

    def count_revealed_witch_tryals(self):
        return sum(
            1
            for player in self.players
            for card in player.tryal_cards
            if card.kind == TryalType.WITCH and card.revealed
        )

    def get_current_player(self):
        if not self.players:
            return None
        if self.current_player_index >= len(self.players):
            self.current_player_index = 0
        return self.players[self.current_player_index]

    def get_alive_players(self):
        return [p for p in self.players if p.alive]

    def get_player_by_name(self, player_name):
        for player in self.players:
            if player.name == player_name:
                return player
        return None

    def _get_player_by_id(self, player_id):
        for player in self.players:
            if player.id == player_id:
                return player
        return None

    def add_to_log(self, message):
        self.game_log.append(message)
        print(message)

    def draw_cards_for_current_player(self):
        """
        A turn may draw 2 cards and end, unless the player already played cards.
        Black cards reveal immediately and count as drawn cards.
        """
        player = self.get_current_player()
        if not player or not player.alive:
            return False, "Invalid player."

        if self.turn_cards_played > 0:
            return False, "You already played cards this turn. You cannot draw now."

        if self.turn_has_drawn:
            return False, "You already chose the draw action this turn."

        messages = []
        draws_done = 0
        normal_draws = 0

        while draws_done < 2:
            card = self.deck.draw_card()
            if not card:
                messages.append("No more cards to draw.")
                break

            draws_done += 1

            if card.color == CardColor.BLACK:
                self.add_to_log(f"{player.name} draws a Black card: {card.name}")
                messages.append(f"Drew BLACK card: {card.name}")
                self.resolve_black_card(player, card)
            else:
                player.add_card(card)
                normal_draws += 1
                messages.append(f"Drew {card}")

        if normal_draws > 0:
            card_word = "a card" if normal_draws == 1 else f"{normal_draws} cards"
            self.add_to_log(f"{player.name} draws {card_word}.")

        self.turn_has_drawn = True
        return True, "\n".join(messages)

    def resolve_black_card(self, player, card):
        if card.name == "Conspiracy":
            self.resolve_conspiracy(player)
            self.deck.discard_card(card)
        elif card.name == "Night":
            self.night_pending = True
            self.add_to_log("Night has begun. Resolve the Night phase before ending the turn.")
            self.deck.discard_card(card)
        else:
            self.deck.discard_card(card)

    def resolve_conspiracy(self, triggering_player):
        self.add_to_log("=== Conspiracy ===")

        # Reveal one Tryal card from Black Cat owner, if possible
        if self.black_cat_owner and self.black_cat_owner.alive:
            revealed = self.black_cat_owner.reveal_tryal()
            if revealed:
                self.add_to_log(
                    f"Conspiracy reveals one Tryal card from {self.black_cat_owner.name}: {revealed.kind.value}"
                )
                self.handle_reveal_death(self.black_cat_owner)
        else:
            self.add_to_log("No Black Cat owner available for the Conspiracy reveal.")

        alive_players = self.get_alive_players()
        if len(alive_players) < 2:
            self.add_to_log("Not enough players alive for Conspiracy to move Tryal cards.")
            return

        moves = []
        for i, player in enumerate(alive_players):
            left_player = alive_players[(i + 1) % len(alive_players)]
            hidden_indices = left_player.unrevealed_tryal_indices()
            if hidden_indices:
                chosen_index = random.choice(hidden_indices)
                moves.append((player, left_player, chosen_index))

        transferred_cards = []
        for receiver, giver, chosen_index in moves:
            card = giver.tryal_cards.pop(chosen_index)
            transferred_cards.append((receiver, giver, card))

        self.last_conspiracy_transfers = []  # reset before each conspiracy

        for receiver, giver, card in transferred_cards:
            receiver.tryal_cards.append(card)
            if card.kind == TryalType.WITCH:
                receiver.ever_witch = True
            self.last_conspiracy_transfers.append({
                "giver": giver.name,
                "receiver": receiver.name,
                "card_kind": card.kind.value,  # revealed only to receiver in get_game_state
            })
            self.add_to_log(f"{receiver.name} takes one hidden Tryal card from {giver.name}.")

        self._separate_constable_from_witch(log_change=True)
        self.check_win_condition()

    def play_card(self, hand_index, target_name=None, secondary_target_name=None):
        player = self.get_current_player()
        if not player or not player.alive:
            return False, "Invalid player."

        if self.turn_has_drawn:
            return False, "You already chose to draw this turn. End your turn."

        card = player.remove_card_by_index(hand_index)
        if card is None:
            return False, "Invalid card selection."

        if card.color == CardColor.BLACK:
            # Just in case; black cards should normally never sit in hand
            self.resolve_black_card(player, card)
            self.turn_cards_played += 1
            return True, f"{player.name} reveals {card.name}."

        target = self.get_player_by_name(target_name) if target_name else None
        secondary = self.get_player_by_name(secondary_target_name) if secondary_target_name else None

        # 1st Law of Salem
        if target is not None and target == player:
            player.add_card(card)
            return False, "You may not play a card on yourself."

        if secondary is not None and secondary == player:
            player.add_card(card)
            return False, "You may not directly affect yourself with that card."

        message = self.apply_card_effect(player, card, target, secondary)
        self.turn_cards_played += 1

        if card.color in (CardColor.GREEN, CardColor.RED) and card not in player.hand:
            self.deck.discard_card(card)

        self.add_to_log(message)
        self.check_win_condition()
        return True, message

    def apply_card_effect(self, player, card, target, secondary):
        if card.name in ("Accusation", "Evidence", "Testimony"):
            if not target or not target.alive:
                player.add_card(card)
                self.turn_cards_played -= 0
                return "No valid target selected."

            target.add_red_card(card)
            total = target.accusation_total()
            msg = f"{player.name} plays {card.name} on {target.name}. Total accusations: {total}"

            if total >= 7:
                revealed = target.reveal_tryal()
                target.clear_red_cards()
                if revealed:
                    msg += f" | {target.name} reveals: {revealed.kind.value}"
                    death_msg = self.handle_reveal_death(target)
                    if death_msg:
                        msg += f" | {death_msg}"
            return msg

        if card.name in ("Asylum", "Piety", "Alibi"):
            if not target or not target.alive:
                player.add_card(card)
                return "No valid target selected."
            target.add_blue_card(card)
            if card.name == "Black Cat":
                self.black_cat_owner = target
            return f"{player.name} places {card.name} in front of {target.name}."

        if card.name == "Curse":
            if not target or not target.alive:
                player.add_card(card)
                return "No valid target selected."
            removed = None
            for blue in list(target.blue_cards):
                if blue.name != "Black Cat":
                    removed = blue
                    target.blue_cards.remove(blue)
                    self.deck.discard_card(removed)
                    break
            if removed:
                return f"{player.name} uses Curse and discards a blue card from {target.name}."
            return f"{player.name} uses Curse on {target.name}, but no removable blue card was there."

        if card.name == "Scapegoat":
            if not target or not secondary or not target.alive or not secondary.alive:
                player.add_card(card)
                return "Scapegoat needs two valid other players."
            moved_red = list(target.red_cards)
            moved_blue = list(target.blue_cards)
            target.red_cards = []
            target.blue_cards = []
            secondary.red_cards.extend(moved_red)
            secondary.blue_cards.extend(moved_blue)

            if self.black_cat_owner == target:
                self.black_cat_owner = secondary

            return f"{player.name} moves all red and blue cards from {target.name} to {secondary.name}."

        if card.name == "Robbery":
            if not target or not secondary or not target.alive or not secondary.alive:
                player.add_card(card)
                return "Robbery needs two valid other players."
            if not target.hand:
                return f"{player.name} tries Robbery, but {target.name} has no cards."
            stolen = random.choice(target.hand)
            target.hand.remove(stolen)
            secondary.hand.append(stolen)
            return f"{player.name} uses Robbery: a random card moves from {target.name} to {secondary.name}."

        if card.name == "Stock":
            if not target or not target.alive:
                player.add_card(card)
                return "Stock needs a valid target."
            target.stocks_count += 1
            return f"{player.name} places {target.name} in the Stocks — they will skip their next turn."

        if card.name == "Arson":
            if not target or not target.alive:
                player.add_card(card)
                return "Arson needs a valid target."
            burned = [c for c in target.blue_cards if c.name != "Black Cat"]
            for c in burned:
                target.blue_cards.remove(c)
            self.deck.discard_many(burned)
            if burned:
                return f"{player.name} plays Arson on {target.name}, burning {len(burned)} blue card(s)."
            return f"{player.name} plays Arson on {target.name}, but they had no burnable blue cards."

        player.add_card(card)
        return f"{card.name} is not implemented."

    def handle_reveal_death(self, player):
        if player.has_revealed_witch():
            self.kill_player(player, "A revealed Tryal card showed Witch.")
            return f"{player.name} dies because a revealed Tryal card says Witch."

        if player.all_tryals_revealed():
            self.kill_player(player, "All Tryal cards were revealed.")
            return f"{player.name} dies because all Tryal cards are revealed."

        return None

    def kill_player(self, player, reason):
        if not player.alive:
            return

        player.alive = False

        # discard hand + blue cards
        self.deck.discard_many(player.hand)
        self.deck.discard_many(player.blue_cards)
        player.hand = []
        player.blue_cards = []
        player.red_cards = []

        for card in player.tryal_cards:
            card.revealed = True

        witch_truth = "was EVER a Witch" if player.ever_witch else "was never a Witch"
        self.add_to_log(f"{player.name} dies. Reason: {reason}")
        self.add_to_log(f"{player.name} {witch_truth}.")

        self.check_win_condition()

    def resolve_night(self, kill_name, save_name=None, confess_name=None, confess_tryal_index=None):
        if not self.night_pending:
            return False, "Night is not pending."

        alive = self.get_alive_players()
        if len(alive) <= 1:
            self.night_pending = False
            self.deck.reshuffle_after_night()
            return True, "Night skipped."

        for player in self.players:
            # Preserve confession from button press — only reset if they didn't pre-confess
            already_confessed = player.id in self.confessed_this_round
            player.reset_night_flags()
            if already_confessed:
                player.confessed_this_night = True

        victim = self.get_player_by_name(kill_name)
        saver_target = self.get_player_by_name(save_name) if save_name else None
        confessor = self.get_player_by_name(confess_name) if confess_name else None

        if victim is None or not victim.alive:
            return False, "Invalid Night victim."

        # confession
        if confessor and confessor.alive:
            revealed = confessor.reveal_tryal(confess_tryal_index)
            confessor.confessed_this_night = True
            if revealed:
                self.add_to_log(f"{confessor.name} confesses and reveals: {revealed.kind.value}")
                self.handle_reveal_death(confessor)

        # constable save
        constables = [p for p in alive if p.currently_has_constable()]
        if saver_target and saver_target.alive and constables:
            saver_target.gavel_protected = True
            self.add_to_log(f"The Constable protects {saver_target.name} with the Gavel.")

        self.add_to_log(f"Witches attempt to kill {victim.name}.")

        if not victim.alive:
            result = f"{victim.name} already died before the Night kill resolved."
        elif victim.gavel_protected:
            result = f"{victim.name} survives the Night because of the Gavel."
        elif victim.confessed_this_night:
            result = f"{victim.name} survives the Night by confessing."
        elif victim.has_blue_card("Asylum"):
            result = f"{victim.name} survives the Night because Asylum is in front of them."
        else:
            self.kill_player(victim, "Killed during the Night.")
            result = f"{victim.name} is killed during the Night."

        self.last_night_result = result
        self.add_to_log(result)

        self.night_pending = False
        self.deck.reshuffle_after_night()
        self.check_win_condition()
        return True, result

    def can_end_turn(self):
        return self.turn_has_drawn or self.turn_cards_played > 0

    def next_turn(self, player_id=None):
        """Advance to next turn. If player_id given, validates it's that player's turn."""
        if player_id is not None:
            current = self.get_current_player()
            if not current or current.id != player_id:
                return None, "It's not your turn."

        alive_players = self.get_alive_players()
        if not alive_players:
            return None, "No alive players."

        start_index = self.current_player_index
        while True:
            self.current_player_index = (self.current_player_index + 1) % len(self.players)
            if self.players[self.current_player_index].alive:
                break
            if self.current_player_index == start_index:
                break

        self.turn_has_drawn = False
        self.turn_cards_played = 0
        self.confessed_this_round = set()  # reset confessions each new turn
        for p in self.players:
            p.confessed_this_night = False  # reset flag ready for next Night
        current = self.get_current_player()

        # Handle Stock card: if the incoming player has stocks, skip them
        if current.stocks_count > 0:
            current.stocks_count -= 1
            self.add_to_log(f"{current.name} is in the Stocks and loses their turn! ({current.stocks_count} remaining)")
            return self.next_turn()

        self.add_to_log(f"It is now {current.name}'s turn.")
        return current, f"It is now {current.name}'s turn."

    def draw_card(self, player_id):
        """Network-facing: draw cards for the player with the given ID."""
        current = self.get_current_player()
        if not current or current.id != player_id:
            return None, "It's not your turn."
        success, msg = self.draw_cards_for_current_player()
        card = current.hand[-1] if success and current.hand else None
        return (card, msg) if success else (None, msg)

    def start_accusation(self, accuser_id, accused_name):
        """Network-facing: begin an accusation vote."""
        accuser = self._get_player_by_id(accuser_id)
        accused = self.get_player_by_name(accused_name)
        if not accuser or not accuser.alive:
            return False, "You are not in the game or are eliminated."
        if not accused or not accused.alive:
            return False, f"Player '{accused_name}' not found or eliminated."
        if accuser == accused:
            return False, "You cannot accuse yourself."
        self.accused_player = accused
        self.accused_by = accuser
        self.votes_cast = {}
        self.add_to_log(f"{accuser.name} accuses {accused.name}!")
        return True, f"{accuser.name} has accused {accused.name}. Voting begins!"

    def cast_vote(self, voter_id, guilty):
        """Network-facing: cast a guilty/not-guilty vote."""
        voter = self._get_player_by_id(voter_id)
        if not voter or not voter.alive:
            return False, "You cannot vote."
        if not self.accused_player:
            return False, "No active accusation."
        if voter == self.accused_player:
            return False, "The accused cannot vote."
        if voter_id in self.votes_cast:
            return False, "You already voted."
        self.votes_cast[voter_id] = guilty
        vote_word = "GUILTY" if guilty else "NOT GUILTY"
        self.add_to_log(f"{voter.name} votes {vote_word}.")
        return True, f"Vote recorded: {vote_word}"

    def resolve_accusation(self):
        """Tally votes and eliminate or acquit the accused."""
        if not self.accused_player:
            return False, "No active accusation.", None
        guilty_votes = sum(1 for v in self.votes_cast.values() if v)
        total_votes = len(self.votes_cast)
        accused = self.accused_player
        if guilty_votes > total_votes / 2:
            self.kill_player(accused, "Eliminated by vote.")
            msg = f"{accused.name} was eliminated by the town! ({guilty_votes}/{total_votes} guilty)"
        else:
            msg = f"{accused.name} was acquitted! ({guilty_votes}/{total_votes} guilty)"
        winner = self.check_win_condition()
        self.accused_player = None
        self.accused_by = None
        self.votes_cast = {}
        return True, msg, winner

    def check_win_condition(self):
        total_witch_tryals = self.count_total_witch_tryals()
        revealed_witch_tryals = self.count_revealed_witch_tryals()

        if total_witch_tryals > 0 and revealed_witch_tryals == total_witch_tryals:
            self.winner = "Town"
            self.add_to_log("=== Town wins! All Witch Tryal cards are revealed. ===")
            return self.winner

        alive_players = self.get_alive_players()
        if alive_players:
            alive_witches = [p for p in alive_players if p.is_witch()]
            alive_town = [p for p in alive_players if not p.is_witch()]
            if len(alive_witches) >= len(alive_town) and len(alive_witches) > 0:
                self.winner = "Witches"
                self.add_to_log("=== Witches win! Witches equal or outnumber the town. ===")
                return self.winner

        return None

    def get_player_hand(self, player_name_or_id):
        player = self.get_player_by_name(player_name_or_id)
        if player is None:
            player = self._get_player_by_id(player_name_or_id)
        return player.hand if player else []

    def get_game_state(self, for_player_id=None):
        current = self.get_current_player()
        alive_players = self.get_alive_players()

        players_data = []
        for p in self.players:
            players_data.append({
                "id": p.id,
                "name": p.name,
                "alive": p.alive,
                "tryal_total": len(p.tryal_cards),
                "tryal_hidden": sum(1 for c in p.tryal_cards if not c.revealed),
                "accusation_total": p.accusation_total(),
            })

        # Tell each player whether they personally hold an active Constable tryal
        requesting_player = self._get_player_by_id(for_player_id) if for_player_id is not None else None
        is_constable = requesting_player.currently_has_constable() if requesting_player else False

        # Own tryal cards (full detail — only sent to the owning player)
        own_tryals = []
        if requesting_player:
            for tc in requesting_player.tryal_cards:
                own_tryals.append({
                    "kind": tc.kind.value,
                    "revealed": tc.revealed,
                })

        # Conspiracy transfers — card_kind shown only to the receiver
        req_name = requesting_player.name if requesting_player else None
        conspiracy_transfers = []
        for t in self.last_conspiracy_transfers:
            entry = {"giver": t["giver"], "receiver": t["receiver"]}
            if t["receiver"] == req_name:
                entry["card_kind"] = t["card_kind"]
            else:
                entry["card_kind"] = None  # hidden from everyone else
            conspiracy_transfers.append(entry)

        return {
            "players": players_data,
            "alive_players": [{"id": p.id, "name": p.name} for p in alive_players],
            "current_player": current.id if current else None,
            "current_player_name": current.name if current else None,
            "winner": self.winner,
            "log": self.game_log[-30:],
            "night_pending": self.night_pending,
            "dawn_pending": self.dawn_pending,
            "black_cat_owner": self.black_cat_owner.name if self.black_cat_owner else None,
            "turn_has_drawn": self.turn_has_drawn,
            "turn_cards_played": self.turn_cards_played,
            "revealed_witch_tryals": self.count_revealed_witch_tryals(),
            "total_witch_tryals": self.count_total_witch_tryals(),
            "accusation_phase": self.accused_player is not None,
            "accused_player_name": self.accused_player.name if self.accused_player else None,
            "accused_by_name": self.accused_by.name if self.accused_by else None,
            "is_constable": is_constable,
            "constable_save_submitted": self.constable_save_vote is not None,
            "already_confessed": for_player_id in self.confessed_this_round,
            "own_tryals": own_tryals,
            "conspiracy_transfers": conspiracy_transfers,
        }