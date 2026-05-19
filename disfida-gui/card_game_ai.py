# card_game_ai.py
"""
Computer opponent for Disfida.

Key design invariants
─────────────────────
• Every strategy is suit-agnostic: cards are categorised by ROLE (attack /
  heal / shield) not by hardcoded suit name.  A Cavallo of Bastoni should be
  just as aggressive as a Cavallo of Spade.

• Every combo candidate is validated against the allied-suit rule (at most 1
  wildcard) before being returned.  _can_append_to_combo() is the single gate
  for this check.

• The AI never skips during the main game.  Every strategy branch terminates
  with _best_single_fallback(), which always returns a card.

• Rank-match bonus: only the LAST card doubles, and Aces never qualify.
  last_two_rank_match() already encodes both constraints.
"""

import itertools
from card_game_logic import ALLIED_SUITS, last_two_rank_match

HEAL_THRESHOLD    = {"Re": 15, "Cavallo": 10, "Fante": 22}
SHIELD_FLOOR      = {"Re": 2,  "Cavallo": 0,  "Fante": 1}
POISON_CUP_TRIGGER = {"Re": 8,  "Cavallo": 6,  "Fante": 6}


class DisfidaAI:

    def __init__(self, difficulty="normal"):
        self.difficulty = difficulty

    # ── Public API ────────────────────────────────────────────────────────────

    def choose_pre_shield(self, player, opponent):
        """Return inp string for pre-shield. '0' only if genuinely no options."""
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

    def choose_action(self, player, opponent):
        """Returns (inp_str, rank_match, rank_match_shield_bonus)."""
        if not player.hand:
            return "0", False, None
        if self.difficulty == "easy":
            return self._random_action(player, opponent)
        return self._smart_action(player, opponent)

    # ── Easy mode ─────────────────────────────────────────────────────────────

    def _random_action(self, player, opponent):
        import random
        card = random.choice(player.hand)
        idx  = player.hand.index(card)
        if player.character.suit == "Bastoni" and card.suit == "Bastoni":
            card._temp_bastoni_choice = random.choice(["attack", "shield"])
            return f"{idx + 1}s", False, None
        return f"{idx + 1}", False, None

    # ── Smart mode ────────────────────────────────────────────────────────────

    def _smart_action(self, player, opponent):
        char = player.character
        opp_eff_shields = sum(
            s.value + opponent.character.defense_bonus for s in opponent.shields)
        need_heal   = player.health <= HEAL_THRESHOLD[char.face]
        need_shield = len(player.shields) < SHIELD_FLOOR[char.face]

        kill = self._try_kill(player, opponent)
        if kill:
            return kill
        if need_heal:
            act = self._heal_action(player, opponent)
            if act:
                return act
        if char.face == "Re":
            return self._strategy_re(player, opponent, need_shield, opp_eff_shields)
        elif char.face == "Cavallo":
            return self._strategy_cavallo(player, opponent, opp_eff_shields)
        else:
            return self._strategy_fante(player, opponent, need_heal, opp_eff_shields)

    # ── Kill-shot search ──────────────────────────────────────────────────────

    def _try_kill(self, player, opponent):
        best_dmg, best_play = 0, None
        for indices in self._valid_combos(player):
            cards = [player.hand[i] for i in indices]
            ba    = self._bastoni_attack_map(player, indices)
            pc    = self._pc_set(player, indices)
            rm    = last_two_rank_match(cards)
            dmg   = self._sim_damage(player, opponent, indices, ba, pc, rm)
            if dmg >= opponent.health and dmg > best_dmg:
                best_dmg, best_play = dmg, (indices, ba, pc, rm)
        if best_play:
            indices, ba, pc, rm = best_play
            return self._build(player, indices, ba, pc, rm, "attack")
        return None

    # ── Re strategy ───────────────────────────────────────────────────────────

    def _strategy_re(self, player, opponent, need_shield, opp_eff_shields):
        hand               = player.hand
        attacks            = self._build_attack_indices(player)
        shields, flex_shld = self._shield_cards(player)
        all_shields        = shields + flex_shld
        heals              = [c for c in hand if c.suit == "Coppe"]
        opp_is_pc          = opponent.character.suit in ("Spade", "Coppe")

        # Rebuild shields first (unless opponent bypasses them with PC)
        if need_shield and all_shields and not opp_is_pc:
            best = max(all_shields, key=lambda c: c.value)
            idx  = hand.index(best)
            if best.suit == "Bastoni":
                best._temp_bastoni_choice = "shield"
                return f"{idx + 1}s", False, None
            return f"{idx + 1}", False, None

        # Combo: best attack + best Denari shield
        if attacks and shields:
            atk  = hand[max(attacks, key=lambda i: hand[i].value)]
            shld = max(shields, key=lambda c: c.value)
            ai, si = hand.index(atk), hand.index(shld)
            # Try both orderings; prefer whichever gives rank match
            for order in ([ai, si], [si, ai]):
                if last_two_rank_match([hand[i] for i in order]):
                    rm  = True
                    rsb = "health" if player.health < 25 else "attack"
                    ba  = self._bastoni_attack_map(player, [ai])
                    return self._build(player, order, ba, set(), rm, rsb)
            # No rank match — default: attack first, shield last
            indices = [ai, si]
            ba = self._bastoni_attack_map(player, [ai])
            return self._build(player, indices, ba, set(), False, None)

        # Attack chain only
        if attacks:
            indices = list(attacks)  # already respects allied-suit constraint
            # Append a heal for rank match if possible
            indices = self._try_rank_match_append(player, indices,
                                                   sorted(heals, key=lambda c: -c.value))
            cards = [hand[i] for i in indices]
            rm    = last_two_rank_match(cards)
            ba    = self._bastoni_attack_map(player, attacks)
            return self._build(player, indices, ba, set(), rm, "attack")

        # Shields only
        if all_shields:
            best = max(all_shields, key=lambda c: c.value)
            idx  = hand.index(best)
            if best.suit == "Bastoni":
                best._temp_bastoni_choice = "shield"
                return f"{idx + 1}s", False, None
            return f"{idx + 1}", False, None

        return self._best_single_fallback(player, opponent)

    # ── Cavallo strategy ──────────────────────────────────────────────────────

    def _strategy_cavallo(self, player, opponent, opp_eff_shields):
        hand  = player.hand
        atk_i = self._build_attack_indices(player)
        heals = sorted([c for c in hand if c.suit == "Coppe"], key=lambda c: -c.value)

        if atk_i:
            indices = list(atk_i)
            indices = self._try_rank_match_append(player, indices, heals)
            cards   = [hand[i] for i in indices]
            rm      = last_two_rank_match(cards)
            ba      = self._bastoni_attack_map(player, atk_i)
            return self._build(player, indices, ba, set(), rm, "attack")

        if heals:
            return self._heal_action(player, opponent) or self._best_single_fallback(player, opponent)

        return self._best_single_fallback(player, opponent)

    # ── Fante strategy ────────────────────────────────────────────────────────

    def _strategy_fante(self, player, opponent, need_heal, opp_eff_shields):
        hand  = player.hand
        char  = player.character
        atk_i = self._build_attack_indices(player)
        heals = sorted([c for c in hand if c.suit == "Coppe"], key=lambda c: -c.value)

        # Poison Cup when opponent heavily shielded (only for Spade/Coppe chars)
        can_pc = char.suit in ("Spade", "Coppe")
        if can_pc and heals and opp_eff_shields >= POISON_CUP_TRIGGER[char.face]:
            cup      = heals[0]
            ci       = hand.index(cup)
            self_dmg = max(0, cup.value // 2 - char.heal_bonus)
            if player.health - self_dmg > 8:
                # Pair with same-rank attack (it goes first; PC doubles last)
                atk_cards = [hand[i] for i in atk_i]
                match_atk = next((c for c in atk_cards if c.rank == cup.rank), None)
                if match_atk:
                    si      = hand.index(match_atk)
                    indices = [si, ci]
                    rm      = last_two_rank_match([hand[i] for i in indices])
                    return self._build(player, indices, {}, {ci}, rm, "attack")
                return f"{ci + 1}s", False, None

        if need_heal and heals:
            act = self._heal_action(player, opponent)
            if act:
                return act

        if atk_i:
            indices = list(atk_i)
            indices = self._try_rank_match_append(player, indices, heals)
            cards   = [hand[i] for i in indices]
            rm      = last_two_rank_match(cards)
            ba      = self._bastoni_attack_map(player, atk_i)
            return self._build(player, indices, ba, set(), rm, "attack")

        if heals:
            return self._heal_action(player, opponent) or self._best_single_fallback(player, opponent)

        return self._best_single_fallback(player, opponent)

    # ── Combo building helpers ────────────────────────────────────────────────

    def _can_append_to_combo(self, player, current_indices, new_idx):
        """Would appending new_idx still satisfy the allied-suit constraint?"""
        allied = ALLIED_SUITS[player.character.suit]
        all_i  = current_indices + [new_idx]
        cards  = [player.hand[i] for i in all_i]
        non_al = [c for c in cards if c.suit not in allied]
        return len(non_al) <= 1 and (len(cards) - len(non_al)) >= 1

    def _build_attack_indices(self, player):
        """Valid attack-card indices respecting allied-suit rules.

        Primary attack cards (in allied suits) are all included.
        At most ONE non-allied attack card is appended as a wildcard.
        """
        hand   = player.hand
        allied = ALLIED_SUITS[player.character.suit]

        primary = sorted(
            [c for c in hand if c.suit in ("Spade", "Bastoni") and c.suit in allied],
            key=lambda c: -c.value)
        wildcards = [c for c in hand
                     if c.suit in ("Spade", "Bastoni") and c.suit not in allied]

        if not primary and not wildcards:
            return []

        indices = [hand.index(c) for c in primary]

        if not indices:
            # Nothing allied to attack with — use the best wildcard alone
            best_wc = max(wildcards, key=lambda c: c.value)
            return [hand.index(best_wc)]

        # Optionally add one wildcard attack
        if wildcards:
            best_wc = max(wildcards, key=lambda c: c.value)
            wi      = hand.index(best_wc)
            if self._can_append_to_combo(player, indices, wi):
                indices.append(wi)

        return indices

    def _try_rank_match_append(self, player, indices, candidates):
        """Append the first candidate that creates a rank match and stays valid."""
        hand = player.hand
        for card in candidates:
            ci    = hand.index(card)
            if ci in indices:
                continue
            trial = indices + [ci]
            if (self._can_append_to_combo(player, indices, ci) and
                    last_two_rank_match([hand[i] for i in trial])):
                return trial
        return indices

    # ── Role-based card categorisation ────────────────────────────────────────

    def _shield_cards(self, player):
        """(denari_list, flex_bastoni_list).  Flex only for Bastoni characters."""
        hand   = player.hand
        denari = [c for c in hand if c.suit == "Denari"]
        flex   = ([c for c in hand if c.suit == "Bastoni"]
                  if player.character.suit == "Bastoni" else [])
        return denari, flex

    def _bastoni_attack_map(self, player, indices):
        """{idx: 'attack'} for Bastoni cards when character is Bastoni."""
        if player.character.suit != "Bastoni":
            return {}
        hand = player.hand
        return {i: "attack" for i in indices if hand[i].suit == "Bastoni"}

    def _pc_set(self, player, indices):
        """Indices to use as Poison Cup (Coppe cards, Spade/Coppe characters only)."""
        if player.character.suit not in ("Spade", "Coppe"):
            return set()
        hand = player.hand
        return {i for i in indices if hand[i].suit == "Coppe"}

    # ── Never-skip fallback ───────────────────────────────────────────────────

    def _best_single_fallback(self, player, opponent):
        """Always play something.  Priority: attack > heal > shield > anything."""
        hand    = player.hand
        if not hand:
            return "0", False, None
        char    = player.character
        attacks = [c for c in hand if c.suit in ("Spade", "Bastoni")]
        heals   = [c for c in hand if c.suit == "Coppe"]
        shields = [c for c in hand if c.suit == "Denari"]

        best = (max(attacks, key=lambda c: c.value) if attacks else
                max(heals,   key=lambda c: c.value) if heals   else
                max(shields, key=lambda c: c.value) if shields  else
                max(hand,    key=lambda c: c.value))

        idx = hand.index(best)
        if char.suit == "Bastoni" and best.suit == "Bastoni":
            best._temp_bastoni_choice = "attack"
            return f"{idx + 1}s", False, None
        return f"{idx + 1}", False, None

    # ── Simulation ────────────────────────────────────────────────────────────

    def _sim_damage(self, player, opponent, indices, bastoni_as, poison_cups, rm):
        """Simulate sequential HP damage from a combo.  Only last card doubles."""
        hand        = player.hand
        cards       = [hand[i] for i in indices]
        n           = len(cards)
        sim_shields = sorted(opponent.shields, key=lambda c: c.value)
        def_bonus   = opponent.character.defense_bonus
        total_dmg   = 0

        for j, (idx, card) in enumerate(zip(indices, cards)):
            double = rm and j == n - 1
            mult   = 2 if double else 1

            if idx in poison_cups and card.suit == "Coppe":
                total_dmg += (card.value + player.character.attack_bonus) * mult
                continue

            # Bastoni attacks: always attack for non-Bastoni chars;
            # for Bastoni chars check the bastoni_as dict
            is_attack = (card.suit == "Spade" or
                         (card.suit == "Bastoni" and
                          (player.character.suit != "Bastoni" or
                           bastoni_as.get(idx) == "attack")))
            if not is_attack:
                continue

            atk       = (card.value + player.character.attack_bonus) * mult
            remaining = atk
            surviving = []
            for shield in sim_shields:
                eff = shield.value + def_bonus
                remaining -= eff
                if remaining <= 0:
                    surviving.append(shield)
                    break
            sim_shields = surviving
            total_dmg  += max(0, remaining)

        return total_dmg

    def _heal_action(self, player, opponent):
        heals = [c for c in player.hand if c.suit == "Coppe"]
        if not heals:
            return None
        best = max(heals, key=lambda c: c.value + player.character.heal_bonus)
        return f"{player.hand.index(best) + 1}", False, None

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
