"""Serialize game state to JSON for the web API."""

from typing import List, Optional, Any

# Import when used - avoid circular imports at module load
def _get_game():
    from game import Game
    return Game

def serialize_card(card) -> str:
    """Serialize a Card to string representation."""
    return str(card)

def serialize_cards(cards) -> List[str]:
    """Serialize a list of cards."""
    return [serialize_card(c) for c in cards] if cards else []

def serialize_game_state(game) -> dict:
    """Serialize full game state for API response."""
    pot = (
        game.current_betting_round.pot
        if game.current_betting_round else 0
    )

    # Build valid actions for human player
    valid_actions = {"can_fold": False, "can_check": False, "can_call": False,
                     "can_raise": False, "can_all_in": False,
                     "amount_to_call": 0, "min_raise": 0, "max_raise": 0}
    if game.current_betting_round:
        br = game.current_betting_round
        amount_to_call = br.get_amount_to_call(0)
        current_bet = br.current_bet
        min_raise = current_bet * 2 if current_bet > 0 else game.big_blind * 2
        player_chips = game.human_player.chips
        human_contrib = br.player_contributions[0]
        max_raise = player_chips + human_contrib

        valid_actions["amount_to_call"] = amount_to_call
        valid_actions["min_raise"] = min_raise
        valid_actions["max_raise"] = max_raise
        if amount_to_call > 0:
            valid_actions["can_fold"] = True
            valid_actions["can_call"] = True
        else:
            valid_actions["can_check"] = True
        valid_actions["can_raise"] = True
        valid_actions["can_all_in"] = player_chips > 0

    state: dict[str, Any] = {
        "hand_number": game.hand_number,
        "game_state": game.state.value,
        "human_player": {
            "name": game.human_player.name,
            "chips": game.human_player.chips,
            "hole_cards": serialize_cards(game.human_player.hole_cards),
            "folded": game.human_player.folded,
            "all_in": game.human_player.all_in,
        },
        "ai_player": {
            "name": game.ai_player.name,
            "chips": game.ai_player.chips,
            "hole_cards": serialize_cards(game.ai_player.hole_cards)
            if game.state.value == "game_over" else ["?", "?"],
            "folded": game.ai_player.folded,
            "all_in": game.ai_player.all_in,
        },
        "community_cards": serialize_cards(game.community_cards),
        "pot": pot,
        "current_bet": (
            game.current_betting_round.current_bet
            if game.current_betting_round else 0
        ),
        "dealer_index": game.dealer_index,
        "valid_actions": valid_actions,
        "is_human_turn": False,
        "game_over": game.is_game_over(),
    }

    # Add winner info when hand is over (and a hand was actually played)
    if game.state.value == "game_over":
        if game.hand_number > 0:
            winner_info = game.get_winner_info()
            state["winner_info"] = winner_info
            state["ai_player"]["hole_cards"] = serialize_cards(
                game.ai_player.hole_cards
            )
        else:
            state["winner_info"] = None
    else:
        state["winner_info"] = None
        # Determine if it's human's turn
        state["is_human_turn"] = _is_human_turn(game)

    return state


def _is_human_turn(game) -> bool:
    """Check if it's the human player's turn to act."""
    br = game.current_betting_round
    if br is None:
        return False
    hp = game.human_player
    if hp.folded or hp.all_in:
        return False

    human_acted = br.players_acted[0]
    ai_acted = br.players_acted[1]
    human_contribution = br.player_contributions[0]
    ai_contribution = br.player_contributions[1]
    current_bet = br.current_bet

    if not human_acted and not ai_acted:
        active_index = game.get_active_player_index()
    elif not human_acted:
        active_index = 0
    elif not ai_acted:
        active_index = 1
    else:
        if human_contribution < ai_contribution:
            active_index = 0
        elif ai_contribution < human_contribution:
            active_index = 1
        elif current_bet > 0 and br.last_to_act is not None:
            active_index = 1 if br.last_to_act == 0 else 0
        else:
            human_short = current_bet > 0 and human_contribution < current_bet
            ai_short = current_bet > 0 and ai_contribution < current_bet
            if human_short:
                active_index = 0
            elif ai_short:
                active_index = 1
            else:
                return False

    return active_index == 0
