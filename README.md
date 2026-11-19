# 2-Player Texas Hold'em Poker Game

A heads-up Texas Hold'em poker game where you play against an AI opponent. Play in the **terminal** or in a **web browser**, and optionally host the web version on a Raspberry Pi (or any Docker host) for your home network.

## Features

- Full Texas Hold'em hands with every betting round (pre-flop, flop, turn, river) and a showdown
- AI opponent that weighs hand strength and pot odds, bluffs occasionally, and never raises more than you can match
- Fold, check, call, raise, and all-in actions, with minimum-raise and stack limits enforced
- Hand evaluation, split pots on ties, and chip and pot tracking across hands
- Two front ends that share the same game engine:
  - **Command line**: no dependencies beyond the Python standard library
  - **Web**: a browser table served by FastAPI
- Docker and Docker Compose setup, a systemd service for Raspberry Pi, and an optional nginx HTTPS reverse proxy

## Requirements

- Python 3.9 or higher
- **CLI**: no external dependencies
- **Web**: FastAPI and Uvicorn (`pip install -r requirements.txt`)
- **Docker**: Docker with the Compose plugin (the image uses Python 3.11)

## How to Run

### Command Line

```bash
python src/main.py
```

On Linux or macOS you can also run `./src/main.py` directly.

### Web Interface

1. Install dependencies: `pip install -r requirements.txt`
2. Start the server: `python src/web_main.py`
3. Open http://localhost:3076 in your browser
4. Click **Deal New Hand** to begin

`web_main.py` runs Uvicorn with auto-reload, which is handy for development. Games are kept in server memory, so refreshing the page or restarting the server starts a new game.

### Docker (e.g. Raspberry Pi)

```bash
docker compose up -d
```

Then open http://localhost:3076, or http://\<host-ip\>:3076 from other devices on your network.

To run it as a systemd service that starts on boot, or to add HTTPS on port 3077 through an nginx reverse proxy on the host, see [deploy/README.md](deploy/README.md).

## Game Rules

- Each player starts with 1000 chips
- Small blind: 10 chips, big blind: 20 chips
- The dealer button rotates each hand. Following heads-up rules, the dealer posts the small blind and acts first pre-flop; after the flop, the big blind acts first and the dealer acts last.
- A player who can't cover a blind or a bet goes all-in for what they have. The part of the other player's bet they can't match is returned, and the remaining cards are dealt straight to a showdown.
- On a tie the pot is split, with any odd chip going to the dealer
- The game ends when one player runs out of chips

## How to Play

1. You're dealt 2 hole cards and the blinds are posted automatically.
2. On your turn, choose an action:

   | Action | CLI | Web | What it does |
   |--------|-----|-----|--------------|
   | Fold | `f` | Fold | Give up the hand |
   | Check | `c` | Check | Pass when there's no bet to call |
   | Call | `c` | Call | Match the current bet |
   | Raise | `r 100` (or `r`, then enter the amount) | Enter an amount, then Raise | Raise the total bet to that amount |
   | All-in | `a` | All-In | Bet all your remaining chips |

3. After pre-flop betting the flop (3 community cards) is dealt, then the turn (1 card), then the river (1 card), with a betting round after each.
4. If both players are still in after the river, there's a showdown and the best 5-card hand wins the pot.

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
│   └── web/
│       ├── app.py           # FastAPI routes
│       ├── serializers.py   # Game state → JSON
│       ├── game_session.py  # In-memory game sessions
│       └── static/          # HTML, CSS, JS
├── deploy/
│   ├── nginx/
│   │   └── poker-https.conf  # nginx HTTPS reverse proxy config
│   ├── create-ssl-certs.sh   # Generate self-signed certs for nginx
│   ├── deploy-nginx.sh       # Deploy nginx config and certs
│   ├── poker-web.service     # systemd unit for Raspberry Pi
│   └── README.md             # Deployment instructions
├── Dockerfile
├── docker-compose.yml
├── requirements.txt
├── LICENSE
└── README.md
```

## License

Public domain, via [The Unlicense](LICENSE). Copy, modify, sell, or use this code for anything, with or without credit.
