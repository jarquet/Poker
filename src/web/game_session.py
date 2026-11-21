"""Session storage for web games.

By default sessions live in this process's memory, which suits a single
long-running server (local, Docker, Raspberry Pi). Serverless hosts such as
Vercel spread requests across short-lived instances that don't share memory,
so when Upstash Redis REST credentials are set, sessions are stored there
instead and survive across instances and restarts.
"""

import base64
import http.client
import json
import os
import pickle
import sys
import threading
import time
import uuid
from contextvars import ContextVar
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Tuple
from urllib.parse import urlsplit

# Idle games are dropped after a week so storage doesn't grow forever.
SESSION_TTL_SECONDS = 7 * 24 * 60 * 60
KEY_PREFIX = "poker:session:"

# Milliseconds spent on each storage call during the current request,
# reported in the Server-Timing response header.
store_timings: ContextVar[Optional[List[float]]] = ContextVar(
    "store_timings", default=None
)
# One entry per storage call that had to open a new connection.
store_new_connections: ContextVar[Optional[List[int]]] = ContextVar(
    "store_new_connections", default=None
)


@dataclass
class Session:
    """A game session with its game instance and AI logic."""
    game: Any
    ai_logic: Any
    session_id: str = field(default_factory=lambda: str(uuid.uuid4()))


class MemoryStore:
    """Keeps sessions in this process. Lost when the server restarts.

    Like Redis, it stores pickled copies, so each request works on its own
    copy of the game and concurrent requests (handled on separate threads)
    never modify the same live object at once.
    """

    def __init__(self):
        self._sessions: Dict[str, bytes] = {}

    def load(self, session_id: str) -> Optional[Session]:
        data = self._sessions.get(session_id)
        return pickle.loads(data) if data is not None else None

    def save(self, session: Session) -> None:
        self._sessions[session.session_id] = pickle.dumps(session)


class UpstashStore:
    """Keeps sessions in Upstash Redis through its REST API (stdlib only).

    Sessions are pickled. Only this server writes them, using a token that
    is never sent to the browser, so loading them back is safe.
    """

    def __init__(self, url: str, token: str):
        parts = urlsplit(url)
        self.scheme = parts.scheme
        self.host = parts.hostname
        self.port = parts.port
        self.path = parts.path or "/"
        self.token = token
        # A small pool of kept-alive connections shared by all threads.
        # Opening a new HTTPS connection costs extra round trips, and
        # requests are handled on whichever pool thread is free.
        self._idle: List[http.client.HTTPConnection] = []
        self._lock = threading.Lock()

    MAX_IDLE_CONNECTIONS = 8

    def _command(self, *args) -> Any:
        start = time.perf_counter()
        try:
            return self._send(*args)
        finally:
            timings = store_timings.get()
            if timings is not None:
                timings.append((time.perf_counter() - start) * 1000)

    def _acquire(self, fresh: bool = False) -> http.client.HTTPConnection:
        conn = None
        if not fresh:
            with self._lock:
                if self._idle:
                    conn = self._idle.pop()
        if conn is None:
            conn_class = (http.client.HTTPSConnection
                          if self.scheme == "https"
                          else http.client.HTTPConnection)
            conn = conn_class(self.host, self.port, timeout=5)
        if conn.sock is None:  # new, or closed by the server: will connect
            new_connections = store_new_connections.get()
            if new_connections is not None:
                new_connections.append(1)
        return conn

    def _release(self, conn: http.client.HTTPConnection) -> None:
        with self._lock:
            if len(self._idle) < self.MAX_IDLE_CONNECTIONS:
                self._idle.append(conn)
                return
        conn.close()

    def _send(self, *args) -> Any:
        body = json.dumps(args).encode("utf-8")
        headers = {
            "Authorization": f"Bearer {self.token}",
            "Content-Type": "application/json",
        }
        # A kept-alive connection may have been closed by the server while
        # idle; retry once on a fresh connection. GET and SET are safe to
        # repeat.
        for attempt in (1, 2):
            conn = self._acquire(fresh=attempt == 2)
            try:
                conn.request("POST", self.path, body=body, headers=headers)
                response = conn.getresponse()
                data = response.read()
            except (http.client.HTTPException, OSError):
                conn.close()
                if attempt == 2:
                    raise
                continue
            self._release(conn)
            break
        if response.status != 200:
            detail = data.decode("utf-8", "replace")
            raise RuntimeError(
                f"Upstash Redis error {response.status}: {detail}"
            )
        result = json.loads(data)
        if "error" in result:
            raise RuntimeError(f"Upstash Redis error: {result['error']}")
        return result.get("result")

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


def get_session(session_id: str) -> Optional[Session]:
    """Get a session by ID, or None if it doesn't exist or has expired."""
    if not _is_valid_id(session_id):
        return None
    return _store.load(session_id)


def load_or_new_session(session_id: Optional[str]) -> Tuple[Session, bool]:
    """Load a session, or make a new one that isn't saved yet.

    Returns (session, is_new). The caller saves it once it's done changing
    it, so a request costs at most one read and one write.
    """
    session = get_session(session_id) if session_id else None
    if session:
        return session, False
    return _new_session(), True


def save_session(session: Session) -> None:
    """Persist a session after its game has changed."""
    _store.save(session)


def new_match(session_id: Optional[str]) -> Session:
    """Start a fresh match under the given session ID (or a new one).

    The old game is simply overwritten, so there's no need to load it.
    """
    fresh = _new_session(session_id if _is_valid_id(session_id) else None)
    _store.save(fresh)
    return fresh
