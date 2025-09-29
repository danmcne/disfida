# Disfida

(NOTE THAT THE GUI VERSION MAY HAVE IMAGES WHICH ARE COPYRIGHTED. CLEARLY THESE ARE ONLY MEANT AS PLACEHOLDERS FOR PERSONAL USE, NOT FOR A SALEABLE VERSION OF THE GAME.)

A strategic two-player card combat game built with the 40-card Italian/Neapolitan deck (but easily adapted to French cards with spades (spade), hearts (coppe), clubs (bastoni), and diamonds (denari)). Inspired by traditional Italian card games but reimagined as a tactical duel where players use **characters**, **suit specials**, and **combos** to outmaneuver their opponent and reduce their health to zero.


## 🎮 Game Overview

**Disfida** transforms the classic Italian 40-card deck into a battle of wits and strategy. Each player commands a **character** (Fante/Page, Cavallo/Knight, or Re/King) of one suit, wielding unique bonuses and suit-specific abilities. The goal? Reduce your opponent's health from 40 to 0 while protecting your own.

### Core Mechanics
- **40-card Italian deck**: 4 suits (Coins, Cups, Swords, Clubs) × 10 ranks (A=11, 2-7, 3 face cards)
- **Character bonuses**: Kings bolster shields, Knights enhance attacks, Pages amplify healing
- **Suit specials**: Coins offer more cards, Swords sacrifice health for power, Cups share blessings, Clubs adapt to any role
- **Combo system**: Play sequences of your character's suit + 1 wildcard card
- **Shield mechanics**: Visible defense cards that persist until destroyed, then cycle back to your deck
- **Mechanics still under development**: In the current description the game can be a little slow. I will probably add more combo possibilities.

### Win Condition
Reduce your opponent's health to ≤0. If both players reach 0 simultaneously, it's a **tie**!

## 🎯 How to Play

### Setup
1. **Character Assignment**: Each player receives a unique face card (Fante, Cavallo, or Re) of one suit
2. **Deck Building**: 
   - Standard characters: 12-card stack, 4-card starting hand
   - Coins character: 13-card stack, 5-card starting hand (Wealth of Choice)
3. **Pre-game**: Players may play one shield (Coins or Clubs special) before normal play begins
4. **Starting Health**: Both players begin at 40 HP (capped at 40)

