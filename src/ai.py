from typing import List, Optional
from card import Card
from betting import BettingAction
from handEvaluator import HandEvaluator, HandRank
import random


class AIPlayer:
    def __init__(self, player_instance, difficulty: str = "medium"):
        """
        Initialize AI player.
        difficulty: "easy", "medium", "hard"
        """
        self.player = player_instance
        self.difficulty = difficulty

    def get_action(
        self, amount_to_call: int, current_bet: int,
        min_raise: int, community_cards: List[Card],
        pot_size: int, other_player_stack: int = 0,
        other_player_contribution: int = 0
    ) -> tuple[BettingAction, Optional[int]]:
        """
        Determine AI action based on hand strength and game state.
        Returns: (BettingAction, raise_amount or None)
        other_player_stack/contribution: used to cap raises at what opponent can match
        """
        # Evaluate hand strength
        all_cards = self.player.hole_cards + community_cards
        if len(all_cards) < 2:
            # Pre-flop, only hole cards
            hand_strength = self._evaluate_preflop_hand()
        else:
            hand_strength = self._evaluate_hand_strength(all_cards)

        # Calculate pot odds
        pot_odds = self._calculate_pot_odds(amount_to_call, pot_size)
        max_raise_to = other_player_stack + other_player_contribution

        # Make decision based on difficulty and hand strength
        if self.difficulty == "easy":
            return self._easy_strategy(
                hand_strength, amount_to_call, current_bet, min_raise,
                max_raise_to
            )
        elif self.difficulty == "medium":
            return self._medium_strategy(
                hand_strength, amount_to_call, pot_odds, current_bet, min_raise,
                max_raise_to
            )
        else:  # hard
            return self._hard_strategy(
                hand_strength, amount_to_call, pot_odds,
                current_bet, min_raise, _pot_size=pot_size,
                max_raise_to=max_raise_to
            )

    def _evaluate_preflop_hand(self) -> float:
        """Evaluate hand strength pre-flop (0.0 to 1.0)"""
        cards = self.player.hole_cards
        if len(cards) != 2:
            return 0.0

        rank1 = cards[0].rank.value
        rank2 = cards[1].rank.value
        is_pair = rank1 == rank2
        is_suited = cards[0].suit == cards[1].suit
        high_card = max(rank1, rank2)
        low_card = min(rank1, rank2)

        # Premium hands
        if is_pair:
            if high_card >= 10:  # 10s or better
                return 0.9
            elif high_card >= 7:  # 7s-9s
                return 0.6
            else:
                return 0.4
        else:
            # High cards
            if high_card == 14:  # Ace
                if low_card >= 10:
                    return 0.85
                elif low_card >= 6:
                    return 0.7 if is_suited else 0.6
                else:
                    return 0.5 if is_suited else 0.4
            elif high_card == 13:  # King
                if low_card >= 10:
                    return 0.7
                elif low_card >= 9:
                    return 0.55 if is_suited else 0.45
                else:
                    return 0.4 if is_suited else 0.3
            elif high_card >= 10:
                if low_card == high_card - 1:
                    return 0.5 if is_suited else 0.4
                else:
                    return 0.35 if is_suited else 0.25
            else:
                return 0.2

    def _evaluate_hand_strength(self, cards: List[Card]) -> float:
        """Evaluate hand strength post-flop (0.0 to 1.0)"""
        if len(cards) < 5:
            # Not enough cards, use pre-flop evaluation
            return self._evaluate_preflop_hand()

        rank, _ = HandEvaluator.evaluate_hand(cards)

        # Convert hand rank to strength (0.0 to 1.0)
        strength_map = {
            HandRank.HIGH_CARD: 0.1,
            HandRank.PAIR: 0.3,
            HandRank.TWO_PAIR: 0.5,
            HandRank.THREE_OF_A_KIND: 0.65,
            HandRank.STRAIGHT: 0.75,
            HandRank.FLUSH: 0.8,
            HandRank.FULL_HOUSE: 0.9,
            HandRank.FOUR_OF_A_KIND: 0.95,
            HandRank.STRAIGHT_FLUSH: 0.98,
            HandRank.ROYAL_FLUSH: 1.0
        }

        base_strength = strength_map.get(rank, 0.1)

        # Add some randomness for realism
        return min(1.0, base_strength + random.uniform(-0.05, 0.05))

    def _calculate_pot_odds(self, amount_to_call: int, pot_size: int) -> float:
        """Calculate pot odds as a ratio"""
        if amount_to_call == 0:
            return float('inf')
        if pot_size == 0:
            return 0.0
        return pot_size / amount_to_call

    def _safe_raise_amount(
        self, computed: int, min_raise: int,
        current_bet: int, amount_to_call: int,
        max_raise_to: int = 999999
    ) -> Optional[int]:
        """Return a valid raise amount (total bet), or None if cannot raise."""
        contribution = current_bet - amount_to_call
        max_total = min(
            self.player.chips + contribution,
            max_raise_to  # Cap at what opponent can match
        )
        if min_raise > max_total:
            return None
        return max(min_raise, min(computed, max_total))

    def _easy_strategy(
        self, hand_strength: float, amount_to_call: int,
        current_bet: int, min_raise: int,
        max_raise_to: int = 999999
    ) -> tuple[BettingAction, Optional[int]]:
        """Easy AI strategy - very conservative"""
        if hand_strength < 0.4:
            if amount_to_call == 0:
                return BettingAction.CHECK, None
            return BettingAction.FOLD, None
        elif hand_strength < 0.6:
            if amount_to_call == 0:
                return BettingAction.CHECK, None
            if amount_to_call > self.player.chips * 0.1:  # Don't call big bets
                return BettingAction.FOLD, None
            return BettingAction.CALL, None
        else:
            if amount_to_call == 0:
                if hand_strength > 0.7 and random.random() < 0.3:
                    raise_amount = self._safe_raise_amount(
                        min(min_raise, int(self.player.chips * 0.2)),
                        min_raise, current_bet, amount_to_call, max_raise_to
                    )
                    if raise_amount is not None:
                        return BettingAction.RAISE, raise_amount
                return BettingAction.CHECK, None
            if hand_strength > 0.8 and random.random() < 0.4:
                raise_amount = self._safe_raise_amount(
                    min(min_raise * 2, int(self.player.chips * 0.3)),
                    min_raise, current_bet, amount_to_call, max_raise_to
                )
                if raise_amount is not None:
                    return BettingAction.RAISE, raise_amount
            return BettingAction.CALL, None

    def _medium_strategy(
        self, hand_strength: float, amount_to_call: int,
        pot_odds: float, current_bet: int, min_raise: int,
        max_raise_to: int = 999999
    ) -> tuple[BettingAction, Optional[int]]:
        """Medium AI strategy - balanced"""
        if hand_strength < 0.3:
            if amount_to_call == 0:
                return BettingAction.CHECK, None
            # Fold if pot odds are bad
            if pot_odds < 3 and amount_to_call > self.player.chips * 0.15:
                return BettingAction.FOLD, None
            return BettingAction.CALL, None
        elif hand_strength < 0.5:
            if amount_to_call == 0:
                if random.random() < 0.2:  # Occasional bluff
                    raise_amount = self._safe_raise_amount(
                        min(min_raise, int(self.player.chips * 0.15)),
                        min_raise, current_bet, amount_to_call, max_raise_to
                    )
                    if raise_amount is not None:
                        return BettingAction.RAISE, raise_amount
                return BettingAction.CHECK, None
            if pot_odds > 4:
                return BettingAction.CALL, None
            if amount_to_call > self.player.chips * 0.2:
                return BettingAction.FOLD, None
            return BettingAction.CALL, None
        elif hand_strength < 0.7:
            if amount_to_call == 0:
                if random.random() < 0.4:
                    raise_amount = self._safe_raise_amount(
                        min(min_raise, int(self.player.chips * 0.25)),
                        min_raise, current_bet, amount_to_call, max_raise_to
                    )
                    if raise_amount is not None:
                        return BettingAction.RAISE, raise_amount
                return BettingAction.CHECK, None
            if hand_strength > 0.6 and random.random() < 0.3:
                raise_amount = self._safe_raise_amount(
                    min(min_raise * 2, int(self.player.chips * 0.3)),
                    min_raise, current_bet, amount_to_call, max_raise_to
                )
                if raise_amount is not None:
                    return BettingAction.RAISE, raise_amount
            return BettingAction.CALL, None
        else:  # Strong hand
            if amount_to_call == 0:
                if random.random() < 0.6:
                    raise_amount = self._safe_raise_amount(
                        min(min_raise * 2, int(self.player.chips * 0.4)),
                        min_raise, current_bet, amount_to_call, max_raise_to
                    )
                    if raise_amount is not None:
                        return BettingAction.RAISE, raise_amount
                return BettingAction.CHECK, None
            if random.random() < 0.5:
                raise_amount = self._safe_raise_amount(
                    min(min_raise * 2, int(self.player.chips * 0.5)),
                    min_raise, current_bet, amount_to_call, max_raise_to
                )
                if raise_amount is not None:
                    return BettingAction.RAISE, raise_amount
            return BettingAction.CALL, None

    def _hard_strategy(
        self, hand_strength: float, amount_to_call: int,
        pot_odds: float, current_bet: int, min_raise: int,
        _pot_size: int = 0,  # Reserved for future implied-odds logic
        max_raise_to: int = 999999
    ) -> tuple[BettingAction, Optional[int]]:
        """Hard AI strategy - more aggressive and strategic"""
        # More sophisticated pot odds and implied odds consideration
        effective_odds = pot_odds if pot_odds != float('inf') else 10

        if hand_strength < 0.25:
            if amount_to_call == 0:
                # Bluff occasionally
                if random.random() < 0.15:
                    raise_amount = self._safe_raise_amount(
                        min(min_raise, int(self.player.chips * 0.2)),
                        min_raise, current_bet, amount_to_call, max_raise_to
                    )
                    if raise_amount is not None:
                        return BettingAction.RAISE, raise_amount
                return BettingAction.CHECK, None
            if effective_odds < 2 or amount_to_call > self.player.chips * 0.2:
                return BettingAction.FOLD, None
            return BettingAction.CALL, None
        elif hand_strength < 0.5:
            if amount_to_call == 0:
                if random.random() < 0.3:
                    raise_amount = self._safe_raise_amount(
                        min(min_raise, int(self.player.chips * 0.2)),
                        min_raise, current_bet, amount_to_call, max_raise_to
                    )
                    if raise_amount is not None:
                        return BettingAction.RAISE, raise_amount
                return BettingAction.CHECK, None
            if effective_odds > 3:
                return BettingAction.CALL, None
            if amount_to_call > self.player.chips * 0.25:
                return BettingAction.FOLD, None
            return BettingAction.CALL, None
        elif hand_strength < 0.7:
            if amount_to_call == 0:
                if random.random() < 0.5:
                    raise_amount = self._safe_raise_amount(
                        min(min_raise * 2, int(self.player.chips * 0.3)),
                        min_raise, current_bet, amount_to_call, max_raise_to
                    )
                    if raise_amount is not None:
                        return BettingAction.RAISE, raise_amount
                return BettingAction.CHECK, None
            if hand_strength > 0.6 and random.random() < 0.4:
                raise_amount = self._safe_raise_amount(
                    min(min_raise * 2, int(self.player.chips * 0.35)),
                    min_raise, current_bet, amount_to_call, max_raise_to
                )
                if raise_amount is not None:
                    return BettingAction.RAISE, raise_amount
            return BettingAction.CALL, None
        else:  # Very strong hand
            if amount_to_call == 0:
                if random.random() < 0.7:
                    raise_amount = self._safe_raise_amount(
                        min(min_raise * 2, int(self.player.chips * 0.5)),
                        min_raise, current_bet, amount_to_call, max_raise_to
                    )
                    if raise_amount is not None:
                        return BettingAction.RAISE, raise_amount
                return BettingAction.CHECK, None
            if random.random() < 0.6:
                raise_amount = self._safe_raise_amount(
                    min(min_raise * 3, int(self.player.chips * 0.6)),
                    min_raise, current_bet, amount_to_call, max_raise_to
                )
                if raise_amount is not None:
                    return BettingAction.RAISE, raise_amount
            return BettingAction.CALL, None
