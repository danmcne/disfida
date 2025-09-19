import random
import math

# -----------------------------
# Data structures
# -----------------------------
class Card:
    def __init__(self, suit, rank):
        self.suit = suit
        self.rank = rank
        if rank == "A":
            self.value = 11
        elif rank in ["Fante", "Cavallo", "Re"]:
            self.value = 10  # Face cards have value 10
        else:
            self.value = int(rank)
    
    def __str__(self):
        return f"{self.rank} of {self.suit}"

class Character:
    def __init__(self, face, suit):
        self.face = face
        self.suit = suit
        # Set bonuses
        self.attack_bonus = 1 if face == "Cavallo" else 0
        self.defense_bonus = 2 if face == "Re" else 0
        self.heal_bonus = 2 if face == "Fante" else 0
        # Coin character gets extra cards
        self.stack_size = 13 if suit == "Denari" else 12
        self.hand_size = 5 if suit == "Denari" else 4

class Player:
    def __init__(self, name, character, stack):
        self.name = name
        self.character = character
        self.stack = stack
        self.hand = []
        self.shields = []  # List of active Card objects
        self.health = 40

# -----------------------------
# Helper functions
# -----------------------------
def build_numeric_deck():
    """Build the 32 numeric cards (A-7 for each suit)"""
    suits = ["Denari", "Coppe", "Spade", "Bastoni"]
    ranks = ["A", "2", "3", "4", "5", "6", "7"]
    deck = [Card(s, r) for s in suits for r in ranks]
    return deck

def create_face_cards():
    """Create the 8 face cards (Fante, Cavallo, Re for each suit)"""
    suits = ["Denari", "Coppe", "Spade", "Bastoni"]
    faces = ["Fante", "Cavallo", "Re"]
    return [Card(s, f) for s in suits for f in faces]

def print_rules_summary():
    """Print concise rules at game start"""
    print("=" * 50)
    print("ITALIAN CARD COMBAT - RULES SUMMARY")
    print("=" * 50)
    print("OBJECTIVE: Reduce opponent's HP to 0 or less")
    print("DECK: 40-card Italian deck (A=11, 2-7, Fante/Cavallo/Re=10)")
    print("START: 40 HP each, 4-card hand (5 for Coins char)")
    print("\nCHARACTERS & BONUSES:")
    print("• Re (King): +2 defense per shield")
    print("• Cavallo (Knight): +1 attack per attack card")
    print("• Fante (Page): +2 healing per healing card")
    print("\nSUIT SPECIALS:")
    print("• Coins: Wealth of Choice - +1 card in stack/hand (passive)")
    print("• Swords: Blood Price - Use Cups as attacks (ignore shields, self-damage)")
    print("• Cups: Charity's Burden - Use Swords as healing (opponent gains half)")
    print("• Clubs: Iron Versatility - Clubs can be attack OR shield")
    print("\nCOMBOS: Sequence of character-suit cards + optional 1 non-suit card")
    print("TURNS: Skip, play 1 card, or play combo. Draw to hand size at turn end")
    print("SHIELDS: Visible on table, destroyed smallest→largest, cycle to deck bottom")
    print("WIN: Opponent HP ≤ 0 (ties possible)")
    print("=" * 50)
    input("\nPress Enter to continue...")

def draw_cards(player, n):
    """Draw n cards from stack to hand"""
    drawn = 0
    for _ in range(n):
        if player.stack:
            player.hand.append(player.stack.pop(0))
            drawn += 1
        else:
            # Empty stack - can't draw
            break
    return drawn

