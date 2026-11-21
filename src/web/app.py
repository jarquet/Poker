"""
FastAPI web application for Texas Hold'em poker.
"""

import time
from pathlib import Path
from typing import Optional

from fastapi import FastAPI, HTTPException, Header, Request
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
from pydantic import BaseModel

from game import Game, GameState
from betting import BettingAction
from .serializers import serialize_game_state
from .game_session import (
    load_or_new_session, new_match, save_session, store_new_connections,
    store_timings,
)


app = FastAPI(title="Texas Hold'em Poker", version="1.0")


@app.middleware("http")
async def add_server_timing(request: Request, call_next):
    """Report time spent in the app and in session storage.

    Browsers show the Server-Timing header in their developer tools.
    """
    timings, new_connections = [], []
    tokens = (store_timings.set(timings),
              store_new_connections.set(new_connections))
    start = time.perf_counter()
    try:
        response = await call_next(request)
    finally:
        store_timings.reset(tokens[0])
        store_new_connections.reset(tokens[1])
    total_ms = (time.perf_counter() - start) * 1000
    store_ms = sum(timings)
    response.headers["Server-Timing"] = (
        f'app;dur={total_ms:.1f}, '
        f'store;dur={store_ms:.1f};desc="{len(timings)} storage calls, '
        f'{len(new_connections)} new connections"'
    )
    return response

# Serve static files from web/static
STATIC_DIR = Path(__file__).parent / "static"
if STATIC_DIR.exists():
    app.mount("/static", StaticFiles(directory=str(STATIC_DIR)), name="static")


class ActionRequest(BaseModel):
    action: str  # fold, check, call, raise, all_in
    amount: Optional[int] = None


def _get_active_player_index(game: Game) -> Optional[int]:
    """Get the index of the player who should act next, or None if round complete."""
    br = game.current_betting_round
    if br is None:
        return None
    if br.round_complete:
        return None

    human_acted = br.players_acted[0]
    ai_acted = br.players_acted[1]
    human_contribution = br.player_contributions[0]
    ai_contribution = br.player_contributions[1]
    current_bet = br.current_bet

    if not human_acted and not ai_acted:
        return game.get_active_player_index()
    if not human_acted:
        return 0
    if not ai_acted:
        return 1
    if human_contribution < ai_contribution:
        return 0
    if ai_contribution < human_contribution:
        return 1
    if current_bet > 0 and br.last_to_act is not None:
        return 1 if br.last_to_act == 0 else 0
    human_short = current_bet > 0 and human_contribution < current_bet
    if human_short:
        return 0
    if current_bet > 0 and ai_contribution < current_bet:
        return 1
    return None


def _run_ai_turns(session) -> int:
    """Run all AI turns until it's human's turn or hand is over.

    Returns how many actions the AI took.
    """
    game = session.game
    ai_logic = session.ai_logic
    actions = 0

    while game.state != GameState.GAME_OVER:
        active_index = _get_active_player_index(game)
        if active_index is None:
            break
        if active_index == 0:
            # Human's turn
            break

        # AI's turn
        ap = game.ai_player
        if ap.folded or ap.all_in:
            break

        br = game.current_betting_round
        amount_to_call = br.get_amount_to_call(1)
        current_bet = br.current_bet
        min_raise = (
            current_bet * 2 if current_bet > 0 else game.big_blind * 2
        )
        other_stack = game.human_player.chips
        other_contrib = br.player_contributions[0]

        action, amount = ai_logic.get_action(
            amount_to_call,
            current_bet,
            min_raise,
            game.community_cards,
            br.pot,
            other_player_stack=other_stack,
            other_player_contribution=other_contrib,
        )

        success, _ = game.process_betting_action(1, action, amount)
        if not success:
            break
        actions += 1

    return actions


def _parse_action(action_str: str) -> BettingAction:
    """Parse action string to BettingAction enum."""
    mapping = {
        "fold": BettingAction.FOLD,
        "check": BettingAction.CHECK,
        "call": BettingAction.CALL,
        "raise": BettingAction.RAISE,
        "all_in": BettingAction.ALL_IN,
    }
    if action_str.lower() not in mapping:
        raise ValueError(f"Invalid action: {action_str}")
    return mapping[action_str.lower()]


@app.get("/")
async def root():
    """Serve the main game page."""
    index_path = STATIC_DIR / "index.html"
    if index_path.exists():
        return FileResponse(index_path)
    return {"message": "Texas Hold'em Poker API", "docs": "/docs"}


# The API handlers are plain `def` functions, so FastAPI runs them in a
# thread pool: their blocking session-storage calls don't hold up other
# requests being served by the same instance.

@app.get("/api/state")
def get_state(x_session_id: Optional[str] = Header(None, alias="X-Session-Id")):
    """Get current game state. Creates new session if none exists.
    If it's the AI's turn (e.g. after page refresh), runs AI turns before returning."""
    session, is_new = load_or_new_session(x_session_id)
    if _run_ai_turns(session) or is_new:
        save_session(session)
    state = serialize_game_state(session.game)
    state["session_id"] = session.session_id
    return state


@app.post("/api/action")
def submit_action(
    req: ActionRequest,
    x_session_id: Optional[str] = Header(None, alias="X-Session-Id"),
):
    """Submit a betting action. AI will act automatically if it's their turn after."""
    session, _ = load_or_new_session(x_session_id)
    session_id = session.session_id
    game = session.game

    if game.state == GameState.GAME_OVER:
        raise HTTPException(400, "Hand is over. Start a new hand first.")

    active_index = _get_active_player_index(game)
    if active_index != 0:
        raise HTTPException(
            400,
            "Not your turn" if active_index == 1 else "Betting round complete",
        )

    try:
        action = _parse_action(req.action)
    except ValueError as e:
        raise HTTPException(400, str(e))

    if action == BettingAction.RAISE and req.amount is None:
        raise HTTPException(400, "Raise requires an amount")

    success, message = game.process_betting_action(
        0, action, req.amount
    )
    if not success:
        raise HTTPException(400, message)

    # Run AI turns until human's turn or hand over
    _run_ai_turns(session)
    save_session(session)

    state = serialize_game_state(game)
    state["session_id"] = session_id
    return state


@app.post("/api/start-hand")
def start_hand(
    x_session_id: Optional[str] = Header(None, alias="X-Session-Id"),
):
    """Start a new hand. Requires game to be in GAME_OVER state."""
    session, _ = load_or_new_session(x_session_id)
    session_id = session.session_id
    game = session.game

    if game.is_game_over():
        # Full game over - one player out of chips
        raise HTTPException(400, "Game over. One player is out of chips.")

    if game.state != GameState.GAME_OVER:
        raise HTTPException(400, "Current hand not finished yet.")

    game.start_new_hand()

    # If AI is first to act (dealer/small blind pre-flop), run their turn
    _run_ai_turns(session)
    save_session(session)

    state = serialize_game_state(game)
    state["session_id"] = session_id
    return state


@app.post("/api/new-game")
def new_game(
    x_session_id: Optional[str] = Header(None, alias="X-Session-Id"),
):
    """Start a new match (fresh chip stacks) under the same session."""
    session = new_match(x_session_id)
    state = serialize_game_state(session.game)
    state["session_id"] = session.session_id
    return state
