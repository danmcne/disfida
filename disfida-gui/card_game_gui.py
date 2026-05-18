# card_game_gui.py
import tkinter as tk
from tkinter import messagebox
from card_game_logic import *
from card_image_manager import CardImageManager
from card_game_ai import DisfidaAI

# ── Colour palette ────────────────────────────────────────────────────────────
BG         = "#1a472a"
PANEL_BG   = "#163d24"
GOLD       = "#d4af37"
WHITE      = "#f0f0e8"
LIGHT_GREY = "#a0a090"
BTN_BG     = "#2d6a4f"
BTN_ACTIVE = "#40916c"

AI_DELAY_MS = 800   # ms between AI pre-shield and main turns


class CardGameGUI:
    def __init__(self, root):
        self.root = root
        self.root.title("Disfida — Italian Card Combat")

        # Two-column layout: game canvas left, log panel right
        self.side_panel = tk.Frame(root, width=270, bg="#0d1f17")
        self.side_panel.pack(side="right", fill="y")
        self.side_panel.pack_propagate(False)

        self.canvas = tk.Canvas(root, width=990, height=720,
                                bg=BG, highlightthickness=0)
        self.canvas.pack(side="left", fill="both", expand=True)

        self.image_manager = CardImageManager()
        self.selected_cards = []
        self.player1, self.player2, init_messages = init_game()
        self.current_player = self.player1
        self.turn_count = 0
        self.phase = "pre_shield_p1"

        self.p1_hand_widgets    = []
        self.p2_hand_widgets    = []
        self.p1_shield_widgets  = []
        self.p2_shield_widgets  = []
        self.played_card_widgets = []

        # AI state (set in _choose_game_mode)
        self.ai_mode = False
        self.ai      = None

        self.setup_gui()
        self.log_messages(init_messages, tag="system")
        self.show_rules_modal()
        self._choose_game_mode()
        self.start_pre_shield_phase()

    # ── Layout constants ──────────────────────────────────────────────────────
    CARD_X_START = 150
    CARD_STEP    = 95
    STACK_X      = 860

    P2_INFO_Y   = 8
    P2_HP_BAR_Y = 28
    P2_HAND_Y   = 55
    P2_SHIELD_Y = 205

    DIVIDER_Y   = 345

    P1_SHIELD_Y = 360
    P1_HAND_Y   = 455
    P1_INFO_Y   = 605
    P1_HP_BAR_Y = 628
    P1_BTN_Y    = 668

    BAR_X0, BAR_X1 = 300, 550

    # ── GUI setup ─────────────────────────────────────────────────────────────
    def setup_gui(self):
        W = 990

        # Turn banner / divider
        self.canvas.create_rectangle(0, self.DIVIDER_Y - 16, W,
                                     self.DIVIDER_Y + 16, fill=PANEL_BG, outline="")
        self.turn_label = self.canvas.create_text(
            W // 2, self.DIVIDER_Y, anchor="center",
            text="Pre-Shield Phase: Player 1",
            font=("Georgia", 13, "bold"), fill=GOLD)

        # Player 2 info strip
        self.canvas.create_rectangle(0, 0, W, 52, fill=PANEL_BG, outline="")
        self.p2_char_label = self.canvas.create_text(
            10, self.P2_INFO_Y, anchor="nw",
            text="", font=("Georgia", 11, "bold"), fill=GOLD)
        self.p2_hp_text = self.canvas.create_text(
            self.BAR_X0, self.P2_INFO_Y, anchor="nw",
            text="", font=("Courier", 11, "bold"), fill=WHITE)
        self.p2_bonus_label = self.canvas.create_text(
            10, self.P2_INFO_Y + 18, anchor="nw",
            text="", font=("Courier", 9), fill=LIGHT_GREY)
        self.p2_stack_label = self.canvas.create_text(
            600, self.P2_INFO_Y, anchor="nw",
            text="", font=("Courier", 10), fill=LIGHT_GREY)
        self.p2_hp_bar_bg = self.canvas.create_rectangle(
            self.BAR_X0, self.P2_HP_BAR_Y,
            self.BAR_X1, self.P2_HP_BAR_Y + 10,
            fill="#550000", outline="")
        self.p2_hp_bar = self.canvas.create_rectangle(
            self.BAR_X0, self.P2_HP_BAR_Y,
            self.BAR_X1, self.P2_HP_BAR_Y + 10,
            fill="#44bb44", outline="")
        self.p2_char_img = self.canvas.create_image(
            self.STACK_X, self.P2_HAND_Y,
            image=self.image_manager.get_image(None, rotated=True), anchor="nw")

        # Player 1 info strip
        self.canvas.create_rectangle(0, self.P1_INFO_Y - 4,
                                     W, 720, fill=PANEL_BG, outline="")
        self.p1_char_label = self.canvas.create_text(
            10, self.P1_INFO_Y, anchor="nw",
            text="", font=("Georgia", 11, "bold"), fill=GOLD)
        self.p1_hp_text = self.canvas.create_text(
            self.BAR_X0, self.P1_INFO_Y, anchor="nw",
            text="", font=("Courier", 11, "bold"), fill=WHITE)
        self.p1_bonus_label = self.canvas.create_text(
            10, self.P1_INFO_Y + 18, anchor="nw",
            text="", font=("Courier", 9), fill=LIGHT_GREY)
        self.p1_stack_label = self.canvas.create_text(
            600, self.P1_INFO_Y, anchor="nw",
            text="", font=("Courier", 10), fill=LIGHT_GREY)
        self.p1_hp_bar_bg = self.canvas.create_rectangle(
            self.BAR_X0, self.P1_HP_BAR_Y,
            self.BAR_X1, self.P1_HP_BAR_Y + 10,
            fill="#550000", outline="")
        self.p1_hp_bar = self.canvas.create_rectangle(
            self.BAR_X0, self.P1_HP_BAR_Y,
            self.BAR_X1, self.P1_HP_BAR_Y + 10,
            fill="#44bb44", outline="")
        self.p1_char_img = self.canvas.create_image(
            self.STACK_X, self.P1_HAND_Y,
            image=self.image_manager.get_image(None), anchor="nw")

        # Section labels
        for x, y, txt in [
            (10, self.P2_HAND_Y   - 12, "P2 hand"),
            (10, self.P2_SHIELD_Y - 12, "P2 shields ▼"),
            (10, self.P1_SHIELD_Y - 12, "P1 shields ▲"),
            (10, self.P1_HAND_Y   - 12, "P1 hand"),
        ]:
            self.canvas.create_text(x, y, text=txt, anchor="nw",
                                    font=("Courier", 8), fill=LIGHT_GREY)

        # Log panel
        tk.Label(self.side_panel, text="GAME LOG",
                 font=("Georgia", 10, "bold"),
                 bg="#0d1f17", fg=GOLD, pady=6).pack(fill="x")
        tk.Frame(self.side_panel, height=1, bg=GOLD).pack(fill="x")
        log_inner = tk.Frame(self.side_panel, bg="#0d1f17")
        log_inner.pack(fill="both", expand=True, padx=4, pady=4)
        self.log_text = tk.Text(
            log_inner, font=("Courier", 9),
            bg="#0d1f17", fg=WHITE,
            insertbackground=WHITE, relief="flat",
            wrap=tk.WORD, padx=6, pady=4)
        log_scroll = tk.Scrollbar(log_inner, command=self.log_text.yview,
                                   bg="#163d24", troughcolor=BG)
        self.log_text.config(yscrollcommand=log_scroll.set)
        log_scroll.pack(side="right", fill="y")
        self.log_text.pack(side="left", fill="both", expand=True)

        self.log_text.tag_config("system",  foreground="#aaaaaa")
        self.log_text.tag_config("damage",  foreground="#ff7070")
        self.log_text.tag_config("heal",    foreground="#70ff70")
        self.log_text.tag_config("shield",  foreground="#70c8ff")
        self.log_text.tag_config("special", foreground="#ffdd55")
        self.log_text.tag_config("rank",    foreground="#ff99ff",
                                            font=("Courier", 9, "bold"))
        self.log_text.tag_config("destroy", foreground="#ff4444",
                                            font=("Courier", 9, "bold"))
        self.log_text.tag_config("skip",    foreground="#888888")
        self.log_text.tag_config("draw",    foreground="#99bbaa")
        self.log_text.tag_config("ai",      foreground="#c8aaff")

        # Buttons
        btn_cfg = dict(font=("Georgia", 11, "bold"),
                       bg=BTN_BG, fg=WHITE,
                       activebackground=BTN_ACTIVE, activeforeground=WHITE,
                       relief="flat", padx=12, pady=4, cursor="hand2")
        self.play_button  = tk.Button(self.root, text="▶  Play / Confirm",
                                      command=self.play_combo, **btn_cfg)
        self.skip_button  = tk.Button(self.root, text="⏭  Skip Turn",
                                      command=self.skip_turn,  **btn_cfg)
        self.rules_button = tk.Button(self.root, text="📖  Rules",
                                      command=self.show_rules, **btn_cfg)
        self.canvas.create_window(320, self.P1_BTN_Y, window=self.play_button)
        self.canvas.create_window(490, self.P1_BTN_Y, window=self.skip_button)
        self.canvas.create_window(640, self.P1_BTN_Y, window=self.rules_button)

        self.update_gui()

    # ── Helpers ───────────────────────────────────────────────────────────────
    def _hp_color(self, hp):
        if hp > 25: return "#44bb44"
        if hp > 12: return "#ff9900"
        return "#dd2222"

    def ask_choice(self, title, option1, option2):
        """Minimal dialog — title bar + two buttons, close disabled."""
        result = [option1]
        dlg = tk.Toplevel(self.root)
        dlg.title(title)
        dlg.configure(bg=PANEL_BG)
        dlg.resizable(False, False)
        dlg.protocol("WM_DELETE_WINDOW", lambda: None)

        frm = tk.Frame(dlg, bg=PANEL_BG, padx=24, pady=20)
        frm.pack()
        btn_cfg = dict(font=("Georgia", 14, "bold"),
                       bg=BTN_BG, fg=WHITE,
                       activebackground=BTN_ACTIVE, activeforeground=WHITE,
                       relief="flat", padx=22, pady=10, cursor="hand2", width=12)

        def pick(v):
            result[0] = v
            dlg.destroy()

        tk.Button(frm, text=option1,
                  command=lambda: pick(option1), **btn_cfg).pack(side="left", padx=10)
        tk.Button(frm, text=option2,
                  command=lambda: pick(option2), **btn_cfg).pack(side="left", padx=10)

        dlg.update_idletasks()
        dlg.lift()
        dlg.focus_force()
        dlg.wait_window()
        return result[0]

    # ── Log ───────────────────────────────────────────────────────────────────
    def log_messages(self, messages, tag=None):
        for msg in messages:
            t = tag or self._auto_tag(msg)
            self.log_text.insert(tk.END, msg + "\n", t)
        self.log_text.see(tk.END)

    def _auto_tag(self, msg):
        m = msg.lower()
        if "🤖" in msg:                                      return "ai"
        if "rank match" in m or "✨" in m:                   return "rank"
        if "destroyed" in m or "removed" in m:               return "destroy"
        if "blocked" in m:                                    return "destroy"
        if "poison cup" in m or ("damage" in m and "self" not in m): return "damage"
        if "attack" in m and "blocked" not in m:             return "damage"
        if "heal" in m or "+hp" in m:                        return "heal"
        if "shield" in m:                                     return "shield"
        if "skip" in m:                                       return "skip"
        if "draw" in m or "draws" in m:                      return "draw"
        if "special" in m or "iron" in m:                    return "special"
        return "system"

    # ── update_gui ────────────────────────────────────────────────────────────
    def update_gui(self):
        p1, p2 = self.player1, self.player2

        self.canvas.itemconfig(
            self.p1_char_img,
            image=self.image_manager.get_image(
                Card(p1.character.suit, p1.character.face)))
        self.canvas.itemconfig(
            self.p2_char_img,
            image=self.image_manager.get_image(
                Card(p2.character.suit, p2.character.face), rotated=True))

        ai_tag = "  🤖" if self.ai_mode else ""
        self.canvas.itemconfig(self.p1_char_label,
            text=f"P1 — {p1.character.face} of {p1.character.suit}")
        self.canvas.itemconfig(self.p2_char_label,
            text=f"P2 — {p2.character.face} of {p2.character.suit}{ai_tag}")
        self.canvas.itemconfig(self.p1_hp_text,
            text=f"HP: {p1.health}/40", fill=self._hp_color(p1.health))
        self.canvas.itemconfig(self.p2_hp_text,
            text=f"HP: {p2.health}/40", fill=self._hp_color(p2.health))
        self.canvas.itemconfig(self.p1_bonus_label,
            text=(f"Atk +{p1.character.attack_bonus}  "
                  f"Heal +{p1.character.heal_bonus}  "
                  f"Def +{p1.character.defense_bonus}  │  "
                  f"Removed: {len(p1.discard_pile)}"))
        self.canvas.itemconfig(self.p2_bonus_label,
            text=(f"Atk +{p2.character.attack_bonus}  "
                  f"Heal +{p2.character.heal_bonus}  "
                  f"Def +{p2.character.defense_bonus}  │  "
                  f"Removed: {len(p2.discard_pile)}"))
        self.canvas.itemconfig(self.p1_stack_label,
            text=f"Deck: {len(p1.stack)} cards")
        self.canvas.itemconfig(self.p2_stack_label,
            text=f"Deck: {len(p2.stack)} cards")

        for player, bar_id, bar_y in [
            (p1, self.p1_hp_bar, self.P1_HP_BAR_Y),
            (p2, self.p2_hp_bar, self.P2_HP_BAR_Y),
        ]:
            frac = max(0.0, min(1.0, player.health / 40))
            x1   = self.BAR_X0 + int((self.BAR_X1 - self.BAR_X0) * frac)
            self.canvas.coords(bar_id, self.BAR_X0, bar_y, x1, bar_y + 10)
            self.canvas.itemconfig(bar_id, fill=self._hp_color(player.health))

        # P1 hand
        for w in self.p1_hand_widgets: self.canvas.delete(w)
        self.p1_hand_widgets = []
        for i, card in enumerate(p1.hand):
            x = self.CARD_X_START + i * self.CARD_STEP
            w = self.canvas.create_image(x, self.P1_HAND_Y,
                image=self.image_manager.get_image(card), anchor="nw")
            self.canvas.tag_bind(w, "<Button-1>",
                lambda e, c=card, ww=w: self.select_card(c, ww))
            self.p1_hand_widgets.append(w)

        # P2 hand
        for w in self.p2_hand_widgets: self.canvas.delete(w)
        self.p2_hand_widgets = []
        for i, card in enumerate(p2.hand):
            x = self.CARD_X_START + i * self.CARD_STEP
            w = self.canvas.create_image(x, self.P2_HAND_Y,
                image=self.image_manager.get_image(card, rotated=True), anchor="nw")
            # P2 hand is only clickable in two-player mode
            if not self.ai_mode:
                self.canvas.tag_bind(w, "<Button-1>",
                    lambda e, c=card, ww=w: self.select_card(c, ww))
            self.p2_hand_widgets.append(w)

        # P1 shields
        for w in self.p1_shield_widgets: self.canvas.delete(w)
        self.p1_shield_widgets = []
        for i, card in enumerate(sorted(p1.shields, key=lambda c: c.value)):
            x = self.CARD_X_START + i * 72
            w = self.canvas.create_image(x, self.P1_SHIELD_Y,
                image=self.image_manager.get_image(card), anchor="nw")
            self.p1_shield_widgets.append(w)

        # P2 shields
        for w in self.p2_shield_widgets: self.canvas.delete(w)
        self.p2_shield_widgets = []
        for i, card in enumerate(sorted(p2.shields, key=lambda c: c.value)):
            x = self.CARD_X_START + i * 72
            w = self.canvas.create_image(x, self.P2_SHIELD_Y,
                image=self.image_manager.get_image(card, rotated=True), anchor="nw")
            self.p2_shield_widgets.append(w)

        # Selected card staging
        for w in self.played_card_widgets: self.canvas.delete(w)
        self.played_card_widgets = []
        stage_y = self.P1_SHIELD_Y if self.current_player == p1 else self.P2_SHIELD_Y
        rotated = (self.current_player == p2)
        for i, (card, _, _) in enumerate(self.selected_cards):
            x = self.CARD_X_START + 500 + i * 72
            w = self.canvas.create_image(x, stage_y,
                image=self.image_manager.get_image(card, rotated=rotated), anchor="nw")
            self.played_card_widgets.append(w)

        if self.phase == "main":
            p1a = "◀ ACTIVE" if self.current_player == p1 else ""
            p2a = ("ACTIVE ▶  🤖" if self.ai_mode and self.current_player == p2
                   else ("ACTIVE ▶" if self.current_player == p2 else ""))
            self.canvas.itemconfig(
                self.turn_label,
                text=(f"{p2a}  Turn {self.turn_count + 1}/40  "
                      f"(P1: {p1.turns_played}/20  P2: {p2.turns_played}/20)  {p1a}"))

    # ── Card selection ────────────────────────────────────────────────────────
    def select_card(self, card, widget):
        if self.ai_mode and card in self.player2.hand:
            return   # AI controls P2

        if card in self.player1.hand and self.current_player != self.player1:
            return
        if card in self.player2.hand and self.current_player != self.player2:
            return

        # Deselect if already selected
        for i, (c, s, w) in enumerate(self.selected_cards):
            if c is card:
                self.selected_cards.pop(i)
                self.canvas.delete(f"highlight_{id(w)}")
                self.update_gui()
                return

        special = False
        if can_use_special(self.current_player, card, True):
            char = self.current_player.character
            if char.suit == "Bastoni" and card.suit == "Bastoni":
                choice = self.ask_choice("Iron Versatility", "Attack", "Shield")
                card._temp_bastoni_choice = choice.lower()
                special = True
            elif char.suit in ("Spade", "Coppe") and card.suit == "Coppe":
                self_dmg = max(0, card.value // 2 - char.heal_bonus)
                title    = f"Poison Cup  ·  {self_dmg} HP self-damage"
                choice   = self.ask_choice(title, "Poison Cup", "Heal Normally")
                special  = (choice == "Poison Cup")

        self.selected_cards.append((card, special, widget))
        bbox = self.canvas.bbox(widget)
        if bbox:
            self.canvas.create_rectangle(
                bbox, outline=GOLD, width=3,
                tags=f"highlight_{id(widget)}")
        self.update_gui()

    # ── Rank-match check ──────────────────────────────────────────────────────
    def _rank_match_check(self):
        if len(self.selected_cards) < 2:
            return False, None
        last_two = self.selected_cards[-2:]
        cards = [c for c, _, _ in last_two]
        if cards[0].rank != cards[1].rank:
            return False, None

        shield_in_match = any(
            (not sp and c.suit == "Denari") or
            (sp and self.current_player.character.suit == "Bastoni"
             and c.suit == "Bastoni"
             and getattr(c, '_temp_bastoni_choice', 'attack') == 'shield')
            for c, sp, _ in last_two
        )
        shield_bonus = None
        if shield_in_match:
            title  = f"Rank Match  ·  {cards[0].rank}s  ·  Shield bonus →"
            choice = self.ask_choice(title, "Extra Health", "Extra Attack")
            shield_bonus = "health" if choice == "Extra Health" else "attack"

        return True, shield_bonus

    # ── Game mode selection ───────────────────────────────────────────────────
    def _choose_game_mode(self):
        """Ask 'Two Players' vs 'vs Computer' after rules are dismissed."""
        mode = self.ask_choice("Game Mode", "Two Players", "vs Computer")
        if mode == "vs Computer":
            diff = self.ask_choice("Difficulty", "Normal", "Easy")
            self.ai      = DisfidaAI(difficulty=diff.lower())
            self.ai_mode = True
            self.log_messages(
                [f"🤖 Computer opponent ({diff}) will play as Player 2."],
                tag="ai")
        else:
            self.ai_mode = False

    # ── AI turn automation ────────────────────────────────────────────────────
    def _do_ai_pre_shield(self):
        """Execute AI's pre-shield choice automatically."""
        inp     = self.ai.choose_pre_shield(self.player2, self.player1)
        summary, _ = player_pre_shield(self.player2, self.player1, inp)
        self.log_messages(["🤖 AI pre-shield:"] + summary, tag="ai")
        self.phase = "main"
        self.current_player = self.player1
        self.canvas.itemconfig(self.turn_label,
                               text="Turn 1/40 — Player 1 goes first")
        self.log_messages(["✅ Pre-shield phase complete!"], tag="system")
        self.update_gui()

    def _do_ai_turn(self):
        """Execute the AI player's full turn."""
        player   = self.player2
        opponent = self.player1

        self.log_messages(["🤖 AI is thinking…"], tag="ai")
        self.root.update()   # render the log line before computing

        inp, rm, rsb = self.ai.choose_action(player, opponent)

        summary, turn_consumed = resolve_turn(
            player, opponent, inp,
            rank_match=rm,
            rank_match_shield_bonus=rsb)
        self.log_messages(summary)

        if not turn_consumed:
            # Fallback: skip (shouldn't normally happen)
            self.log_messages(["🤖 AI falls back to skip."], tag="ai")
            resolve_turn(player, opponent, "0")

        result, victory_messages = check_victory(self.player1, self.player2)
        if result:
            self.log_messages(victory_messages, tag="special")
            self.update_gui()
            self.end_game(result)
            return

        draw_summary = refill_hand(player)
        self.log_messages(draw_summary, tag="draw")

        if check_turn_limit(self.player1, self.player2):
            winner, end_summary = resolve_tournament_end(self.player1, self.player2)
            self.log_messages(end_summary, tag="special")
            self.update_gui()
            self.end_game(winner.name.lower())
            return

        self.turn_count += 1
        self.current_player = self.player1
        self.update_gui()

    def _maybe_trigger_ai(self):
        """If AI mode and it's now P2's turn, schedule AI action."""
        if self.ai_mode and self.current_player == self.player2:
            self.root.after(AI_DELAY_MS, self._do_ai_turn)

    def _maybe_trigger_ai_preshield(self):
        """If AI mode and we're in pre_shield_p2, schedule AI pre-shield."""
        if self.ai_mode and self.phase == "pre_shield_p2":
            self.root.after(AI_DELAY_MS, self._do_ai_pre_shield)

    # ── play_combo ────────────────────────────────────────────────────────────
    def play_combo(self):
        # Pre-shield P1
        if self.phase == "pre_shield_p1":
            if len(self.selected_cards) != 1:
                self.log_messages(
                    ["Select exactly one card for pre-shield, or Skip."],
                    tag="system")
                return
            card, special, _ = self.selected_cards[0]
            idx = self.player1.hand.index(card)
            inp = f"{idx + 1}{'s' if special else ''}"
            summary, success = player_pre_shield(self.player1, self.player2, inp)
            self.log_messages(summary)
            self.selected_cards = []
            if not success:
                self.update_gui()
                return
            self.phase = "pre_shield_p2"
            self.current_player = self.player2
            self.canvas.itemconfig(self.turn_label,
                                   text="Pre-Shield Phase: Player 2")
            self.update_gui()
            self._maybe_trigger_ai_preshield()
            return

        # Pre-shield P2 (human)
        if self.phase == "pre_shield_p2":
            if self.ai_mode:
                return   # AI handles this automatically
            if len(self.selected_cards) != 1:
                self.log_messages(
                    ["Select exactly one card for pre-shield, or Skip."],
                    tag="system")
                return
            card, special, _ = self.selected_cards[0]
            idx = self.player2.hand.index(card)
            inp = f"{idx + 1}{'s' if special else ''}"
            summary, success = player_pre_shield(self.player2, self.player1, inp)
            self.log_messages(summary)
            self.selected_cards = []
            if not success:
                self.update_gui()
                return
            self.phase = "main"
            self.current_player = self.player1
            self.canvas.itemconfig(self.turn_label,
                                   text="Turn 1/40 — Player 1 goes first")
            self.log_messages(["✅ Pre-shield phase complete!"], tag="system")
            self.update_gui()
            return

        # Main game turn
        inp = "0"
        rank_match, rank_match_shield_bonus = False, None

        if self.selected_cards:
            indices = [self.current_player.hand.index(c) + 1
                       for c, _, _ in self.selected_cards]
            specials = ["s" if s else "" for _, s, _ in self.selected_cards]
            inp = ",".join(f"{i}{sf}" for i, sf in zip(indices, specials))
            rank_match, rank_match_shield_bonus = self._rank_match_check()

        opponent = (self.player2 if self.current_player == self.player1
                    else self.player1)
        summary, turn_consumed = resolve_turn(
            self.current_player, opponent, inp,
            rank_match=rank_match,
            rank_match_shield_bonus=rank_match_shield_bonus)
        self.log_messages(summary)

        if not turn_consumed:
            self.selected_cards = []
            self.update_gui()
            return

        self.selected_cards = []

        result, victory_messages = check_victory(self.player1, self.player2)
        if result:
            self.log_messages(victory_messages, tag="special")
            self.update_gui()
            self.end_game(result)
            return

        draw_summary = refill_hand(self.current_player)
        self.log_messages(draw_summary, tag="draw")

        if check_turn_limit(self.player1, self.player2):
            winner, end_summary = resolve_tournament_end(self.player1, self.player2)
            self.log_messages(end_summary, tag="special")
            self.update_gui()
            self.end_game(winner.name.lower())
            return

        self.turn_count += 1
        self.current_player = (self.player2 if self.current_player == self.player1
                                else self.player1)
        self.update_gui()
        self._maybe_trigger_ai()

    # ── skip_turn ─────────────────────────────────────────────────────────────
    def skip_turn(self):
        if self.phase in ("pre_shield_p1", "pre_shield_p2"):
            if self.phase == "pre_shield_p2" and self.ai_mode:
                return   # AI handles P2 pre-shield

            player   = self.player1 if self.phase == "pre_shield_p1" else self.player2
            opponent = self.player2 if self.phase == "pre_shield_p1" else self.player1
            summary, _ = player_pre_shield(player, opponent, "0")
            self.log_messages(summary, tag="skip")

            next_phase = "pre_shield_p2" if self.phase == "pre_shield_p1" else "main"
            self.phase = next_phase
            self.current_player = (self.player2 if next_phase == "pre_shield_p2"
                                    else self.player1)
            lbl = ("Pre-Shield Phase: Player 2" if next_phase == "pre_shield_p2"
                   else "Turn 1/40 — Player 1 goes first")
            self.canvas.itemconfig(self.turn_label, text=lbl)
            self.update_gui()

            if next_phase == "main":
                self.log_messages(["✅ Pre-shield phase complete!"], tag="system")
            else:
                self._maybe_trigger_ai_preshield()
            return

        opponent = (self.player2 if self.current_player == self.player1
                    else self.player1)
        summary, _ = resolve_turn(self.current_player, opponent, "0")
        self.log_messages(summary, tag="skip")
        draw_summary = refill_hand(self.current_player)
        self.log_messages(draw_summary, tag="draw")

        if check_turn_limit(self.player1, self.player2):
            winner, end_summary = resolve_tournament_end(self.player1, self.player2)
            self.log_messages(end_summary, tag="special")
            self.update_gui()
            self.end_game(winner.name.lower())
            return

        self.turn_count += 1
        self.current_player = (self.player2 if self.current_player == self.player1
                                else self.player1)
        self.update_gui()
        self._maybe_trigger_ai()

    # ── Rules modal ───────────────────────────────────────────────────────────
    def show_rules_modal(self):
        modal = tk.Toplevel(self.root)
        modal.title("Disfida — Rules")
        modal.configure(bg=PANEL_BG)
        modal.resizable(False, False)

        text = tk.Text(modal, width=62, height=38,
                       font=("Courier", 10), bg="#0d1f17", fg=WHITE,
                       insertbackground=WHITE, relief="flat",
                       wrap=tk.WORD, padx=12, pady=10)
        scrollbar = tk.Scrollbar(modal, command=text.yview,
                                  bg=PANEL_BG, troughcolor=BG)
        text.config(yscrollcommand=scrollbar.set)
        text.insert(tk.END, get_rules_summary())
        text.config(state="disabled")
        text.grid(row=0, column=0, sticky="nsew")
        scrollbar.grid(row=0, column=1, sticky="ns")
        tk.Button(modal, text="⚔️  Start Game",
                  font=("Georgia", 13, "bold"),
                  bg=BTN_BG, fg=WHITE,
                  activebackground=BTN_ACTIVE, activeforeground=WHITE,
                  relief="flat", padx=24, pady=8,
                  command=modal.destroy).grid(
            row=1, column=0, columnspan=2, pady=14)

        modal.update_idletasks()
        modal.lift()
        modal.focus_force()
        modal.wait_window()

    def show_rules(self):
        self.show_rules_modal()

    # ── End game ──────────────────────────────────────────────────────────────
    def end_game(self, result):
        messagebox.showinfo("Game Over",
                            f"Tournament complete!\n\n{result.upper()} WINS!")
        self.root.quit()

    def start_pre_shield_phase(self):
        self.log_messages(
            ["🛡️  PRE-GAME SHIELD PHASE",
             "Each player may place one shield before the game begins."],
            tag="system")
