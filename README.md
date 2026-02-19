# 2-Player Texas Hold'em Poker Game

A Texas Hold'em poker game where you play against an AI opponent. Play via **command line** or **web browser**.

## Features

- Full Texas Hold'em gameplay with all betting rounds (pre-flop, flop, turn, river)
- AI opponent (medium difficulty)
- Betting system with fold, check, call, raise, and all-in actions
- Hand evaluation and showdown logic
- Chip management and pot tracking

## Requirements

- Python 3.9 or higher
- **CLI**: No external dependencies (uses only Python standard library)
- **Web**: FastAPI and Uvicorn (see requirements.txt)

## How to Run

### Command Line Interface

```bash
python src/main.py
```

Or on Unix-like systems:

```bash
chmod +x src/main.py
./src/main.py
```

### Web Interface

1. Install dependencies: `pip install -r requirements.txt`
2. Start the server: `python src/web_main.py`
3. Open http://localhost:8000 in your browser
4. Click "Deal New Hand" to begin

### Docker (e.g. Raspberry Pi)

```bash
docker compose up -d
```

Then open http://localhost:8000 (or http://\<host-ip\>:8000 from other devices on your network).

For Raspberry Pi with systemd, see [deploy/README.md](deploy/README.md).

## Game Rules

- Each player starts with 1000 chips
- Small blind: 10 chips, Big blind: 20 chips
- Standard Texas Hold'em rules apply
- Dealer button rotates each hand

## How to Play

1. You'll be dealt 2 hole cards
2. Blinds are posted automatically
3. During each betting round, you can:
   - **Fold (f)**: Give up your hand
   - **Check (c)**: Pass when no bet to call
   - **Call (c)**: Match the current bet
   - **Raise (r)**: Increase the bet (enter amount)
   - **All-in (a)**: Bet all your remaining chips

4. After pre-flop betting, the flop (3 community cards) is dealt
5. After flop betting, the turn (1 card) is dealt
6. After turn betting, the river (1 card) is dealt
7. After river betting, if both players remain, there's a showdown
8. The best 5-card hand wins the pot

## Project Structure

```
Poker/
├── src/
│   ├── card.py           # Card and Deck classes
│   ├── handEvaluator.py  # Hand evaluation logic
│   ├── betting.py        # Betting round management
│   ├── player.py         # Player classes
│   ├── ai.py             # AI decision logic
│   ├── game.py           # Game state management
│   ├── cli.py            # Command-line interface
│   ├── main.py           # CLI entry point
│   ├── web_main.py       # Web server entry point
│   ├── web/
│   │   ├── app.py        # FastAPI routes
│   │   ├── serializers.py
│   │   ├── game_session.py
│   │   └── static/       # HTML, CSS, JS
├── deploy/
│   ├── poker-web.service # systemd unit for Raspberry Pi
│   └── README.md         # Deployment instructions
├── Dockerfile
├── docker-compose.yml
├── requirements.txt
└── README.md
```

## License

ISC

