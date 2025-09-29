# card_game_logic.py
import random
import math

class Card:
    def __init__(self, suit, rank):
        self.suit = suit
        self.rank = rank
        if rank == "A":
            self.value = 11
        elif rank in ["Fante", "Cavallo", "Re"]:
            self.value = 10
        else:
            self.value = int(rank)
    
    def __str__(self):
        return f"{self.rank} of {self.suit}"

class Character:
    def __init__(self, face, suit):
        self.face = face
        self.suit = suit
        self.attack_bonus = 1 if face == "Cavallo" else 0
        self.defense_bonus = 2 if face == "Re" else 0
        self.heal_bonus = 2 if face == "Fante" else 0
        self.stack_size = 13 if suit == "Denari" else 12
        self.hand_size = 5 if suit == "Denari" else 4

class Player:
    def __init__(self, name, character, stack):
        self.name = name
        self.character = character
        self.stack = stack
        self.hand = []
        self.shields = []
        self.health = 40
        self.turns_played = 0

MAX_PLAYER_TURNS = 20
RESOLUTION = "hp_winner_player2_tie"

def build_numeric_deck():
    suits = ["Denari", "Coppe", "Spade", "Bastoni"]
    ranks = ["A", "2", "3", "4", "5", "6", "7"]
    deck = [Card(s, r) for s in suits for r in ranks]
    return deck

def create_face_cards():
    suits = ["Denari", "Coppe", "Spade", "Bastoni"]
    faces = ["Fante", "Cavallo", "Re"]
    return [Card(s, f) for s in suits for f in faces]

def get_rules_summary():
    rules = [
        "=" * 50,
        "ITALIAN CARD COMBAT - TOURNAMENT RULES",
        "=" * 50,
        "OBJECTIVE: Reduce opponent's HP to 0 or survive 40 turns with more HP",
        f"TURN LIMIT: {MAX_PLAYER_TURNS} turns each (40 total)",
        f"RESOLUTION: Higher HP wins. Exact tie: Player 2 wins!",
        "DECK: 40-card Italian deck (A=11, 2-7, Fante/Cavallo/Re=10)",
        "START: 40 HP each, 4-card hand (5 for Coins char)",
        "\nCHARACTERS & BONUSES:",
        "• Re (King): +2 defense per shield",
        "• Cavallo (Knight): +1 attack per attack card",
        "• Fante (Page): +2 healing per healing card",
        "\nSUIT SPECIALS:",
        "• Coins: Wealth of Choice - +1 card in stack/hand (passive)",
        "• Swords: Blood Price - Use Cups as attacks (ignore shields, self-damage)",
        "• Cups: Charity's Burden - Use Swords as healing (opponent gains half)",
        "• Clubs: Iron Versatility - Clubs can be attack OR shield",
        "\nCOMBOS: Sequence of character-suit cards + optional 1 non-suit card",
        "TURNS: Skip, play 1 card, or play combo. Draw to hand size at turn end",
        "SHIELDS: Visible on table, destroyed smallest→largest, cycle to deck bottom",
        "ENDGAME: After 40 turns, higher HP wins. Exact tie = Player 2 wins!",
        "=" * 50
    ]
    return "\n".join(rules)

def draw_cards(player, n):
    drawn = 0
    drawn_cards = []
    for _ in range(n):
        if player.stack:
            card = player.stack.pop(0)  # Remove from top
            player.hand.append(card)
            drawn_cards.append(card)
            drawn += 1
        else:
            break
    return drawn, drawn_cards

def validate_combo(actions, player):
    if len(actions) == 0:
        return False
    cards = [player.hand[idx] for idx, _ in actions]
    if len(cards) == 1:
        return True
    character_suit = player.character.suit
    non_suit_count = 0
    for i, card in enumerate(cards):
        if i < len(cards) - 1:
            if card.suit != character_suit:
                return False
        else:
            if card.suit != character_suit:
                non_suit_count += 1
    return non_suit_count <= 1


def move_card_to_bottom(player, card):
    # Ensure card is not already in stack to prevent duplicates
    if card not in player.stack:
        player.stack.append(card)

def remove_shields_for_attack(opponent, attack_value):
    if not opponent.shields:
        return attack_value, []
    remaining = attack_value
    sorted_shields = sorted(opponent.shields, key=lambda c: c.value)
    removed_shields = []
    for shield in sorted_shields:
        effective_defense = shield.value + opponent.character.defense_bonus
        remaining -= effective_defense
        removed_shields.append(shield)
        if remaining <= 0:
            break
    for shield in removed_shields:
        opponent.shields.remove(shield)
        move_card_to_bottom(opponent, shield)
    shields_str = ", ".join([str(s) for s in removed_shields]) if removed_shields else ""
    summary = [f"Shields {shields_str} absorbed attack, sent to bottom of deck"] if removed_shields else []
    return max(0, remaining), summary

