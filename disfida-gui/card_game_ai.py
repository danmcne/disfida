# card_game_ai.py
"""
Computer opponent for Disfida.

──────────────────────────────────────────────────────────────────────────────
DESIGN PRINCIPLE — suit-agnostic roles
  Characters (Re/Cavallo/Fante) can be assigned to any suit, so strategy
  must work from *roles*, not hardcoded suit names:

    Denari (♦/Coins)  → shield
    Coppe  (♥/Cups)   → heal  (or Poison Cup special)
    Spade  (♠/Swords) → attack
    Bastoni(♣/Clubs)  → attack OR shield (Iron Versatility, Bastoni char only)

  A Re of Spade has the same King bonus (+2 def/shield) and the same desire
  to maintain shields, but his allied pair is Spade+Coppe, not Bastoni+Denari.
  The strategy must find Denari for shields regardless of character suit.

──────────────────────────────────────────────────────────────────────────────
NO-SKIP GUARANTEE
  During the main game the AI *never* skips if it has cards.
  Every strategy branch ends either with a real play or with a call to
  `_best_single_fallback`, which always returns a card.
  The only legitimate skip is in choose_pre_shield when no shield card exists.
──────────────────────────────────────────────────────────────────────────────
RANK-MATCH NOTE
  `last_two_rank_match` already excludes Aces and only signals a match when
  the last two cards share the same non-Ace rank.  The AI looks for matching
  pairs when building combos so it can put the matched card last (the one
  that doubles).
──────────────────────────────────────────────────────────────────────────────
CHARACTER STRATEGIES

  Re (King) — +2 defence per shield
    Wants ≥2 shields on the table at all times.  Rebuilds shields first, then
    attacks.  Best combo: one attack card + one shield card; tries both orders
    to find a rank match (shield last if that's the match, otherwise attack last).
    Against Poison Cup threats (opponent is Spade/Coppe character): shields are
    bypassed, so switches to pure pressure instead of rebuilding.

  Cavallo (Knight) — +1 per attack
    Chains every attack card in hand each turn.  Appends a heal card at the end
    only when it creates a rank match (doubled heal is a bonus, not the goal).
    Heals only below HP threshold ≤10 — the Knight fights through pain.

  Fante (Page) — +2 per heal, reduced Poison Cup self-damage
    Fires Poison Cup (ignores shields) when opponent's effective shield total
    is worth dodging (≥6 by default, lower threshold than Cavallo).
    Pairs a same-rank attack before the PC when possible so the PC doubles.
    Heals aggressively (threshold 22) because the bonus makes it efficient.
──────────────────────────────────────────────────────────────────────────────
"""

import itertools
from card_game_logic import ALLIED_SUITS, last_two_rank_match

# HP at or below which healing is prioritised over attacking
HEAL_THRESHOLD = {"Re": 15, "Cavallo": 10, "Fante": 22}

# Minimum active shields to maintain
SHIELD_FLOOR = {"Re": 2, "Cavallo": 0, "Fante": 1}

# Effective opponent shield total that justifies using Poison Cup
POISON_CUP_TRIGGER = {"Re": 8, "Cavallo": 6, "Fante": 6}


