/**
 * Texas Hold'em Poker - Web Client
 */

let sessionId = null;

async function apiFetch(path, options = {}) {
  const headers = {
    'Content-Type': 'application/json',
    ...options.headers,
  };
  if (sessionId) {
    headers['X-Session-Id'] = sessionId;
  }
  const res = await fetch(path, { ...options, headers });
  if (!res.ok) {
    const err = await res.json().catch(() => ({ detail: res.statusText }));
    throw new Error(err.detail || err.message || 'Request failed');
  }
  return res.json();
}

function cardClass(cardStr) {
  if (!cardStr || cardStr === '?') return 'card';
  const suit = cardStr.slice(-1);
  const isRed = suit === '♥' || suit === '♦';
  return `card ${isRed ? 'red' : 'black'}`;
}

function renderCards(containerId, cards) {
  const el = document.getElementById(containerId);
  if (!cards || cards.length === 0) {
    el.innerHTML = '';
    return;
  }
  el.innerHTML = cards
    .map((c) => `<span class="${cardClass(c)}">${c}</span>`)
    .join('');
}

function updateUI(state) {
  sessionId = state.session_id;

  document.getElementById('hand-num').textContent =
    state.hand_number > 0 ? `#${state.hand_number}` : '—';
  document.getElementById('pot').textContent = state.pot;
  document.getElementById('human-name').textContent = state.human_player.name;
  document.getElementById('human-chips').textContent =
    `${state.human_player.chips} chips`;
  document.getElementById('ai-name').textContent = state.ai_player.name;
  document.getElementById('ai-chips').textContent =
    `${state.ai_player.chips} chips`;

  renderCards('human-cards', state.human_player.hole_cards);
  renderCards('ai-cards', state.ai_player.hole_cards);
  renderCards('community-cards', state.community_cards);

  const currentBetEl = document.getElementById('current-bet');
  if (state.current_bet > 0) {
    currentBetEl.textContent = `Current bet: ${state.current_bet}`;
  } else {
    currentBetEl.textContent = '';
  }

  // Actions
  const actionsEl = document.getElementById('actions');
  const startHandEl = document.getElementById('start-hand');
  const resultEl = document.getElementById('result');

  if (state.game_state === 'game_over') {
    actionsEl.classList.add('hidden');

    if (state.game_over) {
      startHandEl.classList.add('hidden');
      resultEl.classList.remove('hidden');
      const hp = state.human_player.chips;
      const ap = state.ai_player.chips;
      const winner =
        hp > ap ? state.human_player.name : state.ai_player.name;
      resultEl.textContent = `GAME OVER! ${winner} wins the match!`;
      resultEl.classList.add('winner');
    } else {
      startHandEl.classList.remove('hidden');
      if (state.winner_info) {
        resultEl.classList.remove('hidden');
        const wi = state.winner_info;
        let msg = `${wi.winner} wins!`;
        if (wi.reason === 'Showdown' && wi.human_hand && wi.ai_hand) {
          msg += ` (${wi.human_hand} vs ${wi.ai_hand})`;
        } else if (wi.reason) {
          msg += ` - ${wi.reason}`;
        }
        resultEl.textContent = msg;
        resultEl.classList.add('winner');
      }
    }
  } else {
    startHandEl.classList.add('hidden');
    resultEl.classList.add('hidden');

    if (state.is_human_turn) {
      actionsEl.classList.remove('hidden');
      const va = state.valid_actions;

      document.querySelector('[data-action="fold"]').disabled = !va.can_fold;
      document.querySelector('[data-action="check"]').disabled = !va.can_check;
      document.querySelector('[data-action="call"]').disabled = !va.can_call;
      document.querySelector('[data-action="raise"]').disabled = !va.can_raise;
      document.querySelector('[data-action="all_in"]').disabled = !va.can_all_in;

      const callBtn = document.querySelector('[data-action="call"]');
      if (va.can_call) {
        callBtn.textContent = `Call (${va.amount_to_call})`;
      } else {
        callBtn.textContent = 'Call';
      }

      const raiseInput = document.getElementById('raise-amount');
      raiseInput.placeholder = `min ${va.min_raise}`;
      raiseInput.min = va.min_raise;
      raiseInput.max = va.max_raise;
    } else {
      actionsEl.classList.add('hidden');
      showMessage(`${state.ai_player.name} is thinking...`);
    }
  }

}

function showMessage(msg) {
  document.getElementById('message').textContent = msg || '';
}

document.addEventListener('DOMContentLoaded', async () => {
  try {
    const state = await apiFetch('/api/state');
    updateUI(state);
    if (state.game_state === 'game_over' && !state.game_over) {
      showMessage('Click "Deal New Hand" to start');
    }
  } catch (err) {
    showMessage('Error: ' + err.message);
  }
});

document.getElementById('raise-amount')?.addEventListener('click', (e) => {
  e.stopPropagation();
});

document.getElementById('actions').addEventListener('click', async (e) => {
  if (e.target.id === 'raise-amount' || e.target.closest('#raise-amount')) {
    return;
  }
  const btn = e.target.closest('[data-action]');
  if (!btn || btn.disabled) return;

  const action = btn.dataset.action;
  let amount = null;
  if (action === 'raise') {
    amount = parseInt(
      document.getElementById('raise-amount').value,
      10
    );
    if (isNaN(amount)) {
      showMessage('Enter a valid raise amount');
      return;
    }
  }

  showMessage('');

  try {
    const state = await apiFetch('/api/action', {
      method: 'POST',
      body: JSON.stringify({ action, amount }),
    });
    updateUI(state);
  } catch (err) {
    showMessage('Error: ' + err.message);
  }
});

document.getElementById('btn-start-hand').addEventListener('click', async () => {
  showMessage('');

  try {
    const state = await apiFetch('/api/start-hand', {
      method: 'POST',
    });
    updateUI(state);
  } catch (err) {
    showMessage('Error: ' + err.message);
  }
});
