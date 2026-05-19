# card_game_ai.py
"""
Computer opponent for Disfida — three difficulty levels.

Architecture
────────────
All three difficulties share a single scoring engine (_score_combo).
The differences are controlled by two flags:

  penalize_destruction  (Normal + Hard)
    Strong cards (value ≥ STRONG_THRESHOLD, including Ace=11) that would be
    destroyed by a play incur a heavy score penalty.  This prevents moves like
    attacking with A♣ into a shield wall that will fully block it.

  use_lookahead  (Hard only)
    After scoring the immediate turn, _lookahead_value reads the top few cards
    of both decks and adjusts the score:
      • Upcoming draws that will deal damage or heal effectively → bonus
      • Opponent about to draw a strong shield or attack → penalty/bonus

Difficulty summary
──────────────────
  easy   – Greedy: picks the combo with the highest immediate effect.
           Will waste strong cards if they happen to be the strongest play.

  normal – Same evaluation plus destruction penalties.  Prefers a weaker combo
           that preserves strong cards over a stronger one that destroys them.
           Also tries all special-card interpretations (Bastoni attack vs shield,
           Coppe as Poison Cup vs heal) and picks the highest-scoring option.

  hard   – Normal + 1-turn deck lookahead.  Knows the top few cards coming from
           each player's deck and uses that to refine timing decisions.
"""

import itertools
from card_game_logic import ALLIED_SUITS, last_two_rank_match

STRONG_THRESHOLD = 5    # value ≥ this (incl. Ace=11) counts as a "strong" card

# Per-character personality weights — keep identical structure for both dimensions
HEAL_WEIGHT   = {"Re": 1.0, "Cavallo": 0.6, "Fante": 1.4}
SHIELD_WEIGHT = {"Re": 2.0, "Cavallo": 0.4, "Fante": 1.0}


