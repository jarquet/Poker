"""
FastAPI web application for Texas Hold'em poker.
"""

from pathlib import Path
from typing import Optional

from fastapi import FastAPI, HTTPException, Header
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
from pydantic import BaseModel

from game import Game, GameState
from betting import BettingAction
from .serializers import serialize_game_state
from .game_session import get_or_create_session


app = FastAPI(title="Texas Hold'em Poker", version="1.0")

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


def _run_ai_turns(session) -> None:
    """Run all AI turns until it's human's turn or hand is over."""
    game = session.game
    ai_logic = session.ai_logic

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

        action, amount = ai_logic.get_action(
            amount_to_call,
            current_bet,
            min_raise,
            game.community_cards,
            br.pot,
        )

        success, _ = game.process_betting_action(1, action, amount)
        if not success:
            break


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


@app.get("/api/state")
async def get_state(x_session_id: Optional[str] = Header(None, alias="X-Session-Id")):
    """Get current game state. Creates new session if none exists."""
    session_id, session = get_or_create_session(x_session_id)
    state = serialize_game_state(session.game)
    state["session_id"] = session_id
    return state


@app.post("/api/action")
async def submit_action(
    req: ActionRequest,
    x_session_id: Optional[str] = Header(None, alias="X-Session-Id"),
):
    """Submit a betting action. AI will act automatically if it's their turn after."""
    session_id, session = get_or_create_session(x_session_id)
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

    state = serialize_game_state(game)
    state["session_id"] = session_id
    return state


@app.post("/api/start-hand")
async def start_hand(
    x_session_id: Optional[str] = Header(None, alias="X-Session-Id"),
):
    """Start a new hand. Requires game to be in GAME_OVER state."""
    session_id, session = get_or_create_session(x_session_id)
    game = session.game

    if game.is_game_over():
        # Full game over - one player out of chips
        raise HTTPException(400, "Game over. One player is out of chips.")

    if game.state != GameState.GAME_OVER:
        raise HTTPException(400, "Current hand not finished yet.")

    game.start_new_hand()

    # If AI is first to act (big blind), run their turn
    _run_ai_turns(session)

    state = serialize_game_state(game)
    state["session_id"] = session_id
    return state