class DisfidaAI:
    """Priority-based computer player.

    difficulty = "easy"   – random single card
    difficulty = "normal" – full character-aware strategy
    """

    def __init__(self, difficulty="normal"):
        self.difficulty = difficulty

    # ── Public API ────────────────────────────────────────────────────────────

    def choose_pre_shield(self, player, opponent):
        """Return inp string for pre-shield phase. '0' only if no shield exists."""
        shields, flex = self._shield_cards(player)
        candidates = shields + flex
        if not candidates:
            return "0"

        min_val = {"Re": 2, "Fante": 4, "Cavallo": 6}.get(player.character.face, 4)
        good = [c for c in candidates if c.value >= min_val]
        if not good:
            return "0"

        best = max(good, key=lambda c: c.value)
        idx  = player.hand.index(best)
        if best.suit == "Bastoni":
            best._temp_bastoni_choice = "shield"
            return f"{idx + 1}s"
        return f"{idx + 1}"

    def choose_action(self, player, opponent):
        """Main entry point.

        Returns (inp_str, rank_match: bool, rank_match_shield_bonus: str|None).
        Sets _temp_bastoni_choice on any Bastoni combo cards as a side-effect.
        """
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
            s.value + opponent.character.defense_bonus
            for s in opponent.shields)

        need_heal   = player.health <= HEAL_THRESHOLD[char.face]
        need_shield = len(player.shields) < SHIELD_FLOOR[char.face]

        # 1. Kill shot
        kill = self._try_kill(player, opponent)
        if kill:
            return kill

        # 2. Desperate heal
        if need_heal:
            act = self._heal_action(player, opponent)
            if act:
                return act

        # 3. Character strategy
        if char.face == "Re":
            return self._strategy_re(player, opponent, need_shield, opp_eff_shields)
        elif char.face == "Cavallo":
            return self._strategy_cavallo(player, opponent, opp_eff_shields)
        else:
            return self._strategy_fante(player, opponent, need_heal, opp_eff_shields)

    # ── Kill-shot search ──────────────────────────────────────────────────────

    def _try_kill(self, player, opponent):
        best_dmg  = 0
        best_play = None
        for indices in self._valid_combos(player):
            cards = [player.hand[i] for i in indices]
            ba    = self._bastoni_attack_map(player, indices)
            pc    = self._pc_set(player, indices)
            rm    = last_two_rank_match(cards)
            dmg   = self._sim_damage(player, opponent, indices, ba, pc, rm)
            if dmg >= opponent.health and dmg > best_dmg:
                best_dmg  = dmg
                best_play = (indices, ba, pc, rm)

        if best_play:
            indices, ba, pc, rm = best_play
            return self._build(player, indices, ba, pc, rm, "attack")
        return None

    # ── Re (King) strategy ────────────────────────────────────────────────────

    def _strategy_re(self, player, opponent, need_shield, opp_eff_shields):
        """Shields first, then combo attack+shield.  Switches to pressure vs PC chars."""
        char = player.character
        hand = player.hand

        attacks            = self._attack_cards(player)
        shields, flex_shld = self._shield_cards(player)
        all_shields        = shields + flex_shld
        heals              = [c for c in hand if c.suit == "Coppe"]

        # Opponent is a Poison Cup threat → shields are less useful, pressure instead
        opp_is_pc = opponent.character.suit in ("Spade", "Coppe")

        # Rebuild shields if below floor (unless they'll just get bypassed)
        if need_shield and all_shields and not opp_is_pc:
            best = max(all_shields, key=lambda c: c.value)
            idx  = hand.index(best)
            if best.suit == "Bastoni":
                best._temp_bastoni_choice = "shield"
                return f"{idx + 1}s", False, None
            return f"{idx + 1}", False, None

        # Combo: attack + shield — try both orders to fish for rank match
        if attacks and shields:
            atk  = max(attacks,  key=lambda c: c.value)
            shld = max(shields,   key=lambda c: c.value)
            ai, si = hand.index(atk), hand.index(shld)
            order_ab = [ai, si];   cards_ab = [hand[i] for i in order_ab]
            order_ba = [si, ai];   cards_ba = [hand[i] for i in order_ba]
            if last_two_rank_match(cards_ba) and not last_two_rank_match(cards_ab):
                indices = order_ba
            else:
                indices = order_ab
            cards = [hand[i] for i in indices]
            rm    = last_two_rank_match(cards)
            ba    = self._bastoni_attack_map(player, [ai])
            rsb   = "health" if player.health < 25 else "attack"
            return self._build(player, indices, ba, set(), rm, rsb)

        # Attack-only chain
        if attacks:
            attacks_s = sorted(attacks, key=lambda c: -c.value)
            indices   = [hand.index(c) for c in attacks_s]
            # Append a heal at the end if it creates a rank match
            if heals:
                cup = max(heals, key=lambda c: c.value)
                ci  = hand.index(cup)
                trial = indices + [ci]
                if last_two_rank_match([hand[i] for i in trial]):
                    indices = trial
            cards = [hand[i] for i in indices]
            rm    = last_two_rank_match(cards)
            ba    = self._bastoni_attack_map(player, [hand.index(c) for c in attacks_s])
            return self._build(player, indices, ba, set(), rm, "attack")

        # Shield only
        if all_shields:
            best = max(all_shields, key=lambda c: c.value)
            idx  = hand.index(best)
            if best.suit == "Bastoni":
                best._temp_bastoni_choice = "shield"
                return f"{idx + 1}s", False, None
            return f"{idx + 1}", False, None

        # Fallback — never skip
        return self._best_single_fallback(player, opponent)

    # ── Cavallo (Knight) strategy ─────────────────────────────────────────────

    def _strategy_cavallo(self, player, opponent, opp_eff_shields):
        """Chain all attack cards; append heal only when it creates a rank match."""
        char    = player.character
        hand    = player.hand
        attacks = sorted(self._attack_cards(player), key=lambda c: -c.value)
        heals   = sorted([c for c in hand if c.suit == "Coppe"], key=lambda c: -c.value)

        if attacks:
            indices = [hand.index(c) for c in attacks]
            # Only append heal if it doubles (rank match on last two)
            if heals:
                cup   = max(heals, key=lambda c: c.value)
                ci    = hand.index(cup)
                trial = indices + [ci]
                if last_two_rank_match([hand[i] for i in trial]):
                    indices = trial
            cards = [hand[i] for i in indices]
            rm    = last_two_rank_match(cards)
            ba    = self._bastoni_attack_map(player, [hand.index(c) for c in attacks])
            return self._build(player, indices, ba, set(), rm, "attack")

        # No attacks — heal with best Coppe
        if heals:
            return self._heal_action(player, opponent) or self._best_single_fallback(player, opponent)

        return self._best_single_fallback(player, opponent)

    # ── Fante (Page) strategy ─────────────────────────────────────────────────

    def _strategy_fante(self, player, opponent, need_heal, opp_eff_shields):
        """Poison Cup when shields are up; heal aggressively; attack otherwise."""
        char    = player.character
        hand    = player.hand
        attacks = sorted(self._attack_cards(player), key=lambda c: -c.value)
        heals   = sorted([c for c in hand if c.suit == "Coppe"], key=lambda c: -c.value)

        # Poison Cup: only available when character is Spade or Coppe
        can_pc = char.suit in ("Spade", "Coppe")
        if can_pc and heals and opp_eff_shields >= POISON_CUP_TRIGGER[char.face]:
            cup      = heals[0]
            ci       = hand.index(cup)
            self_dmg = max(0, cup.value // 2 - char.heal_bonus)
            if player.health - self_dmg > 8:
                # Try to pair with a same-rank attack BEFORE the PC (so PC is last = doubles)
                match_atk = next((c for c in attacks if c.rank == cup.rank), None)
                if match_atk:
                    si      = hand.index(match_atk)
                    indices = [si, ci]
                    rm      = last_two_rank_match([hand[i] for i in indices])
                    return self._build(player, indices, {}, {ci}, rm, "attack")
                # Just PC on its own
                return f"{ci + 1}s", False, None

        # Heal when needed
        if need_heal and heals:
            act = self._heal_action(player, opponent)
            if act:
                return act

        # Attack chain (with optional rank-match heal appended last)
        if attacks:
            indices = [hand.index(c) for c in attacks]
            if heals:
                cup   = max(heals, key=lambda c: c.value)
                ci    = hand.index(cup)
                trial = indices + [ci]
                if last_two_rank_match([hand[i] for i in trial]):
                    indices = trial
            cards = [hand[i] for i in indices]
            rm    = last_two_rank_match(cards)
            ba    = self._bastoni_attack_map(player, [hand.index(c) for c in attacks])
            return self._build(player, indices, ba, set(), rm, "attack")

        # Heal if that's all we have
        if heals:
            return self._heal_action(player, opponent) or self._best_single_fallback(player, opponent)

        return self._best_single_fallback(player, opponent)

    # ── Role-based card categorisation ────────────────────────────────────────

    def _attack_cards(self, player):
        """Cards whose default role is attack (Spade always; Bastoni always for AI)."""
        return [c for c in player.hand if c.suit in ("Spade", "Bastoni")]

    def _shield_cards(self, player):
        """(denari_list, flex_bastoni_list) — flex only for Bastoni characters."""
        hand    = player.hand
        denari  = [c for c in hand if c.suit == "Denari"]
        flex    = ([c for c in hand if c.suit == "Bastoni"]
                   if player.character.suit == "Bastoni" else [])
        return denari, flex

    def _bastoni_attack_map(self, player, indices):
        """Return {idx: 'attack'} for every Bastoni card in indices (Bastoni chars only)."""
        if player.character.suit != "Bastoni":
            return {}
        hand = player.hand
        return {i: "attack" for i in indices if hand[i].suit == "Bastoni"}

    def _pc_set(self, player, indices):
        """Indices that should be Poison Cup (Coppe cards, Spade/Coppe characters)."""
        if player.character.suit not in ("Spade", "Coppe"):
            return set()
        hand = player.hand
        return {i for i in indices if hand[i].suit == "Coppe"}

    # ── Universal fallback — never skip ──────────────────────────────────────

    def _best_single_fallback(self, player, opponent):
        """Always play something.  Priority: attack > heal > shield > anything."""
        hand = player.hand
        if not hand:
            return "0", False, None

        char    = player.character
        attacks = self._attack_cards(player)
        heals   = [c for c in hand if c.suit == "Coppe"]
        shields = [c for c in hand if c.suit == "Denari"]

        if attacks:
            best = max(attacks, key=lambda c: c.value)
        elif heals:
            best = max(heals, key=lambda c: c.value)
        elif shields:
            best = max(shields, key=lambda c: c.value)
        else:
            best = max(hand, key=lambda c: c.value)

        idx = hand.index(best)
        if char.suit == "Bastoni" and best.suit == "Bastoni":
            best._temp_bastoni_choice = "attack"
            return f"{idx + 1}s", False, None
        return f"{idx + 1}", False, None

    # ── Helpers ───────────────────────────────────────────────────────────────

    def _heal_action(self, player, opponent):
        """Return action to play the best heal card, or None if none available."""
        heals = [c for c in player.hand if c.suit == "Coppe"]
        if not heals:
            return None
        best = max(heals, key=lambda c: c.value + player.character.heal_bonus)
        return f"{player.hand.index(best) + 1}", False, None

    def _valid_combos(self, player):
        """All valid index-list combos from the current hand."""
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

    def _sim_damage(self, player, opponent, indices, bastoni_as, poison_cups, rm):
        """Simulate HP damage from a combo.  Only the LAST card doubles on rank match."""
        hand        = player.hand
        cards       = [hand[i] for i in indices]
        n           = len(cards)
        sim_shields = sorted(opponent.shields, key=lambda c: c.value)
        def_bonus   = opponent.character.defense_bonus
        total_dmg   = 0

        for j, (idx, card) in enumerate(zip(indices, cards)):
            double = rm and j == n - 1   # only the final card doubles
            mult   = 2 if double else 1

            # Poison Cup — ignores shields entirely
            if idx in poison_cups and card.suit == "Coppe":
                total_dmg += (card.value + player.character.attack_bonus) * mult
                continue

            is_attack = (card.suit == "Spade" or
                         (card.suit == "Bastoni" and bastoni_as.get(idx) == "attack"))
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

    def _build(self, player, indices, bastoni_as, poison_cups, rm, rsb):
        """Build (inp_str, rank_match, rank_match_shield_bonus)."""
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