def print_game_state(p1, p2, active_player):
    """Display current game state - side by side layout"""
    # Clear screen (works on most terminals)
    print("\033[H\033[J", end="")
    
    print("="*80)
    print("ITALIAN CARD COMBAT" + " " * 28 + "TURN")
    print("="*80)
    
    # Player 0 info (left side)
    p1_info = f"{p1.name}: {p1.character.face} of {p1.character.suit} | HP: {p1.health}"
    print(f"{p1_info:<38}", end="")
    
    # Turn indicator (center)
    active_name = "Player 0" if active_player == p1 else "Player 1"
    turn_marker = f"ACTIVE: {active_name}" if active_player == p1 else f"ACTIVE: {active_name}"
    print(f"{turn_marker:>40}")
    
    # Player 0 bonuses and shields
    bonus_str = f"Bonuses: +{p1.character.attack_bonus} atk, +{p1.character.heal_bonus} heal, +{p1.character.defense_bonus} def/shield"
    print(f"{bonus_str:<38}", end="")
    print(" " * 40)
    
    if p1.shields:
        shields_str = ", ".join([str(c) for c in p1.shields])
        print(f"Shields: {shields_str:<30}", end="")
    else:
        print("Shields: None              ", end="")
    print(" " * 40)
    
    print("-" * 38 + " " * 40 + "-" * 40)
    
    # Player 1 info (right side)
    p2_info = f"{p2.name}: {p2.character.face} of {p2.character.suit} | HP: {p2.health}"
    print(" " * 38, end="")
    print(f"{p2_info:>40}")
    
    # Player 1 bonuses and shields
    bonus_str = f"Bonuses: +{p2.character.attack_bonus} atk, +{p2.character.heal_bonus} heal, +{p2.character.defense_bonus} def/shield"
    print(" " * 38, end="")
    print(f"{bonus_str:>40}")
    
    if p2.shields:
        shields_str = ", ".join([str(c) for c in p2.shields])
        print(" " * 38, end="")
        print(f"Shields: {shields_str:>40}")
    else:
        print(" " * 38, end="")
        print("Shields: None              ", end="")
    print()
    
    print("-" * 80)
    
    # Active player's hand (bottom)
    hand_size = active_player.character.hand_size
    print(f"\n{active_player.name}'s Hand ({len(active_player.hand)}/{hand_size}):")
    print("-" * 80)
    for idx, card in enumerate(active_player.hand):
        print(f"  {idx+1:2d}: {card}")
    
    # Inactive player's hand (if not active player)
    if active_player != p1:
        print(f"\n{p1.name}'s Hand ({len(p1.hand)}/{p1.character.hand_size}):")
        for idx, card in enumerate(p1.hand):
            print(f"  {idx+1:2d}: {card}")
    else:
        print(f"\n{p2.name}'s Hand ({len(p2.hand)}/{p2.character.hand_size}):")
        for idx, card in enumerate(p2.hand):
            print(f"  {idx+1:2d}: {card}")
    
    print("="*80)
    print("Commands: '1' (single card), '1,2,3' (combo), '3s' (special), '0' (skip)")

def validate_combo(actions, player):
    """Validate combo rules: same-suit cards matching character suit + optional 1 non-suit"""
    if len(actions) == 0:
        return False
    
    cards = [player.hand[idx] for idx, _ in actions]
    
    # Check if single card (always valid)
    if len(cards) == 1:
        return True
    
    # For combos (2+ cards), first N-1 must match character suit
    character_suit = player.character.suit
    non_suit_count = 0
    
    for i, card in enumerate(cards):
        if i < len(cards) - 1:  # All but last card must match character suit
            if card.suit != character_suit:
                return False
        else:  # Last card can be any suit
            if card.suit != character_suit:
                non_suit_count += 1
    
    # At most 1 non-suit card allowed (the optional ending card)
    return non_suit_count <= 1

def move_card_to_bottom(player, card):
    """Move any played/removed card to bottom of stack"""
    player.stack.append(card)

def remove_shields_for_attack(opponent, attack_value):
    """Remove shields smallest→largest until cumulative >= attack"""
    if not opponent.shields:
        return attack_value
    
    remaining = attack_value
    sorted_shields = sorted(opponent.shields, key=lambda c: c.value)
    removed_shields = []
    
    for shield in sorted_shields:
        # Calculate effective defense with character bonus
        effective_defense = shield.value + opponent.character.defense_bonus
        remaining -= effective_defense
        removed_shields.append(shield)
        
        if remaining <= 0:
            break
    
    # Remove shields from active shields and cycle to bottom
    for shield in removed_shields:
        opponent.shields.remove(shield)
        move_card_to_bottom(opponent, shield)
    
    # Log shield removal
    if removed_shields:
        shields_str = ", ".join([str(s) for s in removed_shields])
        print(f"  Shields {shields_str} absorbed attack, sent to bottom of deck")
    
    return max(0, remaining)

