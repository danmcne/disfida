# card_game_gui.py
import tkinter as tk
from tkinter import messagebox
from card_game_logic import *
from card_image_manager import CardImageManager
from card_game_ai import DisfidaAI

BG         = "#1a472a"
PANEL_BG   = "#163d24"
GOLD       = "#d4af37"
WHITE      = "#f0f0e8"
LIGHT_GREY = "#a0a090"
BTN_BG     = "#2d6a4f"
BTN_ACTIVE = "#40916c"

CARD_W, CARD_H = 80, 132    # fixed card image dimensions
AI_CARD_DELAY  = 250         # ms per card during AI animation
AI_RESOLVE_DELAY = 350       # ms pause after last card before resolving


class CardGameGUI:
    def __init__(self, root):
        self.root = root
        self.root.title("Disfida — Italian Card Combat")
        self.root.geometry("1280x780")
        self.root.minsize(1050, 750)
        # Prevent accidental closure destroying root while modals are up
        self.root.protocol("WM_DELETE_WINDOW", self._on_close)

        self.side_panel = tk.Frame(root, width=270, bg="#0d1f17")
        self.side_panel.pack(side="right", fill="y")
        self.side_panel.pack_propagate(False)

        self.canvas = tk.Canvas(root, bg=BG, highlightthickness=0)
        self.canvas.pack(side="left", fill="both", expand=True)

        self.image_manager = CardImageManager()
        self.selected_cards  = []   # (card, special, widget) — human selection
        self.ai_staged       = []   # card objects staged during AI animation
        self.player1, self.player2, init_messages = init_game()
        self.current_player = self.player1
        self.turn_count = 0
        self.phase = "pre_shield_p1"
        self._resize_job = None

        self.p1_hand_widgets    = []
        self.p2_hand_widgets    = []
        self.p1_shield_widgets  = []
        self.p2_shield_widgets  = []
        self.played_card_widgets = []

        self.ai_mode = False
        self.ai      = None
        self._dialog_active = False   # True while ask_choice is waiting

        self.setup_gui()
        self.log_messages(init_messages, tag="system")

        # Ensure canvas has rendered before showing modals
        self.root.update_idletasks()

        self.show_rules_modal()
        self._choose_game_mode()
        self.start_pre_shield_phase()

    # ── Proportional layout ───────────────────────────────────────────────────

    def _L(self):
        """Compute layout positions from current canvas size.

        P2 items anchor at the top; P1 items anchor from the bottom.
        Divider sits between them.  Card images are fixed 80×132 px.
        """
        W = max(self.canvas.winfo_width(),  900)
        H = max(self.canvas.winfo_height(), 750)

        # P2 area — anchored to top
        p2_hand_y   = 55
        p2_shield_y = p2_hand_y + CARD_H + 15          # 202

        # P1 area — anchored to bottom
        p1_info_h   = 85    # height of the info+hp+button strip
        p1_info_y   = H - p1_info_h - 10
        p1_hand_y   = p1_info_y - CARD_H - 15
        p1_shield_y = p1_hand_y - CARD_H - 15

        # Divider: midpoint between P2 shields bottom and P1 shields top
        top_end  = p2_shield_y + CARD_H + 8
        bot_start = p1_shield_y - 8
        divider_y = (top_end + bot_start) // 2

        bar_x0 = int(W * 0.28)
        bar_x1 = int(W * 0.57)
        card_x  = int(W * 0.11)
        card_step = max(CARD_W + 10, int(W * 0.092))
        stack_x = min(W - CARD_W - 20, int(W * 0.86))

        return dict(
            W=W, H=H,
            p2_hand_y=p2_hand_y,
            p2_shield_y=p2_shield_y,
            divider_y=divider_y,
            p1_shield_y=p1_shield_y,
            p1_hand_y=p1_hand_y,
            p1_info_y=p1_info_y,
            p1_hp_bar_y=p1_info_y + 22,
            p1_btn_y=p1_info_y + 55,
            p2_info_y=8,
            p2_hp_bar_y=28,
            bar_x0=bar_x0, bar_x1=bar_x1,
            card_x=card_x, card_step=card_step, stack_x=stack_x,
            mid_x=W // 2,
        )

    # ── GUI setup (creates canvas items; update_gui positions them) ───────────

    def setup_gui(self):
        c = self.canvas

        # Static background strips — repositioned in update_gui
        self.bg_p2_strip  = c.create_rectangle(0, 0, 1, 1, fill=PANEL_BG, outline="")
        self.bg_divider   = c.create_rectangle(0, 0, 1, 1, fill=PANEL_BG, outline="")
        self.bg_p1_strip  = c.create_rectangle(0, 0, 1, 1, fill=PANEL_BG, outline="")

        # Turn / phase banner
        self.turn_label = c.create_text(
            0, 0, text="Pre-Shield Phase: Player 1",
            font=("Georgia", 13, "bold"), fill=GOLD)

        # P2 static info
        self.p2_char_label  = c.create_text(0, 0, anchor="nw", text="",
                                              font=("Georgia", 11, "bold"), fill=GOLD)
        self.p2_hp_text     = c.create_text(0, 0, anchor="nw", text="",
                                             font=("Courier", 11, "bold"), fill=WHITE)
        self.p2_bonus_label = c.create_text(0, 0, anchor="nw", text="",
                                             font=("Courier", 9), fill=LIGHT_GREY)
        self.p2_stack_label = c.create_text(0, 0, anchor="nw", text="",
                                             font=("Courier", 10), fill=LIGHT_GREY)
        self.p2_hp_bar_bg   = c.create_rectangle(0, 0, 1, 1, fill="#550000", outline="")
        self.p2_hp_bar      = c.create_rectangle(0, 0, 1, 1, fill="#44bb44", outline="")
        self.p2_char_img    = c.create_image(
            0, 0, image=self.image_manager.get_image(None, rotated=True), anchor="nw")

        # P1 static info
        self.p1_char_label  = c.create_text(0, 0, anchor="nw", text="",
                                              font=("Georgia", 11, "bold"), fill=GOLD)
        self.p1_hp_text     = c.create_text(0, 0, anchor="nw", text="",
                                             font=("Courier", 11, "bold"), fill=WHITE)
        self.p1_bonus_label = c.create_text(0, 0, anchor="nw", text="",
                                             font=("Courier", 9), fill=LIGHT_GREY)
        self.p1_stack_label = c.create_text(0, 0, anchor="nw", text="",
                                             font=("Courier", 10), fill=LIGHT_GREY)
        self.p1_hp_bar_bg   = c.create_rectangle(0, 0, 1, 1, fill="#550000", outline="")
        self.p1_hp_bar      = c.create_rectangle(0, 0, 1, 1, fill="#44bb44", outline="")
        self.p1_char_img    = c.create_image(
            0, 0, image=self.image_manager.get_image(None), anchor="nw")

        # Section labels (repositioned in update_gui)
        self.lbl_p2_hand   = c.create_text(0, 0, anchor="nw", text="P2 hand",
                                            font=("Courier", 8), fill=LIGHT_GREY)
        self.lbl_p2_shield = c.create_text(0, 0, anchor="nw", text="P2 shields ▼",
                                            font=("Courier", 8), fill=LIGHT_GREY)
        self.lbl_p1_shield = c.create_text(0, 0, anchor="nw", text="P1 shields ▲",
                                            font=("Courier", 8), fill=LIGHT_GREY)
        self.lbl_p1_hand   = c.create_text(0, 0, anchor="nw", text="P1 hand",
                                            font=("Courier", 8), fill=LIGHT_GREY)

        # Log panel in side_panel
        tk.Label(self.side_panel, text="GAME LOG",
                 font=("Georgia", 10, "bold"), bg="#0d1f17",
                 fg=GOLD, pady=6).pack(fill="x")
        tk.Frame(self.side_panel, height=1, bg=GOLD).pack(fill="x")
        log_inner = tk.Frame(self.side_panel, bg="#0d1f17")
        log_inner.pack(fill="both", expand=True, padx=4, pady=4)
        self.log_text = tk.Text(log_inner, font=("Courier", 9),
                                bg="#0d1f17", fg=WHITE,
                                insertbackground=WHITE, relief="flat",
                                wrap=tk.WORD, padx=6, pady=4)
        log_scroll = tk.Scrollbar(log_inner, command=self.log_text.yview,
                                   bg="#163d24", troughcolor=BG)
        self.log_text.config(yscrollcommand=log_scroll.set)
        log_scroll.pack(side="right", fill="y")
        self.log_text.pack(side="left", fill="both", expand=True)
        for tag, fg, font in [
            ("system",  "#aaaaaa", None),
            ("damage",  "#ff7070", None),
            ("heal",    "#70ff70", None),
            ("shield",  "#70c8ff", None),
            ("special", "#ffdd55", None),
            ("rank",    "#ff99ff", ("Courier", 9, "bold")),
            ("destroy", "#ff4444", ("Courier", 9, "bold")),
            ("skip",    "#888888", None),
            ("draw",    "#99bbaa", None),
            ("ai",      "#c8aaff", None),
        ]:
            kw = dict(foreground=fg)
            if font:
                kw["font"] = font
            self.log_text.tag_config(tag, **kw)

        # Buttons in side_panel (no repositioning needed on resize)
        btn_frame = tk.Frame(self.side_panel, bg=PANEL_BG)
        btn_frame.pack(side="bottom", fill="x", padx=6, pady=8)
        btn_cfg = dict(font=("Georgia", 11, "bold"), bg=BTN_BG, fg=WHITE,
                       activebackground=BTN_ACTIVE, activeforeground=WHITE,
                       relief="flat", pady=5, cursor="hand2")
        tk.Button(btn_frame, text="▶  Play / Confirm",
                  command=self.play_combo, **btn_cfg).pack(fill="x", pady=2)
        tk.Button(btn_frame, text="⏭  Skip Turn",
                  command=self.skip_turn, **btn_cfg).pack(fill="x", pady=2)
        tk.Button(btn_frame, text="📖  Rules",
                  command=self.show_rules, **btn_cfg).pack(fill="x", pady=2)

        # Resize binding
        self.canvas.bind("<Configure>", self._on_canvas_resize)

        self.update_gui()

    def _on_canvas_resize(self, event):
        if self._resize_job:
            self.root.after_cancel(self._resize_job)
        self._resize_job = self.root.after(80, self.update_gui)

    # ── Helpers ───────────────────────────────────────────────────────────────

    def _hp_color(self, hp):
        if hp > 25: return "#44bb44"
        if hp > 12: return "#ff9900"
        return "#dd2222"

    def _on_close(self):
        if messagebox.askokcancel("Quit", "Quit Disfida?"):
            self.root.destroy()

    def ask_choice(self, title, option1, option2):
        """Minimal dialog: title bar + two large buttons.  TclError-safe.
        Sets _dialog_active while waiting so select_card ignores stray clicks.
        The Rules window deliberately does NOT use this method, so card clicks
        behind the rules popup remain unblocked.
        """
        result = [option1]
        self._dialog_active = True
        try:
            dlg = tk.Toplevel(self.root)
        except tk.TclError:
            self._dialog_active = False
            return option1
        try:
            dlg.title(title)
            dlg.configure(bg=PANEL_BG)
            dlg.resizable(False, False)
            dlg.protocol("WM_DELETE_WINDOW", lambda: None)

            frm = tk.Frame(dlg, bg=PANEL_BG, padx=24, pady=20)
            frm.pack()
            btn_cfg = dict(font=("Georgia", 14, "bold"), bg=BTN_BG, fg=WHITE,
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
        except tk.TclError:
            pass
        finally:
            self._dialog_active = False
        return result[0]

    # ── Log ───────────────────────────────────────────────────────────────────

    def log_messages(self, messages, tag=None):
        for msg in messages:
            t = tag or self._auto_tag(msg)
            self.log_text.insert(tk.END, msg + "\n", t)
        self.log_text.see(tk.END)

    def _auto_tag(self, msg):
        m = msg.lower()
        if "🤖" in msg:                                     return "ai"
        if "rank match" in m or "✨" in m:                  return "rank"
        if "destroyed" in m or "removed" in m:              return "destroy"
        if "blocked" in m:                                   return "destroy"
        if "poison cup" in m or ("damage" in m and "self" not in m): return "damage"
        if "attack" in m and "blocked" not in m:            return "damage"
        if "heal" in m or "+hp" in m:                       return "heal"
        if "shield" in m:                                    return "shield"
        if "skip" in m:                                      return "skip"
        if "draw" in m or "draws" in m:                     return "draw"
        if "special" in m or "iron" in m:                   return "special"
        return "system"

    # ── update_gui ────────────────────────────────────────────────────────────

    def update_gui(self):
        L  = self._L()
        W, H = L['W'], L['H']
        c  = self.canvas
        p1, p2 = self.player1, self.player2

        # ── Background strips ──
        c.coords(self.bg_p2_strip,  0, 0, W, 52)
        c.coords(self.bg_divider,   0, L['divider_y'] - 16, W, L['divider_y'] + 16)
        c.coords(self.bg_p1_strip,  0, L['p1_info_y'] - 4, W, H)

        # ── Turn banner ──
        c.coords(self.turn_label, L['mid_x'], L['divider_y'])

        # ── P2 info ──
        c.coords(self.p2_char_label,  10, L['p2_info_y'])
        c.coords(self.p2_hp_text,     L['bar_x0'], L['p2_info_y'])
        c.coords(self.p2_bonus_label, 10, L['p2_info_y'] + 18)
        c.coords(self.p2_stack_label, int(W * 0.6), L['p2_info_y'])
        c.coords(self.p2_hp_bar_bg,   L['bar_x0'], L['p2_hp_bar_y'],
                                      L['bar_x1'], L['p2_hp_bar_y'] + 10)
        frac2 = max(0.0, min(1.0, p2.health / 40))
        c.coords(self.p2_hp_bar, L['bar_x0'], L['p2_hp_bar_y'],
                 L['bar_x0'] + int((L['bar_x1'] - L['bar_x0']) * frac2),
                 L['p2_hp_bar_y'] + 10)
        c.itemconfig(self.p2_hp_bar, fill=self._hp_color(p2.health))
        c.coords(self.p2_char_img, L['stack_x'], L['p2_hand_y'])

        # ── P1 info ──
        c.coords(self.p1_char_label,  10, L['p1_info_y'])
        c.coords(self.p1_hp_text,     L['bar_x0'], L['p1_info_y'])
        c.coords(self.p1_bonus_label, 10, L['p1_info_y'] + 18)
        c.coords(self.p1_stack_label, int(W * 0.6), L['p1_info_y'])
        c.coords(self.p1_hp_bar_bg,   L['bar_x0'], L['p1_hp_bar_y'],
                                      L['bar_x1'], L['p1_hp_bar_y'] + 10)
        frac1 = max(0.0, min(1.0, p1.health / 40))
        c.coords(self.p1_hp_bar, L['bar_x0'], L['p1_hp_bar_y'],
                 L['bar_x0'] + int((L['bar_x1'] - L['bar_x0']) * frac1),
                 L['p1_hp_bar_y'] + 10)
        c.itemconfig(self.p1_hp_bar, fill=self._hp_color(p1.health))
        c.coords(self.p1_char_img, L['stack_x'], L['p1_hand_y'])

        # ── Text content ──
        ai_tag = "  🤖" if self.ai_mode else ""
        c.itemconfig(self.p1_char_label,
            text=f"P1 — {p1.character.face} of {p1.character.suit}")
        c.itemconfig(self.p2_char_label,
            text=f"P2 — {p2.character.face} of {p2.character.suit}{ai_tag}")
        c.itemconfig(self.p1_hp_text,
            text=f"HP: {p1.health}/40", fill=self._hp_color(p1.health))
        c.itemconfig(self.p2_hp_text,
            text=f"HP: {p2.health}/40", fill=self._hp_color(p2.health))
        c.itemconfig(self.p1_bonus_label,
            text=(f"Atk +{p1.character.attack_bonus}  "
                  f"Heal +{p1.character.heal_bonus}  "
                  f"Def +{p1.character.defense_bonus}  │  "
                  f"Removed: {len(p1.discard_pile)}"))
        c.itemconfig(self.p2_bonus_label,
            text=(f"Atk +{p2.character.attack_bonus}  "
                  f"Heal +{p2.character.heal_bonus}  "
                  f"Def +{p2.character.defense_bonus}  │  "
                  f"Removed: {len(p2.discard_pile)}"))
        c.itemconfig(self.p1_stack_label, text=f"Deck: {len(p1.stack)} cards")
        c.itemconfig(self.p2_stack_label, text=f"Deck: {len(p2.stack)} cards")
        c.itemconfig(self.p1_char_img,
            image=self.image_manager.get_image(Card(p1.character.suit, p1.character.face)))
        c.itemconfig(self.p2_char_img,
            image=self.image_manager.get_image(Card(p2.character.suit, p2.character.face),
                                               rotated=True))

        # ── Section labels ──
        c.coords(self.lbl_p2_hand,   10, L['p2_hand_y'] - 12)
        c.coords(self.lbl_p2_shield, 10, L['p2_shield_y'] - 12)
        c.coords(self.lbl_p1_shield, 10, L['p1_shield_y'] - 12)
        c.coords(self.lbl_p1_hand,   10, L['p1_hand_y'] - 12)

        # ── P1 hand ──
        for w in self.p1_hand_widgets: c.delete(w)
        self.p1_hand_widgets = []
        for i, card in enumerate(p1.hand):
            x = L['card_x'] + i * L['card_step']
            w = c.create_image(x, L['p1_hand_y'],
                image=self.image_manager.get_image(card), anchor="nw")
            c.tag_bind(w, "<Button-1>",
                lambda e, cc=card, ww=w: self.select_card(cc, ww))
            self.p1_hand_widgets.append(w)

        # ── P2 hand ──
        for w in self.p2_hand_widgets: c.delete(w)
        self.p2_hand_widgets = []
        for i, card in enumerate(p2.hand):
            x = L['card_x'] + i * L['card_step']
            w = c.create_image(x, L['p2_hand_y'],
                image=self.image_manager.get_image(card, rotated=True), anchor="nw")
            if not self.ai_mode:
                c.tag_bind(w, "<Button-1>",
                    lambda e, cc=card, ww=w: self.select_card(cc, ww))
            self.p2_hand_widgets.append(w)

        # ── P1 shields ──
        for w in self.p1_shield_widgets: c.delete(w)
        self.p1_shield_widgets = []
        for i, card in enumerate(sorted(p1.shields, key=lambda cc: cc.value)):
            x = L['card_x'] + i * 72
            w = c.create_image(x, L['p1_shield_y'],
                image=self.image_manager.get_image(card), anchor="nw")
            self.p1_shield_widgets.append(w)

        # ── P2 shields ──
        for w in self.p2_shield_widgets: c.delete(w)
        self.p2_shield_widgets = []
        for i, card in enumerate(sorted(p2.shields, key=lambda cc: cc.value)):
            x = L['card_x'] + i * 72
            w = c.create_image(x, L['p2_shield_y'],
                image=self.image_manager.get_image(card, rotated=True), anchor="nw")
            self.p2_shield_widgets.append(w)

        # ── Staged cards (human selected OR AI staged) ──
        for w in self.played_card_widgets: c.delete(w)
        self.played_card_widgets = []

        if self.ai_staged:
            # AI animation: show staged cards in P2's staging area
            for i, card in enumerate(self.ai_staged):
                x = L['card_x'] + int(W * 0.38) + i * 72
                w = c.create_image(x, L['p2_shield_y'],
                    image=self.image_manager.get_image(card, rotated=True), anchor="nw")
                self.played_card_widgets.append(w)
        else:
            # Human selection staging
            is_p2  = (self.current_player == p2)
            stage_y = L['p2_shield_y'] if is_p2 else L['p1_shield_y']
            rot     = is_p2
            for i, (card, _, _) in enumerate(self.selected_cards):
                x = L['card_x'] + int(W * 0.38) + i * 72
                w = c.create_image(x, stage_y,
                    image=self.image_manager.get_image(card, rotated=rot), anchor="nw")
                self.played_card_widgets.append(w)

        # ── Turn banner text ──
        if self.phase == "main":
            p1a = "◀ ACTIVE" if self.current_player == p1 else ""
            p2a = ("ACTIVE ▶  🤖" if self.ai_mode and self.current_player == p2
                   else ("ACTIVE ▶" if self.current_player == p2 else ""))
            c.itemconfig(self.turn_label,
                text=(f"{p2a}  Turn {self.turn_count + 1}/40  "
                      f"(P1: {p1.turns_played}/20  P2: {p2.turns_played}/20)  {p1a}"))

    # ── Card selection ────────────────────────────────────────────────────────

    def select_card(self, card, widget):
        if self._dialog_active:
            return   # a choice dialog is open — ignore stray clicks
        if self.ai_staged:
            return   # block interaction during AI animation
        if self.ai_mode and card in self.player2.hand:
            return
        if card in self.player1.hand and self.current_player != self.player1:
            return
        if card in self.player2.hand and self.current_player != self.player2:
            return

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
                choice   = self.ask_choice(
                    f"Poison Cup  ·  {self_dmg} HP self-damage",
                    "Poison Cup", "Heal Normally")
                special = (choice == "Poison Cup")

        self.selected_cards.append((card, special, widget))
        bbox = self.canvas.bbox(widget)
        if bbox:
            self.canvas.create_rectangle(
                bbox, outline=GOLD, width=3, tags=f"highlight_{id(widget)}")
        self.update_gui()

    # ── Rank-match check ──────────────────────────────────────────────────────

    def _rank_match_check(self):
        if len(self.selected_cards) < 2:
            return False, None

        last_two = self.selected_cards[-2:]
        cards    = [c for c, _, _ in last_two]

        # Ranks must match, and the last card must not be an Ace
        if cards[0].rank != cards[1].rank or cards[-1].rank == "A":
            return False, None

        # Shield bonus only fires when the LAST card (the one that doubles)
        # is itself a shield.  Second-to-last shields just play at face value.
        last_card, last_special, _ = self.selected_cards[-1]
        last_is_shield = (
            (not last_special and last_card.suit == "Denari") or
            (last_special
             and self.current_player.character.suit == "Bastoni"
             and last_card.suit == "Bastoni"
             and getattr(last_card, '_temp_bastoni_choice', 'attack') == 'shield')
        )
        shield_bonus = None
        if last_is_shield:
            choice = self.ask_choice(
                f"Rank Match  ·  {cards[0].rank}s  ·  Shield bonus →",
                "Extra Health", "Extra Attack")
            shield_bonus = "health" if choice == "Extra Health" else "attack"

        return True, shield_bonus

    # ── Game mode selection ───────────────────────────────────────────────────

    def _choose_game_mode(self):
        mode = self.ask_choice("Game Mode", "Two Players", "vs Computer")
        if mode == "vs Computer":
            diff         = self.ask_choice("Difficulty", "Normal", "Easy")
            self.ai      = DisfidaAI(difficulty=diff.lower())
            self.ai_mode = True
            self.log_messages(
                [f"🤖 Computer opponent ({diff}) will play as Player 2."], tag="ai")

    # ── AI turn automation ────────────────────────────────────────────────────

    def _maybe_trigger_ai(self):
        if self.ai_mode and self.current_player == self.player2:
            self.root.after(AI_CARD_DELAY, self._do_ai_turn)

    def _maybe_trigger_ai_preshield(self):
        if self.ai_mode and self.phase == "pre_shield_p2":
            self.root.after(AI_CARD_DELAY, self._do_ai_pre_shield)

    def _do_ai_pre_shield(self):
        inp      = self.ai.choose_pre_shield(self.player2, self.player1)
        summary, _ = player_pre_shield(self.player2, self.player1, inp)
        self.log_messages(["🤖 AI pre-shield:"] + summary, tag="ai")
        self.phase = "main"
        self.current_player = self.player1
        self.canvas.itemconfig(self.turn_label, text="Turn 1/40 — Player 1 goes first")
        self.log_messages(["✅ Pre-shield phase complete!"], tag="system")
        self.update_gui()

    def _do_ai_turn(self):
        """Compute AI action then display cards one at a time before resolving."""
        player   = self.player2
        opponent = self.player1

        self.log_messages(["🤖 AI is thinking…"], tag="ai")
        self.root.update()

        try:
            inp, rm, rsb = self.ai.choose_action(player, opponent)
        except Exception as exc:
            self.log_messages(
                [f"🤖 AI error ({type(exc).__name__}: {exc}) — skipping."], tag="ai")
            self._finish_ai_turn(player, opponent, "0", False, None)
            return

        if inp == "0":
            self.log_messages(["🤖 AI skips."], tag="skip")
            self._finish_ai_turn(player, opponent, "0", False, None)
            return

        # Parse the combo into card objects for staged display
        actions = parse_input(inp, player)
        if not actions:
            self._finish_ai_turn(player, opponent, inp, rm, rsb)
            return

        cards_to_stage = [player.hand[idx] for idx, _ in actions]
        self.ai_staged = []

        def stage_next(i):
            if i < len(cards_to_stage):
                self.ai_staged.append(cards_to_stage[i])
                self.update_gui()
                self.root.after(AI_CARD_DELAY, lambda: stage_next(i + 1))
            else:
                # All cards displayed — pause then resolve
                self.root.after(AI_RESOLVE_DELAY,
                                lambda: self._finish_ai_turn(player, opponent, inp, rm, rsb))

        stage_next(0)

    def _finish_ai_turn(self, player, opponent, inp, rm, rsb):
        """Execute the AI's previously staged turn."""
        self.ai_staged = []

        summary, turn_consumed = resolve_turn(
            player, opponent, inp, rank_match=rm, rank_match_shield_bonus=rsb)
        self.log_messages(summary)

        if not turn_consumed:
            self.log_messages(["🤖 AI invalid move — skipping."], tag="ai")
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

    # ── play_combo ────────────────────────────────────────────────────────────

    def play_combo(self):
        if self.ai_staged:
            return   # block during AI animation

        if self.phase == "pre_shield_p1":
            if len(self.selected_cards) != 1:
                self.log_messages(["Select one card for pre-shield, or Skip."],
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
            self.canvas.itemconfig(self.turn_label, text="Pre-Shield Phase: Player 2")
            self.update_gui()
            self._maybe_trigger_ai_preshield()
            return

        if self.phase == "pre_shield_p2":
            if self.ai_mode:
                return
            if len(self.selected_cards) != 1:
                self.log_messages(["Select one card for pre-shield, or Skip."],
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
            self.canvas.itemconfig(self.turn_label, text="Turn 1/40 — Player 1 goes first")
            self.log_messages(["✅ Pre-shield phase complete!"], tag="system")
            self.update_gui()
            return

        # Main turn
        inp = "0"
        rm, rsb = False, None
        if self.selected_cards:
            indices = [self.current_player.hand.index(c) + 1
                       for c, _, _ in self.selected_cards]
            specials = ["s" if s else "" for _, s, _ in self.selected_cards]
            inp = ",".join(f"{i}{sf}" for i, sf in zip(indices, specials))
            rm, rsb = self._rank_match_check()

        opponent = (self.player2 if self.current_player == self.player1
                    else self.player1)
        summary, turn_consumed = resolve_turn(
            self.current_player, opponent, inp, rank_match=rm,
            rank_match_shield_bonus=rsb)
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
        if self.ai_staged:
            return

        if self.phase in ("pre_shield_p1", "pre_shield_p2"):
            if self.phase == "pre_shield_p2" and self.ai_mode:
                return
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
        try:
            modal = tk.Toplevel(self.root)
        except tk.TclError:
            return
        modal.title("Disfida — Rules")
        modal.configure(bg=PANEL_BG)
        modal.resizable(False, False)

        text = tk.Text(modal, width=62, height=38, font=("Courier", 10),
                       bg="#0d1f17", fg=WHITE, insertbackground=WHITE,
                       relief="flat", wrap=tk.WORD, padx=12, pady=10)
        scrollbar = tk.Scrollbar(modal, command=text.yview,
                                  bg=PANEL_BG, troughcolor=BG)
        text.config(yscrollcommand=scrollbar.set)
        text.insert(tk.END, get_rules_summary())
        text.config(state="disabled")
        text.grid(row=0, column=0, sticky="nsew")
        scrollbar.grid(row=0, column=1, sticky="ns")
        tk.Button(modal, text="⚔️  Start Game",
                  font=("Georgia", 13, "bold"), bg=BTN_BG, fg=WHITE,
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
