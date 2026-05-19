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
        self.discard_pile = []

MAX_PLAYER_TURNS = 20
RESOLUTION = "hp_winner_player2_tie"

# Allied suit pairs for cross-combos:
#   Spade + Coppe  (Swords+Cups)
#   Bastoni + Denari  (Clubs+Coins)
ALLIED_SUITS = {
    "Spade":   {"Spade", "Coppe"},
    "Coppe":   {"Spade", "Coppe"},
    "Bastoni": {"Bastoni", "Denari"},
    "Denari":  {"Bastoni", "Denari"},
}

def last_two_rank_match(cards):
    """True if the last two cards share the same rank AND that rank is not Ace.
    Aces are already the strongest card; doubling them is too powerful.
    """
    if len(cards) < 2:
        return False
    return cards[-1].rank == cards[-2].rank and cards[-1].rank != "A"

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
        "=" * 54,
        "         DISFIDA — TOURNAMENT RULES",
        "=" * 54,
        "",
        "OBJECTIVE",
        "  Reduce your opponent's HP to 0.",
        f"  If neither falls in {MAX_PLAYER_TURNS} turns each, higher HP wins.",
        "  Exact HP tie at end: Player 2 wins.",
        "",
        "THE CARDS",
        "  Uses the 40-card Italian deck (or French equivalent).",
        "  Face cards (Fante/Cavallo/Re) are character cards only —",
        "  they are NOT part of the playing deck.",
        "  Playing deck: A=11, 2–7 (face value). Split between players.",
        "  Coins (Denari / ♦) = Shield   Cups (Coppe / ♥) = Heal",
        "  Swords (Spade / ♠) = Attack   Clubs (Bastoni / ♣) = Attack",
        "",
        "CHARACTERS & BONUSES",
        "  Re   (King):   +2 to effective defense of each shield",
        "  Cavallo (Knight): +1 to each attack",
        "  Fante (Page):  +2 to each heal; reduces Poison Cup self-damage by 2",
        "",
        "SUIT SPECIALS",
        "  Coins:  Wealth of Choice — +1 card in stack and opening hand (passive)",
        "  Swords or Cups: Poison Cup — play a Cups card as an attack:",
        "            • Ignores opponent's shields",
        "            • Self-damage = floor(card value / 2)",
        "            • Fante's heal bonus reduces self-damage (min 0)",
        "            • The Cups card is ALWAYS permanently removed after use",
        "  Clubs:  Iron Versatility — play a Clubs card as attack OR shield (you choose)",
        "",
        "COMBOS",
        "  Allied pairs:  Swords + Cups (♠/♥)  |  Clubs + Coins (♣/♦)",
        "  A combo = any allied-suit cards + at most 1 wildcard from any other suit.",
        "  Each card plays its normal role (Coins=shield, Cups=heal, others=attack).",
        "",
        "RANK-MATCH BONUS",
        "  If the last two cards of your combo share the same rank (2–7 only, not Ace),",
        "  the LAST card's effect is doubled.",
        "  Example: play 5♠ then 5♥ — the 5♥ heals for double value.",
        "  (Ordering matters: put the card you want doubled in the final position.)",
        "",
        "CARD DESTRUCTION (ineffective cards permanently leave the game)",
        "  Attack fully blocked by shields → attack card destroyed",
        "  Shield overwhelmed (attack continues past it) → shield destroyed",
        "  Shield that stops the attack → cycles to bottom of deck",
        "  Heal that doesn't restore player to full health (40 HP) → heal card destroyed",
        "  Poison Cup card → always destroyed after use",
        "",
        "TURNS",
        "  Skip, play 1 card, or play a combo.",
        "  Draw back to hand size at end of turn.",
        "=" * 54,
    ]
    return "\n".join(rules)

def draw_cards(player, n):
    drawn = 0
    drawn_cards = []
    for _ in range(n):
        if player.stack:
            card = player.stack.pop(0)
            player.hand.append(card)
            drawn_cards.append(card)
            drawn += 1
        else:
            break
    return drawn, drawn_cards