def apply_heal(player, card, opponent, turn_summary):
    """Apply healing with character bonus and suit specials"""
    heal_amount = card.value + player.character.heal_bonus
    old_health = player.health
    player.health = min(40, player.health + heal_amount)
    
    # Cups special: Charity's Burden - opponent gains floor(value/2)
    opponent_bonus = 0
    if player.character.suit == "Coppe" and card.suit == "Spade":
        opponent_bonus = card.value // 2
        old_opp_health = opponent.health
        opponent.health = min(40, opponent.health + opponent_bonus)
        turn_summary.append(f"Heal {card}: +{heal_amount} HP ({player.health-old_health}), +{opponent_bonus} to opponent ({opponent.health-old_opp_health})")
    else:
        turn_summary.append(f"Heal {card}: +{heal_amount} HP ({player.health-old_health})")
    
    print(f"  {player.name} heals {heal_amount}, health now {player.health}")
    if opponent_bonus > 0:
        print(f"  Charity's Burden: {opponent.name} gains {opponent_bonus} HP")
    
    return heal_amount, opponent_bonus

def apply_attack(player, card, opponent, ignore_shields=False, turn_summary=None):
    """Apply attack with character bonus and suit specials"""
    attack_value = card.value + player.character.attack_bonus
    
    if ignore_shields:
        # Blood Price - ignore shields
        old_health = opponent.health
        opponent.health -= attack_value
        if turn_summary:
            turn_summary.append(f"Blood Price attack {card}: {attack_value} damage (ignores shields)")
        print(f"  {player.name} attacks for {attack_value} (ignores shields)")
    else:
        # Normal attack vs shields
        remaining_damage = remove_shields_for_attack(opponent, attack_value)
        if remaining_damage > 0:
            old_health = opponent.health
            opponent.health -= remaining_damage
            if turn_summary:
                turn_summary.append(f"Attack {card}: {attack_value} total, {remaining_damage} damage after shields")
            print(f"  {player.name} attacks for {attack_value}, {remaining_damage} damage after shields")
        else:
            if turn_summary:
                turn_summary.append(f"Attack {card}: {attack_value} total, 0 damage (blocked by shields)")
            print(f"  {player.name} attacks for {attack_value}, all blocked by shields")
    
    # Swords special self-damage (Blood Price)
    self_damage = 0
    if player.character.suit == "Spade" and card.suit == "Coppe":
        self_damage = card.value // 2
        old_self_health = player.health
        player.health -= self_damage
        if turn_summary:
            turn_summary.append(f"Blood Price self-damage: -{self_damage} HP ({player.health-old_self_health})")
        print(f"  {player.name} suffers Blood Price self-damage {self_damage}, health now {player.health}")
    
    return attack_value, remaining_damage if not ignore_shields else attack_value, self_damage

def apply_shield(player, card, turn_summary):
    """Add shield to active shields"""
    effective_value = card.value + player.character.defense_bonus
    player.shields.append(card)
    if turn_summary:
        turn_summary.append(f"Shield {card}: +{effective_value} defense")
    print(f"  {player.name} plays shield {card} (effective: {effective_value})")

def parse_input(inp, player):
    """Parse input string into list of (index, special_flag) tuples"""
    if inp.strip() == "0":
        return []
    
    actions = []
    parts = inp.split(',')
    
    for part in parts:
        part = part.strip()
        if not part:
            continue
            
        special = False
        if part.endswith('s'):
            special = True
            part = part[:-1]
        
        try:
            idx = int(part) - 1
            if idx < 0 or idx >= len(player.hand):
                print(f"  Invalid card index {part}. Must be 1-{len(player.hand)}")
                return None
            actions.append((idx, special))
        except ValueError:
            print(f"  Invalid input: '{part}'")
            return None
    
    return actions

def can_use_special(player, card, special_flag):
    """Check if player can use special ability with this card"""
    if not special_flag:
        return False
    
    if player.character.suit == "Spade" and card.suit == "Coppe":
        return True  # Blood Price
    elif player.character.suit == "Coppe" and card.suit == "Spade":
        return True  # Charity's Burden
    elif player.character.suit == "Bastoni" and card.suit == "Bastoni":
        return True  # Iron Versatility
    return False

def print_turn_summary(player, turn_summary):
    """Print summary of turn effects"""
    if not turn_summary:
        return
    
    print(f"\n--- {player.name}'s Turn Summary ---")
    for effect in turn_summary:
        print(f"  {effect}")
    print("--------------------------------")