### Turn Structure
1. **Play Phase**: 
   - Skip your turn
   - Play one card (normal or special)
   - Play a combo (sequence of your character's suit + optional 1 non-suit card)
2. **Resolution**: Cards resolve in order (attacks vs shields, heals restore HP, shields add defense)
3. **Draw Phase**: Refill hand to starting size (4 or 5 cards)

### Card Roles & Values
| Suit | Base Role | Value |
|------|-----------|-------|
| **Coins (Denari)** | Shield (defense) | A=11, 2-7 |
| **Cups (Coppe)** | Heal (restore HP) | A=11, 2-7 |
| **Swords (Spade)** | Attack (damage) | A=11, 2-7 |
| **Clubs (Bastoni)** | Attack (damage) | A=11, 2-7 |

### Character Bonuses
| Character | Bonus |
|-----------|-------|
| **Re (King)** | +2 defense per shield card in play |
| **Cavallo (Knight)** | +1 attack per attack card played |
| **Fante (Page)** | +2 healing per healing card played |

### Suit Specials
| Suit | Special | Effect |
|------|---------|--------|
| **Coins** | **Wealth of Choice** | +1 card in stack and hand (passive) |
| **Swords** | **Blood Price** | Use Cups as attacks (ignore shields(?), take floor(value/2) self-damage) |
| **Cups** | **Charity's Burden** | Use Swords as healing (opponent also gains floor(value/2) HP) |
| **Clubs** | **Iron Versatility** | Clubs can be used as attack OR shield (choice at play) |

## 🛡️ Shield Mechanics

Shields are **visible cards on the table** that provide persistent defense:

1. **Playing Shields**: Coins cards or Clubs (with special for Clubs Heroes) add defense during your turn
2. **Attack Resolution**: When attacked, shields are destroyed from **smallest to largest** until cumulative defense ≥ attack value
3. **Destruction**: Destroyed shields cycle to the bottom of your deck (not discarded)
4. **Character Bonus**: King's +2 defense applies to each active shield dynamically

**Example**: King with shields 3 coins (diamonds) and 7 coins (diamonds) has effective defense of 5 and 9 respectively.

## ⚔️ Combat Resolution

### Attack vs Shields
```
Attack Value: 8 (7♠ +1 Knight bonus)
vs Shields: 3♢ (3+2=5), 7♢ (7+2=9)

Step 1: 8 - 5 = 3 remaining
Step 2: 3 - 9 = -6 (success!)
Result: Attack fully blocked, both shields destroyed and cycled
```
Another example, both Heroes being Fante/Pages, and therefor no bonuses for attack or defense:

```
Attack Value: 2♠
vs Shields: 3♢, 7♢

Step 1: 2 - 3 = -1 (successfully blocked by smallest shield)

Result: Attack fully blocked, 3♢ destroyed and cycled, 7♢ undamaged and remains
```

## 🎮 CLI Controls

Run the game and interact via terminal commands:

### Basic Commands
| Input | Action |
|-------|--------|
| `0` | Skip turn |
| `1` | Play card #1 from hand |
| `1,2,3` | Play combo (cards 1, 2, and 3) |
| `3s` | Play card #3 with special ability |

### Special Prompts
- **Clubs special**: When playing Club with `s` flag → "Play as attack (a) or shield (s)?"
- **Invalid combos**: Must be character-suit sequence + optional 1 non-suit card

### Example Turn
```
Player 0's turn. Hand: 1:7♠ 2:4♠ 3:3♢ 4:2♣
> 1,2,4s

Player 0 plays combo:
  Attack 7 of Spade: 8 total, 3 damage after shields
  Attack 4 of Spade: 5 total, 2 damage after shields  
  Play 2 of Clubs as attack (a) or shield (s)? a
  Attack 2 of Clubs: 3 total, 0 damage (blocked by shields)

--- Player 0's Turn Summary ---
  Attack 7 of Spade: 8 total, 3 damage after shields
  Attack 4 of Spade: 5 total, 2 damage after shields
  Attack 2 of Clubs: 3 total, 0 damage (blocked by shields)
--------------------------------

Player 0 draws 3 card(s) at end of turn
```

## 🚀 Installation & Running

### Prerequisites
- Python 3.6+

### Quick Start
```bash
# Clone the repository
git clone https://github.com/yourusername/italian-card-combat.git
cd italian-card-combat

# Run the game
python disfida.py
```

### GUI Quick Start
```bash
# Clone the repository
git clone https://github.com/yourusername/italian-card-combat.git
cd italian-card-combat/disfida-gui

# Run the game
python main.py
```



### Development
```bash
# Install dependencies (none required!)
pip install -r requirements.txt  # Empty file

# Run with debugging
python -m disfida
```

## 📋 Game Flow

### Complete Turn Example
```
1. Display state: Both players' HP, shields, bonuses, hands visible
2. Input: "1,2,3s" (combo with special on card 3)
3. Validation: Check combo rules and special eligibility
4. Resolution: 
   - Card 1 (♠): Attack for 8 damage, breaks 2 shields
   - Card 2 (♠): Attack for 5 damage, hits for 3 after shields
   - Card 3 (♣s): Clubs special → "Attack or Shield?" → Attack for 3
5. Summary: "Total: 16 damage dealt, 5 blocked, 2 shields destroyed"
6. Draw: Refill hand to 4 cards
```

### Pre-Game Sequence
1. **Rules Summary**: Brief rules displayed
2. **Character Assignment**: Random face cards assigned (Fante/Cavallo/Re of suits)
3. **Initial Deal**: Stacks and hands built (Coins gets bonus cards)
4. **Players Pre-shield**: Optional single shield play before turn 1
5. **Turn 1**: Player 1 begins normal play

## 🎨 UI/UX Features

### Information Layout
```
================================================================================
Player 0: Fante of Spade | HP: 38                ACTIVE: Player 0
Bonuses: +0 atk, +2 heal, +0 def/shield
Shields: 3 of Denari
--------------------------------------        ----------------------------------------
                                          Player 1: Cavallo of Coppe | HP: 40
                                          Bonuses: +1 atk, +0 heal, +0 def/shield
                                          Shields: 7 of Denari
--------------------------------------------------------------------------------

Player 0's Hand (4/4):
--------------------------------------------------------------------------------
   1: 3 of Bastoni    2: 2 of Coppe     3: 7 of Spade     4: 4 of Spade

Player 1's Hand (4/4):
   1: 6 of Spade      2: 4 of Coppe     3: 2 of Spade     4: A of Coppe
================================================================================
```

### Visual Cues
- **Side-by-side layout**: Both players visible at all times
- **Active turn indicator**: Clear "ACTIVE: Player X" marker
- **Color-coded sections**: Shields, hands, bonuses clearly separated
- **Turn summaries**: Recap of all effects after each turn

## 🧪 Testing Scenarios

### Combo Validation
```
Valid: "1,2,3" (all Spade for Spade character)
Valid: "1,2,4" (two Spade + 1 Club wildcard)
Invalid: "1,3,4" (mixed suits, no character suit sequence)
```

### Special Plays
```
Swords + "2s" (Cup card): Blood Price attack, ignores shields
Cups + "3s" (Sword card): Charity's Burden heal, opponent gains half
Clubs + "4s" (Club card): Choose attack or shield mode
Coins + "5s": Error - no special for Coins character
```

### Shield Resolution
```
Attack 10 vs Shields [2♢, 5♢, 7♠] (King +2 each):
Step 1: 10 - 4 (2+2) = 6 remaining
Step 2: 6 - 7 (5+2) = -1 (success!)
Result: 2♢ and 5♢ destroyed, 7♠ survives
```

## 🤝 Contributing

1. Fork the repository
2. Create feature branch (`git checkout -b feature/new-special`)
3. Commit changes (`git commit -m 'Add new suit special'`)
4. Push to branch (`git push origin feature/new-special`)
5. Open Pull Request

### Development Roadmap
- [x] Core mechanics (attacks, heals, shields)
- [x] Character bonuses and suit specials
- [x] Combo validation and resolution
- [x] CLI interface with full state display
- [x] Simple GUI version
- [ ] AI opponent
- [ ] Character selection screen
- [ ] Save/load game state
- [ ] Online multiplayer

## 📄 License

### Game Design & Code
**Disfida** by danmcne is licensed under the **Creative Commons Attribution 4.0 International License** (CC BY 4.0).

#### What this means:
- **✅ Free to use**: Play, share, and enjoy the game
- **✅ Free to modify**: Adapt rules, create variants, or build expansions
- **✅ Free to profit**: Commercial use allowed (mobile apps, board game versions, etc.)
- **✅ Free to distribute**: Share with friends, sell, or publish anywhere

#### Attribution Requirements:
- Include: "Disfida by danmcne, licensed under CC BY 4.0"
- Link: [https://creativecommons.org/licenses/by/4.0/](https://creativecommons.org/licenses/by/4.0/)
- Preserve: Original creator credit in any derivative works

#### No Warranty
The game is provided "as is" without warranty of any kind. Play at your own risk!

### Italian Card Deck
The game uses the traditional 40-card Italian/Neapolitan deck, which is **public domain** and free for any use.

---

## 🙏 Acknowledgments

- **Traditional Italian Card Games**: Inspiration from Scopa, Briscola, and regional variants
- **Game Design**: danmcne - Original mechanics and balance
- **Development**: Python CLI implementation with clean, modular architecture
- **Playtesting**: Friends, family, and the open-source community

*Last Updated: September 2025*  
*Version: 1.0.0*  
