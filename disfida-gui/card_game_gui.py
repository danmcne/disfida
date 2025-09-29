# card_game_gui.py
import tkinter as tk
from tkinter import messagebox
from card_game_logic import *
from card_image_manager import CardImageManager

class CardGameGUI:
    def __init__(self, root):
        self.root = root
        self.root.title("Italian Card Combat")
        self.canvas = tk.Canvas(root, width=1280, height=720, bg="darkgreen")
        self.canvas.pack(fill="both", expand=True)
        self.image_manager = CardImageManager()
        self.selected_cards = []  # List of (card, special_flag, widget) tuples
        self.player1, self.player2, init_messages = init_game()
        self.current_player = self.player1
        self.turn_count = 0
        self.phase = "pre_shield_p1"
        self.p1_hand_widgets = []
        self.p2_hand_widgets = []
        self.p1_shield_widgets = []
        self.p2_shield_widgets = []
        self.played_card_widgets = []
        self.setup_gui()
        self.log_messages(init_messages)
        self.start_pre_shield_phase()

    def setup_gui(self):
        # Turn indicator
        self.turn_label = self.canvas.create_text(640, 10, text="Pre-Shield Phase: Player 1", anchor="center", font=("Arial", 12))
        
        # Player 1 (bottom, cards at y=500, info at y=640)
        self.p1_char_img = self.canvas.create_image(50, 500, image=self.image_manager.get_image(None), anchor="nw")
        self.p1_char_label = self.canvas.create_text(50, 640, text=f"{self.player1.character.face} of {self.player1.character.suit}", anchor="nw", font=("Arial", 12))
        self.p1_hp_label = self.canvas.create_text(50, 660, text=f"HP: {self.player1.health}/40", anchor="nw", font=("Arial", 12))
        self.p1_bonus_label = self.canvas.create_text(50, 680, text=f"Attack: +{self.player1.character.attack_bonus}, Heal: +{self.player1.character.heal_bonus}, Defense: +{self.player1.character.defense_bonus}", anchor="nw", font=("Arial", 12))
        self.p1_stack_img = self.canvas.create_image(850, 500, image=self.image_manager.get_image(None), anchor="nw")
        self.p1_stack_label = self.canvas.create_text(850, 640, text=f"Stack: {len(self.player1.stack)}", anchor="nw", font=("Arial", 12))
        
        # Player 2 (top, cards at y=100, info at y=0)
        self.p2_char_img = self.canvas.create_image(50, 100, image=self.image_manager.get_image(None, rotated=True), anchor="nw")
        self.p2_char_label = self.canvas.create_text(50, 0, text=f"{self.player2.character.face} of {self.player2.character.suit}", anchor="nw", font=("Arial", 12))
        self.p2_hp_label = self.canvas.create_text(50, 20, text=f"HP: {self.player2.health}/40", anchor="nw", font=("Arial", 12))
        self.p2_bonus_label = self.canvas.create_text(50, 40, text=f"Attack: +{self.player2.character.attack_bonus}, Heal: +{self.player2.character.heal_bonus}, Defense: +{self.player2.character.defense_bonus}", anchor="nw", font=("Arial", 12))
        self.p2_stack_img = self.canvas.create_image(850, 100, image=self.image_manager.get_image(None, rotated=True), anchor="nw")
        self.p2_stack_label = self.canvas.create_text(850, 0, text=f"Stack: {len(self.player2.stack)}", anchor="nw", font=("Arial", 12))
        
        # Play area: two rows (P2: y=200-250, P1: y=350-400)
        self.log_text = tk.Text(self.canvas, width=40, height=10, font=("Arial", 10))
        self.canvas.create_window(1050, 300, window=self.log_text)
        
        # Control buttons (bottom center, y=650)
        self.play_button = tk.Button(self.canvas, text="Play Combo", command=self.play_combo)
        self.canvas.create_window(540, 650, window=self.play_button)
        self.skip_button = tk.Button(self.canvas, text="Skip Turn", command=self.skip_turn)
        self.canvas.create_window(640, 650, window=self.skip_button)
        self.rules_button = tk.Button(self.canvas, text="Rules", command=self.show_rules)
        self.canvas.create_window(740, 650, window=self.rules_button)
        
        self.update_gui()

    def log_messages(self, messages):
        for msg in messages:
            self.log_text.insert(tk.END, msg + "\n")
        self.log_text.see(tk.END)

    def update_gui(self):
        # Update character images
        p1_char_card = Card(self.player1.character.suit, self.player1.character.face)
        p2_char_card = Card(self.player2.character.suit, self.player2.character.face)
        self.canvas.itemconfig(self.p1_char_img, image=self.image_manager.get_image(p1_char_card))
        self.canvas.itemconfig(self.p2_char_img, image=self.image_manager.get_image(p2_char_card, rotated=True))
        
        # Update health and stack
        self.canvas.itemconfig(self.p1_hp_label, text=f"HP: {self.player1.health}/40")
        self.canvas.itemconfig(self.p2_hp_label, text=f"HP: {self.player2.health}/40")
        self.canvas.itemconfig(self.p1_stack_label, text=f"Stack: {len(self.player1.stack)}")
        self.canvas.itemconfig(self.p2_stack_label, text=f"Stack: {len(self.player2.stack)}")
        
        # Update hands (5 slots, no overlap)
        for widget in self.p1_hand_widgets:
            self.canvas.delete(widget)
        self.p1_hand_widgets = []
        for i in range(5):
            x = 200 + i * 100  # 80px card + 20px gap
            if i < len(self.player1.hand):
                card = self.player1.hand[i]
                img = self.image_manager.get_image(card)
                card_widget = self.canvas.create_image(x, 500, image=img, anchor="nw")
                self.canvas.tag_bind(card_widget, "<Button-1>", lambda e, c=card, w=card_widget: self.select_card(c, w))
                self.p1_hand_widgets.append(card_widget)
        
        for widget in self.p2_hand_widgets:
            self.canvas.delete(widget)
        self.p2_hand_widgets = []
        for i in range(5):
            x = 200 + i * 100
            if i < len(self.player2.hand):
                card = self.player2.hand[i]
                img = self.image_manager.get_image(card, rotated=True)
                card_widget = self.canvas.create_image(x, 100, image=img, anchor="nw")
                self.canvas.tag_bind(card_widget, "<Button-1>", lambda e, c=card, w=card_widget: self.select_card(c, w))
                self.p2_hand_widgets.append(card_widget)
        
        # Update shields (left side)
        for widget in self.p1_shield_widgets:
            self.canvas.delete(widget)
        self.p1_shield_widgets = []
        for i, card in enumerate(sorted(self.player1.shields, key=lambda c: c.value)):
            x = 200 + i * 70  # Smaller spacing for shields
            card_widget = self.canvas.create_image(x, 350, image=self.image_manager.get_image(card), anchor="nw")
            self.p1_shield_widgets.append(card_widget)
        
        for widget in self.p2_shield_widgets:
            self.canvas.delete(widget)
        self.p2_shield_widgets = []
        for i, card in enumerate(sorted(self.player2.shields, key=lambda c: c.value)):
            x = 200 + i * 70
            card_widget = self.canvas.create_image(x, 200, image=self.image_manager.get_image(card, rotated=True), anchor="nw")
            self.p2_shield_widgets.append(card_widget)
        
        # Update played cards (right side)
        for widget in self.played_card_widgets:
            self.canvas.delete(widget)
        self.played_card_widgets = []
        for i, (card, special, _) in enumerate(self.selected_cards):
            x = 450 + i * 70
            y = 350 if self.current_player == self.player1 else 200
            img = self.image_manager.get_image(card, rotated=(self.current_player == self.player2))
            card_widget = self.canvas.create_image(x, y, image=img, anchor="nw")
            self.played_card_widgets.append(card_widget)
        
        # Update turn label
        if self.phase == "main":
            self.canvas.itemconfig(self.turn_label, text=f"{self.current_player.name}'s Turn ({self.turn_count + 1}/40) | P1: {self.player1.turns_played}/20, P2: {self.player2.turns_played}/20")

    def select_card(self, card, widget):
        if self.current_player != self.player1 and self.current_player != self.player2:
            return
        if card in self.player1.hand and self.current_player != self.player1:
            return
        if card in self.player2.hand and self.current_player != self.player2:
            return
        
        # Deselect if already selected
        for i, (c, s, w) in enumerate(self.selected_cards):
            if c == card:
                self.selected_cards.pop(i)
                self.canvas.delete(self.canvas.find_withtag(f"highlight_{id(w)}"))
                self.update_gui()
                return
        
        special = False
        if can_use_special(self.current_player, card, True):
            if self.current_player.character.suit == "Bastoni" and card.suit == "Bastoni":
                choice = messagebox.askquestion("Bastoni Special", f"Play {card} as attack or shield?", icon="question")
                card._temp_bastoni_choice = "attack" if choice == "yes" else "shield"
                special = True
            elif self.current_player.character.suit in ["Spade", "Coppe"]:
                special = messagebox.askyesno("Special Action", f"Use {card} as special (e.g., Blood Price or Charity's Burden)?")
        
        self.selected_cards.append((card, special, widget))
        self.canvas.create_rectangle(self.canvas.bbox(widget), outline="yellow", width=3, tags=f"highlight_{id(widget)}")
        self.update_gui()

    def play_combo(self):
        if self.phase == "pre_shield_p1":
            if len(self.selected_cards) != 1:
                self.log_messages(["Select exactly one card for pre-shield"])
                return
            card, special, _ = self.selected_cards[0]
            idx = self.player1.hand.index(card)
            inp = f"{idx + 1}{'s' if special else ''}"
            summary = player_pre_shield(self.player1, self.player2, inp)
            self.log_messages(summary)
            self.selected_cards = []
            self.phase = "pre_shield_p2"
            self.current_player = self.player2
            self.canvas.itemconfig(self.turn_label, text="Pre-Shield Phase: Player 2")
            self.update_gui()
            return
        elif self.phase == "pre_shield_p2":
            if len(self.selected_cards) != 1:
                self.log_messages(["Select exactly one card for pre-shield"])
                return
            card, special, _ = self.selected_cards[0]
            idx = self.player2.hand.index(card)
            inp = f"{idx + 1}{'s' if special else ''}"
            summary = player_pre_shield(self.player2, self.player1, inp)
            self.log_messages(summary)
            self.selected_cards = []
            self.phase = "main"
            self.current_player = self.player1
            self.canvas.itemconfig(self.turn_label, text=f"{self.current_player.name}'s Turn (1/40)")
            self.log_messages(["✅ Pre-shield phase complete! Player 1 attacks first..."])
            self.update_gui()
            return
        
        inp = "0"
        if self.selected_cards:
            indices = [self.current_player.hand.index(card) + 1 for card, _, _ in self.selected_cards]
            special_flags = ["s" if special else "" for _, special, _ in self.selected_cards]
            inp = ",".join(f"{idx}{s}" for idx, s in zip(indices, special_flags))
        
        opponent = self.player2 if self.current_player == self.player1 else self.player1
        summary = resolve_turn(self.current_player, opponent, inp)
        self.log_messages(summary)
        
        self.selected_cards = []
        result, victory_messages = check_victory(self.player1, self.player2)
        if result:
            self.log_messages(victory_messages)
            self.end_game(result)
            return
        
        draw_summary = refill_hand(self.current_player)
        self.log_messages(draw_summary)
        
        if check_turn_limit(self.player1, self.player2):
            winner, end_summary = resolve_tournament_end(self.player1, self.player2)
            self.log_messages(end_summary)
            self.end_game(winner.name.lower())
            return
        
        self.turn_count += 1
        self.current_player = self.player2 if self.current_player == self.player1 else self.player1
        self.update_gui()

    def skip_turn(self):
        if self.phase in ["pre_shield_p1", "pre_shield_p2"]:
            player = self.player1 if self.phase == "pre_shield_p1" else self.player2
            opponent = self.player2 if self.phase == "pre_shield_p1" else self.player1
            summary = player_pre_shield(player, opponent, "0")
            self.log_messages(summary)
            self.phase = "pre_shield_p2" if self.phase == "pre_shield_p1" else "main"
            self.current_player = self.player2 if self.phase == "pre_shield_p2" else self.player1
            self.canvas.itemconfig(self.turn_label, text=f"Pre-Shield Phase: Player 2" if self.phase == "pre_shield_p2" else f"{self.current_player.name}'s Turn (1/40)")
            self.update_gui()
            if self.phase == "main":
                self.log_messages(["✅ Pre-shield phase complete! Player 1 attacks first..."])
            return
        
        opponent = self.player2 if self.current_player == self.player1 else self.player1
        summary = resolve_turn(self.current_player, opponent, "0")
        self.log_messages(summary)
        draw_summary = refill_hand(self.current_player)
        self.log_messages(draw_summary)
        if check_turn_limit(self.player1, self.player2):
            winner, end_summary = resolve_tournament_end(self.player1, self.player2)
            self.log_messages(end_summary)
            self.end_game(winner.name.lower())
            return
        self.turn_count += 1
        self.current_player = self.player2 if self.current_player == self.player1 else self.player1
        self.update_gui()

    def show_rules(self):
        rules_window = tk.Toplevel(self.root)
        rules_window.title("Game Rules")
        rules_text = tk.Text(rules_window, width=80, height=30, font=("Arial", 10))
        rules_text.insert(tk.END, get_rules_summary())
        rules_text.pack()
        rules_text.config(state="disabled")

    def end_game(self, result):
        messagebox.showinfo("Game Over", f"Tournament Complete! {result.upper()} Wins!")
        self.root.quit()

    def start_pre_shield_phase(self):
        self.log_messages(["🛡️ PRE-GAME SHIELD PHASE", "Both players may play one shield before the game begins."])
