from typing import List, Tuple
from collections import Counter
from enum import Enum
from card import Card


class HandRank(Enum):
    HIGH_CARD = 1
    PAIR = 2
    TWO_PAIR = 3
    THREE_OF_A_KIND = 4
    STRAIGHT = 5
    FLUSH = 6
    FULL_HOUSE = 7
    FOUR_OF_A_KIND = 8
    STRAIGHT_FLUSH = 9
    ROYAL_FLUSH = 10


class HandEvaluator:
    @staticmethod
    def evaluate_hand(cards: List[Card]) -> Tuple[HandRank, List[int]]:
        """
        Evaluate a poker hand and return its rank and tiebreaker values.
        Returns: (HandRank, tiebreaker_values)
        """
        if len(cards) < 5:
            raise ValueError("Need at least 5 cards to evaluate a hand")

        # Get all possible 5-card combinations from the 7 cards
        best_rank = HandRank.HIGH_CARD
        best_tiebreakers = []

        # Generate all combinations of 5 cards from the available cards
        from itertools import combinations
        for combo in combinations(cards, 5):
            rank, tiebreakers = HandEvaluator._evaluate_five_cards(
                list(combo))
            if (rank.value > best_rank.value or
                    (rank == best_rank and tiebreakers > best_tiebreakers)):
                best_rank = rank
                best_tiebreakers = tiebreakers

        return best_rank, best_tiebreakers

    @staticmethod
    def _evaluate_five_cards(cards: List[Card]) -> Tuple[HandRank, List[int]]:
        """Evaluate exactly 5 cards"""
        ranks = [card.rank.value for card in cards]
        suits = [card.suit for card in cards]
        rank_counts = Counter(ranks)
        suit_counts = Counter(suits)

        # Sort ranks by frequency then value
        sorted_ranks = sorted(rank_counts.items(),
                              key=lambda x: (x[1], x[0]), reverse=True)

        is_flush = len(suit_counts) == 1
        is_straight = HandEvaluator._is_straight(ranks)

        # Royal Flush
        if is_flush and is_straight and min(ranks) == 10:
            return HandRank.ROYAL_FLUSH, []

        # Straight Flush
        if is_flush and is_straight:
            # Handle A-2-3-4-5 straight (wheel)
            if 14 in ranks and 2 in ranks:
                return HandRank.STRAIGHT_FLUSH, [5]
            return HandRank.STRAIGHT_FLUSH, [max(ranks)]

        # Four of a Kind
        if sorted_ranks[0][1] == 4:
            return HandRank.FOUR_OF_A_KIND, [
                sorted_ranks[0][0], sorted_ranks[1][0]
            ]

        # Full House
        if sorted_ranks[0][1] == 3 and sorted_ranks[1][1] == 2:
            return HandRank.FULL_HOUSE, [
                sorted_ranks[0][0], sorted_ranks[1][0]
            ]

        # Flush
        if is_flush:
            return HandRank.FLUSH, sorted(ranks, reverse=True)

        # Straight
        if is_straight:
            # Handle A-2-3-4-5 straight (wheel)
            if 14 in ranks and 2 in ranks:
                return HandRank.STRAIGHT, [5]
            return HandRank.STRAIGHT, [max(ranks)]

        # Three of a Kind
        if sorted_ranks[0][1] == 3:
            kickers = sorted([r[0] for r in sorted_ranks[1:]], reverse=True)
            return HandRank.THREE_OF_A_KIND, [sorted_ranks[0][0]] + kickers

        # Two Pair
        if sorted_ranks[0][1] == 2 and sorted_ranks[1][1] == 2:
            pairs = sorted(
                [sorted_ranks[0][0], sorted_ranks[1][0]], reverse=True
            )
            kicker = sorted_ranks[2][0]
            return HandRank.TWO_PAIR, pairs + [kicker]

        # Pair
        if sorted_ranks[0][1] == 2:
            pair_rank = sorted_ranks[0][0]
            kickers = sorted([r[0] for r in sorted_ranks[1:]], reverse=True)
            return HandRank.PAIR, [pair_rank] + kickers

        # High Card
        return HandRank.HIGH_CARD, sorted(ranks, reverse=True)

    @staticmethod
    def _is_straight(ranks: List[int]) -> bool:
        """Check if ranks form a straight"""
        unique_ranks = sorted(set(ranks))

        # Check for regular straight
        if len(unique_ranks) == 5:
            if unique_ranks[-1] - unique_ranks[0] == 4:
                return True

        # Check for A-2-3-4-5 straight (wheel)
        if set(unique_ranks) == {14, 2, 3, 4, 5}:
            return True

        return False

    @staticmethod
    def compare_hands(hand1: List[Card], hand2: List[Card]) -> int:
        """
        Compare two hands.
        Returns: 1 if hand1 wins, -1 if hand2 wins, 0 if tie
        """
        rank1, tiebreakers1 = HandEvaluator.evaluate_hand(hand1)
        rank2, tiebreakers2 = HandEvaluator.evaluate_hand(hand2)

        if rank1.value > rank2.value:
            return 1
        elif rank1.value < rank2.value:
            return -1
        else:
            # Same rank, compare tiebreakers
            for t1, t2 in zip(tiebreakers1, tiebreakers2):
                if t1 > t2:
                    return 1
                elif t1 < t2:
                    return -1
            return 0

    @staticmethod
    def get_hand_name(rank: HandRank) -> str:
        """Get human-readable name for hand rank"""
        names = {
            HandRank.HIGH_CARD: "High Card",
            HandRank.PAIR: "Pair",
            HandRank.TWO_PAIR: "Two Pair",
            HandRank.THREE_OF_A_KIND: "Three of a Kind",
            HandRank.STRAIGHT: "Straight",
            HandRank.FLUSH: "Flush",
            HandRank.FULL_HOUSE: "Full House",
            HandRank.FOUR_OF_A_KIND: "Four of a Kind",
            HandRank.STRAIGHT_FLUSH: "Straight Flush",
            HandRank.ROYAL_FLUSH: "Royal Flush"
        }
        return names[rank]