def validate_combo(actions, player):
    """Allied-suit cards + at most 1 wildcard from any other suit.
    Single-card plays always valid.
    """
    if len(actions) == 0:
        return False
    cards = [player.hand[idx] for idx, _ in actions]
    if len(cards) == 1:
        return True
    allied = ALLIED_SUITS[player.character.suit]
    non_allied = [c for c in cards if c.suit not in allied]
    # At most 1 wildcard, and at least 1 allied-suit card
    return len(non_allied) <= 1 and (len(cards) - len(non_allied)) >= 1

def move_card_to_bottom(player, card):
    if card not in player.stack:
        player.stack.append(card)

def discard_card(player, card):
    player.discard_pile.append(card)

def remove_shields_for_attack(opponent, attack_value):
    """Process shields smallest->largest until attack is stopped or all are consumed.

    Destruction rules:
      - Shields overwhelmed by the attack (attack continues past them) -> DESTROYED
      - The one shield that finally stops the attack -> cycles to bottom of deck
      - If the attack breaks through everything, all shields consumed are destroyed
    """
    if not opponent.shields:
        return attack_value, [], False
    remaining = attack_value
    sorted_shields = sorted(opponent.shields, key=lambda c: c.value)
    summary = []
    attack_got_through = False

    for shield in sorted_shields:
        effective_defense = shield.value + opponent.character.defense_bonus
        opponent.shields.remove(shield)
        remaining -= effective_defense

        if remaining <= 0:
            # This shield stopped the attack -- cycle it back
            move_card_to_bottom(opponent, shield)
            summary.append(f"Shield {shield} (def {effective_defense}) blocked the attack, returned to deck")
            break
        else:
            # This shield was overwhelmed -- destroy it permanently
            discard_card(opponent, shield)
            summary.append(f"Shield {shield} (def {effective_defense}) overwhelmed and DESTROYED")
            attack_got_through = True

    return max(0, remaining), summary, attack_got_through

def apply_heal(player, card, opponent, double=False):
    """Heal player. Card is effective (cycles back) only if it restores the player
    to full health (40 HP). Otherwise permanently removed.
    double=True when this card is part of a rank-match bonus pair.
    """
    turn_summary = []
    base = card.value + player.character.heal_bonus
    heal_amount = base * 2 if double else base
    player.health = min(40, player.health + heal_amount)
    was_effective = (player.health == 40)
    double_str = " [×2 rank match]" if double else ""
    destroyed_str = "" if was_effective else " [didn't restore full HP — card DESTROYED]"
    turn_summary.append(f"Heal {card}: +{heal_amount} HP{double_str}{destroyed_str}")
    return heal_amount, turn_summary, was_effective

def apply_attack(player, card, opponent, ignore_shields=False, double=False):
    """Apply attack. was_effective = True only if damage reached the opponent.
    double=True when this card is part of a rank-match bonus pair.
    """
    turn_summary = []
    base = card.value + player.character.attack_bonus
    attack_value = base * 2 if double else base
    remaining_damage = 0
    double_str = " [×2 rank match]" if double else ""
    if ignore_shields:
        remaining_damage = attack_value
        opponent.health -= attack_value
        turn_summary.append(f"Poison Cup {card}: {attack_value} damage (ignores shields){double_str}")
        was_effective = True
    else:
        remaining_damage, shield_summary, _ = remove_shields_for_attack(opponent, attack_value)
        turn_summary.extend(shield_summary)
        was_effective = remaining_damage > 0
        if remaining_damage > 0:
            opponent.health -= remaining_damage
            turn_summary.append(f"Attack {card}: {attack_value}→{remaining_damage} damage{double_str}")
        else:
            turn_summary.append(f"Attack {card}: {attack_value} fully blocked [card DESTROYED]")
    return attack_value, remaining_damage, turn_summary, was_effective

