"""Session storage for web games.

By default sessions live in this process's memory, which suits a single
long-running server (local, Docker, Raspberry Pi). Serverless hosts such as
Vercel spread requests across short-lived instances that don't share memory,
so when Upstash Redis REST credentials are set, sessions are stored there
instead and survive across instances and restarts.
"""

import base64
import json
import os
import pickle
import sys
import urllib.error
import urllib.request
import uuid
from dataclasses import dataclass, field
from typing import Any, Dict, Optional, Tuple

# Idle games are dropped after a week so storage doesn't grow forever.
SESSION_TTL_SECONDS = 7 * 24 * 60 * 60
KEY_PREFIX = "poker:session:"


@dataclass
class Session:
    """A game session with its game instance and AI logic."""
    game: Any
    ai_logic: Any
    session_id: str = field(default_factory=lambda: str(uuid.uuid4()))


class MemoryStore:
    """Keeps sessions in this process. Lost when the server restarts."""

    def __init__(self):
        self._sessions: Dict[str, Session] = {}

    def load(self, session_id: str) -> Optional[Session]:
        return self._sessions.get(session_id)

    def save(self, session: Session) -> None:
        self._sessions[session.session_id] = session


class UpstashStore:
    """Keeps sessions in Upstash Redis through its REST API (stdlib only).

    Sessions are pickled. Only this server writes them, using a token that
    is never sent to the browser, so loading them back is safe.
    """

    def __init__(self, url: str, token: str):
        self.url = url.rstrip("/")
        self.token = token

    def _command(self, *args) -> Any:
        request = urllib.request.Request(
            self.url,
            data=json.dumps(args).encode("utf-8"),
            headers={
                "Authorization": f"Bearer {self.token}",
                "Content-Type": "application/json",
            },
            method="POST",
        )
        try:
            with urllib.request.urlopen(request, timeout=5) as response:
                body = json.load(response)
        except urllib.error.HTTPError as e:
            detail = e.read().decode("utf-8", "replace")
            raise RuntimeError(f"Upstash Redis error {e.code}: {detail}")
        if "error" in body:
            raise RuntimeError(f"Upstash Redis error: {body['error']}")
        return body.get("result")

    def load(self, session_id: str) -> Optional[Session]:
        data = self._command("GET", KEY_PREFIX + session_id)
        if data is None:
            return None
        try:
            return pickle.loads(base64.b64decode(data))
        except Exception:
            # Saved by an incompatible older version of the code
            return None

    def save(self, session: Session) -> None:
        data = base64.b64encode(pickle.dumps(session)).decode("ascii")
        self._command(
            "SET", KEY_PREFIX + session.session_id, data,
            "EX", SESSION_TTL_SECONDS,
        )


def _create_store():
    # Upstash's own variable names, or the KV_* names that Vercel's
    # storage integration has used for the same database.
    url = (os.environ.get("UPSTASH_REDIS_REST_URL")
           or os.environ.get("KV_REST_API_URL"))
    token = (os.environ.get("UPSTASH_REDIS_REST_TOKEN")
             or os.environ.get("KV_REST_API_TOKEN"))
    if url and token:
        return UpstashStore(url, token)
    if os.environ.get("VERCEL"):
        print(
            "WARNING: no Upstash Redis credentials found. Games are kept in "
            "memory and will reset when Vercel switches instances. Connect "
            "an Upstash Redis database to this project and redeploy.",
            file=sys.stderr,
        )
    return MemoryStore()


_store = _create_store()


def _new_session(session_id: Optional[str] = None) -> Session:
    from game import Game
    from ai import AIPlayer as AILogic

    game = Game(starting_chips=1000, small_blind=10)
    ai_logic = AILogic(game.ai_player, difficulty="medium")
    session = Session(game=game, ai_logic=ai_logic)
    if session_id:
        session.session_id = session_id
    return session


def _is_valid_id(session_id: Optional[str]) -> bool:
    try:
        return session_id is not None and str(uuid.UUID(session_id)) == session_id
    except ValueError:
        return False


def create_session() -> Tuple[str, Session]:
    """Create and store a new game session. Returns (session_id, session)."""
    session = _new_session()
    _store.save(session)
    return session.session_id, session


def get_session(session_id: str) -> Optional[Session]:
    """Get a session by ID, or None if it doesn't exist or has expired."""
    if not _is_valid_id(session_id):
        return None
    return _store.load(session_id)


def get_or_create_session(session_id: Optional[str]) -> Tuple[str, Session]:
    """Get existing session or create new one. Returns (session_id, session)."""
    session = get_session(session_id) if session_id else None
    if session:
        return session.session_id, session
    return create_session()


def save_session(session: Session) -> None:
    """Persist a session after its game has changed."""
    _store.save(session)


def reset_session(session: Session) -> Session:
    """Start a fresh match under the same session ID."""
    fresh = _new_session(session.session_id)
    _store.save(fresh)
    return fresh