def apply_heal(player, card, opponent):
    turn_summary = []
    heal_amount = card.value + player.character.heal_bonus
    player.health = min(40, player.health + heal_amount)
    opponent_bonus = 0
    if player.character.suit == "Coppe" and card.suit == "Spade":
        opponent_bonus = card.value // 2
        opponent.health = min(40, opponent.health + opponent_bonus)
        turn_summary.append(f"Heal {card}: +{heal_amount} HP, +{opponent_bonus} to opponent")
    else:
        turn_summary.append(f"Heal {card}: +{heal_amount} HP")
    return heal_amount, opponent_bonus, turn_summary

def apply_attack(player, card, opponent, ignore_shields=False):
    turn_summary = []
    attack_value = card.value + player.character.attack_bonus
    remaining_damage = attack_value
    if ignore_shields:
        opponent.health -= attack_value
        turn_summary.append(f"Blood Price {card}: {attack_value} damage (ignores shields)")
    else:
        remaining_damage, shield_summary = remove_shields_for_attack(opponent, attack_value)
        turn_summary.extend(shield_summary)
        if remaining_damage > 0:
            opponent.health -= remaining_damage
            turn_summary.append(f"Attack {card}: {attack_value}→{remaining_damage} damage")
        else:
            turn_summary.append(f"Attack {card}: {attack_value} blocked by shields")
    self_damage = 0
    if player.character.suit == "Spade" and card.suit == "Coppe" and ignore_shields:
        self_damage = card.value // 2
        player.health -= self_damage
        turn_summary.append(f"Blood Price self-damage: -{self_damage} HP")
    return attack_value, remaining_damage, self_damage, turn_summary

def apply_shield(player, card):
    effective_value = card.value + player.character.defense_bonus
    player.shields.append(card)
    return [f"Shield {card}: +{effective_value} defense"]

def can_use_special(player, card, special_flag):
    if not special_flag:
        return False
    if player.character.suit == "Spade" and card.suit == "Coppe":
        return True
    elif player.character.suit == "Coppe" and card.suit == "Spade":
        return True
    elif player.character.suit == "Bastoni" and card.suit == "Bastoni":
        return True
    return False

def parse_input(inp, player):
    if inp == "0":
        return []
    actions = []
    parts = inp.split(',')
    for part in parts:
        part = part.strip()
        if not part:
            continue
        special = part.endswith('s')
        if special:
            part = part[:-1]
        try:
            idx = int(part) - 1
            if idx < 0 or idx >= len(player.hand):
                return None
            actions.append((idx, special))
        except ValueError:
            return None
    return actions

def resolve_turn(player, opponent, inp):
    turn_summary = []
    if inp == "0":
        turn_summary.append(f"{player.name} skips turn")
        player.turns_played += 1
        return turn_summary
    actions = parse_input(inp, player)
    if actions is None:
        turn_summary.append("Invalid input")
        return turn_summary
    if not validate_combo(actions, player):
        turn_summary.append("Invalid combo! Must be character-suit cards + optional 1 non-suit card.")
        return turn_summary
    special_error = False
    for idx, special in actions:
        card = player.hand[idx]
        if special and not can_use_special(player, card, special):
            turn_summary.append(f"Error: {card} has no special play for {player.character.face} of {player.character.suit}")
            special_error = True
            break
    if special_error:
        return turn_summary
    cards_to_play = [(player.hand[idx], special) for idx, special in actions]
    for idx, _ in sorted(actions, key=lambda x: x[0], reverse=True):
        del player.hand[idx]
    cycled_cards = []
    for card, special in cards_to_play:
        was_shield = False
        if special:
            if player.character.suit == "Bastoni" and card.suit == "Bastoni":
                choice = getattr(card, '_temp_bastoni_choice', 'attack')
                if choice == 'attack':
                    _, remaining, self_dmg, attack_summary = apply_attack(player, card, opponent)
                    turn_summary.extend(attack_summary)
                    cycled_cards.append(card)
                else:
                    turn_summary.extend(apply_shield(player, card))
                    was_shield = True
            elif player.character.suit == "Spade" and card.suit == "Coppe":
                _, _, self_dmg, attack_summary = apply_attack(player, card, opponent, ignore_shields=True)
                turn_summary.extend(attack_summary)
                cycled_cards.append(card)
            elif player.character.suit == "Coppe" and card.suit == "Spade":
                heal_amt, opp_bonus, heal_summary = apply_heal(player, card, opponent)
                turn_summary.extend(heal_summary)
                cycled_cards.append(card)
        else:
            if card.suit == "Denari":
                turn_summary.extend(apply_shield(player, card))
                was_shield = True
            elif card.suit == "Coppe":
                heal_amt, opp_bonus, heal_summary = apply_heal(player, card, opponent)
                turn_summary.extend(heal_summary)
                cycled_cards.append(card)
            else:
                _, remaining, self_dmg, attack_summary = apply_attack(player, card, opponent)
                turn_summary.extend(attack_summary)
                cycled_cards.append(card)
    for card in cycled_cards:
        move_card_to_bottom(player, card)
    player.turns_played += 1
    return turn_summary