def apply_poison_cup(player, card, opponent, double=False):
    turn_summary = []
    base = card.value + player.character.attack_bonus
    attack_value = base * 2 if double else base
    self_damage = max(0, (card.value // 2) - player.character.heal_bonus)
    opponent.health -= attack_value
    player.health -= self_damage
    double_str = " [×2 rank match]" if double else ""
    turn_summary.append(f"Poison Cup {card}: {attack_value} damage, -{self_damage} self-damage{double_str}")
    return attack_value, self_damage, turn_summary, True

def apply_shield(player, card):
    effective_value = card.value + player.character.defense_bonus
    player.shields.append(card)
    return [f"Shield {card}: +{effective_value} defense"], True

def can_use_special(player, card, special_flag):
    if not special_flag:
        return False
    if (player.character.suit in ["Spade", "Coppe"]) and card.suit == "Coppe":
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

def resolve_turn(player, opponent, inp, rank_match=False, rank_match_shield_bonus=None):
    """Resolve a player's turn.

    rank_match: True if the GUI detected that the last two played cards share a rank.
    rank_match_shield_bonus: 'health' or 'attack' — used when one of those last two
        cards is a shield and the player chose where to redirect the doubled effect.

    Returns (summary: list[str], turn_consumed: bool).
    turn_consumed is False for invalid input; the GUI should let the player retry.
    """
    turn_summary = []
    if inp == "0":
        turn_summary.append(f"{player.name} skips turn")
        player.turns_played += 1
        return turn_summary, True

    actions = parse_input(inp, player)
    if actions is None:
        turn_summary.append("Invalid input — please try again.")
        return turn_summary, False

    if not validate_combo(actions, player):
        allied = sorted(ALLIED_SUITS[player.character.suit])
        turn_summary.append(f"Invalid combo! Allied suits for {player.character.suit}: {', '.join(allied)}")
        turn_summary.append("Combos: allied-suit cards + at most 1 wildcard from any other suit.")
        return turn_summary, False

    for idx, special in actions:
        card = player.hand[idx]
        if special and not can_use_special(player, card, special):
            turn_summary.append(f"Error: {card} has no special play for {player.character.face} of {player.character.suit}")
            return turn_summary, False

    # Snapshot cards then remove from hand
    cards_to_play = [(player.hand[idx], special) for idx, special in actions]
    for idx, _ in sorted(actions, key=lambda x: x[0], reverse=True):
        del player.hand[idx]

    # Rank-match: last card only, and never for Aces.
    # The defensive Ace check here catches any case where rank_match=True was
    # passed incorrectly (e.g. from an older GUI version).
    n = len(cards_to_play)
    last_card_rank = cards_to_play[-1][0].rank if cards_to_play else None
    rank_match_set = (
        {n - 1}
        if rank_match and n >= 2 and last_card_rank != "A"
        else set()
    )
    if rank_match_set:
        turn_summary.append("✨ RANK MATCH! Last card is doubled!")

    # Process each card
    for i, (card, special) in enumerate(cards_to_play):
        was_shield = False
        card_summary = []
        was_effective = False
        double = i in rank_match_set

        # Detect if this doubled card is a shield (so bonus is redirected)
        is_shield_card = (not special and card.suit == "Denari") or (
            special and player.character.suit == "Bastoni" and card.suit == "Bastoni"
            and getattr(card, '_temp_bastoni_choice', 'attack') == 'shield'
        )
        apply_shield_bonus = double and is_shield_card and rank_match_shield_bonus in ('health', 'attack')

        if special:
            if (player.character.suit in ["Spade", "Coppe"]) and card.suit == "Coppe":
                _, _, strike_summary, was_effective = apply_poison_cup(player, card, opponent, double=double)
                card_summary.extend(strike_summary)
                discard_card(player, card)
                card_summary.append(f"{card} (Poison Cup) permanently removed from game")

            elif player.character.suit == "Bastoni" and card.suit == "Bastoni":
                choice = getattr(card, '_temp_bastoni_choice', 'attack')
                if choice == 'attack':
                    _, _, attack_summary, was_effective = apply_attack(
                        player, card, opponent, double=(double and not apply_shield_bonus))
                    card_summary.extend(attack_summary)
                else:
                    # Shield play
                    card_summary, was_effective = apply_shield(player, card)
                    was_shield = True
                    if apply_shield_bonus:
                        card_summary, was_effective = _apply_rank_match_shield_bonus(
                            player, opponent, card, rank_match_shield_bonus, card_summary)
        else:
            if card.suit == "Denari":
                card_summary, was_effective = apply_shield(player, card)
                was_shield = True
                if apply_shield_bonus:
                    card_summary, was_effective = _apply_rank_match_shield_bonus(
                        player, opponent, card, rank_match_shield_bonus, card_summary)
            elif card.suit == "Coppe":
                _, heal_summary, was_effective = apply_heal(player, card, opponent, double=double)
                card_summary.extend(heal_summary)
            else:
                _, _, attack_summary, was_effective = apply_attack(
                    player, card, opponent, double=double)
                card_summary.extend(attack_summary)

        turn_summary.extend(card_summary)

        # Fate: Poison Cup always discarded (done above); shields stay on table;
        # others cycle if effective, destroyed if not.
        if special and card.suit == "Coppe" and player.character.suit in ["Spade", "Coppe"]:
            continue  # already discarded
        if was_shield:
            pass  # lives on player.shields until hit
        elif was_effective:
            move_card_to_bottom(player, card)
        else:
            discard_card(player, card)
            turn_summary.append(f"{card} was ineffective — permanently removed from game")

    player.turns_played += 1
    return turn_summary, True


def _apply_rank_match_shield_bonus(player, opponent, card, bonus_type, existing_summary):
    """Apply the redirected rank-match bonus for a shield card.
    Instead of doubled defense, player takes the bonus as health or direct attack.
    Returns (updated_summary, was_effective=True).
    """
    bonus_value = card.value  # card's raw value (not defense bonus, which is shield-specific)
    if bonus_type == 'health':
        old_hp = player.health
        player.health = min(40, player.health + bonus_value)
        gained = player.health - old_hp
        existing_summary.append(f"  Rank match shield bonus → +{gained} HP")
    else:  # 'attack'
        opponent.health -= bonus_value
        existing_summary.append(f"  Rank match shield bonus → {bonus_value} direct damage")
    return existing_summary, True

def player_pre_shield(player, opponent, inp):
    """Returns (summary, success). success=False means invalid play; caller should not advance phase."""
    turn_summary = []
    if inp == "0":
        turn_summary.append(f"{player.name} skips pre-shield")
        needed = player.character.hand_size - len(player.hand)
        if needed > 0:
            drawn, _ = draw_cards(player, needed)
            turn_summary.append(f"{player.name} draws {drawn} card(s) to hand")
        return turn_summary, True
    actions = parse_input(inp, player)
    if actions is None or len(actions) != 1:
        turn_summary.append("Invalid: must be exactly ONE card (e.g., '1' or '3s')")
        return turn_summary, False
    idx, special = actions[0]
    card = player.hand[idx]
    del player.hand[idx]
    if card.suit == "Denari":
        summary, _ = apply_shield(player, card)
        turn_summary.extend(summary)
        turn_summary.append(f"{player.name} plays starting shield: {card}")
    elif special and player.character.suit == "Bastoni" and card.suit == "Bastoni":
        summary, _ = apply_shield(player, card)
        turn_summary.extend(summary)
        turn_summary.append(f"{player.name} plays starting shield {card} (Club special)")
    else:
        turn_summary.append(f"Invalid: {card} cannot be played as a shield here")
        player.hand.insert(idx, card)
        return turn_summary, False
    needed = player.character.hand_size - len(player.hand)
    if needed > 0:
        drawn, _ = draw_cards(player, needed)
        turn_summary.append(f"{player.name} draws {drawn} card(s) to reach full hand size")
    return turn_summary, True

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
        summary.append(f"🏆 PLAYER 2 WINS BY SURVIVAL! ({p2.health} > {p1.health} HP)")
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