def resolve_turn(player, opponent):
    """Handle complete turn resolution"""
    print(f"\n{player.name}'s turn. Enter cards to play (e.g., '1' or '1,2,3' or '3s'). '0' to skip.")
    turn_summary = []
    
    while True:
        inp = input("> ").strip()
        actions = parse_input(inp, player)
        
        if actions is None:
            continue  # Invalid input, try again
        
        if not actions:
            # Skip turn
            print(f"{player.name} skips turn")
            print_turn_summary(player, turn_summary)
            return
        
        # Validate combo rules
        if not validate_combo(actions, player):
            print("  Invalid combo! Must be character-suit cards + optional 1 non-suit card.")
            continue
        
        # Check special plays validity
        special_error = False
        for idx, special in actions:
            card = player.hand[idx]
            if special and not can_use_special(player, card, special):
                print(f"  Error: {card} has no special play for {player.character.face} of {player.character.suit}")
                special_error = True
                break
        if special_error:
            continue
        
        # FIXED: Extract all cards FIRST, then remove from hand, then process
        print(f"{player.name} plays combo:")
        cards_to_play = []
        for idx, special in actions:
            card = player.hand[idx]
            cards_to_play.append((card, special))
        
        # Remove all cards from hand at once (in reverse order to preserve indices)
        for idx, _ in sorted(actions, key=lambda x: x[0], reverse=True):
            del player.hand[idx]
        
        # Now process all cards
        for card, special in cards_to_play:
            # Handle special plays first
            if special:
                if player.character.suit == "Bastoni" and card.suit == "Bastoni":
                    # Clubs special: choose attack or shield
                    choice = input(f"  Play {card} as attack (a) or shield (s)? ").strip().lower()
                    if choice == 'a':
                        apply_attack(player, card, opponent, turn_summary=turn_summary)
                    elif choice == 's':
                        apply_shield(player, card, turn_summary)
                    else:
                        print("  Invalid choice, treated as attack")
                        apply_attack(player, card, opponent, turn_summary=turn_summary)
                
                elif player.character.suit == "Spade" and card.suit == "Coppe":
                    # Swords special: Blood Price (Cups as attack)
                    apply_attack(player, card, opponent, ignore_shields=True, turn_summary=turn_summary)
                
                elif player.character.suit == "Coppe" and card.suit == "Spade":
                    # Cups special: Charity's Burden (Swords as heal)
                    apply_heal(player, card, opponent, turn_summary)
            
            else:
                # Default roles
                if card.suit == "Denari":
                    apply_shield(player, card, turn_summary)
                elif card.suit == "Coppe":
                    apply_heal(player, card, opponent, turn_summary)
                else:  # Spade or Bastoni
                    apply_attack(player, card, opponent, turn_summary=turn_summary)
        
        # Cycle only non-shield cards to bottom of deck
        # (Shields remain in shields list until destroyed by attacks)
        non_shield_cards = [card for card, special in cards_to_play if card.suit != "Denari"]
        for card in non_shield_cards:
            move_card_to_bottom(player, card)
        
        # Check for immediate victory
        if opponent.health <= 0:
            print(f"\n{player.name}'s combo defeats {opponent.name}!")
        
        # Print turn summary
        print_turn_summary(player, turn_summary)
        
        break  # Successfully resolved turn

def player_zero_pre_shield(player, opponent):
    """Player 0's special starting shield play - single card only, Clubs can use special"""
    print(f"\n{player.name} may play one shield before game begins.")
    print_game_state(player, opponent, player)
    
    while True:
        print("Enter ONE card number (1-5) for shield or '0' to skip:")
        inp = input("> ").strip()
        
        if inp == "0":
            print(f"{player.name} skips pre-shield")
            # Refill hand to proper size after skipping
            needed = player.character.hand_size - len(player.hand)
            if needed > 0:
                drawn = draw_cards(player, needed)
                if drawn > 0:
                    print(f"{player.name} draws {drawn} card(s) to hand")
            return
        
        actions = parse_input(inp, player)
        if actions is None or len(actions) != 1:
            print("  Invalid: must be exactly ONE card (e.g., '1' or '3s')")
            continue
        
        idx, special = actions[0]
        card = player.hand[idx]
        
        # Remove card from hand BEFORE adding to shields
        del player.hand[idx]
        
        # Check if this card can be played as a shield
        if card.suit == "Denari":
            # Coins can always be shields
            apply_shield(player, card, None)  # No turn summary for pre-shield
            print(f"{player.name} plays starting shield!")
            break
        elif special and player.character.suit == "Bastoni" and card.suit == "Bastoni":
            # Clubs special: allow Club as shield
            apply_shield(player, card, None)  # No turn summary for pre-shield
            print(f"{player.name} plays starting shield {card} (Club special)!")
            break
        else:
            print(f"  Invalid: {card} cannot be played as a shield")
            # Put card back in hand
            player.hand.insert(idx, card)
            if special and not can_use_special(player, card, special):
                print(f"  (Special play also invalid for {player.character.face} of {player.character.suit})")
            continue
    
    # After playing shield, refill hand to proper size
    needed = player.character.hand_size - len(player.hand)
    if needed > 0:
        drawn = draw_cards(player, needed)
        if drawn > 0:
            print(f"{player.name} draws {drawn} card(s) to reach full hand size")

