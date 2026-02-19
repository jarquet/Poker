from typing import List, Optional, Tuple
from enum import Enum


class BettingAction(Enum):
    FOLD = "fold"
    CHECK = "check"
    CALL = "call"
    RAISE = "raise"
    ALL_IN = "all_in"


class BettingRound:
    def __init__(self, small_blind: int, big_blind: int):
        self.small_blind = small_blind
        self.big_blind = big_blind
        self.pot = 0
        self.current_bet = 0  # Start at 0, will be set by blinds or first bet
        self.player_bets: List[int] = [0, 0]  # Track bets for each player this round
        self.player_contributions: List[int] = [0, 0]  # Total contributions this round
        self.folded: List[bool] = [False, False]
        self.all_in: List[bool] = [False, False]
        self.round_complete = False
        self.last_to_act: Optional[int] = None  # Track who last raised
        self.players_acted: List[bool] = [False, False]  # Track if each player has acted this round

    def post_blinds(self, player_stacks: List[int], dealer_index: int):
        """Post small and big blinds"""
        small_blind_index = (dealer_index + 1) % 2
        big_blind_index = (dealer_index + 2) % 2

        # Post small blind
        small_blind_amount = min(self.small_blind, player_stacks[small_blind_index])
        self.player_bets[small_blind_index] = small_blind_amount
        self.player_contributions[small_blind_index] = small_blind_amount
        player_stacks[small_blind_index] -= small_blind_amount
        self.pot += small_blind_amount

        # Post big blind
        big_blind_amount = min(self.big_blind, player_stacks[big_blind_index])
        self.player_bets[big_blind_index] = big_blind_amount
        self.player_contributions[big_blind_index] = big_blind_amount
        player_stacks[big_blind_index] -= big_blind_amount
        self.pot += big_blind_amount
        self.current_bet = big_blind_amount

        if player_stacks[small_blind_index] == 0:
            self.all_in[small_blind_index] = True
        if player_stacks[big_blind_index] == 0:
            self.all_in[big_blind_index] = True

    def make_action(self, player_index: int, action: BettingAction, 
                   amount: Optional[int], player_stack: int,
                   other_player_stack: Optional[int] = None) -> Tuple[bool, str, int]:
        """
        Make a betting action.
        Returns: (success, message, new_stack)
        other_player_stack: Stack of the other player (for validation)
        """
        if self.round_complete:
            return False, "Betting round is already complete", player_stack

        if self.folded[player_index]:
            return False, "Player has already folded", player_stack

        if self.all_in[player_index]:
            return False, "Player is already all-in", player_stack

        # Calculate amount needed to call
        amount_to_call = self.current_bet - self.player_contributions[player_index]

        if action == BettingAction.FOLD:
            self.folded[player_index] = True
            self.round_complete = True
            return True, "Player folded", player_stack

        elif action == BettingAction.CHECK:
            if amount_to_call > 0:
                return False, "Cannot check - must call or fold", player_stack
            # Mark that this player has acted
            self.players_acted[player_index] = True
            # Check if round is complete (both players have acted and checked)
            if self._is_round_complete():
                self.round_complete = True
            return True, "Checked", player_stack

        elif action == BettingAction.CALL:
            if amount_to_call == 0:
                return False, "Nothing to call - can check instead", player_stack
            
            call_amount = min(amount_to_call, player_stack)
            self.player_contributions[player_index] += call_amount
            new_stack = player_stack - call_amount
            self.pot += call_amount
            self.players_acted[player_index] = True

            if new_stack == 0:
                self.all_in[player_index] = True

            # If this player called and matched the bet, check if round is complete
            if self.player_contributions[player_index] == self.current_bet:
                if self._is_round_complete():
                    self.round_complete = True
            return True, f"Called {call_amount}", new_stack

        elif action == BettingAction.RAISE:
            if amount is None:
                return False, "Raise amount required", player_stack
            
            min_raise = self.current_bet * 2 if self.current_bet > 0 else self.big_blind * 2
            if amount < min_raise:
                return False, f"Raise must be at least {min_raise} (double the current bet)", player_stack
            
            if amount > player_stack + self.player_contributions[player_index]:
                return False, "Cannot raise more than available chips", player_stack

            # Calculate total needed (call + raise)
            total_needed = amount - self.player_contributions[player_index]
            if total_needed > player_stack:
                return False, "Insufficient chips for this raise", player_stack
            
            # Ensure the bet doesn't exceed what the other player can match
            if other_player_stack is not None:
                other_index = 1 - player_index
                other_contribution = self.player_contributions[other_index]
                max_other_can_match = other_player_stack + other_contribution
                # The bet amount should not exceed what the other player can match
                if amount > max_other_can_match:
                    max_bet = max_other_can_match
                    return False, f"Cannot raise to more than {max_bet} (other player's stack limit)", player_stack

            # Ensure current_bet doesn't exceed minimum stack
            if other_player_stack is not None:
                other_index = 1 - player_index
                other_contribution = self.player_contributions[other_index]
                max_other_can_match = other_player_stack + other_contribution
                # Cap the bet at what the other player can match
                amount = min(amount, max_other_can_match)
                # Recalculate total_needed with capped amount
                total_needed = amount - self.player_contributions[player_index]
            
            # Make the raise
            self.player_contributions[player_index] = amount
            new_stack = player_stack - total_needed
            self.pot += total_needed
            self.current_bet = amount
            self.last_to_act = player_index
            self.players_acted[player_index] = True

            if new_stack == 0:
                self.all_in[player_index] = True

            # Reset the other player's action status (they need to act again)
            other_index = 1 - player_index
            if not self.folded[other_index] and not self.all_in[other_index]:
                self.round_complete = False
                self.players_acted[other_index] = False  # They need to act again

            return True, f"Raised to {amount}", new_stack

        elif action == BettingAction.ALL_IN:
            all_in_amount = player_stack
            if all_in_amount == 0:
                return False, "No chips to go all-in with", player_stack

            # Calculate the effective all-in amount: min of player's chips and opponent's chips
            effective_all_in = all_in_amount
            if other_player_stack is not None:
                other_index = 1 - player_index
                other_contribution = self.player_contributions[other_index]
                # The effective all-in is the minimum of:
                # - Player's remaining chips
                # - Opponent's remaining chips + what they've already contributed
                max_opponent_total = other_player_stack + other_contribution
                player_total_if_all_in = self.player_contributions[player_index] + all_in_amount
                # Effective bet is the minimum of both players' total possible contributions
                effective_total = min(player_total_if_all_in, max_opponent_total)
                # Calculate how much the player actually needs to bet
                effective_all_in = effective_total - self.player_contributions[player_index]
            
            # Player goes all-in (bets the effective amount)
            total_contribution = self.player_contributions[player_index] + effective_all_in
            self.player_contributions[player_index] = total_contribution
            self.pot += effective_all_in
            new_stack = player_stack - effective_all_in
            # Mark as all-in only if they bet all their chips
            if new_stack == 0:
                self.all_in[player_index] = True
            self.players_acted[player_index] = True

            # Update current_bet to the effective bet (minimum of both stacks)
            if total_contribution > self.current_bet:
                self.current_bet = total_contribution
                self.last_to_act = player_index
                # Other player needs to act
                other_index = 1 - player_index
                if not self.folded[other_index] and not self.all_in[other_index]:
                    self.round_complete = False
                    self.players_acted[other_index] = False  # They need to act again
            else:
                # All-in but didn't raise, check if round is complete
                if self._is_round_complete():
                    self.round_complete = True

            return True, f"Went all-in with {effective_all_in}", new_stack

        return False, "Invalid action", player_stack

    def _is_round_complete(self) -> bool:
        """Check if betting round is complete"""
        # Round is complete if:
        # 1. Someone folded
        if any(self.folded):
            return True

        # Special case: if both are all-in, round is complete regardless
        if all(self.all_in):
            return True

        # If one player is all-in, round is complete when the other player has acted
        # and matched the all-in bet (or checked if no bet to call)
        if any(self.all_in):
            all_in_index = 0 if self.all_in[0] else 1
            other_index = 1 - all_in_index
            # If the other player has acted and matched the bet, round is complete
            if self.players_acted[other_index]:
                # Check if contributions match or if other player checked
                if (self.player_contributions[0] == self.player_contributions[1] or
                    (self.current_bet == 0 and
                     self.player_contributions[other_index] ==
                     self.player_contributions[all_in_index])):
                    return True

        # Both players have contributed the same amount
        if self.player_contributions[0] == self.player_contributions[1]:
            # If both are all-in, round is complete (already checked above)
            # If last to act was set and both have matched, round is complete
            if self.last_to_act is not None:
                # Both have matched the raise, round is complete
                return True
            # If both have acted and contributions match (both checked or both called)
            # For checking: current_bet must be 0 and both have acted
            # For calling: current_bet must equal contributions and both have acted
            if all(self.players_acted):
                if self.current_bet == 0:
                    # Both checked - round is complete
                    return True
                elif self.current_bet == self.player_contributions[0]:
                    # Both called the same bet - round is complete
                    return True

        return False

    def get_amount_to_call(self, player_index: int) -> int:
        """Get the amount a player needs to call"""
        return max(0, self.current_bet - self.player_contributions[player_index])

    def reset_for_new_round(self):
        """Reset for a new betting round (called when starting flop/turn/river)"""
        self.current_bet = 0
        self.player_bets = [0, 0]
        self.player_contributions = [0, 0]
        self.round_complete = False
        self.last_to_act = None
        self.players_acted = [False, False]  # Reset action tracking
        # Note: folded and all_in states persist across rounds

