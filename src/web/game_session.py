"""In-memory session storage for web games."""

import uuid
from typing import Dict, Optional, Tuple, Any
from dataclasses import dataclass, field


@dataclass
class Session:
    """A game session with its game instance and AI logic."""
    game: Any
    ai_logic: Any
    session_id: str = field(default_factory=lambda: str(uuid.uuid4()))


# In-memory store: session_id -> Session
_sessions: Dict[str, Session] = {}


def create_session() -> Tuple[str, Session]:
    """Create a new game session. Returns (session_id, session)."""
    from game import Game
    from ai import AIPlayer as AILogic

    game = Game(starting_chips=1000, small_blind=10)
    ai_logic = AILogic(game.ai_player, difficulty="medium")
    session = Session(game=game, ai_logic=ai_logic)
    _sessions[session.session_id] = session
    return session.session_id, session


def get_session(session_id: str) -> Optional[Session]:
    """Get a session by ID."""
    return _sessions.get(session_id)


def get_or_create_session(session_id: Optional[str]) -> Tuple[str, Session]:
    """Get existing session or create new one. Returns (session_id, session)."""
    if session_id:
        session = get_session(session_id)
        if session:
            return session_id, session
    sid, session = create_session()
    return sid, session