def player_pre_shield(player, opponent, inp):
    turn_summary = []
    if inp == "0":
        turn_summary.append(f"{player.name} skips pre-shield")
        needed = player.character.hand_size - len(player.hand)
        if needed > 0:
            drawn, _ = draw_cards(player, needed)
            turn_summary.append(f"{player.name} draws {drawn} card(s) to hand")
        return turn_summary
    actions = parse_input(inp, player)
    if actions is None or len(actions) != 1:
        turn_summary.append("Invalid: must be exactly ONE card (e.g., '1' or '3s')")
        return turn_summary
    idx, special = actions[0]
    card = player.hand[idx]
    del player.hand[idx]
    if card.suit == "Denari":
        turn_summary.extend(apply_shield(player, card))
        turn_summary.append(f"{player.name} plays starting shield: {card}")
    elif special and player.character.suit == "Bastoni" and card.suit == "Bastoni":
        turn_summary.extend(apply_shield(player, card))
        turn_summary.append(f"{player.name} plays starting shield {card} (Club special)")
    else:
        turn_summary.append(f"Invalid: {card} cannot be played as a shield")
        player.hand.insert(idx, card)
        return turn_summary
    needed = player.character.hand_size - len(player.hand)
    if needed > 0:
        drawn, _ = draw_cards(player, needed)
        turn_summary.append(f"{player.name} draws {drawn} card(s) to reach full hand size")
    return turn_summary

def check_victory(p1, p2):
    if p1.health <= 0 and p2.health <= 0:
        return "tie", ["DOUBLE KNOCKOUT - IT'S A TIE!"]
    elif p1.health <= 0:
        return "p2", ["Player 2 WINS BY KNOCKOUT!"]
    elif p2.health <= 0:
        return "p1", ["Player 1 WINS BY KNOCKOUT!"]
    return None, []

def check_turn_limit(p1, p2):
    return p1.turns_played >= MAX_PLAYER_TURNS or p2.turns_played >= MAX_PLAYER_TURNS

def resolve_tournament_end(p1, p2):
    summary = [
        f"⏰ TOURNAMENT END! {p1.turns_played + p2.turns_played} total turns played",
        f"Final Health - Player 1 ({p1.character.face}): {p1.health}HP",
        f"Player 2 ({p2.character.face}): {p2.health}HP"
    ]
    if p1.health > p2.health:
        summary.append(f"🏆 PLAYER 1 WINS BY SURVIVAL! ({p1.health} > {p2.health} HP)")
        return p1, summary
    elif p2.health > p1.health:
        summary.append(f"🏆 PLAYER 2 WINS BY SURVIVAL! ({p2.health} > {p2.health} HP)")
        return p2, summary
    else:
        summary.append(f"⚖️ EXACT HEALTH TIE ({p1.health} HP each)!")
        summary.append(f"🎯 PLAYER 2 WINS TIEBREAKER!")
        return p2, summary

def refill_hand(player):
    needed = player.character.hand_size - len(player.hand)
    summary = []
    if needed > 0:
        drawn, _ = draw_cards(player, needed)
        if drawn > 0:
            summary.append(f"{player.name} draws {drawn} card(s) at end of turn")
    return summary

def init_game():
    face_cards = create_face_cards()
    numeric_deck = build_numeric_deck()
    random.shuffle(numeric_deck)
    p1_char_card = random.choice(face_cards)
    remaining_faces = [c for c in face_cards if c != p1_char_card]
    p2_char_card = random.choice(remaining_faces)
    p1_character = Character(p1_char_card.rank, p1_char_card.suit)
    p2_character = Character(p2_char_card.rank, p2_char_card.suit)
    total_needed = p1_character.stack_size + p2_character.stack_size
    available_cards = numeric_deck[:total_needed]
    if len(available_cards) < total_needed:
        extra_needed = total_needed - len(available_cards)
        extra_cards = random.sample(numeric_deck, min(extra_needed, len(numeric_deck)))
        available_cards.extend(extra_cards)
        random.shuffle(available_cards)
        available_cards = available_cards[:total_needed]
    p1_stack = available_cards[:p1_character.stack_size]
    p2_stack = available_cards[p1_character.stack_size:p1_character.stack_size + p2_character.stack_size]
    # Ensure no duplicates between stacks
    if any(card in p2_stack for card in p1_stack):
        random.shuffle(available_cards)
        p1_stack = available_cards[:p1_character.stack_size]
        p2_stack = available_cards[p1_character.stack_size:p1_character.stack_size + p2_character.stack_size]
    player1 = Player("Player 1", p1_character, p1_stack)
    player2 = Player("Player 2", p2_character, p2_stack)
    drawn1, _ = draw_cards(player1, p1_character.hand_size)
    drawn2, _ = draw_cards(player2, p2_character.hand_size)
    return player1, player2, [
        f"🎭 Characters assigned:",
        f"Player 1: {p1_character.face} of {p1_character.suit}",
        f"Player 2: {p2_character.face} of {p2_character.suit}",
        f"Player 1 draws {drawn1} cards",
        f"Player 2 draws {drawn2} cards"
    ]