def check_victory(p1, p2):
    """Check for victory conditions including ties"""
    if p1.health <= 0 and p2.health <= 0:
        print("\n*** DOUBLE KNOCKOUT - IT'S A TIE! ***")
        return True
    elif p1.health <= 0:
        print(f"\n*** {p2.name} WINS! ***")
        return True
    elif p2.health <= 0:
        print(f"\n*** {p1.name} WINS! ***")
        return True
    return False

def refill_hand(player):
    """Draw cards to refill hand to proper size"""
    needed = player.character.hand_size - len(player.hand)
    if needed > 0:
        drawn = draw_cards(player, needed)
        if drawn > 0:
            print(f"{player.name} draws {drawn} card(s) at end of turn")

def end_of_turn(player):
    """Handle end-of-turn drawing"""
    refill_hand(player)

# -----------------------------
# Game initialization
# -----------------------------
def init_game():
    """Initialize complete game state"""
    print_rules_summary()
    
    # Create face cards and assign characters
    face_cards = create_face_cards()
    numeric_deck = build_numeric_deck()
    random.shuffle(numeric_deck)
    
    # Randomly assign characters (or could be chosen)
    p1_char_card = random.choice(face_cards)
    remaining_faces = [c for c in face_cards if c != p1_char_card]
    p2_char_card = random.choice(remaining_faces)
    
    p1_character = Character(p1_char_card.rank, p1_char_card.suit)
    p2_character = Character(p2_char_card.rank, p2_char_card.suit)
    
    # Build player stacks - ensure no duplicate cards
    total_needed = p1_character.stack_size + p2_character.stack_size
    available_cards = numeric_deck[:total_needed]
    
    # If not enough cards, shuffle and take more
    if len(available_cards) < total_needed:
        extra_needed = total_needed - len(available_cards)
        extra_cards = random.sample(numeric_deck, min(extra_needed, len(numeric_deck)))
        available_cards.extend(extra_cards)
        random.shuffle(available_cards)
        available_cards = available_cards[:total_needed]
    
    p1_stack = available_cards[:p1_character.stack_size]
    p2_stack = available_cards[p1_character.stack_size:p1_character.stack_size + p2_character.stack_size]
    
    player0 = Player("Player 0", p1_character, p1_stack)
    player1 = Player("Player 1", p2_character, p2_stack)
    
    # Initial hands - Coins gets 5, others get 4
    initial_draw = p1_character.hand_size
    draw_cards(player0, initial_draw)
    print(f"{player0.name} draws {initial_draw} cards (Coins bonus)")
    
    draw_cards(player1, p2_character.hand_size)
    print(f"{player1.name} draws {p2_character.hand_size} cards")
    
    # Player 0 pre-shield (this is NOT a normal turn)
    player_zero_pre_shield(player0, player1)
    
    return player0, player1

def main():
    """Main game loop"""
    player0, player1 = init_game()
    turn = 0
    
    print(f"\nGame begins! Player 0: {player0.character.face} of {player0.character.suit}")
    print(f"Player 1: {player1.character.face} of {player1.character.suit}")
    print(f"\nPlayer 1 takes first turn after Player 0's pre-shield!")
    
    while True:
        # Player 1 goes first (turn 0), then Player 0 (turn 1), Player 1 (turn 2), etc.
        active = player1 if turn % 2 == 0 else player0
        opponent = player0 if turn % 2 == 0 else player1
        
        print_game_state(player0, player1, active)
        
        resolve_turn(active, opponent)
        end_of_turn(active)
        
        if check_victory(player0, player1):
            break
        
        turn += 1

if __name__ == "__main__":
    main()