class DisfidaAI:

    def __init__(self, difficulty="normal"):
        self.difficulty = difficulty.lower()

    # ── Pre-shield ────────────────────────────────────────────────────────────

    def choose_pre_shield(self, player, opponent):
        """Return inp string for pre-shield phase.  '0' only if no options."""
        shields, flex = self._shield_cards(player)
        candidates    = shields + flex
        if not candidates:
            return "0"
        min_val = {"Re": 2, "Fante": 4, "Cavallo": 6}.get(player.character.face, 4)
        good    = [c for c in candidates if c.value >= min_val]
        if not good:
            return "0"
        best = max(good, key=lambda c: c.value)
        idx  = player.hand.index(best)
        if best.suit == "Bastoni":
            best._temp_bastoni_choice = "shield"
            return f"{idx + 1}s"
        return f"{idx + 1}"

    # ── Main entry point ──────────────────────────────────────────────────────

    def choose_action(self, player, opponent):
        """Returns (inp_str, rank_match, rank_match_shield_bonus)."""
        if not player.hand:
            return "0", False, None
        penalize  = self.difficulty in ("normal", "hard")
        lookahead = self.difficulty == "hard"
        return self._find_best_action(player, opponent, penalize, lookahead)

    # ── Scoring loop ──────────────────────────────────────────────────────────

    def _find_best_action(self, player, opponent, penalize, lookahead):
        """Score every valid combo (and each of its special interpretations).
        Return the highest-scoring (inp_str, rm, rsb) triple."""
        best_score = -float("inf")
        best_play  = None

        for indices in self._valid_combos(player):
            cards = [player.hand[i] for i in indices]
            rm    = last_two_rank_match(cards)

            for ba, pc in self._special_options(player, indices):
                score = self._score_combo(
                    player, opponent, indices, ba, pc, rm,
                    penalize, lookahead)
                if score > best_score:
                    best_score = score
                    best_play  = (indices, ba, pc, rm)

        if best_play is None:
            return self._best_single_fallback(player, opponent)

        indices, ba, pc, rm = best_play
        rsb = "attack" if player.health >= 25 else "health"
        return self._build(player, indices, ba, pc, rm, rsb)

    # ── Combo scorer ──────────────────────────────────────────────────────────

    def _score_combo(self, player, opponent, indices, ba, pc, rm,
                     penalize, lookahead):
        """
        Score a single combo interpretation.

        Component weights (approximate priority order):
          damage to opponent   ×10   — top priority
          self heal (actual)   ×8    — × heal_weight[face]
          shield added         ×4    — × shield_weight[face]
          self-damage (PC)     −5
          destruction penalty  −50 (strong) / −8 (weak)   [if penalize=True]
          lookahead value      variable                     [if lookahead=True]
        """
        hand   = player.hand
        cards  = [hand[i] for i in indices]
        n      = len(cards)
        char   = player.character

        sim_shields = sorted(opponent.shields, key=lambda c: c.value)
        def_bonus   = opponent.character.defense_bonus
        sim_hp      = player.health

        score     = 0
        hw = HEAL_WEIGHT.get(char.face, 1.0)
        sw = SHIELD_WEIGHT.get(char.face, 1.0)

        for j, (idx, card) in enumerate(zip(indices, cards)):
            double    = rm and j == n - 1
            mult      = 2 if double else 1
            is_strong = card.value >= STRONG_THRESHOLD

            # ── Poison Cup ──────────────────────────────────────────────────
            if idx in pc and card.suit == "Coppe":
                atk      = (card.value + char.attack_bonus) * mult
                self_dmg = max(0, card.value // 2 - char.heal_bonus)
                score   += min(atk, opponent.health) * 10
                score   -= self_dmg * 5
                # PC cards are always destroyed by design — no extra penalty
                continue

            # ── Attack ──────────────────────────────────────────────────────
            is_attack = (
                card.suit == "Spade" or
                (card.suit == "Bastoni" and (
                    char.suit != "Bastoni" or ba.get(idx) == "attack")))

            if is_attack:
                atk       = (card.value + char.attack_bonus) * mult
                remaining = atk
                surviving = []
                for shield in sim_shields:
                    eff = shield.value + def_bonus
                    remaining -= eff
                    if remaining <= 0:
                        surviving.append(shield)
                        break
                sim_shields = surviving
                dmg = max(0, remaining)
                score += min(dmg, opponent.health) * 10

                if penalize and dmg == 0:
                    # Attack fully blocked → card destroyed
                    score -= 50 if is_strong else 8
                continue

            # ── Heal ────────────────────────────────────────────────────────
            if card.suit == "Coppe":
                heal   = (card.value + char.heal_bonus) * mult
                room   = 40 - sim_hp
                actual = min(heal, room)
                score += actual * 8 * hw
                sim_hp = min(40, sim_hp + heal)

                if penalize and actual < heal and is_strong:
                    # Heal capped → strong card destroyed
                    score -= 35
                elif penalize and actual < heal:
                    score -= 5
                continue

            # ── Shield (Denari, or Bastoni played as shield) ─────────────────
            if card.suit == "Denari" or (
                    card.suit == "Bastoni" and ba.get(idx) == "shield"):
                eff_def = card.value + char.defense_bonus
                score  += eff_def * 4 * sw

        # ── Lookahead (Hard only) ────────────────────────────────────────────
        if lookahead:
            score += self._lookahead_value(player, opponent, indices, sim_shields)

        return score

    # ── Deck lookahead ────────────────────────────────────────────────────────

    def _lookahead_value(self, player, opponent, indices_played, sim_shields_after):
        """
        Estimate the value of the position after this combo, using knowledge
        of the top cards in both decks.

        Positive adjustments:
          • Upcoming attacks that will deal net damage (after current shields)
          • Upcoming heals while player HP is low

        Negative adjustments:
          • Opponent drawing a strong shield before we can attack next
          • Opponent drawing a strong attack and we have no shields
        """
        bonus = 0
        char  = player.character
        depth = min(3, len(player.stack))

        for card in player.stack[:depth]:
            if card.suit in ("Spade", "Bastoni"):
                atk     = card.value + char.attack_bonus
                opp_def = sum(s.value + opponent.character.defense_bonus
                              for s in sim_shields_after)
                if atk > opp_def:
                    bonus += (atk - opp_def) * 1.5   # will deal damage next turn
            elif card.suit == "Coppe":
                room  = 40 - player.health
                heal  = card.value + char.heal_bonus
                bonus += min(heal, room) * 1.2

        if opponent.stack:
            opp_next = opponent.stack[0]
            if opp_next.suit == "Denari" and opp_next.value >= STRONG_THRESHOLD:
                # Opponent gets a strong shield — attack now while unshielded
                dmg_now = sum(
                    min(max(0, (hand_card.value + char.attack_bonus)
                            - sum(s.value + opponent.character.defense_bonus
                                  for s in sim_shields_after)),
                        opponent.health)
                    for hand_card in player.hand
                    if hand_card.suit in ("Spade", "Bastoni")
                )
                if dmg_now > 0:
                    bonus += 6   # reward attacking before shield arrives

            elif opp_next.suit in ("Spade", "Bastoni") and opp_next.value >= STRONG_THRESHOLD:
                # Opponent drawing a strong attack — value having shields up
                if not player.shields:
                    bonus -= 8   # we have no shields; incoming attack is scary

        return bonus

    # ── Special interpretation generator ─────────────────────────────────────

    def _special_options(self, player, indices):
        """
        Yield (bastoni_as, poison_cups) pairs to try for this combo.

        Bastoni characters: try all-attack and all-shield interpretations.
        Spade/Coppe characters: try no-PC and all-Coppe-as-PC.
        """
        hand    = player.hand
        char    = player.character
        is_bast = char.suit == "Bastoni"
        can_pc  = char.suit in ("Spade", "Coppe")

        bast_i  = [i for i in indices if hand[i].suit == "Bastoni" and is_bast]
        coppe_i = [i for i in indices if hand[i].suit == "Coppe"   and can_pc]

        ba_atk  = {i: "attack" for i in bast_i}
        ba_shld = {i: "shield" for i in bast_i}

        yield ba_atk, set()                           # base: attack, no PC
        if coppe_i:
            yield ba_atk, set(coppe_i)               # attack + PC
        if bast_i:
            yield ba_shld, set()                     # shield, no PC
        if bast_i and coppe_i:
            yield ba_shld, set(coppe_i)              # shield + PC

    # ── Helpers ───────────────────────────────────────────────────────────────

    def _shield_cards(self, player):
        hand   = player.hand
        denari = [c for c in hand if c.suit == "Denari"]
        flex   = ([c for c in hand if c.suit == "Bastoni"]
                  if player.character.suit == "Bastoni" else [])
        return denari, flex

    def _best_single_fallback(self, player, opponent):
        """Always play something.  Priority: attack > heal > shield."""
        hand    = player.hand
        if not hand:
            return "0", False, None
        char    = player.character
        attacks = [c for c in hand if c.suit in ("Spade", "Bastoni")]
        heals   = [c for c in hand if c.suit == "Coppe"]
        shields = [c for c in hand if c.suit == "Denari"]
        best    = (max(attacks, key=lambda c: c.value) if attacks else
                   max(heals,   key=lambda c: c.value) if heals   else
                   max(shields, key=lambda c: c.value) if shields  else
                   max(hand,    key=lambda c: c.value))
        idx = hand.index(best)
        if char.suit == "Bastoni" and best.suit == "Bastoni":
            best._temp_bastoni_choice = "attack"
            return f"{idx + 1}s", False, None
        return f"{idx + 1}", False, None

    def _valid_combos(self, player):
        hand   = player.hand
        allied = ALLIED_SUITS[player.character.suit]
        result = []
        for size in range(1, min(len(hand) + 1, 6)):
            for indices in itertools.combinations(range(len(hand)), size):
                indices = list(indices)
                cards   = [hand[i] for i in indices]
                non_al  = [c for c in cards if c.suit not in allied]
                if len(non_al) <= 1 and (len(cards) - len(non_al)) >= 1:
                    result.append(indices)
        return result

    def _build(self, player, indices, bastoni_as, poison_cups, rm, rsb):
        hand  = player.hand
        parts = []
        for idx in indices:
            card    = hand[idx]
            special = False
            if idx in poison_cups and card.suit == "Coppe":
                special = True
            elif card.suit == "Bastoni" and player.character.suit == "Bastoni":
                card._temp_bastoni_choice = bastoni_as.get(idx, "attack")
                special = True
            parts.append(f"{idx + 1}{'s' if special else ''}")
        return ",".join(parts), rm, rsb
